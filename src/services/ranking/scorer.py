"""Two-stage ML pipeline scorer for arXiv papers.

Replaces the old PaperScorer with a two-stage cascade:
  Stage 1: XGBoost recall engine (offline features only)
  Stage 2: XGBoost precision engine (offline + LLM citation features)

Pre-trained models are loaded from src/services/ranking/models/*.pkl
"""

import logging
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder

from src.config import get_settings
from src.services.ranking.features import add_offline_paper_features
from src.services.ranking.llm_scorer import (
    CITE_FLAG_KEYS,
    CITE_SCORE_KEYS,
    score_texts_cite,
)

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).resolve().parent / "models"


def _load_pkl(name: str):
    path = MODEL_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found: {path}\n"
            "Run the export_models.py cell in the notebook first."
        )
    with open(path, "rb") as f:
        return pickle.load(f)


class TwoStageScorer:
    """Two-stage ML pipeline for paper ranking.

    Usage:
        scorer = TwoStageScorer()
        results_df = scorer.rank_papers(papers_df)
    """

    def __init__(self):
        self.settings = get_settings()
        self._load_models()

    def _load_models(self):
        """Load all pre-trained models and preprocessors."""
        logger.info("Loading two-stage pipeline models...")

        # Stage 1
        self.recall_clf = _load_pkl("stage1_recall_model.pkl")
        s1_config = _load_pkl("stage1_config.pkl")
        self.recall_threshold = s1_config["threshold"]

        # Preprocessing
        preproc = _load_pkl("preprocessing.pkl")
        self.num_imputer = preproc["num_imputer"]
        self.ohe: OneHotEncoder = preproc["ohe"]
        self.col_names: list[str] = preproc["col_names"]
        self.num_cols: list[str] = preproc["num_cols"]
        self.drop_features: set[str] = preproc["drop_features"]

        # Stage 2
        self.precision_clf = _load_pkl("stage2_precision_model.pkl")
        s2_config = _load_pkl("stage2_config.pkl")
        self.ohe_tier: OneHotEncoder = s2_config["ohe_tier"]
        self.s2_col_names: list[str] = s2_config["s2_col_names"]
        self.cite_score_keys: list[str] = s2_config["cite_score_keys"]
        self.cite_flag_keys: list[str] = s2_config["cite_flag_keys"]

        logger.info(
            f"Models loaded. Recall threshold: {self.recall_threshold:.4f}, "
            f"Stage 1 features: {len(self.col_names)}, "
            f"Stage 2 features: {len(self.s2_col_names)}"
        )

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Run feature engineering + imputation + OHE + dedup.

        Returns the final feature matrix ready for Stage 1 inference.
        """
        # Feature engineering
        feat_df = add_offline_paper_features(
            df,
            title_col="title",
            abstract_col="abstract",
            authors_col="authors",
            primary_cat_col="primary_category",
            all_cats_col="all_categories",
            published_at_col="published_at",
            author_sep="|",
        )

        # Separate numerical and categorical
        cat_cols = (
            ["primary_category"]
            if "primary_category" in feat_df.columns
            else []
        )

        # Numerical imputation
        num_cols_present = [c for c in self.num_cols if c in feat_df.columns]
        missing_num = set(self.num_cols) - set(num_cols_present)
        if missing_num:
            logger.warning(f"Missing numerical features (will be imputed as 0): {missing_num}")
            for c in missing_num:
                feat_df[c] = 0

        X_num = self.num_imputer.transform(
            feat_df[self.num_cols].values
        ).astype(np.float32)

        # Categorical OHE
        if cat_cols:
            from sklearn.impute import SimpleImputer
            cat_imputer = SimpleImputer(strategy="most_frequent")
            X_cat_raw = cat_imputer.fit_transform(feat_df[cat_cols])
            X_cat = self.ohe.transform(X_cat_raw).astype(np.float32)
        else:
            X_cat = np.zeros((len(feat_df), 0), np.float32)

        # Combine
        ohe_col_names = (
            list(self.ohe.get_feature_names_out(cat_cols)) if cat_cols else []
        )
        all_col_names = list(self.num_cols) + ohe_col_names

        X_final = np.hstack([X_num, X_cat])

        # Feature deduplication
        keep_idx = [
            i for i, c in enumerate(all_col_names) if c not in self.drop_features
        ]
        X_final = X_final[:, keep_idx]

        return X_final, feat_df

    def run_stage1(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """Stage 1: Feature engineering → XGBoost recall prediction.

        Returns:
            (probs, recalled_mask, feat_df) where:
            - probs: P(interesting) from Stage 1
            - recalled_mask: boolean mask for papers above threshold
            - feat_df: DataFrame with engineered features
        """
        X_final, feat_df = self._prepare_features(df)

        probs = self.recall_clf.predict_proba(X_final)[:, 1]
        recalled_mask = probs >= self.recall_threshold

        n_total = len(df)
        n_recalled = recalled_mask.sum()
        logger.info(
            f"Stage 1: {n_recalled}/{n_total} papers recalled "
            f"({n_recalled / max(1, n_total):.1%}) at threshold {self.recall_threshold:.4f}"
        )

        return probs, recalled_mask, feat_df

    def run_stage2(
        self,
        df: pd.DataFrame,
        feat_df: pd.DataFrame,
        X_recalled: np.ndarray,
        recalled_indices: list[int],
    ) -> tuple[np.ndarray, pd.DataFrame]:
        """Stage 2: LLM citation scoring → XGBoost precision prediction.

        Args:
            df: Original DataFrame (with title/abstract columns).
            feat_df: DataFrame with engineered features (from stage 1).
            X_recalled: Feature matrix for recalled papers only.
            recalled_indices: Indices of recalled papers in the original df.

        Returns:
            (probs, llm_scores_df) where:
            - probs: P(interesting) from Stage 2
            - llm_scores_df: DataFrame with LLM citation scores
        """
        # Prepare texts for LLM scoring
        texts = {}
        for i, idx in enumerate(recalled_indices):
            row = df.iloc[idx]
            title = str(row.get("title", ""))
            abstract = str(row.get("abstract", ""))
            texts[i] = f"Title: {title}\nAbstract: {abstract}"

        # LLM scoring
        api_key = self.settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set — required for Stage 2 LLM scoring")

        logger.info(f"Stage 2: Scoring {len(texts)} recalled papers with LLM...")
        llm_scores_df = score_texts_cite(texts, api_key)

        # Prepare LLM feature matrix
        llm_num_cols = self.cite_score_keys + self.cite_flag_keys
        X_llm = llm_scores_df[llm_num_cols].to_numpy(dtype=np.float32)

        # OHE for citation tier
        X_tier = self.ohe_tier.transform(
            llm_scores_df[["citation_tier"]]
        ).astype(np.float32)

        # Combine: original features + LLM features + tier OHE
        X_s2 = np.hstack([X_recalled, X_llm, X_tier])

        # Predict
        probs = self.precision_clf.predict_proba(X_s2)[:, 1]

        logger.info(
            f"Stage 2 complete. Top prob: {probs.max():.3f}, "
            f"Mean prob: {probs.mean():.3f}"
        )

        return probs, llm_scores_df

    def rank_papers(
        self, df: pd.DataFrame, top_k: int = 20
    ) -> pd.DataFrame:
        """Full two-stage pipeline: FE → Stage 1 → recall filter → LLM → Stage 2 → rank.

        Args:
            df: DataFrame with columns: title, abstract, authors, categories,
                primary_category, all_categories, published_at
            top_k: Number of top papers to assign ranks.

        Returns:
            DataFrame with added columns: stage1_prob, recalled, stage2_prob,
            final_score, rank, and LLM citation scores.
        """
        result = df.copy()

        # Initialize output columns
        result["stage1_prob"] = 0.0
        result["recalled"] = False
        result["stage2_prob"] = np.nan
        result["final_score"] = 0.0
        result["rank"] = np.nan
        for k in CITE_SCORE_KEYS:
            result[k] = np.nan
        result["citation_tier"] = None

        if len(df) == 0:
            return result

        # Stage 1
        s1_probs, recalled_mask, feat_df = self.run_stage1(df)
        result["stage1_prob"] = s1_probs
        result["recalled"] = recalled_mask

        recalled_indices = np.where(recalled_mask)[0].tolist()
        if not recalled_indices:
            logger.warning("Stage 1 recalled 0 papers — nothing to rank.")
            return result

        # Prepare recalled feature matrix (same preprocessing as stage 1)
        X_all, _ = self._prepare_features(df)
        X_recalled = X_all[recalled_mask]

        # Stage 2
        s2_probs, llm_scores_df = self.run_stage2(
            df, feat_df, X_recalled, recalled_indices
        )

        # Write Stage 2 results back
        for i, idx in enumerate(recalled_indices):
            result.iloc[idx, result.columns.get_loc("stage2_prob")] = s2_probs[i]
            result.iloc[idx, result.columns.get_loc("final_score")] = s2_probs[i]
            # LLM sub-scores
            for k in CITE_SCORE_KEYS:
                result.iloc[idx, result.columns.get_loc(k)] = llm_scores_df.iloc[i].get(
                    k, np.nan
                )
            result.iloc[idx, result.columns.get_loc("citation_tier")] = (
                llm_scores_df.iloc[i].get("citation_tier", None)
            )

        # Rank by final_score descending (only recalled papers get ranks)
        recalled_result = result[result["recalled"]].sort_values(
            "final_score", ascending=False
        )
        for rank, (idx, _) in enumerate(recalled_result.head(top_k).iterrows(), 1):
            result.at[idx, "rank"] = rank

        n_ranked = result["rank"].notna().sum()
        logger.info(f"Ranking complete. Top {n_ranked} papers assigned ranks.")

        return result

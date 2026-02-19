"""Offline feature engineering for paper ranking.

Ported from eda/notebooks/two_stage_pipeline.ipynb (Section 2).
Generates ~59 features from paper metadata without requiring any external APIs.
"""

import re

import numpy as np
import pandas as pd


# ── Compiled regexes ──
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?")
_SENT_SPLIT_RE = re.compile(r"[.!?]+\s+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w+\b")


def add_offline_paper_features(
    df: pd.DataFrame,
    *,
    title_col: str = "title",
    abstract_col: str = "abstract",
    authors_col: str = "authors",
    primary_cat_col: str = "primary_category",
    all_cats_col: str = "all_categories",
    published_at_col: str = "published_at",
    author_sep: str = "|",
) -> pd.DataFrame:
    """Add offline-only features for impact prediction.

    Args:
        df: DataFrame with paper metadata columns.
        title_col: Column name for paper title.
        abstract_col: Column name for paper abstract.
        authors_col: Column name for authors (separated by author_sep).
        primary_cat_col: Column name for primary arXiv category.
        all_cats_col: Column name for all categories (pipe-separated).
        published_at_col: Column name for publication timestamp.
        author_sep: Separator for authors string.

    Returns:
        DataFrame with added feature columns.
    """
    out = df.copy()

    def safe_str(s):
        return "" if pd.isna(s) else str(s)

    def words(s):
        return _WORD_RE.findall(s)

    def sentence_count(s):
        s = s.strip()
        return 0 if not s else max(1, len(_SENT_SPLIT_RE.split(s)))

    def keyword_flags(text_lower, patterns):
        return {
            name: int(bool(re.search(pat, text_lower)))
            for name, pat in patterns.items()
        }

    # ── Datetime features ──
    if published_at_col in out.columns:
        dt = pd.to_datetime(out[published_at_col], errors="coerce", utc=True)
        out["pub_hour_utc"] = dt.dt.hour
        out["pub_dow"] = dt.dt.dayofweek
        out["pub_month"] = dt.dt.month
        out["is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype("Int64")

    # ── Category features ──
    if all_cats_col in out.columns:
        cats = out[all_cats_col].fillna("").astype(str)
        out["num_categories"] = cats.apply(
            lambda x: 0
            if x.strip() == ""
            else len([c for c in x.split("|") if c.strip()])
        )
        out["is_cross_listed"] = (out["num_categories"] > 1).astype("Int64")

        def starts_with(prefix):
            return cats.apply(
                lambda x: int(
                    any(
                        c.strip().startswith(prefix)
                        for c in x.split("|")
                        if c.strip()
                    )
                )
            )

        out["has_cs"] = starts_with("cs.")
        out["has_stat"] = starts_with("stat.")
        out["has_math"] = starts_with("math.")
        out["has_eess"] = starts_with("eess.")
        out["has_qbio"] = starts_with("q-bio.")

    if primary_cat_col in out.columns:
        pc = out[primary_cat_col].fillna("").astype(str)
        out["primary_is_cs"] = pc.str.startswith("cs.").astype("Int64")
        out["primary_is_stat"] = pc.str.startswith("stat.").astype("Int64")

    # ── Author features ──
    if authors_col in out.columns:
        auth = out[authors_col].fillna("").astype(str)
        author_lists = auth.apply(
            lambda x: [a.strip() for a in x.split(author_sep) if a.strip()]
        )
        out["num_authors_offline"] = author_lists.apply(len)
        author_name_lens = author_lists.apply(
            lambda xs: [len(a) for a in xs] if xs else []
        )
        out["author_name_len_mean"] = author_name_lens.apply(
            lambda ls: float(np.mean(ls)) if ls else np.nan
        )
        out["author_name_len_max"] = author_name_lens.apply(
            lambda ls: float(np.max(ls)) if ls else np.nan
        )
        out["has_many_authors_ge5"] = (out["num_authors_offline"] >= 5).astype("Int64")
        out["has_many_authors_ge10"] = (out["num_authors_offline"] >= 10).astype(
            "Int64"
        )

    # ── Text features ──
    title = out.get(title_col, "").apply(safe_str)
    abstract = out.get(abstract_col, "").apply(safe_str)
    title_lower = title.str.lower()
    abs_lower = abstract.str.lower()

    out["title_char_len"] = title.str.len()
    out["abstract_char_len"] = abstract.str.len()
    out["title_word_count"] = title.apply(lambda s: len(words(s)))
    out["abstract_word_count"] = abstract.apply(lambda s: len(words(s)))
    out["title_avg_word_len"] = title.apply(
        lambda s: np.mean([len(w) for w in words(s)]) if words(s) else np.nan
    )
    out["abstract_avg_word_len"] = abstract.apply(
        lambda s: np.mean([len(w) for w in words(s)]) if words(s) else np.nan
    )
    out["abstract_sentence_count"] = abstract.apply(sentence_count)
    out["abstract_avg_words_per_sentence"] = out["abstract_word_count"] / out[
        "abstract_sentence_count"
    ].replace(0, np.nan)

    def ratio_of(pattern, s):
        return len(re.findall(pattern, s)) / max(1, len(s)) if s else 0.0

    out["title_digit_ratio"] = title.apply(lambda s: ratio_of(r"\d", s))
    out["abstract_digit_ratio"] = abstract.apply(lambda s: ratio_of(r"\d", s))
    out["title_punct_ratio"] = title.apply(lambda s: ratio_of(r"[^\w\s]", s))
    out["abstract_punct_ratio"] = abstract.apply(lambda s: ratio_of(r"[^\w\s]", s))
    out["abstract_has_url"] = abstract.apply(
        lambda s: int(bool(_URL_RE.search(s)))
    ).astype("Int64")
    out["abstract_has_email"] = abstract.apply(
        lambda s: int(bool(_EMAIL_RE.search(s)))
    ).astype("Int64")
    out["mentions_github"] = abs_lower.str.contains("github.com", regex=False).astype(
        "Int64"
    )
    out["mentions_code"] = abs_lower.str.contains("code", regex=False).astype("Int64")
    out["mentions_dataset"] = abs_lower.str.contains("dataset", regex=False).astype(
        "Int64"
    )
    out["mentions_benchmark"] = abs_lower.str.contains(
        "benchmark", regex=False
    ).astype("Int64")
    out["mentions_arxiv_id"] = abs_lower.str.contains("arxiv", regex=False).astype(
        "Int64"
    )
    out["mentions_doi"] = abs_lower.str.contains("doi", regex=False).astype("Int64")

    # ── Keyword flags ──
    kw_patterns = {
        "is_survey": r"\bsurvey\b|\breview\b",
        "is_benchmark_paper": r"\bbenchmark\b|\bleaderboard\b",
        "is_dataset_paper": r"\bdataset\b|\bcorpus\b",
        "is_system_paper": r"\bsystem\b|\bframework\b|\bplatform\b",
        "has_theory": r"\btheorem\b|\bproof\b|\bconvergence\b",
        "mentions_llm": r"\bllm\b|large language model|language model",
        "mentions_diffusion": r"\bdiffusion\b",
        "mentions_transformer": r"\btransformer\b",
        "mentions_agent": r"\bagent\b|\btool\b|\bplanning\b",
        "mentions_rl": r"\breinforcement learning\b|\brl\b",
        "mentions_multimodal": r"\bmultimodal\b|vision-language|vlm",
        "claims_sota": r"\bsota\b|state[- ]of[- ]the[- ]art",
        "claims_novel": r"\bnovel\b|\bnew\b|\bfirst\b|\bintroduce\b",
        "mentions_open_source": r"open[- ]source|we release|code is available",
        "mentions_experiments": r"\bexperiments?\b|\bwe evaluate\b|\bresults?\b",
    }
    combined_lower = (title_lower + " " + abs_lower).fillna("")
    kw_df = pd.DataFrame(
        combined_lower.apply(lambda s: keyword_flags(s, kw_patterns)).tolist(),
        index=out.index,
    )
    out = pd.concat([out, kw_df], axis=1)

    # ── Derived features ──
    def ttr(s):
        ws = [w.lower() for w in words(s)]
        return len(set(ws)) / len(ws) if ws else np.nan

    out["abstract_ttr"] = abstract.apply(ttr)
    out["log_abstract_word_count"] = np.log1p(out["abstract_word_count"])
    out["log_num_authors"] = np.log1p(out.get("num_authors_offline", 0))

    return out

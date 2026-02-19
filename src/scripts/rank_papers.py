"""Script to rank papers using the two-stage ML pipeline.

Two-stage cascade:
1. Stage 1 (Recall): XGBoost on offline features → filter to ~50% of papers
2. Stage 2 (Precision): LLM citation scoring + XGBoost → rank recalled papers
3. Top-20 papers get assigned ranks for digest generation.

Pre-trained models must exist in src/services/ranking/models/.
Run export_models.py from the notebook to generate them.
"""

import logging
import sys

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.paper import Paper
from src.models.score import PaperScore
from src.services.ranking.scorer import TwoStageScorer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Number of top papers to include in the digest
TOP_K = 20


def get_papers_to_rank(db: Session, limit: int | None = None) -> list[Paper]:
    """Get papers that don't have a score yet."""
    stmt = (
        select(Paper)
        .outerjoin(PaperScore)
        .where(PaperScore.id == None)  # noqa: E711
    )
    if limit:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def papers_to_dataframe(papers: list[Paper]) -> pd.DataFrame:
    """Convert Paper ORM objects to a DataFrame for the ML pipeline.

    The pipeline expects columns: title, abstract, authors, categories,
    primary_category, all_categories, published_at.
    """
    rows = []
    for p in papers:
        # categories is stored as comma-separated, e.g. "cs.AI,cs.LG"
        cats = [c.strip() for c in (p.categories or "").split(",") if c.strip()]
        primary_cat = cats[0] if cats else ""
        all_cats = "|".join(cats)  # Pipeline expects pipe-separated

        # authors stored as comma-separated
        # Convert to pipe-separated for the pipeline
        authors_pipe = "|".join(
            a.strip() for a in (p.authors or "").split(",") if a.strip()
        )

        rows.append({
            "paper_id": p.id,
            "run_id": p.run_id,
            "title": p.title or "",
            "abstract": p.abstract or "",
            "authors": authors_pipe,
            "categories": p.categories or "",
            "primary_category": primary_cat,
            "all_categories": all_cats,
            "published_at": p.published_at,
        })

    return pd.DataFrame(rows)


def save_scores_to_db(db: Session, papers_df: pd.DataFrame, results_df: pd.DataFrame):
    """Save pipeline results as PaperScore entries."""
    from src.services.ranking.llm_scorer import CITE_SCORE_KEYS

    count = 0
    for idx in range(len(results_df)):
        row = results_df.iloc[idx]
        paper_row = papers_df.iloc[idx]

        score_entry = PaperScore(
            paper_id=int(paper_row["paper_id"]),
            run_id=int(paper_row["run_id"]),
            stage1_prob=float(row["stage1_prob"]),
            recalled=bool(row["recalled"]),
            stage2_prob=float(row["stage2_prob"]) if pd.notna(row["stage2_prob"]) else None,
            final_score=float(row["final_score"]),
            rank=int(row["rank"]) if pd.notna(row["rank"]) else None,
            # LLM citation sub-scores
            citation_potential=float(row["citation_potential"]) if pd.notna(row.get("citation_potential")) else None,
            methodological_novelty=float(row["methodological_novelty"]) if pd.notna(row.get("methodological_novelty")) else None,
            practical_utility=float(row["practical_utility"]) if pd.notna(row.get("practical_utility")) else None,
            topic_trendiness=float(row["topic_trendiness"]) if pd.notna(row.get("topic_trendiness")) else None,
            reusability=float(row["reusability"]) if pd.notna(row.get("reusability")) else None,
            community_breadth=float(row["community_breadth"]) if pd.notna(row.get("community_breadth")) else None,
            writing_accessibility=float(row["writing_accessibility"]) if pd.notna(row.get("writing_accessibility")) else None,
            citation_tier=str(row["citation_tier"]) if row.get("citation_tier") else None,
        )
        db.add(score_entry)
        count += 1

    db.commit()
    logger.info(f"Saved {count} PaperScore entries to database.")


def rank_papers():
    """Main ranking execution using two-stage ML pipeline."""
    db = next(get_db())

    try:
        # DROP and RECREATE paper_scores table to handle schema changes
        # (Development only)
        from src.models.base import Base
        from src.database import engine
        from sqlalchemy import text

        logger.info("Dropping paper_scores table to apply schema changes...")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS paper_scores CASCADE"))
            conn.commit()

        logger.info("Recreating paper_scores table...")
        Base.metadata.create_all(bind=engine)

        # Get all unranked papers
        papers = get_papers_to_rank(db)
        logger.info(f"Found {len(papers)} unranked papers.")

        if not papers:
            logger.info("No papers to rank.")
            return

        # Convert to DataFrame
        papers_df = papers_to_dataframe(papers)
        logger.info(f"Prepared DataFrame with {len(papers_df)} papers.")

        # Initialize two-stage scorer
        scorer = TwoStageScorer()

        # Run full pipeline
        results_df = scorer.rank_papers(papers_df, top_k=TOP_K)

        # Summary stats
        n_recalled = results_df["recalled"].sum()
        n_ranked = results_df["rank"].notna().sum()
        logger.info(
            f"Pipeline summary: "
            f"{len(papers_df)} total → "
            f"{n_recalled} recalled ({n_recalled / max(1, len(papers_df)):.1%}) → "
            f"{n_ranked} ranked (top-{TOP_K})"
        )

        # Save to database
        save_scores_to_db(db, papers_df, results_df)

        # Log top papers
        top_papers = results_df[results_df["rank"].notna()].sort_values("rank")
        for _, row in top_papers.iterrows():
            title = papers_df.iloc[row.name]["title"][:60]
            logger.info(
                f"  #{int(row['rank']):2d} | "
                f"S1={row['stage1_prob']:.3f} | "
                f"S2={row['stage2_prob']:.3f} | "
                f"{title}..."
            )

    except Exception as e:
        logger.error(f"Error during ranking: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    rank_papers()

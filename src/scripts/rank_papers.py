"""Script to rank papers in the database.

Steps:
1. Find papers without scores (or force re-rank).
2. Calculate heuristic scores (recency, category).
3. Call LLM for interest/novelty score.
4. Compute final weighted score.
5. Save PaperScore to DB.
"""

import logging
import sys
# Add project root to path if running directly
# import os
# sys.path.append(os.getcwd())

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.paper import Paper
from src.models.score import PaperScore
from src.services.llm.client import LLMClient
from src.services.llm.prompts import INTEREST_SCORE_PROMPT, INTEREST_SCORE_SYSTEM_PROMPT
from src.services.ranking.scorer import PaperScorer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_papers_to_rank(db: Session, limit: int = 20) -> list[Paper]:
    """Get papers that don't have a score yet."""
    # Left join papers with scores where score is null
    stmt = (
        select(Paper)
        .outerjoin(PaperScore)
        .where(PaperScore.id == None)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())

def rank_papers(limit: int = 20):
    """Main ranking execution."""
    db = next(get_db())
    scorer = PaperScorer()
    llm_client = LLMClient()
    
    try:
        # DROP and RECREATE paper_scores table to handle schema change
        # (Development only - effective way to apply model changes)
        from src.models.base import Base
        from src.database import engine
        from sqlalchemy import text
        
        logger.info("Dropping paper_scores table to apply schema changes...")
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS paper_scores CASCADE"))
            conn.commit()
            
        logger.info("Recreating paper_scores table...")
        Base.metadata.create_all(bind=engine)
        
        # Now get papers (since we dropped scores, all papers are unranked)
        papers = get_papers_to_rank(db, limit)
        logger.info(f"Found {len(papers)} unranked papers.")
        
        if not papers:
            logger.info("No papers to rank.")
            return

        for i, paper in enumerate(papers):
            logger.info(f"Ranking paper {i+1}/{len(papers)}: {paper.title[:50]}...")
            
            # 1. Heuristic Scores
            # Parse authors string (comma-separated)
            authors_list = [a.strip() for a in paper.authors.split(",")] if paper.authors else []
            author_score, category_score = scorer.calculate_author_score(authors_list), scorer.calculate_category_score(paper.categories)
            
            # 2. LLM Score
            prompt = INTEREST_SCORE_PROMPT.format(
                title=paper.title,
                abstract=paper.abstract
            )
            
            # Call LLM
            llm_result = llm_client.get_structured_completion(
                prompt=prompt,
                system_prompt=INTEREST_SCORE_SYSTEM_PROMPT
            )
            
            llm_score = float(llm_result.get("score", 0.0))
            llm_reasoning = llm_result.get("reasoning", "No output")
            
            # 3. Final Score
            final_score = scorer.calculate_final_score(author_score, category_score, llm_score)
            
            # 4. Save to DB
            score_entry = PaperScore(
                paper_id=paper.id,
                run_id=paper.run_id,
                author_score=author_score,
                category_score=category_score,
                llm_interest_score=llm_score,
                llm_reasoning=llm_reasoning,
                final_score=final_score
            )
            db.add(score_entry)
            db.commit()
            
            logger.info(f"  Score: {final_score:.2f} (Auth: {author_score:.2f}, Cat: {category_score:.2f}, LLM: {llm_score:.2f})")

        # 5. Update Ranks
        logger.info("Updating ranks...")
        # Get all scores for the run(s) - effectively all scores since we cleared table
        stmt = select(PaperScore).order_by(PaperScore.final_score.desc())
        all_scores = db.scalars(stmt).all()
        
        for i, score in enumerate(all_scores, 1):
            score.rank = i
        
        db.commit()
        logger.info(f"Updated ranks for {len(all_scores)} papers.")


    except Exception as e:
        logger.error(f"Error during ranking: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    rank_papers()

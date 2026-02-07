"""Script to generate the weekly digest.

Top 20 papers from the latest run are summarized and compiled into a Markdown digest.
"""

import sys
import logging
from sqlalchemy import select
from src.database import get_db
from src.models.run import Run
from src.models.score import PaperScore
from src.models.digest import Digest
from src.services.llm.summarizer import DigestSummarizer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_digest():
    """Generate the weekly digest for the latest run."""
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        # 1. Get the latest run with ranked papers
        logger.info("Finding latest run with ranked papers...")
        # We look for a run that has PaperScores
        stmt = select(Run).order_by(Run.created_at.desc()).limit(1)
        run = db.execute(stmt).scalar_one_or_none()
        
        if not run:
            logger.error("No runs found.")
            return
        
        logger.info(f"Processing Run ID: {run.id} (Status: {run.status})")
        
        # 2. Get top 20 ranked papers
        stmt = (
            select(PaperScore)
            .where(PaperScore.run_id == run.id)
            .where(PaperScore.rank != None)
            .order_by(PaperScore.rank.asc())
            .limit(20)
        )
        scores = db.execute(stmt).scalars().all()
        
        if not scores:
            logger.error(f"No ranked papers found for Run {run.id}. Did you run rank_papers.py?")
            return
            
        logger.info(f"Found {len(scores)} ranked papers. Starting summarization...")
        
        summarizer = DigestSummarizer()
        paper_summaries = []
        
        # 3. Summarize each paper
        for i, score in enumerate(scores, 1):
            paper = score.paper
            logger.info(f"[{i}/{len(scores)}] Summarizing: {paper.title[:50]}...")
            summary = summarizer.summarize_paper(paper)
            paper_summaries.append(summary)
            
        # 4. Generate Digest
        logger.info("Compiling digest...")
        digest_md = summarizer.generate_digest_markdown(paper_summaries)
        
        # 5. Save to DB
        logger.info("Saving digest to database...")
        digest_obj = Digest(
            run_id=run.id,
            markdown=digest_md,
            html=None # Placeholder for now
        )
        db.add(digest_obj)
        db.commit()
        
        # 6. Save to local file for review
        output_file = "latest_digest.md"
        with open(output_file, "w") as f:
            f.write(digest_md)
            
        logger.info(f"Digest generated successfully! Saved to DB and {output_file}")
        
    except Exception as e:
        logger.error(f"Digest generation failed: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    generate_digest()

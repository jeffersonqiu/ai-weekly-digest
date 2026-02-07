"""Repository for managing Runs and Papers.

Handles database transactions for storing fetched papers.
"""

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.models.run import Run
from src.schemas.paper import ArxivPaper


class PaperRepository:
    """Handles persistence for papers and run metadata."""

    def __init__(self, db: Session):
        self.db = db

    def create_run(self, start_date: date, end_date: date) -> Run:
        """Create a new run entry."""
        run = Run(
            start_date=start_date,
            end_date=end_date,
            status="running",
            papers_count=0,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def save_papers(self, run_id: int, papers: list[ArxivPaper]) -> int:
        """Save a list of papers to the database for a given run.

        Skips papers that already exist in the database (based on arxiv_id).
        This prevents duplicates if fetch windows overlap.

        Returns:
            int: Number of new papers saved.
        """
        if not papers:
            return 0

        new_papers_count = 0
        
        # We process one by one to safely handle duplicates
        # Bulk operations would be faster but we need to check existence per paper
        # Given we fetch ~100-200 papers, this is acceptable for now.
        
        # Optimization: Get all existing arxiv_ids from the input list in one query
        arxiv_ids = [p.arxiv_id for p in papers]
        stmt = select(Paper.arxiv_id).where(Paper.arxiv_id.in_(arxiv_ids))
        existing_ids = set(self.db.scalars(stmt).all())

        for paper_data in papers:
            if paper_data.arxiv_id in existing_ids:
                continue

            db_paper = Paper(
                run_id=run_id,
                arxiv_id=paper_data.arxiv_id,
                title=paper_data.title,
                abstract=paper_data.abstract,
                authors=paper_data.authors_str,
                categories=paper_data.categories_str,
                pdf_url=paper_data.pdf_url,
                published_at=paper_data.published_at,
            )
            self.db.add(db_paper)
            new_papers_count += 1
            
        self.db.commit()
        return new_papers_count

    def update_run_status(self, run_id: int, status: str, papers_count: int | None = None) -> Run | None:
        """Update the status and paper count of a run.
        
        If status is "completed", sets completed_at to now.
        """
        run = self.db.get(Run, run_id)
        if not run:
            return None

        run.status = status
        if papers_count is not None:
            run.papers_count = papers_count
            
        if status == "completed":
            run.completed_at = datetime.now(timezone.utc)
        elif status == "failed":
            # Just to be explicit, though completed_at could arguably be set for failed too
            pass
            
        self.db.commit()
        self.db.refresh(run)
        return run
    
    def get_run(self, run_id: int) -> Run | None:
        """Get a run by ID."""
        return self.db.get(Run, run_id)

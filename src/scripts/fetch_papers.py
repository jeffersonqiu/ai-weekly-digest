"""Script to fetch new papers from arXiv and store them in the database.

Steps:
1. Initialize database connection
2. Create a new "Run" record
3. Construct search query based on configured categories and date range
4. Fetch papers from arXiv API
5. Save papers to database (skipping duplicates)
6. Update Run status to completed/failed
"""

import logging
import sys
from datetime import date, timedelta

# Add project root to path if running directly
# import os
# sys.path.append(os.getcwd())

from src.config import get_settings
from src.database import get_db
from src.models.run import Run
from src.repositories.paper_repo import PaperRepository
from src.services.arxiv.client import ArxivClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Execute the paper fetching pipeline."""
    settings = get_settings()
    
    # Calculate fetch window
    end_date = date.today()
    start_date = end_date - timedelta(days=settings.arxiv_days_lookback)
    
    logger.info(f"Starting paper fetch for window: {start_date} to {end_date}")
    logger.info(f"Categories: {settings.arxiv_category_list}")

    # Database session
    db = next(get_db())
    repo = PaperRepository(db)
    
    # Create run
    run: Run | None = None
    try:
        run = repo.create_run(start_date=start_date, end_date=end_date)
        logger.info(f"Created Run ID: {run.id}")

        # Initialize client
        client = ArxivClient()

        # Fetch papers
        logger.info("Fetching papers from arXiv...")
        # Note: client uses settings.arxiv_days_lookback by default, which matches start_date calculation above
        search_result = client.fetch_recent_papers()
        
        logger.info(f"Found {len(search_result.papers)} papers from arXiv.")

        # Save to DB
        saved_count = repo.save_papers(run.id, search_result.papers)
        logger.info(f"Saved {saved_count} new papers to database.")
        
        # Update run status
        repo.update_run_status(run.id, "completed", papers_count=saved_count)
        logger.info("Run completed successfully.")

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        if run:
            repo.update_run_status(run.id, "failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

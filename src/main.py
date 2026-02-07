"""Main entry point for the Weekly AI Paper Digest pipeline.

Orchestrates the entire process:
1. Fetch new papers from arXiv.
2. Rank and score papers.
"""

import logging
import sys
from src.scripts.fetch_papers import main as fetch_main
from src.scripts.rank_papers import rank_papers as rank_main
from src.scripts.generate_digest import generate_digest as digest_main

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_pipeline():
    """Run the full digest pipeline."""
    try:
        logger.info("=== Starting Weekly AI Digest Pipeline ===")
        
        # Step 1: Fetch Papers
        logger.info("--- Step 1: Fetching Papers ---")
        fetch_main()
        
        # Step 2: Rank Papers
        logger.info("--- Step 2: Ranking Papers ---")
        rank_main()
        
        # Step 3: Generate Digest
        logger.info("--- Step 3: Generating Digest ---")
        digest_main()
        
        logger.info("=== Pipeline Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_pipeline()

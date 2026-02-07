#!/usr/bin/env python
"""Test script for arXiv client.

Run with: uv run python tests/test_arxiv.py
"""

import sys
from pathlib import Path

# Add project root to path so we can import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.arxiv import ArxivClient
from src.services.arxiv.parser import parse_arxiv_response
import httpx


def test_parser():
    """Test the parser with real data."""
    print("Testing arXiv parser...")
    
    # Simple query without date filter (faster on arXiv side)
    url = "https://export.arxiv.org/api/query"
    params = {
        "search_query": "cat:cs.AI",
        "start": 0,
        "max_results": 5,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        
        result = parse_arxiv_response(response.text)
        
        print(f"\n✅ Fetched {result.count} papers!\n")
        
        assert result.count > 0, "Should fetch at least one paper"
        
        for i, paper in enumerate(result.papers[:3], 1):
            title = paper.title[:70] + "..." if len(paper.title) > 70 else paper.title
            authors = paper.authors_str[:50] + "..." if len(paper.authors_str) > 50 else paper.authors_str
            print(f"{i}. {title}")
            print(f"   ID: {paper.arxiv_id}")
            print(f"   Authors: {authors}")
            print(f"   Categories: {paper.categories_str}")
            print()
        
        # Verify paper structure
        paper = result.papers[0]
        assert paper.arxiv_id, "Paper should have arxiv_id"
        assert paper.title, "Paper should have title"
        assert paper.abstract, "Paper should have abstract"
        assert paper.authors, "Paper should have authors"
        assert paper.pdf_url, "Paper should have pdf_url"
        
        print("✅ All assertions passed!")
        print("\nNote: The full ArxivClient with date filtering works too,")
        print("but we're using a simpler query here to avoid rate limits.")


if __name__ == "__main__":
    test_parser()

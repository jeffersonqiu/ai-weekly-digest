#!/usr/bin/env python
"""Test fetching papers from the last week using the full ArxivClient."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.arxiv import ArxivClient


def test_fetch_recent_papers():
    """Test the full ArxivClient with date filtering."""
    print("Testing ArxivClient.fetch_recent_papers()...")
    print("This fetches papers from the last 7 days.\n")
    
    client = ArxivClient(rate_limit_seconds=5.0)  # Be extra conservative
    
    result = client.fetch_recent_papers(
        categories=["cs.AI"],
        days_back=7,
        max_results=10,
    )
    
    print(f"✅ Fetched {result.count} papers from the last 7 days!\n")
    
    if result.count == 0:
        print("⚠️  No papers found. This could be because:")
        print("   1. Rate limiting (try again in a minute)")
        print("   2. Date filter query timing out")
        print("   3. No papers submitted in this category recently")
        return
    
    for i, paper in enumerate(result.papers[:5], 1):
        title = paper.title[:65] + "..." if len(paper.title) > 65 else paper.title
        print(f"{i}. {title}")
        print(f"   ID: {paper.arxiv_id}")
        print(f"   Published: {paper.published_at.strftime('%Y-%m-%d')}")
        print(f"   Categories: {paper.categories_str}")
        print()
    
    if result.count > 5:
        print(f"... and {result.count - 5} more papers")


if __name__ == "__main__":
    test_fetch_recent_papers()

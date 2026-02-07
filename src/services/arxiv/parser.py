"""Parse arXiv Atom feed responses into Python objects.

arXiv API returns Atom XML format. This module handles:
1. Parsing the XML structure
2. Extracting paper metadata
3. Converting to our Pydantic schema

The feedparser library does the heavy XML lifting.
"""

from datetime import datetime, timezone

import feedparser

from src.schemas.paper import ArxivPaper, ArxivSearchResult


def parse_arxiv_response(feed_content: str) -> ArxivSearchResult:
    """Parse arXiv Atom feed into ArxivSearchResult.

    Args:
        feed_content: Raw XML/Atom feed from arXiv API

    Returns:
        ArxivSearchResult with parsed papers
    """
    feed = feedparser.parse(feed_content)

    # Extract total results from opensearch namespace
    total_results = int(feed.feed.get("opensearch_totalresults", 0))
    start_index = int(feed.feed.get("opensearch_startindex", 0))

    papers = []
    for entry in feed.entries:
        paper = _parse_entry(entry)
        if paper:
            papers.append(paper)

    return ArxivSearchResult(
        papers=papers,
        total_results=total_results,
        start_index=start_index,
    )


def _parse_entry(entry: dict) -> ArxivPaper | None:
    """Parse a single Atom entry into ArxivPaper.

    Args:
        entry: A feedparser entry dict

    Returns:
        ArxivPaper or None if parsing fails
    """
    try:
        # Extract arXiv ID from the entry ID URL
        # Format: http://arxiv.org/abs/2401.12345v1 -> 2401.12345
        arxiv_id = _extract_arxiv_id(entry.get("id", ""))
        if not arxiv_id:
            return None

        # Get title (remove newlines that arXiv sometimes includes)
        title = entry.get("title", "").replace("\n", " ").strip()

        # Get abstract (called 'summary' in Atom feed)
        abstract = entry.get("summary", "").replace("\n", " ").strip()

        # Get authors
        authors = [author.get("name", "") for author in entry.get("authors", [])]

        # Get categories
        categories = [tag.get("term", "") for tag in entry.get("tags", [])]

        # Get PDF link
        pdf_url = _find_pdf_link(entry.get("links", []))

        # Get published date
        published_str = entry.get("published", "")
        published_at = _parse_datetime(published_str)

        return ArxivPaper(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            authors=authors,
            categories=categories,
            pdf_url=pdf_url,
            published_at=published_at,
        )
    except Exception as e:
        # Log error but don't crash - skip malformed entries
        print(f"Warning: Failed to parse arXiv entry: {e}")
        return None


def _extract_arxiv_id(entry_id: str) -> str:
    """Extract arXiv ID from entry URL.

    Examples:
        http://arxiv.org/abs/2401.12345v1 -> 2401.12345
        http://arxiv.org/abs/cs/0001001v1 -> cs/0001001
    """
    if "/abs/" in entry_id:
        # Get everything after /abs/ and remove version suffix
        arxiv_id = entry_id.split("/abs/")[-1]
        # Remove version (v1, v2, etc.)
        if "v" in arxiv_id:
            arxiv_id = arxiv_id.rsplit("v", 1)[0]
        return arxiv_id
    return ""


def _find_pdf_link(links: list[dict]) -> str:
    """Find the PDF link from entry links."""
    for link in links:
        if link.get("type") == "application/pdf":
            return link.get("href", "")
        # Fallback: construct PDF URL from abstract URL
        if link.get("rel") == "alternate":
            abs_url = link.get("href", "")
            if "/abs/" in abs_url:
                return abs_url.replace("/abs/", "/pdf/") + ".pdf"
    return ""


def _parse_datetime(date_str: str) -> datetime:
    """Parse arXiv datetime string to datetime object."""
    if not date_str:
        return datetime.now(timezone.utc)

    # arXiv uses ISO format: 2024-01-15T12:00:00Z
    try:
        # Remove 'Z' and parse
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.now(timezone.utc)

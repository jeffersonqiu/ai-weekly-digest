"""arXiv API client for fetching papers.

arXiv API documentation: https://info.arxiv.org/help/api/index.html

Key points:
- Base URL: http://export.arxiv.org/api/query
- Returns Atom 1.0 feed (XML)
- Rate limit: 1 request per 3 seconds (we'll be conservative)
- Max results per request: 2000 (we'll use smaller batches)
"""

import time
from datetime import date, timedelta

import httpx

from src.config import get_settings
from src.schemas.paper import ArxivSearchResult
from src.services.arxiv.parser import parse_arxiv_response


class ArxivClient:
    """Client for interacting with arXiv API."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self, rate_limit_seconds: float = 3.0):
        """Initialize the client.

        Args:
            rate_limit_seconds: Minimum seconds between requests (arXiv asks for 3s)
        """
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time: float = 0

    def fetch_recent_papers(
        self,
        categories: list[str] | None = None,
        days_back: int | None = None,
        max_results: int | None = None,
    ) -> ArxivSearchResult:
        """Fetch recent papers from specified categories.

        Args:
            categories: List of arXiv categories (e.g., ['cs.AI', 'cs.LG'])
                       Defaults to settings.arxiv_categories
            days_back: How many days back to search
                      Defaults to settings.arxiv_days_lookback
            max_results: Maximum papers to fetch
                        Defaults to settings.arxiv_max_papers

        Returns:
            ArxivSearchResult with fetched papers
        """
        settings = get_settings()
        categories = categories or settings.arxiv_category_list
        days_back = days_back or settings.arxiv_days_lookback
        max_results = max_results or settings.arxiv_max_papers

        # Build date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)

        # Build search query
        query = self._build_query(categories, start_date, end_date)

        # Fetch papers (with pagination if needed)
        return self._fetch_with_pagination(query, max_results)

    def _build_query(
        self, categories: list[str], start_date: date, end_date: date
    ) -> str:
        """Build arXiv API search query.

        Query format per arXiv docs:
        - cat:cs.AI = category is cs.AI
        - OR = logical OR
        - submittedDate:[YYYYMMDDTTTT TO YYYYMMDDTTTT] = date range (TTTT is HHMM in GMT)

        Example from docs:
        au:del_maestro+AND+submittedDate:[202301010600+TO+202401010600]
        """
        # Build category part: (cat:cs.AI OR cat:cs.LG)
        cat_queries = [f"cat:{cat}" for cat in categories]
        cat_part = f"({' OR '.join(cat_queries)})"

        # Build date part - format: YYYYMMDDTTTT where TTTT is HHMM in GMT
        # Use 0600 as start (6am GMT) to catch papers from that day
        start_str = start_date.strftime("%Y%m%d") + "0000"
        end_str = end_date.strftime("%Y%m%d") + "2359"
        date_part = f"submittedDate:[{start_str} TO {end_str}]"

        return f"{cat_part} AND {date_part}"

    def _fetch_with_pagination(
        self, query: str, max_results: int, batch_size: int = 100
    ) -> ArxivSearchResult:
        """Fetch papers with pagination.

        arXiv limits results per request, so we may need multiple requests.
        """
        all_papers = []
        start = 0

        while start < max_results:
            # Calculate how many to fetch this batch
            remaining = max_results - start
            this_batch = min(batch_size, remaining)

            # Fetch batch
            result = self._fetch_batch(query, start=start, max_results=this_batch)

            all_papers.extend(result.papers)

            # Check if we got all available papers
            if len(result.papers) < this_batch:
                break  # No more papers available

            start += this_batch

        return ArxivSearchResult(
            papers=all_papers,
            total_results=len(all_papers),
            start_index=0,
        )

    def _fetch_batch(
        self, query: str, start: int = 0, max_results: int = 100, max_retries: int = 3
    ) -> ArxivSearchResult:
        """Fetch a single batch of papers with retry logic.

        Args:
            query: arXiv search query
            start: Starting index for pagination
            max_results: Max papers in this batch
            max_retries: Maximum retry attempts for rate limiting

        Returns:
            ArxivSearchResult for this batch
        """
        params = {
            "search_query": query,
            "start": start,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        headers = {
            "User-Agent": "Weekly-AI-Digest/1.0 (mailto:jeffersonqiu@gmail.com)"
        }

        for attempt in range(max_retries):
            # Respect rate limit
            self._wait_for_rate_limit()

            try:
                with httpx.Client(timeout=60.0, headers=headers) as client:
                    response = client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    return parse_arxiv_response(response.text)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited - wait with exponential backoff
                    wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                    print(f"Rate limited (429). Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
                print(f"Error fetching from arXiv: {e}")
                return ArxivSearchResult(papers=[], total_results=0, start_index=start)

            except httpx.TimeoutException:
                print(f"Request timed out. Retrying (attempt {attempt + 1}/{max_retries})...")
                continue

            except httpx.HTTPError as e:
                print(f"Error fetching from arXiv: {e}")
                return ArxivSearchResult(papers=[], total_results=0, start_index=start)

        print("Max retries exceeded for arXiv API")
        return ArxivSearchResult(papers=[], total_results=0, start_index=start)

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limit."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_seconds:
                time.sleep(self.rate_limit_seconds - elapsed)

        self._last_request_time = time.time()

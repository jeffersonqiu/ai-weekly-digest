"""Pydantic schemas for arXiv papers.

Why Pydantic schemas separate from SQLAlchemy models?
- SQLAlchemy models = database structure (how data is stored)
- Pydantic schemas = API/data transfer structure (how data moves around)

This separation allows:
- Validation of incoming data before it hits the database
- Different representations (e.g., API response vs database row)
- Clear typing for IDE autocomplete and type checking
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ArxivPaper(BaseModel):
    """A paper fetched from arXiv API.

    This represents the raw data from arXiv before it's saved to our database.
    """

    arxiv_id: str = Field(..., description="arXiv identifier, e.g., '2401.12345'")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract/summary")
    authors: list[str] = Field(..., description="List of author names")
    categories: list[str] = Field(..., description="arXiv categories, e.g., ['cs.AI', 'cs.LG']")
    pdf_url: str = Field(..., description="Direct link to PDF")
    published_at: datetime = Field(..., description="Publication date")

    @property
    def primary_category(self) -> str:
        """The first (primary) category."""
        return self.categories[0] if self.categories else ""

    @property
    def authors_str(self) -> str:
        """Authors as comma-separated string (for database storage)."""
        return ", ".join(self.authors)

    @property
    def categories_str(self) -> str:
        """Categories as comma-separated string (for database storage)."""
        return ",".join(self.categories)


class ArxivSearchResult(BaseModel):
    """Result of an arXiv search query."""

    papers: list[ArxivPaper] = Field(default_factory=list)
    total_results: int = Field(0, description="Total papers matching query")
    start_index: int = Field(0, description="Starting index of this batch")

    @property
    def count(self) -> int:
        """Number of papers in this result."""
        return len(self.papers)

"""Paper model - represents an arXiv paper.

Stores the core metadata fetched from arXiv API.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Paper(Base):
    """An arXiv paper fetched during a run."""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), index=True)
    arxiv_id: Mapped[str] = mapped_column(
        String(50), unique=True, index=True
    )  # e.g., "2401.12345"
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str] = mapped_column(Text)
    authors: Mapped[str] = mapped_column(Text)  # JSON array as string
    categories: Mapped[str] = mapped_column(String(200))  # e.g., "cs.AI,cs.LG"
    pdf_url: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="papers")  # noqa: F821
    score: Mapped["PaperScore | None"] = relationship(  # noqa: F821
        "PaperScore", back_populates="paper", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Paper {self.arxiv_id}: {self.title[:50]}...>"

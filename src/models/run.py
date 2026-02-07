"""Run model - represents a single execution of the digest pipeline.

Each run tracks:
- When papers were fetched
- Status of the pipeline
- How many papers were processed
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Run(Base):
    """A single execution of the weekly digest pipeline."""

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, running, completed, failed
    start_date: Mapped[date] = mapped_column(Date)  # Papers from this date
    end_date: Mapped[date] = mapped_column(Date)  # Papers until this date
    papers_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships (defined here, backrefs in related models)
    papers: Mapped[list["Paper"]] = relationship(  # noqa: F821
        "Paper", back_populates="run", cascade="all, delete-orphan"
    )
    scores: Mapped[list["PaperScore"]] = relationship(  # noqa: F821
        "PaperScore", back_populates="run", cascade="all, delete-orphan"
    )
    digest: Mapped["Digest | None"] = relationship(  # noqa: F821
        "Digest", back_populates="run", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Run {self.id}: {self.status} ({self.papers_count} papers)>"

"""Digest model - the generated weekly summary.

Stores both Markdown (for Telegram/plain text) and HTML (for email).
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Digest(Base):
    """Generated weekly digest for a run."""

    __tablename__ = "digests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("runs.id"), unique=True, index=True
    )
    markdown: Mapped[str] = mapped_column(Text)  # For Telegram/plain
    html: Mapped[str | None] = mapped_column(Text, nullable=True)  # For email
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationship
    run: Mapped["Run"] = relationship("Run", back_populates="digest")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Digest run={self.run_id} length={len(self.markdown)} chars>"

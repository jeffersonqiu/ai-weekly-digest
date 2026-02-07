"""PaperScore model - stores scoring signals for each paper.

The multi-signal scoring approach:
- recency_score: Newer papers score higher (0-1)
- category_score: Priority categories rank higher (0-1)
- llm_interest_score: LLM-assessed claimed novelty (0-1)
- final_score: Weighted combination of all signals
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class PaperScore(Base):
    """Scoring signals and final rank for a paper."""

    __tablename__ = "paper_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id"), unique=True, index=True
    )
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), index=True)

    # Individual scoring signals (all 0-1 normalized)
    author_score: Mapped[float] = mapped_column(Float, default=0.0)
    category_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_interest_score: Mapped[float] = mapped_column(Float, default=0.0)
    llm_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # LLM's explanation

    # Combined score and rank
    final_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    paper: Mapped["Paper"] = relationship("Paper", back_populates="score")  # noqa: F821
    run: Mapped["Run"] = relationship("Run", back_populates="scores")  # noqa: F821

    def __repr__(self) -> str:
        return f"<PaperScore paper={self.paper_id} score={self.final_score:.3f} rank={self.rank}>"

"""PaperScore model — stores two-stage ML pipeline scores for each paper.

Two-stage scoring approach:
- stage1_prob: XGBoost recall probability (P(interesting) from offline features)
- stage2_prob: XGBoost precision probability (P(interesting) from offline + LLM features)
- final_score: stage2_prob for recalled papers, 0 otherwise
- LLM citation sub-scores: 7 scores + 7 flags + 1 tier from gpt-4.1-nano
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class PaperScore(Base):
    """Two-stage ML pipeline scores and final rank for a paper."""

    __tablename__ = "paper_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id"), unique=True, index=True
    )
    run_id: Mapped[int] = mapped_column(Integer, ForeignKey("runs.id"), index=True)

    # ── Stage 1: Recall engine ──
    stage1_prob: Mapped[float] = mapped_column(Float, default=0.0)
    recalled: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Stage 2: Precision engine (only for recalled papers) ──
    stage2_prob: Mapped[float | None] = mapped_column(Float, nullable=True)

    # LLM citation sub-scores (7 scores, 0-10)
    citation_potential: Mapped[float | None] = mapped_column(Float, nullable=True)
    methodological_novelty: Mapped[float | None] = mapped_column(Float, nullable=True)
    practical_utility: Mapped[float | None] = mapped_column(Float, nullable=True)
    topic_trendiness: Mapped[float | None] = mapped_column(Float, nullable=True)
    reusability: Mapped[float | None] = mapped_column(Float, nullable=True)
    community_breadth: Mapped[float | None] = mapped_column(Float, nullable=True)
    writing_accessibility: Mapped[float | None] = mapped_column(Float, nullable=True)

    # LLM citation tier
    citation_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)

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
        status = "recalled" if self.recalled else "filtered"
        return f"<PaperScore paper={self.paper_id} score={self.final_score:.3f} rank={self.rank} ({status})>"

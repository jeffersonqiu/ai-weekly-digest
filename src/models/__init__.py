"""Models package - exports all SQLAlchemy models.

Import from here for convenience:
    from src.models import Base, Run, Paper, PaperScore, Digest
"""

from src.models.base import Base
from src.models.digest import Digest
from src.models.paper import Paper
from src.models.run import Run
from src.models.score import PaperScore

__all__ = ["Base", "Run", "Paper", "PaperScore", "Digest"]

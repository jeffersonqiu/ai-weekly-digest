"""SQLAlchemy declarative base.

All models inherit from this Base class.
Alembic uses this for migration auto-generation.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass

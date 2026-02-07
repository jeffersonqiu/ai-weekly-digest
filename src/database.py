"""Database session and engine configuration.

Why separate from models?
- Engine/session setup is shared across all models
- Allows easy testing with different database URLs
- get_db() generator pattern works with FastAPI dependency injection
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings


# Create engine (connection pool to database)
engine = create_engine(
    get_settings().db_url,
    pool_pre_ping=True,  # Verify connections before use
    echo=False,  # Set True to see SQL queries in logs
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session.

    Usage with FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

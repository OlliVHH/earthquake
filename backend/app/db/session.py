"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Human: Process-wide engine and session factory; pool_pre_ping avoids stale MySQL connections.
# Agent: READS settings.database_url; DB engine + SessionLocal; env var DATABASE_URL; failure modes: connection errors at first query.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# Human: FastAPI dependency that opens one session per request and always closes it.
# Agent: YIELDS Session from SessionLocal; WRITES db.close in finally; failure modes: leaked sessions if finally skipped.
def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

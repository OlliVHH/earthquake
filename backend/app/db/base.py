"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


# Human: Shared ORM base; all models inherit metadata and Alembic autogenerate target this class.
# Agent: DB declarative base only; no sessions; failure modes: models not subclassing Base won't migrate.
class Base(DeclarativeBase):
    """Base class for ORM models."""

    pass

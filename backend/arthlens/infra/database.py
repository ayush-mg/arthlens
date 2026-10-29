"""
Database engine and session management for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.arthlens.infra.config import get_database_url


class Base(DeclarativeBase):
    """Base declarative class for all ArthLens SQLAlchemy models."""
    pass


_engine = None
_SessionFactory = None


def get_engine():
    """Lazily initialize and return the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = get_database_url(sync=True)
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory():
    """Lazily initialize and return the sessionmaker."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionFactory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager yielding a transactional database session."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

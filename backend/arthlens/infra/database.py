"""
Database engine and session management for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.arthlens.infra.config import get_database_url


class Base(DeclarativeBase):
    """Base declarative class for all ArthLens SQLAlchemy models."""
    pass


_engine = None
_SessionFactory = None


def reset_engine_for_testing() -> None:
    """Reset cached engine/session_factory to ensure environment changes take effect."""
    global _engine, _SessionFactory
    if _engine is not None:
        _engine.dispose()
        _engine = None
    _SessionFactory = None


def assert_safe_test_database(conn_or_engine, expected_test_db: Optional[str] = None) -> None:
    """
    Explicit safety guard to prevent test execution or destructive operations (e.g. TRUNCATE)
    against the persistent development database.

    Enforces exact database identity validation against explicit test configuration:
    - Reads actual connected database using SELECT current_database().
    - Fails closed if expected test database is missing, ambiguous, or empty.
    - Explicitly rejects the configured development database.
    - Rejects any database that does not exactly equal the configured test database (substring matches forbidden).
    """
    from sqlalchemy import text
    from backend.arthlens.infra.config import (
        get_configured_development_database_name,
        get_configured_test_database_name,
    )

    if hasattr(conn_or_engine, "connect"):
        with conn_or_engine.connect() as conn:
            current_db = conn.execute(text("SELECT current_database();")).scalar()
    else:
        current_db = conn_or_engine.execute(text("SELECT current_database();")).scalar()

    if not current_db or not str(current_db).strip():
        raise RuntimeError("CRITICAL SAFETY VIOLATION: Unable to determine current database name (null or empty).")

    current_db = str(current_db).strip()
    if expected_test_db is not None:
        target_test_db = expected_test_db.strip()
    else:
        target_test_db = get_configured_test_database_name().strip()
    dev_db = get_configured_development_database_name().strip()

    if not target_test_db:
        raise RuntimeError(
            "CRITICAL SAFETY VIOLATION: Configured test database name is missing or empty. "
            "Failing closed to protect persistent data."
        )

    # 1. Explicit rejection of configured development database
    if current_db == dev_db:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Refusing to perform destructive test operations on "
            f"configured development database '{current_db}'! Test execution must strictly use "
            f"configured test database '{target_test_db}'."
        )

    # 2. Strict exact match requirement (substring matching strictly forbidden)
    if current_db != target_test_db:
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Connected database '{current_db}' does not exactly match "
            f"the expected configured test database '{target_test_db}'! Substring matches or "
            f"arbitrary databases are strictly rejected."
        )


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

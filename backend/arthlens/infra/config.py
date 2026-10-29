"""
Configuration and Environment Management for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 3.2, Part 9).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import os
from pathlib import Path
from typing import Optional


def _load_env_file() -> None:
    """Load key-value pairs from .env if present in root or backend without overriding existing env."""
    search_paths = [
        Path(__file__).resolve().parents[3] / ".env",  # c:\arthlens\.env
        Path(__file__).resolve().parents[2] / ".env",  # c:\arthlens\backend\.env
        Path(".env"),
    ]
    for env_path in search_paths:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            os.environ.setdefault(key, val)
                break
            except Exception:
                pass


_load_env_file()


def get_database_url(sync: bool = True) -> str:
    """
    Construct or retrieve the PostgreSQL connection URL.

    Respects DATABASE_URL if present, otherwise constructs from POSTGRES_* environment variables.
    Ensures the psycopg (v3) dialect 'postgresql+psycopg://' is used by default for SQLAlchemy.
    """
    raw_url = os.environ.get("DATABASE_URL")
    if raw_url:
        url = raw_url.strip()
        # Normalise postgres:// or postgresql:// to postgresql+psycopg:// for SQLAlchemy 2.x
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    user = os.environ.get("POSTGRES_USER", "arthlens_dev")
    password = os.environ.get("POSTGRES_PASSWORD", "arthlens_dev_password")
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "arthlens")

    driver = "postgresql+psycopg" if sync else "postgresql+psycopg_async"
    return f"{driver}://{user}:{password}@{host}:{port}/{db}"


def get_environment() -> str:
    """Return runtime environment name (development, test, production)."""
    return os.environ.get("ENVIRONMENT", "development")

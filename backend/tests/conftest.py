"""
Pytest root configuration and global session setup for ArthLens test suite.

Authoritative Reference: ArthLens Build Handbook v1.0.
"""

import os

# Set testing environment indicators
os.environ["ENVIRONMENT"] = "test"
os.environ["POSTGRES_DB"] = "arthlens_test"
os.environ.setdefault("RATE_LIMIT_PER_MINUTE_IP", "10000")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE_USER", "10000")

import pytest
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    reset_engine_for_testing,
)

# Ensure engine is clean for test run
reset_engine_for_testing()


@pytest.fixture(scope="session", autouse=True)
def verify_test_db_isolation():
    """Verify before running any test that the connection targets an isolated test database."""
    engine = get_engine()
    assert_safe_test_database(engine)

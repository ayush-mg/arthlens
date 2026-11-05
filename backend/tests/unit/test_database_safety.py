"""
Unit Tests for Database Safety Guard and Test Database Isolation.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1).
Phase: Phase 2 (P2-2 - Stage 2 Geographic Infrastructure Hardening).
"""

from unittest.mock import MagicMock
import pytest

from backend.arthlens.infra.database import assert_safe_test_database


class DummyConnection:
    """Mock connection returning a simulated current_database() name."""

    def __init__(self, db_name: str) -> None:
        self.db_name = db_name

    def execute(self, statement):
        mock_result = MagicMock()
        mock_result.scalar.return_value = self.db_name
        return mock_result


class DummyEngine:
    """Mock engine context manager yielding DummyConnection."""

    def __init__(self, db_name: str) -> None:
        self._conn = DummyConnection(db_name)

    def connect(self):
        class _CM:
            def __enter__(_s):
                return self._conn

            def __exit__(_s, *exc):
                pass
        return _CM()


class TestDatabaseSafetyGuard:
    """Negative and positive verification of the destructive test safety guard."""

    def test_configured_development_database_is_explicitly_rejected(self):
        """Persistent development database 'arthlens' MUST be rejected with RuntimeError."""
        conn = DummyConnection("arthlens")
        with pytest.raises(RuntimeError, match="Refusing to perform destructive test operations on configured development database"):
            assert_safe_test_database(conn, expected_test_db="arthlens_test")

    def test_substring_match_arthlens_contest_is_rejected(self):
        """Database 'arthlens_contest' containing 'test' as a substring MUST be rejected."""
        conn = DummyConnection("arthlens_contest")
        with pytest.raises(RuntimeError, match="does not exactly match the expected configured test database"):
            assert_safe_test_database(conn, expected_test_db="arthlens_test")

    def test_arbitrary_database_containing_test_is_rejected(self):
        """Arbitrary databases containing 'test' (e.g., 'test_dev', 'my_test_db') MUST be rejected."""
        for arbitrary_name in ["test_dev", "my_test_db", "test", "production_test"]:
            conn = DummyConnection(arbitrary_name)
            with pytest.raises(RuntimeError, match="does not exactly match the expected configured test database"):
                assert_safe_test_database(conn, expected_test_db="arthlens_test")

    def test_empty_or_null_database_name_fails_closed(self):
        """Null or whitespace database names must fail closed."""
        for invalid_name in [None, "", "   "]:
            conn = DummyConnection(invalid_name)
            with pytest.raises(RuntimeError, match="Unable to determine current database name"):
                assert_safe_test_database(conn, expected_test_db="arthlens_test")

    def test_missing_or_empty_expected_test_db_fails_closed(self):
        """Empty expected_test_db parameter must fail closed."""
        conn = DummyConnection("arthlens_test")
        with pytest.raises(RuntimeError, match="Configured test database name is missing or empty"):
            assert_safe_test_database(conn, expected_test_db="")

    def test_exact_configured_test_database_is_accepted(self):
        """Exact match to the configured test database 'arthlens_test' MUST succeed without error."""
        conn = DummyConnection("arthlens_test")
        # Should execute cleanly without raising any exception
        assert_safe_test_database(conn, expected_test_db="arthlens_test")

    def test_engine_wrapper_works_with_exact_match(self):
        """Safety guard works with engine object wrapping exact database."""
        engine = DummyEngine("arthlens_test")
        assert_safe_test_database(engine, expected_test_db="arthlens_test")

    def test_engine_wrapper_rejects_development_db(self):
        """Safety guard works with engine object wrapping development database."""
        engine = DummyEngine("arthlens")
        with pytest.raises(RuntimeError, match="Refusing to perform destructive test operations on configured development database"):
            assert_safe_test_database(engine, expected_test_db="arthlens_test")


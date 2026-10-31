"""
Rate Limiting and Quota Enforcement Service.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Implements:
- Distributed, concurrency-safe atomic rate limiting via PostgreSQL table rate_limits.
- In-memory thread-safe rate limiting fake for offline/unit testing.
- Per-IP and per-user window throttling.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
import threading
from typing import Callable, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.arthlens.infra.database import get_engine, get_session_factory


class RateLimiter(ABC):
    """Abstract base for concurrency-safe rate limiters."""

    @abstractmethod
    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit and increment counter.

        Args:
            key: Throttle key (e.g. 'ip:203.0.113.1', 'user:UUID').
            limit: Maximum allowed requests in the time window.
            window_seconds: Rolling window length in seconds.

        Returns:
            Tuple of (allowed: bool, remaining: int, reset_in_seconds: int)
        """
        raise NotImplementedError

    @abstractmethod
    def prune_expired_entries(self, max_age_seconds: int = 3600) -> int:
        """Prune rate limit records that expired more than max_age_seconds ago."""
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    """Thread-safe in-memory rate limiter using sliding fixed windows."""

    def __init__(self) -> None:
        self._buckets = {}
        self._lock = threading.Lock()

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        now = datetime.now(timezone.utc)
        with self._lock:
            if key not in self._buckets:
                reset_at = now + timedelta(seconds=window_seconds)
                self._buckets[key] = (1, reset_at)
                return True, limit - 1, window_seconds

            count, reset_at = self._buckets[key]
            if now >= reset_at:
                # Window expired, reset bucket
                reset_at = now + timedelta(seconds=window_seconds)
                self._buckets[key] = (1, reset_at)
                return True, limit - 1, window_seconds

            # Increment within active window
            new_count = count + 1
            self._buckets[key] = (new_count, reset_at)
            reset_in = max(0, int((reset_at - now).total_seconds()))
            allowed = new_count <= limit
            remaining = max(0, limit - new_count)
            return allowed, remaining, reset_in

    def prune_expired_entries(self, max_age_seconds: int = 3600) -> int:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=max_age_seconds)
        with self._lock:
            expired = [k for k, (_, reset_at) in self._buckets.items() if reset_at < threshold]
            for k in expired:
                del self._buckets[k]
            return len(expired)

    def clear(self) -> None:
        with self._lock:
            self._buckets.clear()


class PostgresRateLimiter(RateLimiter):
    """
    PostgreSQL-backed atomic rate limiter.
    Uses atomic INSERT ... ON CONFLICT DO UPDATE to ensure zero race conditions across
    multi-process worker deployments without external Redis dependencies.
    """

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> Tuple[bool, int, int]:
        engine = get_engine()
        query = text("""
        INSERT INTO rate_limits (key, count, reset_at)
        VALUES (:key, 1, NOW() + (:window_seconds || ' seconds')::interval)
        ON CONFLICT (key) DO UPDATE
        SET count = CASE
                WHEN rate_limits.reset_at <= NOW() THEN 1
                ELSE rate_limits.count + 1
            END,
            reset_at = CASE
                WHEN rate_limits.reset_at <= NOW() THEN NOW() + (:window_seconds || ' seconds')::interval
                ELSE rate_limits.reset_at
            END
        RETURNING count, GREATEST(0, EXTRACT(EPOCH FROM (reset_at - NOW()))::int) AS reset_in;
        """)

        with engine.begin() as conn:
            row = conn.execute(query, {"key": key, "window_seconds": window_seconds}).one()
            current_count = row[0]
            reset_in = row[1]

        allowed = current_count <= limit
        remaining = max(0, limit - current_count)
        return allowed, remaining, reset_in

    def prune_expired_entries(self, max_age_seconds: int = 3600) -> int:
        """Prune rate limit records that expired more than max_age_seconds ago."""
        engine = get_engine()
        query = text("""
            DELETE FROM rate_limits
            WHERE reset_at < NOW() - (:max_age || ' seconds')::interval;
        """)
        with engine.begin() as conn:
            result = conn.execute(query, {"max_age": max_age_seconds})
            return result.rowcount


_default_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = PostgresRateLimiter()
    return _default_limiter


def set_rate_limiter(limiter: Optional[RateLimiter]) -> None:
    global _default_limiter
    _default_limiter = limiter


__all__ = [
    "RateLimiter",
    "InMemoryRateLimiter",
    "PostgresRateLimiter",
    "get_rate_limiter",
    "set_rate_limiter",
]

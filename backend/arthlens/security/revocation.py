"""
Token Revocation Store for Session Invalidation upon Logout.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import threading
from typing import Callable, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import RevokedTokenModel


class TokenRevocationStore(ABC):
    """Abstract base for JWT ID revocation tracking."""

    @abstractmethod
    def revoke(self, jti: str, expires_at: datetime) -> None:
        """Mark a token ID as revoked until its expiration."""
        raise NotImplementedError

    @abstractmethod
    def is_revoked(self, jti: str) -> bool:
        """Check whether a token ID has been revoked."""
        raise NotImplementedError


class InMemoryTokenRevocationStore(TokenRevocationStore):
    """Thread-safe in-memory fake for token revocation."""

    def __init__(self) -> None:
        self._revoked = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, expires_at: datetime) -> None:
        with self._lock:
            self._revoked[jti] = expires_at

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            if jti not in self._revoked:
                return False
            exp = self._revoked[jti]
            now = datetime.now(timezone.utc)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                del self._revoked[jti]
                return False
            return True

    def clear(self) -> None:
        with self._lock:
            self._revoked.clear()


class PostgresTokenRevocationStore(TokenRevocationStore):
    """PostgreSQL-backed shared token revocation store using table revoked_tokens."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def revoke(self, jti: str, expires_at: datetime) -> None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        with self._get_session() as session:
            existing = session.get(RevokedTokenModel, jti)
            if not existing:
                model = RevokedTokenModel(
                    jti=jti,
                    expires_at=expires_at,
                )
                session.add(model)
                session.commit()

    def is_revoked(self, jti: str) -> bool:
        with self._get_session() as session:
            model = session.get(RevokedTokenModel, jti)
            if not model:
                return False
            now = datetime.now(timezone.utc)
            if model.expires_at.tzinfo is None:
                exp = model.expires_at.replace(tzinfo=timezone.utc)
            else:
                exp = model.expires_at
            if now > exp:
                session.delete(model)
                session.commit()
                return False
            return True

    def prune_expired_tokens(self) -> int:
        """Bulk prune revoked token records whose natural JWT expiration has elapsed."""
        from sqlalchemy import delete
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            stmt = delete(RevokedTokenModel).where(RevokedTokenModel.expires_at < now)
            result = session.execute(stmt)
            session.commit()
            return result.rowcount


_default_revocation_store: Optional[TokenRevocationStore] = None


def get_token_revocation_store() -> TokenRevocationStore:
    """Return the active token revocation store."""
    global _default_revocation_store
    if _default_revocation_store is None:
        _default_revocation_store = PostgresTokenRevocationStore()
    return _default_revocation_store


def set_token_revocation_store(store: Optional[TokenRevocationStore]) -> None:
    """Set the active token revocation store (used in testing)."""
    global _default_revocation_store
    _default_revocation_store = store


__all__ = [
    "TokenRevocationStore",
    "InMemoryTokenRevocationStore",
    "PostgresTokenRevocationStore",
    "get_token_revocation_store",
    "set_token_revocation_store",
]

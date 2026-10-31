"""
Audit Logging Service for Security, Administrative, and Epistemic Operations.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Union
import uuid

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import AuditEventModel


SENSITIVE_FIELD_NAMES = frozenset([
    "password",
    "password_hash",
    "token",
    "secret",
    "authorization",
    "api_key",
    "cookie",
])


class AuditService:
    """Service recording immutable audit events in PostgreSQL."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def _sanitize_payload(self, data: Any) -> Any:
        """Recursively redact sensitive credentials, tokens, and secret parameters."""
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if any(sub in k.lower() for sub in SENSITIVE_FIELD_NAMES):
                    cleaned[k] = "[REDACTED]"
                else:
                    cleaned[k] = self._sanitize_payload(v)
            return cleaned
        elif isinstance(data, (list, tuple)):
            return [self._sanitize_payload(x) for x in data]
        return data

    def record_event(
        self,
        actor: Optional[Union[str, uuid.UUID]],
        action: str,
        target: str,
        payload: Optional[Dict[str, Any]] = None,
        prev_hash: Optional[str] = None,
    ) -> int:
        """
        Record an immutable audit event.

        Args:
            actor: UUID of user performing action (or None for system / anonymous).
            action: Semantic action name (e.g. 'AUTH_LOGIN_SUCCESS', 'AUTH_LOGOUT').
            target: Identifier of target entity (e.g. 'user:UUID', 'policy_rule:UUID').
            payload: Relevant metadata (automatically sanitized of sensitive credentials).
            prev_hash: Optional chained hash.

        Returns:
            Database ID of the newly inserted audit record.
        """
        actor_uuid = None
        if actor:
            if isinstance(actor, uuid.UUID):
                actor_uuid = actor
            else:
                try:
                    actor_uuid = uuid.UUID(str(actor))
                except (ValueError, AttributeError):
                    actor_uuid = None

        sanitized_payload = self._sanitize_payload(payload or {})

        with self._get_session() as session:
            # If prev_hash not provided, chain from the latest audit event in the table
            if prev_hash is None:
                latest = session.execute(
                    select(AuditEventModel.id, AuditEventModel.timestamp)
                    .order_by(desc(AuditEventModel.id))
                    .limit(1)
                ).first()
                if latest:
                    prev_hash = hashlib.sha256(f"{latest[0]}:{latest[1]}".encode("utf-8")).hexdigest()
                else:
                    prev_hash = "GENESIS"

            model = AuditEventModel(
                actor=actor_uuid,
                action=action,
                target=target,
                payload=sanitized_payload,
                prev_hash=prev_hash,
            )
            session.add(model)
            session.commit()
            return int(model.id)

    def list_events(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve audit events ordered by timestamp descending for administrative inspection."""
        with self._get_session() as session:
            stmt = select(AuditEventModel).order_by(desc(AuditEventModel.timestamp)).limit(limit).offset(offset)
            records = session.execute(stmt).scalars().all()
            return [
                {
                    "id": r.id,
                    "actor": str(r.actor) if r.actor else None,
                    "action": r.action,
                    "target": r.target,
                    "payload": r.payload,
                    "prev_hash": r.prev_hash,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in records
            ]


_default_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _default_audit_service
    if _default_audit_service is None:
        _default_audit_service = AuditService()
    return _default_audit_service


__all__ = ["AuditService", "get_audit_service"]

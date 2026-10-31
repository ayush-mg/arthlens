"""
Integration Tests for Append-Only Audit Trail and Database Immutability.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- Security events (login, logout, admin actions) are faithfully recorded in audit_events table.
- Passwords and raw tokens are redacted from audit payloads.
- PostgreSQL trigger trg_audit_events_immutable rejects direct SQL UPDATE operations.
- PostgreSQL trigger trg_audit_events_immutable rejects direct SQL DELETE operations.
"""

import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.arthlens.infra.database import get_engine
from backend.arthlens.security.audit import AuditService


@pytest.mark.integration
class TestAuditImmutability:
    """Tests audit recording and database-level append-only enforcement."""

    def test_record_audit_event_persists_to_database(self):
        """AuditService persists event with actor, action, target, payload, and timestamp."""
        engine = get_engine()
        service = AuditService()

        actor_id = uuid.uuid4()
        event_id = service.record_event(
            actor=actor_id,
            action="AUTH_LOGIN_SUCCESS",
            target=f"user:{actor_id}",
            payload={"ip": "127.0.0.1", "user_agent": "pytest-client"},
        )
        assert event_id is not None

        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, actor, action, target, payload FROM audit_events WHERE id = :id"),
                {"id": event_id},
            ).mappings().one_or_none()

            assert row is not None
            assert row["action"] == "AUTH_LOGIN_SUCCESS"
            assert row["target"] == f"user:{actor_id}"
            assert row["payload"]["ip"] == "127.0.0.1"

    def test_sensitive_fields_are_redacted_from_audit_payload(self):
        """Passwords, secret keys, and raw tokens are redacted from audit payloads."""
        service = AuditService()
        redacted = service._sanitize_payload({
            "email": "user@arthlens.org",
            "password": "SuperSecretPassword123!",
            "token": "secret_jwt_token_here",
            "safe_field": "visible",
        })

        assert redacted["password"] == "[REDACTED]"
        assert redacted["token"] == "[REDACTED]"
        assert redacted["safe_field"] == "visible"

    def test_database_trigger_rejects_direct_sql_update(self):
        """PostgreSQL trigger trg_audit_events_immutable rejects direct SQL UPDATE."""
        engine = get_engine()
        service = AuditService()

        event_id = service.record_event(
            actor=uuid.uuid4(),
            action="SENSITIVE_ACTION",
            target="resource:1",
            payload={"note": "original"},
        )

        with pytest.raises(DBAPIError, match="audit_events is append-only"):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE audit_events SET action = 'TAMPERED' WHERE id = :id"),
                    {"id": event_id},
                )

        # Confirm action was not altered
        with engine.connect() as conn:
            val = conn.execute(
                text("SELECT action FROM audit_events WHERE id = :id"),
                {"id": event_id},
            ).scalar()
            assert val == "SENSITIVE_ACTION"

    def test_database_trigger_rejects_direct_sql_delete(self):
        """PostgreSQL trigger trg_audit_events_immutable rejects direct SQL DELETE."""
        engine = get_engine()
        service = AuditService()

        event_id = service.record_event(
            actor=uuid.uuid4(),
            action="CANNOT_DELETE",
            target="resource:2",
            payload={},
        )

        with pytest.raises(DBAPIError, match="audit_events is append-only"):
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM audit_events WHERE id = :id"),
                    {"id": event_id},
                )

        # Confirm row was not deleted
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT count(*) FROM audit_events WHERE id = :id"),
                {"id": event_id},
            ).scalar()
            assert count == 1

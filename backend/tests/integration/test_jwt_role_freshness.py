"""
Integration Tests for JWT Role Freshness and Real-Time Privilege Revocation.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- A previously issued JWT carrying elevated roles (e.g. ADMIN) immediately loses access
  when the role is removed in the authoritative database, without waiting for token expiration.
- Deleting or deactivating a user account immediately invalidates existing JWT sessions (401).
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def api_client():
    app = create_app()
    return TestClient(app)


@pytest.mark.integration
class TestJWTRoleFreshness:
    """Verifies that role revocations take effect immediately against issued tokens."""

    def test_revoked_role_denies_subsequent_request_with_same_token(self, api_client):
        """
        User issued a token with [ADMIN, ENTREPRENEUR].
        When ADMIN role is stripped in the database, the very next call with that token is 403.
        """
        user_repo = PostgresUserRepository()
        user_id = str(uuid.uuid4())
        email = f"freshness_{user_id[:8]}@arthlens.org"

        # 1. Create user with ADMIN and ENTREPRENEUR roles
        user_repo.save({
            "id": user_id,
            "email": email,
            "password_hash": "dummy_freshness_hash",
            "roles": [Role.ENTREPRENEUR.value, Role.ADMIN.value],
            "quota_counters": {"runs_today": 0},
        })

        # 2. Issue token with [ADMIN, ENTREPRENEUR] claims
        token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value, Role.ADMIN.value])
        cookie = {get_auth_cookie_name(): token}

        # 3. Requesting admin endpoint initially succeeds (200 OK)
        res_admin_initial = api_client.get("/admin/users", cookies=cookie)
        assert res_admin_initial.status_code == 200

        # 4. Demote user in database: strip ADMIN role, keep only ENTREPRENEUR
        user_repo.save({
            "id": user_id,
            "email": email,
            "password_hash": "dummy_freshness_hash",
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"runs_today": 0},
        })

        # 5. Subsequent request with the EXACT SAME token must now fail with 403 Forbidden!
        res_admin_demoted = api_client.get("/admin/users", cookies=cookie)
        assert res_admin_demoted.status_code == 403
        assert "forbidden" in res_admin_demoted.json()["detail"].lower()

        # 6. But entrepreneur endpoints still work for this user
        res_scen = api_client.post("/scenarios", json={"name": "Permitted Entrepreneur Scenario"}, cookies=cookie)
        assert res_scen.status_code in [200, 201]

    def test_deleted_user_account_immediately_invalidates_token(self, api_client):
        """When user is removed from database, their token immediately yields 401 Unauthorized."""
        from sqlalchemy import text
        from backend.arthlens.infra.database import get_engine

        user_repo = PostgresUserRepository()
        user_id = str(uuid.uuid4())
        email = f"deleted_{user_id[:8]}@arthlens.org"

        user_repo.save({
            "id": user_id,
            "email": email,
            "password_hash": "dummy_hash",
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"runs_today": 0},
        })

        token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
        cookie = {get_auth_cookie_name(): token}

        # Verify access works
        res_before = api_client.get("/auth/ping", cookies=cookie)
        assert res_before.status_code == 200

        # Delete user from database
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM user_roles WHERE user_id = :uid"), {"uid": user_id})
            conn.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})

        # Subsequent call with same token must yield 401
        res_after = api_client.post("/scenarios", json={"name": "Post-Delete Scenario"}, cookies=cookie)
        assert res_after.status_code == 401
        assert "no longer exists" in res_after.json()["detail"].lower()

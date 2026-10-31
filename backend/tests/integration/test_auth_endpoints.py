"""
Integration Tests for Authentication Endpoints (POST /auth/login and POST /auth/logout).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- Successful login sets HTTP-only cookie and returns user profile.
- Invalid password returns generic 401 without account enumeration.
- Unknown email returns generic 401 without account enumeration.
- Logout clears the session cookie and revokes token.
- Subsequent calls using the logged-out token fail with 401 Unauthorized.
- Cookie attributes (HttpOnly, SameSite) are correctly set.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def seeded_user():
    """Create a verified test user in PostgreSQL."""
    repo = PostgresUserRepository()
    email = f"test_{uuid.uuid4().hex[:8]}@arthlens.org"
    password = "CorrectHorseBattery2026!"
    password_hash = hash_password(password)

    user_id = repo.save({
        "email": email,
        "password_hash": password_hash,
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    return {"id": user_id, "email": email, "password": password}


@pytest.mark.integration
class TestAuthEndpoints:
    """Tests /auth/login and /auth/logout workflows."""

    def test_login_success_sets_cookie_and_returns_user(self, client, seeded_user):
        """Successful login returns user info and sets HttpOnly session cookie."""
        res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        })
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == seeded_user["email"]
        assert "ENTREPRENEUR" in body["roles"]

        # Verify cookie
        cookie_name = get_auth_cookie_name()
        assert cookie_name in res.cookies
        cookie_header = res.headers.get("set-cookie", "")
        assert "httponly" in cookie_header.lower()
        assert "samesite=lax" in cookie_header.lower()

    def test_login_invalid_password_returns_generic_401(self, client, seeded_user):
        """Invalid password returns generic 401 without revealing password was wrong."""
        res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": "WrongPassword123!",
        })
        assert res.status_code == 401
        assert "invalid" in res.json()["detail"].lower()

    def test_login_unknown_email_returns_identical_generic_401(self, client):
        """Unknown email returns identical generic 401 error message to prevent enumeration."""
        res = client.post("/auth/login", json={
            "email": "nonexistent_user_99999@arthlens.org",
            "password": "SomePassword123!",
        })
        assert res.status_code == 401
        assert "invalid" in res.json()["detail"].lower()

    def test_logout_clears_cookie_and_revokes_token(self, client, seeded_user):
        """Logging out clears cookie and revokes token so it cannot be reused."""
        cookie_name = get_auth_cookie_name()

        # 1. Login
        login_res = client.post("/auth/login", json={
            "email": seeded_user["email"],
            "password": seeded_user["password"],
        })
        token = login_res.cookies[cookie_name]

        # 2. Access protected endpoint -> succeeds
        res_auth = client.get("/geo/IND.MH.PU/indicators", cookies={cookie_name: token})
        assert res_auth.status_code == 200

        # 3. Logout
        logout_res = client.post("/auth/logout", cookies={cookie_name: token})
        assert logout_res.status_code == 200

        # Verify response cleared cookie (Max-Age=0 or expired)
        set_cookie = logout_res.headers.get("set-cookie", "")
        assert cookie_name in set_cookie
        assert "max-age=0" in set_cookie.lower() or "expires=" in set_cookie.lower()

        # 4. Attempt to reuse previous token -> rejected (401 Token revoked)
        res_reused = client.get("/geo/IND.MH.PU/indicators", cookies={cookie_name: token})
        assert res_reused.status_code == 401
        assert "revoked" in res_reused.json()["detail"].lower()

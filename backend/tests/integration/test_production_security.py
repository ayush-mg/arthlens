"""
Production-Mode Security and Hardening Tests.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Acceptance Criteria:
- Startup auto-login and dev credentials are gated out of production.
- Production environment requires explicit JWT_SECRET_KEY (no fallback to default dev secret).
- Session cookies in production enforce Secure=True, HttpOnly=True, SameSite=lax.
- No unauthenticated access to protected epistemic, admin, or policy endpoints.
- No unauthenticated role elevation or forged token acceptance.
- Administrative endpoints (/admin/users, /admin/audit) reject non-admin roles with 403.
- Untrusted origins are blocked by CSRF defense-in-depth on cookie-authenticated mutations.
"""

import os
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import (
    get_auth_cookie_name,
    get_auth_cookie_secure,
    get_jwt_secret_key,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def api_client():
    """Create FastAPI test client with configured test dependencies."""
    app = create_app()
    return TestClient(app)


def test_production_jwt_secret_key_enforcement(monkeypatch):
    """In production mode, JWT_SECRET_KEY must be explicitly set or raise RuntimeError."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable must be set in production"):
        get_jwt_secret_key()

    monkeypatch.setenv("JWT_SECRET_KEY", "super_secret_production_key_32_bytes_minimum!")
    assert get_jwt_secret_key() == "super_secret_production_key_32_bytes_minimum!"


def test_production_cookie_security_flag(monkeypatch):
    """In production mode, session cookie requires Secure=True."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTH_COOKIE_SECURE", raising=False)
    assert get_auth_cookie_secure() is True


def test_unauthenticated_protected_endpoints_return_401(api_client):
    """Protected endpoints strictly require authentication and reject unauthenticated requests."""
    protected_paths = [
        ("GET", "/geo/units"),
        ("GET", "/geo/120"),
        ("GET", "/geo/pilot-boundaries"),
        ("GET", "/admin/users"),
        ("GET", "/admin/audit"),
        ("GET", "/policy/rules"),
    ]

    for method, path in protected_paths:
        if method == "GET":
            response = api_client.get(path)
        elif method == "POST":
            response = api_client.post(path, json={})
        assert response.status_code == 401, f"Expected 401 for {method} {path}, got {response.status_code}"


def test_role_elevation_protection(api_client):
    """A user with only ENTREPRENEUR role cannot access Admin or Policy Steward endpoints."""
    user_id = str(uuid.uuid4())
    email = f"entrepreneur_{user_id[:8]}@example.com"

    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_for_security_test",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })

    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    cookie_name = get_auth_cookie_name()
    cookies = {cookie_name: token}

    # Entrepreneur cannot view admin users or audit log
    r_users = api_client.get("/admin/users", cookies=cookies)
    assert r_users.status_code == 403

    r_audit = api_client.get("/admin/audit", cookies=cookies)
    assert r_audit.status_code == 403

    # Entrepreneur cannot post policy rules (Steward only)
    r_policy = api_client.post(
        "/policy/rules",
        json={"scheme_id": "test", "version": "1.0", "rule_ast": {}},
        cookies=cookies,
        headers={"Origin": "http://localhost:3000"},
    )
    assert r_policy.status_code == 403


def test_forged_or_invalid_jwt_rejected(api_client):
    """Tampered or invalid JWT session cookie must return 401."""
    cookie_name = get_auth_cookie_name()
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"

    response = api_client.get("/geo/units", cookies={cookie_name: fake_token})
    assert response.status_code == 401


def test_csrf_blocks_untrusted_origins(api_client):
    """Cookie-authenticated state-changing operations from untrusted origins are blocked."""
    user_id = str(uuid.uuid4())
    email = f"steward_{user_id[:8]}@example.com"

    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_for_security_test",
        "roles": [Role.STEWARD.value],
        "quota_counters": {"runs_today": 0},
    })

    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.STEWARD.value])
    cookie_name = get_auth_cookie_name()
    cookies = {cookie_name: token}

    # Attacker site origin
    response = api_client.post(
        "/policy/rules",
        json={"scheme_id": "malicious", "version": "1.0", "rule_ast": {}},
        cookies=cookies,
        headers={"Origin": "https://evil-attacker.example.com"},
    )
    assert response.status_code == 403
    assert "Untrusted Origin" in response.text


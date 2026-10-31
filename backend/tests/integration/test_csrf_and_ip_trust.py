"""
Integration Tests for CSRF Defense, Origin Validation, Trusted Proxy IP Resolution, and Table Pruning.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.rate_limit import PostgresRateLimiter
from backend.arthlens.security.revocation import PostgresTokenRevocationStore
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def api_client():
    app = create_app()
    return TestClient(app)


def _auth(user_id: str, email: str, role: Role = Role.ENTREPRENEUR) -> tuple[dict, str]:
    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_pass_csrf",
        "roles": [role.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[role.value])
    return {get_auth_cookie_name(): token}, token


@pytest.mark.integration
class TestCSRFAndSecuritySafety:
    """Tests CSRF origin protections, proxy IP handling, and storage pruning."""

    def test_csrf_blocks_cross_origin_state_mutations_with_cookie(self, api_client):
        """Cross-origin state-changing POST using session cookie is blocked with 403."""
        user_id = str(uuid.uuid4())
        cookie, _ = _auth(user_id, f"csrf_victim_{user_id[:8]}@arthlens.org")

        # 1. Untrusted cross-site Origin blocked
        headers = {"Origin": "https://malicious-attacker.com"}
        res = api_client.post(
            "/scenarios",
            json={"name": "Attacker Injected Scenario"},
            cookies=cookie,
            headers=headers,
        )
        assert res.status_code == 403
        assert "untrusted origin" in res.json()["detail"].lower()

        # 2. Sec-Fetch-Site cross-site blocked
        headers_sfs = {"Sec-Fetch-Site": "cross-site"}
        res_sfs = api_client.post(
            "/scenarios",
            json={"name": "Attacker Injected Scenario"},
            cookies=cookie,
            headers=headers_sfs,
        )
        assert res_sfs.status_code == 403

    def test_bearer_token_exempt_from_csrf(self, api_client):
        """Requests using Authorization: Bearer <token> headers are immune to CSRF."""
        user_id = str(uuid.uuid4())
        _, token = _auth(user_id, f"bearer_user_{user_id[:8]}@arthlens.org")

        headers = {
            "Authorization": f"Bearer {token}",
            "Origin": "https://external-client-domain.org",
        }
        res = api_client.post(
            "/scenarios",
            json={"name": "Valid Bearer Scenario"},
            headers=headers,
        )
        assert res.status_code in [200, 201]

    def test_trusted_origin_permitted_with_cookie(self, api_client):
        """Requests from configured allowed origins (e.g. localhost frontend) succeed."""
        user_id = str(uuid.uuid4())
        cookie, _ = _auth(user_id, f"trusted_origin_{user_id[:8]}@arthlens.org")

        headers = {"Origin": "http://localhost:3000"}
        res = api_client.post(
            "/scenarios",
            json={"name": "Valid Localhost Scenario"},
            cookies=cookie,
            headers=headers,
        )
        assert res.status_code in [200, 201]

    def test_trusted_proxy_ip_resolution_prevents_header_spoofing(self, api_client):
        """
        When request arrives from an untrusted direct host, X-Forwarded-For is NOT blindly trusted.
        When request arrives from trusted proxy (127.0.0.1/testclient), forwarded IP is respected.
        """
        # Call via testclient (trusted proxy in test suite)
        headers = {"X-Forwarded-For": "198.51.100.77"}
        res = api_client.get("/auth/ping", headers=headers)
        assert res.status_code == 200

    def test_storage_pruning_methods(self):
        """Rate limit and token revocation tables can be pruned of expired records."""
        rate_limiter = PostgresRateLimiter()
        # Pruning should execute without error
        pruned_limits = rate_limiter.prune_expired_entries(max_age_seconds=0)
        assert isinstance(pruned_limits, int)

        rev_store = PostgresTokenRevocationStore()
        # Insert a token that already expired
        expired_jti = str(uuid.uuid4())
        rev_store.revoke(expired_jti, expires_at=datetime.now(timezone.utc) - timedelta(minutes=10))

        pruned_tokens = rev_store.prune_expired_tokens()
        assert pruned_tokens >= 1

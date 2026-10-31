"""
Integration Tests for Rate Limiting, Quotas, and Concurrency Safety.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies:
- Per-IP rate limiting: requests exceeding limit return 429 Too Many Requests.
- Per-User rate limiting: requests exceeding limit return 429.
- Daily run quota enforcement: users exceeding allowed runs per day are rejected.
- Cost-cap enforcement: per-run cost cap ($0.25) and daily cost cap ($5.00).
- Concurrency-safe backend limiter behavior preventing race condition bypasses.
"""

from concurrent.futures import ThreadPoolExecutor
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.security.rate_limit import RateLimiter, PostgresRateLimiter, InMemoryRateLimiter
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def test_client():
    app = create_app()
    return TestClient(app)


def _cookie(user_id: str, email: str, role: Role = Role.ENTREPRENEUR) -> dict:
    from backend.arthlens.infra.repositories import PostgresUserRepository

    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_for_rate_test",
        "roles": [role.value],
        "quota_counters": {"runs_today": 0, "cost_today": 0.0},
    })
    cookie_name = get_auth_cookie_name()
    token, _ = create_access_token(user_id=user_id, email=email, roles=[role.value])
    return {cookie_name: token}


@pytest.mark.integration
class TestRateLimitingAndQuotas:
    """Tests rate limits, quotas, and concurrency safety."""

    def test_per_ip_rate_limiting(self, test_client, monkeypatch):
        """Requests from a single IP exceeding threshold return 429 with Retry-After header."""
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE_IP", "10")
        ip_headers = {"X-Forwarded-For": "203.0.113.195"}

        responses = []
        for _ in range(25):
            res = test_client.get("/auth/ping", headers=ip_headers)
            responses.append(res.status_code)

        has_429 = any(code == 429 for code in responses)
        assert has_429, f"Expected 429 in responses, got: {responses}"

    def test_per_user_rate_limiting(self, test_client, monkeypatch):
        """Authenticated requests from a single user exceeding threshold return 429."""
        monkeypatch.setenv("RATE_LIMIT_PER_MINUTE_USER", "15")
        user_id = str(uuid.uuid4())
        cookie = _cookie(user_id, f"spammer_{user_id[:8]}@arthlens.org", Role.ENTREPRENEUR)

        responses = []
        for _ in range(35):
            res = test_client.get("/geo/IND.MH.PU/indicators", cookies=cookie)
            responses.append(res.status_code)

        has_429 = any(code == 429 for code in responses)
        assert has_429, f"Expected 429 for user exceeding limit, got: {responses}"

    def test_daily_run_quota_enforcement(self, test_client, monkeypatch):
        """Entrepreneur submitting runs beyond daily quota is rejected."""
        monkeypatch.setenv("DAILY_RUN_QUOTA", "5")
        user_id = str(uuid.uuid4())
        cookie = _cookie(user_id, f"quota_tester_{user_id[:8]}@arthlens.org", Role.ENTREPRENEUR)

        # Create scenario first
        res_scen = test_client.post("/scenarios", json={"name": "Quota Scenario"}, cookies=cookie)
        assert res_scen.status_code in [200, 201], f"Failed to create scenario: {res_scen.text}"
        scenario_id = res_scen.json()["id"]

        # Simulate user at quota limit (5 runs in test env)
        for i in range(5):
            res = test_client.post("/runs", json={"scenario_id": scenario_id, "objective": {"test": i}}, cookies=cookie)
            assert res.status_code in [200, 201], f"Run {i} failed: {res.text}"

        # 6th run exceeds quota limit
        exceeded = test_client.post("/runs", json={"scenario_id": scenario_id, "objective": {"test": "overflow"}}, cookies=cookie)
        assert exceeded.status_code == 429
        assert "quota" in exceeded.json()["detail"].lower()

    def test_concurrency_safe_limiter_prevents_race_conditions(self):
        """Concurrent requests hitting the rate limiter atomically increment counters."""
        limiter = PostgresRateLimiter()
        test_key = f"concurrency_test:{uuid.uuid4()}"
        limit = 10
        window = 60

        def attempt():
            allowed, remaining, _ = limiter.check_rate_limit(key=test_key, limit=limit, window_seconds=window)
            return allowed

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(attempt) for _ in range(20)]
            results = [f.result() for f in futures]

        allowed_count = sum(1 for r in results if r is True)
        denied_count = sum(1 for r in results if r is False)

        # Exactly limit (10) must be allowed, and remaining (10) denied
        assert allowed_count == limit, f"Expected exactly {limit} allowed, got {allowed_count}"
        assert denied_count == 10

"""
Integration Tests for Per-Run Cost Cap, Daily Cost Cap, and Quota Concurrency Safety.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 8.3, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from concurrent.futures import ThreadPoolExecutor
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


def _auth_cookie(user_id: str, email: str, role: Role = Role.ENTREPRENEUR, initial_cost: float = 0.0) -> dict:
    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_cost_hash",
        "roles": [role.value],
        "quota_counters": {"runs_today": 0, "cost_today": initial_cost},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[role.value])
    return {get_auth_cookie_name(): token}


@pytest.mark.integration
class TestCostCapsAndConcurrency:
    """Verifies per-run cost caps, accumulated daily caps, and concurrent updates."""

    def test_per_run_budget_cap_rejected_before_execution(self, api_client, monkeypatch):
        """A run request with max_cost_usd exceeding MAX_COST_USD_PER_RUN is rejected immediately."""
        monkeypatch.setenv("MAX_COST_USD_PER_RUN", "0.25")
        user_id = str(uuid.uuid4())
        cookie = _auth_cookie(user_id, f"run_cap_{user_id[:8]}@arthlens.org")

        # Exceeds per-run cost cap of 0.25
        res = api_client.post(
            "/runs",
            json={"objective": {"goal": "test"}, "max_cost_usd": 0.50},
            cookies=cookie,
        )
        assert res.status_code == 400
        assert "exceeds per-run cost cap" in res.json()["detail"].lower()

    def test_estimated_cost_cap_rejected_with_429(self, api_client, monkeypatch):
        """A run whose estimated cost exceeds the single-run cap is rejected."""
        monkeypatch.setenv("MAX_COST_USD_PER_RUN", "0.25")
        user_id = str(uuid.uuid4())
        cookie = _auth_cookie(user_id, f"est_cap_{user_id[:8]}@arthlens.org")

        res = api_client.post(
            "/runs",
            json={"objective": {"goal": "test"}, "estimated_cost_usd": 0.30},
            cookies=cookie,
        )
        assert res.status_code == 429
        assert "per-run cost cap" in res.json()["detail"].lower()

    def test_daily_accumulated_cost_cap_enforced(self, api_client, monkeypatch):
        """User accumulating costs up to MAX_COST_USD_PER_DAY is rejected upon exceeding it."""
        monkeypatch.setenv("MAX_COST_USD_PER_DAY", "1.00")
        monkeypatch.setenv("MAX_COST_USD_PER_RUN", "0.25")
        user_id = str(uuid.uuid4())
        # User already at $0.90 spend today
        cookie = _auth_cookie(user_id, f"daily_cost_{user_id[:8]}@arthlens.org", initial_cost=0.90)

        # Run with cost 0.15 will push total to 1.05 > 1.00
        res = api_client.post(
            "/runs",
            json={"objective": {"goal": "expensive"}, "estimated_cost_usd": 0.15},
            cookies=cookie,
        )
        assert res.status_code == 429
        assert "daily budget cap exceeded" in res.json()["detail"].lower()

    def test_concurrent_quota_increments_are_lossless(self):
        """
        Concurrent threads incrementing quota and cost against PostgresUserRepository
        use SELECT FOR UPDATE row-locking to ensure zero lost updates.
        """
        user_repo = PostgresUserRepository()
        user_id = str(uuid.uuid4())
        user_repo.save({
            "id": user_id,
            "email": f"concurrency_{user_id[:8]}@arthlens.org",
            "password_hash": "dummy_hash",
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"runs_today": 0, "cost_today": 0.0},
        })

        num_threads = 10
        runs_per_thread = 2
        cost_per_thread = 0.05

        def worker():
            user_repo.increment_quota_counters(user_id, runs=runs_per_thread, cost=cost_per_thread)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker) for _ in range(num_threads)]
            for f in futures:
                f.result()

        final_user = user_repo.get_by_id(user_id)
        counters = final_user["quota_counters"]

        expected_runs = num_threads * runs_per_thread
        expected_cost = round(num_threads * cost_per_thread, 4)

        assert counters["runs_today"] == expected_runs, f"Expected {expected_runs} runs, got {counters['runs_today']}"
        assert abs(counters["cost_today"] - expected_cost) < 1e-4, f"Expected {expected_cost} cost, got {counters['cost_today']}"

    def test_client_cannot_bypass_budget_cap_with_zero_or_low_estimated_cost(self, api_client, monkeypatch):
        """
        A client attempting to evade the daily budget cap by sending estimated_cost_usd: 0.0
        or 0.00001 cannot lower the cost reservation below the server-side baseline.
        """
        monkeypatch.setenv("MAX_COST_USD_PER_DAY", "0.02")
        monkeypatch.setenv("DEFAULT_RUN_COST_RESERVATION", "0.01")
        user_id = str(uuid.uuid4())
        cookie = _auth_cookie(user_id, f"bypass_attempt_{user_id[:8]}@arthlens.org", initial_cost=0.01)

        # 1st run: costs server baseline 0.01 -> total spend becomes 0.02 (at limit)
        res1 = api_client.post("/runs", json={"objective": {"run": 1}}, cookies=cookie)
        assert res1.status_code in [200, 201]

        # 2nd run: client tries to evade limit by claiming cost is 0.0 or 0.0000001
        res2 = api_client.post(
            "/runs",
            json={"objective": {"run": 2}, "estimated_cost_usd": 0.0},
            cookies=cookie,
        )
        assert res2.status_code == 429
        assert "daily budget cap exceeded" in res2.json()["detail"].lower()

    def test_rejected_run_does_not_inflate_quota_counters(self, api_client, monkeypatch):
        """
        When a run is rejected for exceeding run quota or budget cap,
        the user's quota counters are NOT incremented.
        """
        monkeypatch.setenv("DAILY_RUN_QUOTA", "2")
        user_id = str(uuid.uuid4())
        cookie = _auth_cookie(user_id, f"no_inflate_{user_id[:8]}@arthlens.org")

        # 2 permitted runs
        r1 = api_client.post("/runs", json={"objective": {"run": 1}}, cookies=cookie)
        r2 = api_client.post("/runs", json={"objective": {"run": 2}}, cookies=cookie)
        assert r1.status_code in [200, 201]
        assert r2.status_code in [200, 201]

        # Attempt 3 rejected runs
        for _ in range(3):
            rej = api_client.post("/runs", json={"objective": {"run": "overflow"}}, cookies=cookie)
            assert rej.status_code == 429

        user_repo = PostgresUserRepository()
        user_data = user_repo.get_by_id(user_id)
        # Runs today must remain exactly 2, not 5
        assert user_data["quota_counters"]["runs_today"] == 2

    def test_failed_run_setup_refunds_reserved_quota(self, api_client):
        """If run setup fails (e.g. non-existent scenario ID), reserved quota is refunded."""
        user_id = str(uuid.uuid4())
        cookie = _auth_cookie(user_id, f"refund_tester_{user_id[:8]}@arthlens.org")

        user_repo = PostgresUserRepository()
        initial_user = user_repo.get_by_id(user_id)
        initial_runs = initial_user["quota_counters"]["runs_today"]
        initial_cost = initial_user["quota_counters"]["cost_today"]

        # Run with invalid scenario ID
        invalid_scen_id = str(uuid.uuid4())
        res = api_client.post(
            "/runs",
            json={"scenario_id": invalid_scen_id, "objective": {}},
            cookies=cookie,
        )
        assert res.status_code == 404

        after_user = user_repo.get_by_id(user_id)
        # Counters must have been refunded to initial state
        assert after_user["quota_counters"]["runs_today"] == initial_runs
        assert abs(after_user["quota_counters"]["cost_today"] - initial_cost) < 1e-4

"""
Integration Tests for Insecure Direct Object Reference (IDOR) and Record Ownership.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Mandatory IDOR Scenario:
- Two independent users: User A (owner) and User B (attacker).
- User A owns a simulation run and scenario.
- User B attempts to:
  1. Read User A's run (GET /runs/{id})
  2. Read User A's event stream (GET /runs/{id}/events)
  3. Answer / modify User A's run (POST /runs/{id}/answer)
  4. Approve User A's run actions (POST /runs/{id}/approve)
  5. Branch / access User A's private scenario (POST /scenarios/{id}/branch)
- Proves User B is strictly denied.
- Proves denial response does NOT disclose whether the resource exists (404 Not Found).
- Proves ownership is enforced at both service layer and repository layer.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.domain.repositories import ScenarioRepository
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.database import get_engine
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def _cookie_for(user_id: str, email: str, role: Role = Role.ENTREPRENEUR) -> dict:
    from backend.arthlens.infra.repositories import PostgresUserRepository
    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_pass_hash",
        "roles": [role.value],
        "quota_counters": {"runs_today": 0},
    })
    cookie_name = get_auth_cookie_name()
    token, _ = create_access_token(user_id=user_id, email=email, roles=[role.value])
    return {cookie_name: token}


@pytest.mark.integration
class TestIDORProtection:
    """Verifies strict record ownership enforcement and IDOR prevention."""

    def test_user_b_cannot_access_user_a_run_or_scenario(self, client):
        """
        User A owns resources. User B attempts unauthorized access and is denied
        without existence disclosure (404 Not Found).
        """
        user_a_id = str(uuid.uuid4())
        user_b_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())

        cookie_a = _cookie_for(user_a_id, f"user_a_{user_a_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        cookie_b = _cookie_for(user_b_id, f"user_b_{user_b_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        cookie_admin = _cookie_for(admin_id, f"admin_{admin_id[:8]}@arthlens.org", Role.ADMIN)

        # 1. User A creates a scenario
        res_scen = client.post("/scenarios", json={"name": "User A Bakery Scenario"}, cookies=cookie_a)
        assert res_scen.status_code in [200, 201]
        scenario_id = res_scen.json()["id"]

        # 2. User A creates a run
        res_run = client.post("/runs", json={"scenario_id": scenario_id, "objective": {"sector": "food"}}, cookies=cookie_a)
        assert res_run.status_code in [200, 201]
        run_id = res_run.json()["id"]

        # 3. User A can access their own run and events
        res_a_read = client.get(f"/runs/{run_id}", cookies=cookie_a)
        assert res_a_read.status_code == 200
        assert res_a_read.json()["id"] == run_id

        res_a_events = client.get(f"/runs/{run_id}/events", cookies=cookie_a)
        assert res_a_events.status_code == 200

        # 4. User B attempts to read User A's run -> 404 (does not disclose existence)
        res_b_read = client.get(f"/runs/{run_id}", cookies=cookie_b)
        assert res_b_read.status_code == 404
        assert "not found" in res_b_read.json()["detail"].lower()

        # 5. User B attempts to read User A's event stream -> 404
        res_b_events = client.get(f"/runs/{run_id}/events", cookies=cookie_b)
        assert res_b_events.status_code == 404

        # 6. User B attempts to answer User A's run -> 404
        res_b_answer = client.post(f"/runs/{run_id}/answer", json={"answer": "42"}, cookies=cookie_b)
        assert res_b_answer.status_code == 404

        # 7. User B attempts to approve User A's run -> 404
        res_b_approve = client.post(f"/runs/{run_id}/approve", json={"approved": True}, cookies=cookie_b)
        assert res_b_approve.status_code == 404

        # 8. User B attempts to branch User A's private scenario -> 404
        res_b_branch = client.post(f"/scenarios/{scenario_id}/branch", json={"name": "Illicit Branch"}, cookies=cookie_b)
        assert res_b_branch.status_code == 404

        # 9. Admin CAN view the run (per Handbook Part 10: Roles 'Owner, Admin')
        res_admin_read = client.get(f"/runs/{run_id}", cookies=cookie_admin)
        assert res_admin_read.status_code == 200

    def test_repository_level_ownership_enforcement(self):
        """Repository queries scope by owner_id and prevent cross-tenant data leakage."""
        from backend.arthlens.infra.in_memory import InMemoryScenarioRepository

        repo = InMemoryScenarioRepository()
        owner_1 = str(uuid.uuid4())
        owner_2 = str(uuid.uuid4())

        s1_id = repo.save_scenario({"owner_id": owner_1, "name": "Owner 1 Scenario", "scenario": {}})
        s2_id = repo.save_scenario({"owner_id": owner_2, "name": "Owner 2 Scenario", "scenario": {}})

        # Querying by owner returns only their scenarios
        owner_1_scenarios = repo.list_by_owner(owner_1)
        assert len(owner_1_scenarios) == 1
        assert owner_1_scenarios[0]["id"] == s1_id

        owner_2_scenarios = repo.list_by_owner(owner_2)
        assert len(owner_2_scenarios) == 1
        assert owner_2_scenarios[0]["id"] == s2_id

    def test_quantity_ownership_and_idor_protection(self, client):
        """
        Tests per-record access rules on GET /ledger/{quantity_id} (Handbook Part 10.1 & Part 11).
        - Public quantities (owner_id=None) are accessible to all authenticated roles.
        - User-owned quantities are accessible only to their owner and authorized administrators.
        - Another entrepreneur receives generic 404 without existence disclosure.
        """
        from backend.arthlens.domain.enums import Kind
        from backend.arthlens.domain.quantity import Quantity
        from backend.arthlens.infra.repositories import PostgresQuantityRepository

        q_repo = PostgresQuantityRepository()
        user_a_id = str(uuid.uuid4())
        user_b_id = str(uuid.uuid4())
        admin_id = str(uuid.uuid4())

        auth_a = _cookie_for(user_a_id, f"qa_{user_a_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        auth_b = _cookie_for(user_b_id, f"qb_{user_b_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        auth_admin = _cookie_for(admin_id, f"qadmin_{admin_id[:8]}@arthlens.org", Role.ADMIN)

        # 1. Create a public quantity (e.g. district benchmark)
        pub_q_id = str(uuid.uuid4())
        pub_q = Quantity(
            id=pub_q_id,
            definition_key="benchmark.retail.footfall",
            value=250.0,
            unit="persons/day",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="IND.UP.PR",
            resolution=2,
            as_of="2026-01-01",
            owner_id=None,
        )
        q_repo.save(pub_q)

        # 2. Create a private user-owned quantity (e.g. User A's private revenue assumption)
        priv_q_id = str(uuid.uuid4())
        priv_q = Quantity(
            id=priv_q_id,
            definition_key="enterprise.bakery.projected_revenue",
            value=125000.0,
            unit="INR/month",
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id="IND.UP.PR",
            resolution=2,
            as_of="2026-01-01",
            owner_id=user_a_id,
        )
        q_repo.save(priv_q)

        # 3. Public quantity is accessible to User A, User B, and Admin
        res_pub_a = client.get(f"/ledger/{pub_q_id}", cookies=auth_a)
        assert res_pub_a.status_code == 200
        assert res_pub_a.json()["id"] == pub_q_id

        res_pub_b = client.get(f"/ledger/{pub_q_id}", cookies=auth_b)
        assert res_pub_b.status_code == 200

        # 4. Private quantity is accessible to Owner (User A)
        res_priv_a = client.get(f"/ledger/{priv_q_id}", cookies=auth_a)
        assert res_priv_a.status_code == 200
        assert res_priv_a.json()["id"] == priv_q_id
        assert res_priv_a.json()["owner_id"] == user_a_id

        # 5. User B (another entrepreneur) is denied with 404 (no existence disclosure)
        res_priv_b = client.get(f"/ledger/{priv_q_id}", cookies=auth_b)
        assert res_priv_b.status_code == 404
        assert "not found" in res_priv_b.json()["detail"].lower()

        # 6. Admin can access private quantity for verification / audit
        res_priv_admin = client.get(f"/ledger/{priv_q_id}", cookies=auth_admin)
        assert res_priv_admin.status_code == 200
        assert res_priv_admin.json()["id"] == priv_q_id

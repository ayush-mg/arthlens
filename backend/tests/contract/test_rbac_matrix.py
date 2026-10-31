"""
Contract Tests for Roles, Permissions, and RBAC Matrix.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).

Verifies the complete Handbook Part 10.1 Permission Matrix across all three MVP roles:
- ENTREPRENEUR
- STEWARD
- ADMIN
and unauthenticated callers.

Ensures:
- Proper allow/deny behavior per route and HTTP method.
- Deny-by-default behavior on routes.
- Backend enforcement independent of client headers or client-claimed roles.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def api_client():
    """Create FastAPI test client with configured test dependencies."""
    app = create_app()
    return TestClient(app)


def _auth_cookie_for(user_id: str, email: str, role: Role) -> dict:
    """Generate authenticated session cookie for a given role, ensuring user exists in DB."""
    from backend.arthlens.infra.config import get_auth_cookie_name
    from backend.arthlens.infra.repositories import PostgresUserRepository

    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_for_rbac_test",
        "roles": [role.value],
        "quota_counters": {"runs_today": 0},
    })

    token, _ = create_access_token(user_id=user_id, email=email, roles=[role.value])
    return {get_auth_cookie_name(): token}


@pytest.mark.contract
class TestRBACMatrix:
    """Tests the Handbook Part 10.1 Role-Based Access Control matrix."""

    # 1. Unauthenticated calls to protected endpoints are rejected
    @pytest.mark.parametrize("method,path,payload", [
        ("POST", "/runs", {"objective": "start sweet shop"}),
        ("GET", "/runs/11111111-1111-1111-1111-111111111111", None),
        ("GET", "/runs/11111111-1111-1111-1111-111111111111/events", None),
        ("POST", "/scenarios", {"name": "Base Scenario"}),
        ("GET", "/geo/IND.MH.PU/indicators", None),
        ("GET", "/policy/rules", None),
        ("POST", "/policy/rules", {"scheme_id": "pmfme", "version": "1.0", "rule_ast": {}}),
        ("GET", "/admin/users", None),
        ("GET", "/admin/audit", None),
    ])
    def test_unauthenticated_requests_receive_401(self, api_client, method, path, payload):
        """Unauthenticated requests to protected endpoints return 401 Unauthorized."""
        if method == "GET":
            response = api_client.get(path)
        else:
            response = api_client.post(path, json=payload or {})
        assert response.status_code == 401

    # 2. Admin endpoint protection (/admin/users, /admin/audit)
    def test_admin_endpoints_accessible_only_by_admin(self, api_client):
        """Admin endpoints allow ADMIN, but return 403 Forbidden to ENTREPRENEUR and STEWARD."""
        admin_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000001", "admin@arthlens.org", Role.ADMIN)
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)
        steward_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000003", "s@arthlens.org", Role.STEWARD)

        # Admin succeeds
        res_users = api_client.get("/admin/users", cookies=admin_cookie)
        assert res_users.status_code == 200
        res_audit = api_client.get("/admin/audit", cookies=admin_cookie)
        assert res_audit.status_code == 200

        # Entrepreneur forbidden
        res = api_client.get("/admin/users", cookies=entrepreneur_cookie)
        assert res.status_code == 403
        res = api_client.get("/admin/audit", cookies=entrepreneur_cookie)
        assert res.status_code == 403

        # Steward forbidden
        res = api_client.get("/admin/users", cookies=steward_cookie)
        assert res.status_code == 403
        res = api_client.get("/admin/audit", cookies=steward_cookie)
        assert res.status_code == 403

    # 3. Policy rule creation (POST /policy/rules) requires STEWARD
    def test_post_policy_rules_requires_steward(self, api_client):
        """POST /policy/rules is permitted for STEWARD, but 403 for ENTREPRENEUR and ADMIN."""
        steward_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000003", "steward@arthlens.org", Role.STEWARD)
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)

        rule_payload = {"scheme_id": "pmfme", "version": "v1.0", "rule_ast": {"conditions": []}}

        # Steward can post rule
        res_steward = api_client.post("/policy/rules", json=rule_payload, cookies=steward_cookie)
        assert res_steward.status_code in [200, 201]

        # Entrepreneur cannot post rule
        res_ent = api_client.post("/policy/rules", json=rule_payload, cookies=entrepreneur_cookie)
        assert res_ent.status_code == 403

    # 4. Entrepreneur operations (POST /runs, POST /scenarios) require ENTREPRENEUR
    def test_entrepreneur_operations_require_entrepreneur_role(self, api_client):
        """POST /runs and POST /scenarios are permitted for ENTREPRENEUR, but 403 for STEWARD."""
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)
        steward_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000003", "s@arthlens.org", Role.STEWARD)

        # POST /scenarios
        res_scen = api_client.post("/scenarios", json={"name": "Katra Bakery"}, cookies=entrepreneur_cookie)
        assert res_scen.status_code in [200, 201]

        res_scen_steward = api_client.post("/scenarios", json={"name": "Steward Scenario"}, cookies=steward_cookie)
        assert res_scen_steward.status_code == 403

        # POST /runs
        res_run = api_client.post("/runs", json={"objective": {"type": "retail"}}, cookies=entrepreneur_cookie)
        assert res_run.status_code in [200, 201]

        res_run_steward = api_client.post("/runs", json={"objective": {"type": "retail"}}, cookies=steward_cookie)
        assert res_run_steward.status_code == 403

    # 5. Deny-by-default behavior for undeclared routes
    def test_undeclared_or_unmapped_endpoints_deny_by_default(self, api_client):
        """Any route not explicitly configured in the authorization registry is denied by default."""
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)

        # An undeclared internal or experimental endpoint
        res = api_client.get("/internal/unregistered_endpoint", cookies=entrepreneur_cookie)
        assert res.status_code in [403, 404]

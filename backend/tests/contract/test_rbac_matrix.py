"""
Contract Tests for Roles, Permissions, and RBAC Matrix.

Authoritative Specification: ArthLens — Business Operating System & Decision Intelligence Platform.
"""

import uuid

import pytest
from backend.arthlens.api.app import create_app
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from fastapi.testclient import TestClient


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
    """Tests the Role-Based Access Control matrix for ArthLens Business OS."""

    # 1. Unauthenticated calls to protected endpoints are rejected
    @pytest.mark.parametrize("method,path,payload", [
        ("POST", "/businesses", {"name": "Test Business", "industry": "Retail"}),
        ("GET", "/businesses", None),
        ("GET", "/businesses/11111111-1111-1111-1111-111111111111", None),
        ("GET", "/admin/users", None),
        ("GET", "/admin/audit", None),
        ("GET", "/admin/audit-events", None),
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
        """Admin endpoints allow ADMIN, but return 403 Forbidden to non-admins."""
        admin_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000001", "admin@arthlens.org", Role.ADMIN)
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)

        # Admin succeeds
        res_users = api_client.get("/admin/users", cookies=admin_cookie)
        assert res_users.status_code == 200
        res_audit = api_client.get("/admin/audit", cookies=admin_cookie)
        assert res_audit.status_code == 200
        res_audit_events = api_client.get("/admin/audit-events", cookies=admin_cookie)
        assert res_audit_events.status_code == 200

        # Entrepreneur forbidden from admin user management and audit
        res = api_client.get("/admin/users", cookies=entrepreneur_cookie)
        assert res.status_code == 403
        res = api_client.get("/admin/audit", cookies=entrepreneur_cookie)
        assert res.status_code == 403

    # 3. Entrepreneur operations on /businesses
    def test_entrepreneur_operations(self, api_client):
        """Entrepreneurs can create and list their own businesses with tenant isolation."""
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)

        # POST /businesses
        res_biz = api_client.post("/businesses", json={"name": "Katra Bakery", "industry": "Food & Beverage"}, cookies=entrepreneur_cookie)
        assert res_biz.status_code in [200, 201]

        res_biz_list = api_client.get("/businesses", cookies=entrepreneur_cookie)
        assert res_biz_list.status_code == 200
        assert any(item["id"] == res_biz.json()["id"] for item in res_biz_list.json())

        other_entrepreneur_cookie = _auth_cookie_for(
            "00000000-0000-0000-0000-000000000004",
            "other-e@arthlens.org",
            Role.ENTREPRENEUR,
        )
        res_other_biz = api_client.get("/businesses", cookies=other_entrepreneur_cookie)
        assert res_other_biz.status_code == 200
        assert all(item["id"] != res_biz.json()["id"] for item in res_other_biz.json())

    # 4. Deny-by-default behavior for undeclared routes
    def test_undeclared_or_unmapped_endpoints_deny_by_default(self, api_client):
        """Any route not explicitly configured in the authorization registry is denied by default."""
        entrepreneur_cookie = _auth_cookie_for("00000000-0000-0000-0000-000000000002", "e@arthlens.org", Role.ENTREPRENEUR)

        # An undeclared internal or experimental endpoint
        res = api_client.get("/internal/unregistered_endpoint", cookies=entrepreneur_cookie)
        assert res.status_code in [403, 404]

    def test_workspace_role_matrix_and_owner_archival(self, api_client):
        """Owners manage membership and archive; managers can operate; viewers remain read-only."""
        owner_id = str(uuid.uuid4())
        manager_id = str(uuid.uuid4())
        viewer_id = str(uuid.uuid4())
        owner_cookie = _auth_cookie_for(owner_id, f"owner-{owner_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        manager_cookie = _auth_cookie_for(manager_id, f"manager-{manager_id[:8]}@arthlens.org", Role.ENTREPRENEUR)
        viewer_cookie = _auth_cookie_for(viewer_id, f"viewer-{viewer_id[:8]}@arthlens.org", Role.ENTREPRENEUR)

        business_response = api_client.post(
            "/businesses",
            json={"name": "RBAC Workspace", "industry": "Services"},
            cookies=owner_cookie,
        )
        assert business_response.status_code == 201, business_response.text
        business_id = business_response.json()["id"]

        manager_membership = api_client.post(
            f"/businesses/{business_id}/members",
            json={"user_id": manager_id, "role": "MANAGER"},
            cookies=owner_cookie,
        )
        assert manager_membership.status_code == 201, manager_membership.text
        viewer_membership = api_client.post(
            f"/businesses/{business_id}/members",
            json={"user_id": viewer_id, "role": "VIEWER"},
            cookies=owner_cookie,
        )
        assert viewer_membership.status_code == 201, viewer_membership.text

        manager_read = api_client.get(f"/businesses/{business_id}", cookies=manager_cookie)
        viewer_read = api_client.get(f"/businesses/{business_id}", cookies=viewer_cookie)
        assert manager_read.status_code == 200, manager_read.text
        assert viewer_read.status_code == 200, viewer_read.text

        manager_write = api_client.post(
            f"/businesses/{business_id}/customers",
            json={"name": "Manager-created customer"},
            cookies=manager_cookie,
        )
        assert manager_write.status_code == 201, manager_write.text
        viewer_write = api_client.post(
            f"/businesses/{business_id}/customers",
            json={"name": "Viewer write must be denied"},
            cookies=viewer_cookie,
        )
        assert viewer_write.status_code == 403

        manager_archive = api_client.post(
            f"/businesses/{business_id}/archive",
            json={"is_archived": True},
            cookies=manager_cookie,
        )
        assert manager_archive.status_code == 403

        manager_role_change = api_client.patch(
            f"/businesses/{business_id}/members/{viewer_id}",
            json={"role": "ACCOUNTANT"},
            cookies=manager_cookie,
        )
        assert manager_role_change.status_code == 403
        owner_role_change = api_client.patch(
            f"/businesses/{business_id}/members/{viewer_id}",
            json={"role": "ACCOUNTANT"},
            cookies=owner_cookie,
        )
        assert owner_role_change.status_code == 200, owner_role_change.text
        assert owner_role_change.json()["role"] == "ACCOUNTANT"

        owner_archive = api_client.post(
            f"/businesses/{business_id}/archive",
            json={"is_archived": True},
            cookies=owner_cookie,
        )
        assert owner_archive.status_code == 200, owner_archive.text
        assert owner_archive.json() == {
            "status": "ok",
            "business_id": business_id,
            "is_archived": True,
        }
        archived = api_client.get(f"/businesses/{business_id}", cookies=owner_cookie)
        assert archived.status_code == 200, archived.text
        assert archived.json()["is_archived"] is True

        owner_unarchive = api_client.post(
            f"/businesses/{business_id}/archive",
            json={"is_archived": False},
            cookies=owner_cookie,
        )
        assert owner_unarchive.status_code == 200, owner_unarchive.text
        assert owner_unarchive.json()["is_archived"] is False

"""
Middleware and Route Security Integration Tests (9 Deny-by-Default Cases).

Authoritative Acceptance Reference: ArthLens Build Handbook & Security Specification.
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events, Rate Limiting, and Route Security).

Test Cases:
1. Undeclared arbitrary route (/some/random/route -> 404/denied).
2. Undeclared HTTP method on declared route (PATCH /businesses -> 405/denied).
3. Valid public health route (/health -> 200).
4. Unauthenticated protected route (/businesses -> 401).
5. Authenticated but unauthorized route (non-member access to business -> 403).
6. Valid authorized business route (/businesses -> 200/201).
7. Admin-only route accessed by non-admin (/admin/users -> 403).
8. Parameterized route matching (/businesses/{id} -> 200/404 as appropriate).
9. Path-prefix confusion and trailing-slash edge cases (/businesses_extra -> 404, /businesses/ -> 401).
"""

import uuid
import pytest
from starlette.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def entrepreneur_user():
    user_id = str(uuid.uuid4())
    email = f"entrepreneur_{user_id[:8]}@example.com"
    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_security_hash",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"is_active": True},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    return {"id": user_id, "email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def non_member_user():
    user_id = str(uuid.uuid4())
    email = f"nonmember_{user_id[:8]}@example.com"
    repo = PostgresUserRepository()
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_security_hash",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"is_active": True},
    })
    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    return {"id": user_id, "email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def test_business(client, entrepreneur_user):
    payload = {
        "name": f"Secured Manufacturing Co {uuid.uuid4().hex[:6]}",
        "industry": "Manufacturing",
        "address": "Secured Ind Area, UP",
        "financial_year_start": "04-01",
        "currency": "INR",
    }
    res = client.post("/businesses", json=payload, headers=entrepreneur_user["headers"])
    assert res.status_code == 201
    return res.json()


# ------------------------------------------------------------------------------
# Case 1: Undeclared Arbitrary Route
# ------------------------------------------------------------------------------
def test_case_1_undeclared_arbitrary_route_denied(client):
    """An undeclared arbitrary route is rejected with 404 (or 403 for undeclared internal prefixes)."""
    response = client.get("/some/random/route")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    # Also verify private/internal undeclared paths return 403 deny-by-default
    res_internal = client.get("/internal/unregistered")
    assert res_internal.status_code == 403
    assert "deny-by-default" in res_internal.json()["detail"]


# ------------------------------------------------------------------------------
# Case 2: Undeclared HTTP Method on Declared Route
# ------------------------------------------------------------------------------
def test_case_2_undeclared_http_method_denied(client):
    """Calling an undeclared HTTP method (PATCH) on /businesses is denied with 405 Method Not Allowed."""
    response = client.patch("/businesses")
    assert response.status_code == 405, f"Expected 405, got {response.status_code}"


# ------------------------------------------------------------------------------
# Case 3: Valid Public Health Route
# ------------------------------------------------------------------------------
def test_case_3_valid_public_health_route(client):
    """Public health endpoints /health and /api/v1/health respond with 200 OK without credentials."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_v1 = client.get("/api/v1/health")
    assert res_v1.status_code == 200
    assert res_v1.json()["status"] == "healthy"


# ------------------------------------------------------------------------------
# Case 4: Unauthenticated Protected Route
# ------------------------------------------------------------------------------
def test_case_4_unauthenticated_protected_route_returns_401(client):
    """Protected endpoints like /businesses strictly return 401 when missing authentication credentials."""
    response = client.get("/businesses")
    assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    assert "Authentication required" in response.json()["detail"]


# ------------------------------------------------------------------------------
# Case 5: Authenticated but Unauthorized Route (Tenant Scoping)
# ------------------------------------------------------------------------------
def test_case_5_authenticated_unauthorized_route_returns_403(client, non_member_user, test_business):
    """An authenticated user who is not a member of the target business receives 403 Forbidden."""
    biz_id = test_business["id"]
    response = client.get(f"/businesses/{biz_id}", headers=non_member_user["headers"])
    assert response.status_code == 403, f"Expected 403 for non-member tenant access, got {response.status_code}"


# ------------------------------------------------------------------------------
# Case 6: Valid Authorized Business Route
# ------------------------------------------------------------------------------
def test_case_6_valid_authorized_business_route(client, entrepreneur_user):
    """An authenticated user with ENTREPRENEUR role can list businesses (200) and create one (201)."""
    # GET /businesses
    res_list = client.get("/businesses", headers=entrepreneur_user["headers"])
    assert res_list.status_code == 200
    assert isinstance(res_list.json(), list)

    # POST /businesses
    payload = {
        "name": f"Authorized Biz {uuid.uuid4().hex[:6]}",
        "industry": "Retail & Trading",
        "address": "Civil Lines, Prayagraj",
        "financial_year_start": "04-01",
        "currency": "INR",
    }
    res_create = client.post("/businesses", json=payload, headers=entrepreneur_user["headers"])
    assert res_create.status_code == 201
    assert res_create.json()["name"] == payload["name"]


# ------------------------------------------------------------------------------
# Case 7: Admin-Only Route Accessed by Non-Admin
# ------------------------------------------------------------------------------
def test_case_7_admin_only_route_accessed_by_non_admin_returns_403(client, entrepreneur_user):
    """Non-admin user (ENTREPRENEUR role) accessing administrative routes receives 403 Forbidden."""
    # /admin/users
    res_users = client.get("/admin/users", headers=entrepreneur_user["headers"])
    assert res_users.status_code == 403
    assert "Access forbidden: required role not held" in res_users.json()["detail"]

    # /admin/audit
    res_audit = client.get("/admin/audit", headers=entrepreneur_user["headers"])
    assert res_audit.status_code == 403


# ------------------------------------------------------------------------------
# Case 8: Parameterized Route Matching
# ------------------------------------------------------------------------------
def test_case_8_parameterized_route_matching(client, entrepreneur_user, test_business):
    """Parameterized routes like /businesses/{business_id} match correctly for member users."""
    biz_id = test_business["id"]
    response = client.get(f"/businesses/{biz_id}", headers=entrepreneur_user["headers"])
    assert response.status_code == 200
    assert response.json()["id"] == biz_id

    # Non-existent UUID matches route but yields 404
    non_existent_id = str(uuid.uuid4())
    res_missing = client.get(f"/businesses/{non_existent_id}", headers=entrepreneur_user["headers"])
    assert res_missing.status_code in (403, 404)


# ------------------------------------------------------------------------------
# Case 9: Path-Prefix Confusion and Trailing-Slash Edge Cases
# ------------------------------------------------------------------------------
def test_case_9_path_prefix_confusion_and_trailing_slash(client, entrepreneur_user):
    """
    Path-prefix confusion: /businesses_extra must not route to /businesses and returns 404.
    Trailing slash: /businesses/ does not bypass authentication and requires credentials.
    """
    # Prefix confusion
    res_prefix = client.get("/businesses_extra", headers=entrepreneur_user["headers"])
    assert res_prefix.status_code == 404

    # Trailing slash without credentials still requires authentication
    res_slash_noauth = client.get("/businesses/")
    assert res_slash_noauth.status_code == 401

    # Trailing slash with credentials routes cleanly
    res_slash_auth = client.get("/businesses/", headers=entrepreneur_user["headers"])
    assert res_slash_auth.status_code in (200, 307)


# ------------------------------------------------------------------------------
# Case 10: Dynamic Route Without Registered Policy Denied (Deny-by-Default)
# ------------------------------------------------------------------------------
def test_case_10_dynamic_route_without_policy_denied():
    """
    Dynamically registered route on the framework without a registered policy in
    EndpointPolicyRegistry is actively denied with 403 Forbidden.
    """
    app = create_app()

    @app.get("/unregistered-dynamic-backdoor")
    def unprotected_backdoor():
        return {"status": "vulnerable"}

    test_client = TestClient(app)
    res = test_client.get("/unregistered-dynamic-backdoor")
    assert res.status_code == 403
    assert "deny-by-default" in res.json()["detail"]


# ------------------------------------------------------------------------------
# Case 11: Production Documentation Blocked
# ------------------------------------------------------------------------------
def test_case_11_production_documentation_blocked(monkeypatch):
    """
    In production environment, documentation routes (/docs, /openapi.json, /redoc)
    return 404 Not Found to prevent information disclosure.
    """
    monkeypatch.setenv("ARTHLENS_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    app = create_app()
    test_client = TestClient(app)

    for doc_path in ("/docs", "/openapi.json", "/redoc"):
        res = test_client.get(doc_path)
        assert res.status_code == 404, f"Expected 404 for {doc_path} in production, got {res.status_code}"


# ------------------------------------------------------------------------------
# Case 12: CORS Preflight Allowed
# ------------------------------------------------------------------------------
def test_case_12_cors_preflight_options_allowed(client):
    """OPTIONS preflight requests pass through middleware without credentials."""
    res = client.options(
        "/businesses",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert res.status_code in (200, 204)

"""
Integration tests for public registration, session lifecycle, password recovery,
role administration, and scenario ownership/IDOR protection.
"""

import uuid

import pytest
from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from starlette.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _cookie_for(user_id: str, email: str, roles: list[str]) -> dict[str, str]:
    token, _ = create_access_token(user_id=user_id, email=email, roles=roles)
    return {get_auth_cookie_name(): token}


@pytest.mark.integration
def test_public_registration_and_session(client):
    unique_email = f"entrepreneur_{uuid.uuid4().hex[:8]}@example.com"
    reg_payload = {
        "full_name": "Test Entrepreneur",
        "email": unique_email,
        "password": "SecurePassword123!",
    }

    # 1. Register successfully
    res = client.post("/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == unique_email
    assert data["roles"] == ["ENTREPRENEUR"]
    assert data["full_name"] == "Test Entrepreneur"
    assert "access_token" in data

    # Verify session cookie was set
    cookie_name = get_auth_cookie_name()
    assert cookie_name in res.cookies

    # 2. Duplicate registration rejected with 409
    res_dup = client.post("/auth/register", json=reg_payload)
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"].lower()

    # 3. Weak password rejected
    res_weak = client.post("/auth/register", json={
        "full_name": "Weak Pwd",
        "email": f"weak_{uuid.uuid4().hex[:6]}@example.com",
        "password": "short",
    })
    assert res_weak.status_code in (400, 422)

    # 4. Invalid email rejected
    res_bad_email = client.post("/auth/register", json={
        "full_name": "Bad Email",
        "email": "not-an-email",
        "password": "ValidPassword123!",
    })
    assert res_bad_email.status_code in (400, 422)


@pytest.mark.integration
def test_deactivated_user_cannot_login_or_use_session(client):
    unique_email = f"deact_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/auth/register", json={
        "full_name": "Deact User",
        "email": unique_email,
        "password": "Password123!",
    })
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]
    active_token = reg_res.json()["access_token"]
    cookie = {get_auth_cookie_name(): active_token}

    # Verify session works initially
    me_ok = client.get("/auth/me", cookies=cookie)
    assert me_ok.status_code == 200

    # Deactivate user
    repo = PostgresUserRepository()
    repo.deactivate_user(user_id)

    # 1. Existing active session cookie must now immediately receive 401 Unauthorized
    me_denied = client.get("/auth/me", cookies=cookie)
    assert me_denied.status_code == 401
    assert "deactivated" in me_denied.json()["detail"].lower()

    # 2. Attempt login -> 403 Forbidden
    login_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!",
    })
    assert login_res.status_code == 403
    assert "deactivated" in login_res.json()["detail"].lower()


@pytest.mark.integration
def test_logout_revokes_token(client):
    unique_email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={
        "full_name": "Logout User",
        "email": unique_email,
        "password": "Password123!",
    })

    # Log in
    login_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "Password123!",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    cookie = {get_auth_cookie_name(): token}

    # Verify session active
    me_res = client.get("/auth/me", cookies=cookie)
    assert me_res.status_code == 200

    # Log out
    logout_res = client.post("/auth/logout", cookies=cookie)
    assert logout_res.status_code == 200

    # Subsequent request using the revoked token must fail with 401
    me_after = client.get("/auth/me", cookies=cookie)
    assert me_after.status_code == 401


@pytest.mark.integration
def test_password_recovery_flow(client):
    unique_email = f"recovery_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={
        "full_name": "Recovery User",
        "email": unique_email,
        "password": "OldPassword123!",
    })

    # Log in before reset to obtain an active session cookie
    initial_login = client.post("/auth/login", json={
        "email": unique_email,
        "password": "OldPassword123!",
    })
    assert initial_login.status_code == 200
    old_token = initial_login.json()["access_token"]
    old_cookie = {get_auth_cookie_name(): old_token}

    # Session works before reset
    assert client.get("/auth/me", cookies=old_cookie).status_code == 200

    # Request password reset
    req_res = client.post("/auth/password-reset/request", json={"email": unique_email})
    assert req_res.status_code == 200
    # In dev mode, verify clearly labeled dev recovery details are surfaced
    assert "dev_recovery_token" in req_res.json()
    reset_token = req_res.json()["dev_recovery_token"]
    assert reset_token is not None

    # Confirm password reset
    confirm_res = client.post("/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "BrandNewPassword123!",
    })
    assert confirm_res.status_code == 200

    # 1. Existing session issued prior to password reset must now be revoked
    old_session_check = client.get("/auth/me", cookies=old_cookie)
    assert old_session_check.status_code == 401
    assert "revoked" in old_session_check.json()["detail"].lower()

    # 2. Token must be single-use: repeating confirmation must fail with 400
    repeat_res = client.post("/auth/password-reset/confirm", json={
        "token": reset_token,
        "new_password": "AnotherPassword123!",
    })
    assert repeat_res.status_code == 400

    # 3. Log in with old password fails
    fail_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "OldPassword123!",
    })
    assert fail_res.status_code == 401

    # 4. Log in with new password succeeds
    ok_res = client.post("/auth/login", json={
        "email": unique_email,
        "password": "BrandNewPassword123!",
    })
    assert ok_res.status_code == 200


@pytest.mark.integration
def test_admin_role_management_and_cannot_demote_last_admin(client):
    user_repo = PostgresUserRepository()

    # Create target entrepreneur
    ent_id = str(uuid.uuid4())
    ent_email = f"ent_{uuid.uuid4().hex[:6]}@example.com"
    user_repo.save({
        "id": ent_id,
        "email": ent_email,
        "password_hash": "dummy_hash",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"is_active": True},
    })

    # Find an existing admin or create one
    admin_id = str(uuid.uuid4())
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    user_repo.save({
        "id": admin_id,
        "email": admin_email,
        "password_hash": "dummy_hash",
        "roles": [Role.ADMIN.value],
        "quota_counters": {"is_active": True},
    })
    admin_cookie = _cookie_for(admin_id, admin_email, [Role.ADMIN.value])

    # Admin promotes target to STEWARD
    promo_res = client.post(f"/admin/users/{ent_id}/role", json={"role": "STEWARD"}, cookies=admin_cookie)
    assert promo_res.status_code == 200
    assert promo_res.json()["roles"] == ["STEWARD"]

    # Now demote all other admins so exactly one remains
    total_admins = user_repo.count_active_admins()
    while total_admins > 1:
        # Find another admin and demote them
        with user_repo._get_session() as session:
            from backend.arthlens.infra.models import UserModel, UserRoleModel
            from sqlalchemy import select
            stmt = (
                select(UserModel.id)
                .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
                .where(UserRoleModel.role_id == "ADMIN", UserModel.id != uuid.UUID(admin_id))
            )
            other_admin = session.execute(stmt).scalars().first()
            if not other_admin:
                break
        user_repo.set_user_roles(other_admin, ["ENTREPRENEUR"])
        total_admins = user_repo.count_active_admins()

    # Now admin_id is the sole active admin
    assert user_repo.count_active_admins() == 1

    # Attempt to demote the sole administrator -> 400 Bad Request
    demote_res = client.post(f"/admin/users/{admin_id}/role", json={"role": "ENTREPRENEUR"}, cookies=admin_cookie)
    assert demote_res.status_code == 400
    assert "last active administrator" in demote_res.json()["detail"].lower()

    # Attempt to deactivate the sole administrator -> 400 Bad Request
    deact_res = client.post(f"/admin/users/{admin_id}/deactivate", cookies=admin_cookie)
    assert deact_res.status_code == 400
    assert "last active administrator" in deact_res.json()["detail"].lower()


@pytest.mark.integration
def test_scenario_crud_and_idor_protection(client):
    # Register User A
    email_a = f"usera_{uuid.uuid4().hex[:8]}@example.com"
    res_a = client.post("/auth/register", json={
        "full_name": "User A",
        "email": email_a,
        "password": "Password123!",
    })
    assert res_a.status_code == 201
    cookie_a = {get_auth_cookie_name(): res_a.json()["access_token"]}

    # Register User B
    email_b = f"userb_{uuid.uuid4().hex[:8]}@example.com"
    res_b = client.post("/auth/register", json={
        "full_name": "User B",
        "email": email_b,
        "password": "Password123!",
    })
    assert res_b.status_code == 201
    cookie_b = {get_auth_cookie_name(): res_b.json()["access_token"]}

    # 1. User A creates a scenario
    client.cookies.clear()
    create_res = client.post("/scenarios", json={
        "name": "User A Bakery Scenario",
        "scenario": {"capital": 500000, "location": "in:district:120"},
    }, cookies=cookie_a)
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]

    # 2. User A gets the scenario
    client.cookies.clear()
    get_res = client.get(f"/scenarios/{scenario_id}", cookies=cookie_a)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "User A Bakery Scenario"

    # 3. User B attempts to read User A's scenario -> 404 (IDOR defense)
    client.cookies.clear()
    get_b = client.get(f"/scenarios/{scenario_id}", cookies=cookie_b)
    assert get_b.status_code == 404

    # 4. User B attempts to update User A's scenario -> 404
    client.cookies.clear()
    put_b = client.put(f"/scenarios/{scenario_id}", json={"name": "Hacked"}, cookies=cookie_b)
    assert put_b.status_code == 404

    # 5. User B attempts to delete User A's scenario -> 404
    client.cookies.clear()
    del_b = client.delete(f"/scenarios/{scenario_id}", cookies=cookie_b)
    assert del_b.status_code == 404

    # 6. User A updates their own scenario
    client.cookies.clear()
    put_a = client.put(f"/scenarios/{scenario_id}", json={
        "name": "Updated Bakery",
        "scenario": {"capital": 750000, "location": "in:district:120"},
    }, cookies=cookie_a)
    assert put_a.status_code == 200
    assert put_a.json()["name"] == "Updated Bakery"

    client.cookies.clear()
    branch_res = client.post(
        f"/scenarios/{scenario_id}/branch",
        json={"name": "Updated Bakery Branch"},
        cookies=cookie_a,
    )
    assert branch_res.status_code == 201
    branch = branch_res.json()
    assert branch["parent_id"] == scenario_id
    assert branch["scenario"]["branch_lineage"]["parent_scenario_id"] == scenario_id
    client.cookies.clear()
    assert client.delete(f"/scenarios/{branch['id']}", cookies=cookie_a).status_code == 200

    # 7. User A deletes their scenario
    client.cookies.clear()
    del_a = client.delete(f"/scenarios/{scenario_id}", cookies=cookie_a)
    assert del_a.status_code == 200

    # Scenario now 404 for User A
    client.cookies.clear()
    assert client.get(f"/scenarios/{scenario_id}", cookies=cookie_a).status_code == 404

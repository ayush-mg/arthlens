from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.arthlens.api.business import enforce_archived_workspace_read_only
from backend.arthlens.domain.business import BusinessMembership, BusinessRole
from backend.arthlens.security.rbac import AuthenticatedUser
from backend.arthlens.services.business_service import (
    BusinessService,
    InvalidOperationError,
    UnauthorizedBusinessAccessError,
)
from scripts.seed_demo_accounts import seed_demo_accounts


class FakeMembershipRepository:
    def __init__(self, memberships: list[BusinessMembership]):
        self.rows = {(row.business_id, row.user_id): row for row in memberships}

    def get_membership(self, business_id: uuid.UUID, user_id: uuid.UUID):
        return self.rows.get((business_id, user_id))

    def update_member_role(self, business_id: uuid.UUID, user_id: uuid.UUID, role: BusinessRole):
        row = self.rows.get((business_id, user_id))
        if not row or not row.is_active:
            return None
        row.role = role
        return row


def make_membership(business_id: uuid.UUID, user_id: uuid.UUID, role: BusinessRole) -> BusinessMembership:
    return BusinessMembership(
        id=uuid.uuid4(), business_id=business_id, user_id=user_id, role=role,
    )


def test_admin_has_workspace_admin_permissions_and_analyst_stays_read_only():
    business_id, admin_id, analyst_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    repository = FakeMembershipRepository([
        make_membership(business_id, admin_id, BusinessRole.ADMIN),
        make_membership(business_id, analyst_id, BusinessRole.ANALYST),
    ])
    service = BusinessService.__new__(BusinessService)
    service.business_repo = repository

    assert service.verify_access(business_id, admin_id, [BusinessRole.OWNER]).role == BusinessRole.ADMIN
    assert service.verify_access(business_id, analyst_id).role == BusinessRole.ANALYST
    with pytest.raises(UnauthorizedBusinessAccessError):
        service.verify_access(business_id, analyst_id, [BusinessRole.MANAGER])


def test_demo_seed_requires_an_explicit_production_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    with pytest.raises(SystemExit, match="Refusing to seed demo accounts in production"):
        seed_demo_accounts()


def test_owner_can_change_member_role_but_cannot_change_owner(monkeypatch):
    business_id, owner_id, member_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    owner = make_membership(business_id, owner_id, BusinessRole.OWNER)
    member = make_membership(business_id, member_id, BusinessRole.MANAGER)
    repository = FakeMembershipRepository([owner, member])
    service = BusinessService.__new__(BusinessService)
    service.business_repo = repository
    recorded = []
    import backend.arthlens.security.audit as audit_module
    monkeypatch.setattr(audit_module, "get_audit_service", lambda: SimpleNamespace(
        record_event=lambda **kwargs: recorded.append(kwargs),
    ))

    updated = service.update_member_role(business_id, owner_id, member_id, BusinessRole.ANALYST)
    assert updated.role == BusinessRole.ANALYST
    assert recorded[-1]["payload"] == {"old_role": "MANAGER", "new_role": "ANALYST"}

    with pytest.raises(InvalidOperationError, match="owner's role"):
        service.update_member_role(business_id, owner_id, owner_id, BusinessRole.ADMIN)
    with pytest.raises(InvalidOperationError, match="cannot be assigned"):
        service.update_member_role(business_id, owner_id, member_id, BusinessRole.OWNER)


def make_request(method: str, path: str, business_id: uuid.UUID) -> Request:
    return Request({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
        "query_string": b"", "headers": [], "client": ("127.0.0.1", 8000),
        "server": ("test", 80), "path_params": {"business_id": str(business_id)},
    })


def test_archived_workspaces_reject_writes_but_allow_reads_and_unarchive():
    business_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user = AuthenticatedUser(id=str(user_id), email="owner@example.test", roles=(), jti="test")
    service = SimpleNamespace(get_business=lambda *_: SimpleNamespace(is_archived=True))

    with pytest.raises(HTTPException) as exc:
        enforce_archived_workspace_read_only(
            make_request("POST", f"/businesses/{business_id}/customers", business_id), user, service,
        )
    assert exc.value.status_code == 409

    enforce_archived_workspace_read_only(
        make_request("GET", f"/businesses/{business_id}/customers", business_id), user, service,
    )
    enforce_archived_workspace_read_only(
        make_request("POST", f"/businesses/{business_id}/archive", business_id), user, service,
    )

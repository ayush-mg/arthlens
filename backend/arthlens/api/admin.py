"""
Administrative Endpoints (/admin/users, /admin/audit).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from backend.arthlens.infra.database import get_engine
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/admin", tags=["Administration"])


class UpdateRoleRequest(BaseModel):
    role: str = Field(..., description="Target role name (ENTREPRENEUR, STEWARD, ADMIN)")


@router.get("/users")
def list_admin_users(
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> List[Dict[str, Any]]:
    """Retrieve users, assigned roles, and quotas (Admin only)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
        SELECT u.id, u.email, u.quota_counters, u.created_at,
               COALESCE(array_agg(ur.role_id) FILTER (WHERE ur.role_id IS NOT NULL), '{}') AS roles
        FROM users u
        LEFT JOIN user_roles ur ON u.id = ur.user_id
        GROUP BY u.id, u.email, u.quota_counters, u.created_at
        ORDER BY u.created_at DESC;
        """)).mappings().all()

        return [
            {
                "id": str(r["id"]),
                "email": r["email"],
                "quota_counters": r["quota_counters"],
                "roles": list(r["roles"]),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]


@router.get("/audit")
def list_admin_audit(
    limit: int = 100,
    offset: int = 0,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> List[Dict[str, Any]]:
    """Inspect append-only audit trail (Admin only)."""
    audit = get_audit_service()
    return audit.list_events(limit=limit, offset=offset)


@router.get("/audit-events")
def list_admin_audit_events(
    limit: int = 100,
    offset: int = 0,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> List[Dict[str, Any]]:
    """Inspect append-only audit trail alias (Admin only)."""
    audit = get_audit_service()
    return audit.list_events(limit=limit, offset=offset)


@router.get("/sources")
def list_admin_sources(
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN, Role.STEWARD)),
) -> List[Dict[str, Any]]:
    """List registered authoritative data sources and snapshot versions."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
        SELECT s.id, s.name, s.description, s.status, s.licence_text, s.max_age_days,
               COUNT(sv.id) AS version_count
        FROM sources s
        LEFT JOIN source_versions sv ON s.id = sv.source_id
        GROUP BY s.id, s.name, s.description, s.status, s.licence_text, s.max_age_days
        ORDER BY s.id;
        """)).mappings().all()

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "status": r["status"],
                "licence_text": r["licence_text"],
                "max_age_days": r["max_age_days"],
                "version_count": int(r["version_count"]),
            }
            for r in rows
        ]


@router.post("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    body: UpdateRoleRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> Dict[str, Any]:
    """Promote or demote user role. Prevents removing the last active administrator."""
    target_role = body.role.upper().strip()
    valid_roles = {Role.ENTREPRENEUR.value, Role.STEWARD.value, Role.ADMIN.value}
    if target_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{target_role}'. Must be one of: {sorted(valid_roles)}",
        )

    repo = PostgresUserRepository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    current_roles = user.get("roles") or []
    if "ADMIN" in current_roles and target_role != "ADMIN":
        active_admins = repo.count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last active administrator.",
            )

    repo.set_user_roles(user_id, [target_role])

    audit = get_audit_service()
    audit.record_event(
        actor=current_user.id,
        action="ADMIN_UPDATE_ROLE",
        target=f"user:{user_id}",
        payload={"new_role": target_role, "previous_roles": current_roles},
    )

    return {"status": "ok", "user_id": user_id, "roles": [target_role]}


@router.post("/users/{user_id}/deactivate")
def deactivate_user_account(
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> Dict[str, Any]:
    """Deactivate user account. Prevents deactivating the last active administrator."""
    repo = PostgresUserRepository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if "ADMIN" in (user.get("roles") or []):
        active_admins = repo.count_active_admins()
        if active_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active administrator.",
            )

    repo.deactivate_user(user_id)

    audit = get_audit_service()
    audit.record_event(
        actor=current_user.id,
        action="ADMIN_DEACTIVATE_USER",
        target=f"user:{user_id}",
        payload={},
    )

    return {"status": "ok", "user_id": user_id, "is_active": False}


@router.post("/users/{user_id}/activate")
def activate_user_account(
    user_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ADMIN)),
) -> Dict[str, Any]:
    """Reactivate a previously deactivated user account."""
    repo = PostgresUserRepository()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    repo.activate_user(user_id)

    audit = get_audit_service()
    audit.record_event(
        actor=current_user.id,
        action="ADMIN_ACTIVATE_USER",
        target=f"user:{user_id}",
        payload={},
    )

    return {"status": "ok", "user_id": user_id, "is_active": True}

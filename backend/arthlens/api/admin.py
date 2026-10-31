"""
Administrative Endpoints (/admin/users, /admin/audit).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from backend.arthlens.infra.database import get_engine
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role
from sqlalchemy import text

router = APIRouter(prefix="/admin", tags=["Administration"])


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

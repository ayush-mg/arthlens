"""
Policy Rules API Endpoints (/policy/rules).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.arthlens.infra.repositories import PostgresPolicyRuleRepository
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/policy", tags=["Policy Rules"])


class CreatePolicyRuleRequest(BaseModel):
    scheme_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    rule_ast: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = "DRAFT"


@router.get("/rules")
def list_policy_rules(
    scheme_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> List[Dict[str, Any]]:
    """List policy rule versions (All authenticated roles)."""
    repo = PostgresPolicyRuleRepository()
    if scheme_id:
        return repo.list_rules_by_scheme(scheme_id)
    return []


@router.post("/rules", status_code=status.HTTP_201_CREATED)
def create_policy_rule(
    body: CreatePolicyRuleRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.STEWARD)),
) -> Dict[str, Any]:
    """Create draft policy rule (Steward role only)."""
    repo = PostgresPolicyRuleRepository()
    rule_id = repo.save_rule({
        "scheme_id": body.scheme_id,
        "version": body.version,
        "rule_ast": body.rule_ast,
        "status": body.status or "DRAFT",
    })
    return {
        "id": rule_id,
        "scheme_id": body.scheme_id,
        "version": body.version,
        "status": body.status or "DRAFT",
    }

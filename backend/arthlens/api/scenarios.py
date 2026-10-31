"""
Scenarios API Endpoints (/scenarios, /scenarios/{id}/branch).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.arthlens.infra.repositories import PostgresScenarioRepository
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scenario: Dict[str, Any] = Field(default_factory=dict)


class BranchScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_scenario(
    body: CreateScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Create a new user scenario (Entrepreneur only)."""
    repo = PostgresScenarioRepository()
    scenario_id = repo.save_scenario({
        "owner_id": current_user.id,
        "name": body.name,
        "scenario": body.scenario,
    })
    return {
        "id": scenario_id,
        "name": body.name,
        "owner_id": current_user.id,
    }


@router.post("/{scenario_id}/branch", status_code=status.HTTP_201_CREATED)
def branch_scenario(
    scenario_id: str,
    body: BranchScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Branch an existing scenario (Owner only, IDOR safe: returns 404 on ownership mismatch)."""
    repo = PostgresScenarioRepository()
    parent = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    branch_id = repo.save_scenario({
        "owner_id": current_user.id,
        "name": body.name,
        "scenario": dict(parent.get("scenario") or {}),
    })
    return {
        "id": branch_id,
        "parent_id": scenario_id,
        "name": body.name,
        "owner_id": current_user.id,
    }

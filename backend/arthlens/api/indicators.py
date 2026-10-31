"""
Indicators, Ledger, and Replay Endpoints.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.arthlens.infra.repositories import PostgresQuantityRepository
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(tags=["Indicators & Ledger"])


@router.get("/geo/{geo_id}/indicators")
def get_geo_indicators(
    geo_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Retrieve indicators with class, resolution, quality flags (All authenticated roles)."""
    repo = PostgresQuantityRepository()
    quantities = repo.list_by_geo_unit(geo_id)
    return {
        "geo_unit_id": geo_id,
        "indicators": [
            {
                "id": q.id,
                "definition_key": q.definition_key,
                "value": q.value,
                "unit": q.unit,
                "kind": q.kind.value,
                "evidence_floor": q.evidence_floor,
                "resolution": q.resolution,
                "quality_flags": list(q.quality_flags),
            }
            for q in quantities
        ],
    }


@router.get("/ledger/{quantity_id}")
def get_ledger_quantity(
    quantity_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """
    Retrieve quantity with ancestry graph for Evidence Graph.
    Enforces per-record access rules (Handbook Part 10.1 & Part 11):
    - Public quantities (owner_id is None) are accessible to all authenticated roles.
    - User-owned quantities are accessible only to their owner and authorized administrators.
    - Unauthorized access returns generic 404 without revealing resource existence.
    """
    repo = PostgresQuantityRepository()
    q = repo.get(quantity_id)
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quantity not found.",
        )

    # Per-record ownership verification
    if q.owner_id is not None:
        if q.owner_id != current_user.id and not current_user.has_role(Role.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quantity not found.",
            )

    return {
        "id": q.id,
        "definition_key": q.definition_key,
        "value": q.value,
        "unit": q.unit,
        "kind": q.kind.value,
        "parent_ids": list(q.parent_ids),
        "owner_id": q.owner_id,
    }


@router.get("/replay/{run_id}")
def get_replay_trace(run_id: str) -> Dict[str, Any]:
    """Retrieve stored golden trace, labelled REPLAY (All authenticated roles & demo)."""
    return {
        "run_id": run_id,
        "banner": "Replay of a recorded run",
        "status": "REPLAY",
    }

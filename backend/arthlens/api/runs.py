"""
Runs API Endpoints (/runs, /runs/{id}, /runs/{id}/events, /runs/{id}/answer, /runs/{id}/approve).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.arthlens.infra.config import (
    get_daily_run_quota,
    get_default_run_cost_reservation,
    get_max_cost_usd_per_day,
    get_max_cost_usd_per_run,
)
from backend.arthlens.infra.repositories import PostgresScenarioRepository, PostgresUserRepository
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/runs", tags=["Agent & Simulation Runs"])


class CreateRunRequest(BaseModel):
    scenario_id: Optional[str] = None
    objective: Dict[str, Any] = Field(default_factory=dict)
    seed: Optional[int] = 42
    max_cost_usd: Optional[float] = Field(default=None, ge=0.0)
    estimated_cost_usd: Optional[float] = Field(default=None, ge=0.0)


class AnswerRunRequest(BaseModel):
    answer: Any


class ApproveRunRequest(BaseModel):
    approved: bool


@router.post("", status_code=status.HTTP_201_CREATED)
def create_run(
    body: CreateRunRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """
    Create a new simulation/agent run.
    Enforces entrepreneur per-run cost cap, daily run quota, and accumulated daily budget cap.
    """
    user_repo = PostgresUserRepository()
    scenario_repo = PostgresScenarioRepository()

    # 1. Enforce per-run cost cap before execution (Handbook Part 8.3 baseline $0.25)
    per_run_cap = get_max_cost_usd_per_run()
    if body.max_cost_usd is not None and body.max_cost_usd > per_run_cap:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested run budget (${body.max_cost_usd:.2f}) exceeds per-run cost cap (${per_run_cap:.2f}).",
        )
    if body.estimated_cost_usd is not None and body.estimated_cost_usd > per_run_cap:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Estimated run cost (${body.estimated_cost_usd:.2f}) exceeds per-run cost cap (${per_run_cap:.2f}).",
        )

    # 2. Server-side authoritative cost reservation (cannot be lowered by client manipulation)
    server_baseline = get_default_run_cost_reservation()
    if body.estimated_cost_usd is not None:
        run_cost = max(server_baseline, float(body.estimated_cost_usd))
    else:
        run_cost = server_baseline

    if body.max_cost_usd is not None and body.max_cost_usd < run_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requested budget (${body.max_cost_usd:.2f}) is below minimum server reservation (${run_cost:.2f}).",
        )

    # 3. Atomically check and reserve run and cost in user's quota counters
    daily_quota_limit = get_daily_run_quota()
    daily_cost_limit = get_max_cost_usd_per_day()

    allowed, quota, reason = user_repo.check_and_reserve_quota(
        current_user.id,
        runs=1,
        cost=run_cost,
        max_runs=daily_quota_limit,
        max_cost=daily_cost_limit,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason,
        )

    # 4. Resolve or create parent scenario and simulation run with refund rollback on failure
    try:
        scenario_id = body.scenario_id
        if not scenario_id:
            scenario_id = scenario_repo.save_scenario({
                "owner_id": current_user.id,
                "name": f"Default Scenario for Run {uuid.uuid4().hex[:6]}",
                "scenario": body.objective,
            })
        else:
            # Verify scenario ownership
            scen = scenario_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
            if not scen:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Scenario not found.",
                )

        run_id = scenario_repo.save_simulation_run({
            "scenario_id": scenario_id,
            "seed": body.seed or 42,
            "model_version": "1.0.0",
            "data_version_ids": [],
            "status": "PENDING",
        })
    except Exception:
        # Reconcile / refund quota counters on setup failure
        user_repo.refund_quota_counters(current_user.id, runs=1, cost=run_cost)
        raise

    return {
        "id": run_id,
        "scenario_id": scenario_id,
        "status": "PENDING",
        "owner_id": current_user.id,
    }


@router.get("/{run_id}")
def get_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.ADMIN)),
) -> Dict[str, Any]:
    """
    Retrieve run status and summary.
    Owner or Admin only (IDOR safe: returns 404 Not Found on ownership mismatch).
    """
    scenario_repo = PostgresScenarioRepository()
    if current_user.has_role(Role.ADMIN):
        run = scenario_repo.get_simulation_run(run_id)
    else:
        run = scenario_repo.get_run_by_id_and_owner(run_id, current_user.id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found.",
        )
    return run


@router.get("/{run_id}/events")
def get_run_events(
    run_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.ADMIN)),
) -> Dict[str, Any]:
    """
    Retrieve run event stream.
    Owner or Admin only (IDOR safe: returns 404 Not Found on ownership mismatch).
    """
    scenario_repo = PostgresScenarioRepository()
    if not current_user.has_role(Role.ADMIN):
        run = scenario_repo.get_run_by_id_and_owner(run_id, current_user.id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found.",
            )
    else:
        run = scenario_repo.get_simulation_run(run_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found.",
            )

    return {
        "run_id": run_id,
        "events": [
            {"step_index": 0, "event_type": "INIT", "status": "RUNNING"},
        ],
    }


@router.post("/{run_id}/answer")
def answer_run_question(
    run_id: str,
    body: AnswerRunRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """
    Provide user answer for a pending question (Owner only, IDOR safe).
    """
    scenario_repo = PostgresScenarioRepository()
    run = scenario_repo.get_run_by_id_and_owner(run_id, current_user.id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found.",
        )
    return {"id": run_id, "status": "ANSWERED", "answer": body.answer}


@router.post("/{run_id}/approve")
def approve_run_action(
    run_id: str,
    body: ApproveRunRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD)),
) -> Dict[str, Any]:
    """
    Approve or reject a gated action (Owner or Steward as configured, IDOR safe).
    """
    scenario_repo = PostgresScenarioRepository()
    if current_user.has_role(Role.STEWARD):
        run = scenario_repo.get_simulation_run(run_id)
    else:
        run = scenario_repo.get_run_by_id_and_owner(run_id, current_user.id)

    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found.",
        )
    return {"id": run_id, "status": "APPROVED" if body.approved else "REJECTED"}

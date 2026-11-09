"""Authenticated API for persisted agent-run lifecycle records."""

import asyncio
import json
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from backend.arthlens.agent.followups import UnresolvedGap, tasks_from_unresolved_gaps
from backend.arthlens.agent.run_lifecycle import TERMINAL_RUN_STATES, AgentRunState
from backend.arthlens.agent.worker import execute_agent_run_background
from backend.arthlens.infra.repositories import (
    PostgresAgentRunRepository,
    PostgresFollowupTaskRepository,
)
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role

router = APIRouter(prefix="/agent-runs", tags=["Agent Runs"])


class CreateAgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: dict[str, Any] = Field(default_factory=dict)


class CreateFollowupTasksRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unresolved_gaps: list[UnresolvedGap] = Field(min_length=1, max_length=100)


class UpdateTaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    priority: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
def create_agent_run(
    body: CreateAgentRunRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> dict[str, Any]:
    """Persist a new run without claiming that an orchestration worker has started."""
    repository = PostgresAgentRunRepository()
    objective_payload = dict(body.objective)
    if "objective" not in objective_payload and "goal" in objective_payload:
        objective_payload["objective"] = str(objective_payload["goal"])
    run_id = repository.create_run(current_user.id, objective_payload)
    run = repository.get_run(run_id, current_user.id)
    if run is None:
        raise RuntimeError("Newly created agent run could not be retrieved.")
    return run


@router.post("/{run_id}/start", status_code=status.HTTP_202_ACCEPTED)
def start_agent_run(
    run_id: str,
    background_tasks: BackgroundTasks,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> dict[str, Any]:
    """Start background execution of a persisted agent run."""
    repository = PostgresAgentRunRepository()
    run = repository.get_run(run_id, current_user.id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    if run["state"] != AgentRunState.CREATED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run cannot be started from state {run['state']}.",
        )
    background_tasks.add_task(execute_agent_run_background, run_id)
    return {"status": "started", "run_id": run_id}


@router.post("/{run_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_agent_run_tasks(
    run_id: str,
    body: CreateFollowupTasksRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> list[dict[str, Any]]:
    """Persist explicit follow-up tasks for an entrepreneur-owned agent run."""
    repository = PostgresFollowupTaskRepository()
    try:
        return repository.create_for_run(
            run_id,
            current_user.id,
            tasks_from_unresolved_gaps(body.unresolved_gaps),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        ) from exc


@router.get("/{run_id}/tasks")
def list_agent_run_tasks(
    run_id: str,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.ADMIN)
    ),
) -> list[dict[str, Any]]:
    """List run tasks only to the owner or an administrator."""
    owner_id = None if current_user.has_role(Role.ADMIN) else current_user.id
    tasks = PostgresFollowupTaskRepository().list_for_run(run_id, owner_id)
    if tasks is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    return tasks


@router.patch("/{run_id}/tasks/{task_id}")
def update_agent_run_task(
    run_id: str,
    task_id: str,
    body: UpdateTaskRequest,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.ADMIN)
    ),
) -> dict[str, Any]:
    """Update task status or priority for an owned agent run."""
    if body.status is None and body.priority is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of status or priority must be provided.",
        )
    owner_id = None if current_user.has_role(Role.ADMIN) else current_user.id
    repository = PostgresFollowupTaskRepository()
    try:
        return repository.update_task(
            run_id=run_id,
            task_id=task_id,
            owner_id=owner_id,
            status=body.status,
            priority=body.priority,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run or task not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{run_id}")
def get_agent_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.ADMIN)
    ),
) -> dict[str, Any]:
    """Retrieve a run only for its owner or an administrator."""
    repository = PostgresAgentRunRepository()
    owner_id = None if current_user.has_role(Role.ADMIN) else current_user.id
    run = repository.get_run(run_id, owner_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    return run


@router.get("/{run_id}/events")
def get_agent_run_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.ADMIN)
    ),
) -> dict[str, Any]:
    """Return persisted events after a sequence cursor; no synthetic events are emitted."""
    repository = PostgresAgentRunRepository()
    owner_id = None if current_user.has_role(Role.ADMIN) else current_user.id
    run = repository.get_run(run_id, owner_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )
    events = repository.list_events(
        run_id,
        after_sequence=after_sequence,
        limit=limit,
    )
    next_sequence = events[-1]["seq"] if events else after_sequence
    return {
        "run_id": run["id"],
        "state": AgentRunState(run["state"]).value,
        "events": events,
        "next_sequence": next_sequence,
    }


@router.get("/{run_id}/events/stream")
async def stream_agent_run_events(
    run_id: str,
    request: Request,
    after_sequence: int = Query(default=0, ge=0),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    current_user: AuthenticatedUser = Depends(
        require_roles(Role.ENTREPRENEUR, Role.ADMIN)
    ),
) -> StreamingResponse:
    """Stream persisted run events as SSE, resuming after the supplied event ID."""
    cursor = after_sequence
    if last_event_id is not None:
        try:
            cursor = int(last_event_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last-Event-ID must be a non-negative event sequence.",
            ) from exc
        if cursor < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last-Event-ID must be a non-negative event sequence.",
            )

    repository = PostgresAgentRunRepository()
    owner_id = None if current_user.has_role(Role.ADMIN) else current_user.id
    run = repository.get_run(run_id, owner_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )

    async def event_stream():
        nonlocal cursor
        while not await request.is_disconnected():
            events = repository.list_events(run_id, after_sequence=cursor, limit=100)
            for event in events:
                cursor = event["seq"]
                encoded_event = jsonable_encoder(event)
                data = json.dumps(encoded_event, separators=(",", ":"), ensure_ascii=False)
                yield (
                    f"id: {event['seq']}\n"
                    f"event: {event['type']}\n"
                    f"data: {data}\n\n"
                )

            latest_run = repository.get_run(run_id, owner_id)
            if latest_run is None:
                return
            if (
                AgentRunState(latest_run["state"]) in TERMINAL_RUN_STATES
                and not events
            ):
                # The terminal state and terminal event commit together, but a
                # concurrent commit may land between the first event query and
                # this state read. Recheck before closing so that event is not lost.
                if repository.list_events(run_id, after_sequence=cursor, limit=100):
                    continue
                return
            if not events:
                yield ": keep-alive\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

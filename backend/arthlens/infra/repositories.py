"""
PostgreSQL-backed Repository Implementations for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import json
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from sqlalchemy import delete, func, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.arthlens.agent.budgets import (
    RunBudgetDecision,
    RunBudgetLimits,
    RunBudgetReservation,
)
from backend.arthlens.agent.checkpoints import RunStepCheckpoint
from backend.arthlens.agent.run_lifecycle import (
    TERMINAL_RUN_STATES,
    AgentRunEvent,
    AgentRunState,
    IllegalRunTransition,
    transition_run_state,
)
from backend.arthlens.data.models import SourceRecord
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
)
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ConflictingGeoUnitError,
    GeoUnitRepository,
    ImmutableQuantityError,
    OrphanedGeoUnitError,
    PolicyRuleRepository,
    QuantityRepository,
    ScenarioRepository,
    SourceRecordRepository,
    SourceRepository,
    UserAlreadyExistsError,
    UserRepository,
)
from backend.arthlens.domain.simulation import (
    SimulationMetadata,
    validate_and_convert_seed,
)
from backend.arthlens.infra.config import get_max_cost_usd_per_run
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    AgentRunModel,
    AgentRunStepModel,
    GeoUnitModel,
    PolicyDocumentModel,
    PolicyEvaluationModel,
    PolicyRuleModel,
    QuantityModel,
    RunEventModel,
    ScenarioComparisonModel,
    ScenarioModel,
    SimulationRunModel,
    SourceModel,
    SourceRecordModel,
    SourceVersionModel,
    TaskModel,
    UserModel,
    UserRoleModel,
)
from backend.arthlens.policy.serialization import parse_rule_ast, rule_facts, serialize_rule_ast

GEOMETRY_STATUS_RANK: Dict[str, int] = {
    GeometryStatus.GEOMETRY_VERIFIED.value: 4,
    GeometryStatus.GEOMETRY_HISTORICAL.value: 3,
    GeometryStatus.GEOMETRY_SIMPLIFIED.value: 2,
    GeometryStatus.GEOMETRY_UNVALIDATED.value: 1,
    GeometryStatus.GEOMETRY_MISSING.value: 0,
}


def _to_uuid(val: Union[str, uuid.UUID]) -> uuid.UUID:
    """Deterministically convert a string or UUID object to a valid uuid.UUID."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _policy_document_record(model: PolicyDocumentModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "scheme_id": model.scheme_id,
        "document_url": model.document_url,
        "sha256": model.sha256,
        "source_version_id": model.source_version_id,
        "retrieved_at": model.retrieved_at.isoformat() if model.retrieved_at else None,
        "status": model.status,
        "verified_by": str(model.verified_by) if model.verified_by else None,
        "verified_at": model.verified_at.isoformat() if model.verified_at else None,
        "review_note": model.review_note,
    }


def _policy_rule_record(model: PolicyRuleModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "document_id": str(model.document_id) if model.document_id else None,
        "scheme_id": model.scheme_id,
        "rule_key": model.rule_key,
        "version": model.version,
        "rule_ast": model.rule_ast,
        "evidence_requirements": model.evidence_requirements or {},
        "source_references": model.source_references or [],
        "effective_from": model.effective_from.isoformat() if model.effective_from else None,
        "effective_to": model.effective_to.isoformat() if model.effective_to else None,
        "status": model.status,
        "approved_by": str(model.approved_by) if model.approved_by else None,
        "approved_at": model.approved_at.isoformat() if model.approved_at else None,
        "approval_note": model.approval_note,
        "retired_by": str(model.retired_by) if model.retired_by else None,
        "retired_at": model.retired_at.isoformat() if model.retired_at else None,
        "retirement_reason": model.retirement_reason,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ConcurrentRunTransition(RuntimeError):
    """Raised when a caller's expected run state is stale."""


class PostgresAgentRunRepository:
    """Transactional persistence for the orchestrated agent-run lifecycle."""

    def __init__(
        self,
        session_factory: Optional[Callable[[], Session]] = None,
        budget_limits: Optional[RunBudgetLimits] = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()
        self._budget_limits = budget_limits or RunBudgetLimits(
            max_cost_usd=Decimal(str(get_max_cost_usd_per_run()))
        )

    def _get_session(self) -> Session:
        return self._session_factory()

    def create_run(
        self,
        owner_id: Union[str, uuid.UUID],
        objective: Dict[str, Any],
        run_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> str:
        run_uuid = _to_uuid(run_id or uuid.uuid4())
        owner_uuid = _to_uuid(owner_id)
        if not isinstance(objective, dict):
            raise TypeError("Agent run objective must be a JSON object.")

        with self._get_session() as session:
            model = AgentRunModel(
                id=run_uuid,
                owner_id=owner_uuid,
                objective=objective,
                state=AgentRunState.CREATED.value,
            )
            session.add(model)
            session.commit()
        return str(run_uuid)

    def get_run(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Optional[Dict[str, Any]]:
        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            statement = select(AgentRunModel).where(AgentRunModel.id == run_uuid)
            if owner_id is not None:
                statement = statement.where(AgentRunModel.owner_id == _to_uuid(owner_id))
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "objective": model.objective,
                "state": model.state,
                "steps_used": model.steps_used,
                "replans_used": model.replans_used,
                "model_calls_used": model.model_calls_used,
                "cost_usd": float(model.cost_usd),
                "claimed_by": model.claimed_by,
                "lease_expires_at": model.lease_expires_at,
                "recovery_attempts": model.recovery_attempts,
                "max_recovery_attempts": model.max_recovery_attempts,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }

    def claim_pending_run(
        self,
        worker_id: Optional[str] = None,
        lease_duration_seconds: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """Atomically claim the oldest pending run using SELECT ... FOR UPDATE SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        worker_token = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        lease_expires = now + timedelta(seconds=lease_duration_seconds)
        with self._get_session() as session:
            statement = (
                select(AgentRunModel)
                .where(
                    AgentRunModel.state.in_([
                        AgentRunState.CREATED.value,
                        AgentRunState.RECOVERING.value,
                    ]),
                    (AgentRunModel.lease_expires_at.is_(None) | (AgentRunModel.lease_expires_at <= now)),
                )
                .order_by(AgentRunModel.created_at.asc())
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return None
            model.claimed_by = worker_token
            model.lease_expires_at = lease_expires
            model.updated_at = now
            session.commit()
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "objective": model.objective,
                "state": model.state,
                "steps_used": model.steps_used,
                "replans_used": model.replans_used,
                "model_calls_used": model.model_calls_used,
                "cost_usd": float(model.cost_usd),
                "claimed_by": model.claimed_by,
                "lease_expires_at": model.lease_expires_at,
                "recovery_attempts": model.recovery_attempts,
                "max_recovery_attempts": model.max_recovery_attempts,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }

    def claim_run_by_id(
        self,
        run_id: Union[str, uuid.UUID],
        worker_id: Optional[str] = None,
        lease_duration_seconds: int = 300,
    ) -> bool:
        """Atomically claim a specific run by ID if not currently leased."""
        run_uuid = _to_uuid(run_id)
        now = datetime.now(timezone.utc)
        worker_token = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        lease_expires = now + timedelta(seconds=lease_duration_seconds)
        terminal_values = [s.value for s in TERMINAL_RUN_STATES]
        with self._get_session() as session:
            statement = (
                select(AgentRunModel)
                .where(
                    AgentRunModel.id == run_uuid,
                    AgentRunModel.state.notin_(terminal_values),
                    (AgentRunModel.lease_expires_at.is_(None) | (AgentRunModel.lease_expires_at <= now)),
                )
                .with_for_update(skip_locked=True)
            )
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return False
            model.claimed_by = worker_token
            model.lease_expires_at = lease_expires
            model.updated_at = now
            session.commit()
            return True

    def renew_lease(
        self,
        run_id: Union[str, uuid.UUID],
        worker_id: str,
        lease_duration_seconds: int = 300,
    ) -> bool:
        """Renew the active lease on a claimed run."""
        run_uuid = _to_uuid(run_id)
        now = datetime.now(timezone.utc)
        with self._get_session() as session:
            statement = select(AgentRunModel).where(AgentRunModel.id == run_uuid).with_for_update()
            model = session.execute(statement).scalar_one_or_none()
            if model is None or model.claimed_by != worker_id:
                return False
            model.lease_expires_at = now + timedelta(seconds=lease_duration_seconds)
            model.updated_at = now
            session.commit()
            return True

    def release_claim(
        self,
        run_id: Union[str, uuid.UUID],
        worker_id: Optional[str] = None,
    ) -> bool:
        """Release worker claim and lease upon completion or failure."""
        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            statement = select(AgentRunModel).where(AgentRunModel.id == run_uuid).with_for_update()
            model = session.execute(statement).scalar_one_or_none()
            if model is None:
                return False
            if worker_id is not None and model.claimed_by != worker_id:
                return False
            model.claimed_by = None
            model.lease_expires_at = None
            session.commit()
            return True

    def recover_stale_runs(self, timeout_seconds: int = 300) -> int:
        """
        Detect runs stuck in non-terminal active states whose lease expired or whose
        last update exceeded the timeout threshold, and transition them to RECOVERING
        (with checkpoint recovery) or terminal FAILED when max recovery attempts are exhausted.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=timeout_seconds)
        active_states = [
            AgentRunState.CREATED.value,
            AgentRunState.INTERPRETING.value,
            AgentRunState.PLANNING.value,
            AgentRunState.EXECUTING.value,
            AgentRunState.OBSERVING.value,
            AgentRunState.RECOVERING.value,
            AgentRunState.VERIFYING.value,
        ]
        recovered = 0
        with self._get_session() as session:
            stale_models = session.execute(
                select(AgentRunModel)
                .where(
                    AgentRunModel.state.in_(active_states),
                    (
                        (AgentRunModel.lease_expires_at.is_not(None) & (AgentRunModel.lease_expires_at <= now))
                        | (
                            AgentRunModel.lease_expires_at.is_(None)
                            & (AgentRunModel.state != AgentRunState.CREATED.value)
                            & (AgentRunModel.updated_at < cutoff)
                        )
                    ),
                )
                .with_for_update(skip_locked=True)
            ).scalars().all()

            for model in stale_models:
                last_seq = session.execute(
                    select(func.coalesce(func.max(RunEventModel.seq), 0)).where(
                        RunEventModel.run_id == model.id
                    )
                ).scalar_one()
                seq = int(last_seq) + 1
                from_state = model.state

                if model.recovery_attempts >= model.max_recovery_attempts:
                    model.state = AgentRunState.FAILED.value
                    model.claimed_by = None
                    model.lease_expires_at = None
                    session.add(
                        RunEventModel(
                            run_id=model.id,
                            seq=seq,
                            type="WORKER_RECOVERY_EXHAUSTED",
                            payload={
                                "reason": f"Run exceeded maximum recovery attempts ({model.max_recovery_attempts}).",
                                "from_state": from_state,
                                "to_state": AgentRunState.FAILED.value,
                                "recovery_attempts": model.recovery_attempts,
                            },
                        )
                    )
                    recovered += 1
                    continue

                model.recovery_attempts += 1

                latest_step = session.execute(
                    select(AgentRunStepModel)
                    .where(AgentRunStepModel.run_id == model.id)
                    .order_by(AgentRunStepModel.seq.desc())
                    .limit(1)
                    .with_for_update()
                ).scalar_one_or_none()

                if latest_step is not None:
                    if latest_step.status == "RUNNING":
                        latest_step.status = "RECOVERED"
                    model.state = AgentRunState.RECOVERING.value
                    model.claimed_by = None
                    model.lease_expires_at = None
                    session.add(
                        RunEventModel(
                            run_id=model.id,
                            seq=seq,
                            type="WORKER_CRASH_RECOVERED",
                            payload={
                                "reason": f"Worker lease expired or worker crashed; prepared for checkpoint resume from step seq {latest_step.seq}.",
                                "from_state": from_state,
                                "to_state": AgentRunState.RECOVERING.value,
                                "recovery_attempt": model.recovery_attempts,
                                "step_seq": latest_step.seq,
                            },
                        )
                    )
                else:
                    model.state = AgentRunState.CREATED.value
                    model.claimed_by = None
                    model.lease_expires_at = None
                    session.add(
                        RunEventModel(
                            run_id=model.id,
                            seq=seq,
                            type="WORKER_TIMEOUT_RECOVERED",
                            payload={
                                "reason": f"Run exceeded worker lease threshold of {timeout_seconds}s before executing steps; reset to CREATED.",
                                "from_state": from_state,
                                "to_state": AgentRunState.CREATED.value,
                                "recovery_attempt": model.recovery_attempts,
                            },
                        )
                    )
                recovered += 1

            if recovered > 0:
                session.commit()
        return recovered

    def transition(
        self,
        run_id: Union[str, uuid.UUID],
        event: AgentRunEvent | str,
        payload: Optional[Dict[str, Any]] = None,
        *,
        expected_state: Optional[AgentRunState | str] = None,
        plan_retry_available: bool = False,
    ) -> Dict[str, Any]:
        run_uuid = _to_uuid(run_id)
        event_type = AgentRunEvent(event)
        event_payload = {} if payload is None else payload
        if not isinstance(event_payload, dict):
            raise TypeError("Run event payload must be a JSON object.")

        with self._get_session() as session:
            model = session.execute(
                select(AgentRunModel)
                .where(AgentRunModel.id == run_uuid)
                .with_for_update()
            ).scalar_one_or_none()
            if model is None:
                raise KeyError(f"Agent run {run_id!s} was not found.")

            current_state = AgentRunState(model.state)
            if expected_state is not None and current_state != AgentRunState(expected_state):
                raise ConcurrentRunTransition(
                    f"Agent run is {current_state.value}, not expected {AgentRunState(expected_state).value}."
                )
            persisted_event_type = event_type
            if (
                event_type == AgentRunEvent.NEEDS_REPLAN
                and model.replans_used >= self._budget_limits.max_replans
            ):
                persisted_event_type = AgentRunEvent.BUDGET_LIMIT_HIT
                event_payload = {
                    **event_payload,
                    "budget": "replans",
                    "limit": self._budget_limits.max_replans,
                }
            next_state = transition_run_state(
                current_state,
                persisted_event_type,
                plan_retry_available=plan_retry_available,
            )
            if event_type == AgentRunEvent.NEEDS_REPLAN and persisted_event_type == event_type:
                model.replans_used += 1

            last_sequence = session.execute(
                select(func.coalesce(func.max(RunEventModel.seq), 0)).where(
                    RunEventModel.run_id == run_uuid
                )
            ).scalar_one()
            sequence = int(last_sequence) + 1
            persisted_payload = {
                **event_payload,
                "from_state": current_state.value,
                "to_state": next_state.value,
            }
            model.state = next_state.value
            if next_state in TERMINAL_RUN_STATES:
                model.claimed_by = None
                model.lease_expires_at = None
            session.add(
                RunEventModel(
                    run_id=run_uuid,
                    seq=sequence,
                    type=persisted_event_type.value,
                    payload=persisted_payload,
                )
            )
            if (
                current_state == AgentRunState.EXECUTING
                and event_type
                in {
                    AgentRunEvent.TOOL_RETURNED,
                    AgentRunEvent.ERROR_GAP_OR_CONTRADICTION,
                }
            ):
                latest_step = session.execute(
                    select(AgentRunStepModel)
                    .where(AgentRunStepModel.run_id == run_uuid)
                    .order_by(AgentRunStepModel.seq.desc())
                    .limit(1)
                    .with_for_update()
                ).scalar_one_or_none()
                if latest_step is not None and latest_step.status == "RUNNING":
                    reported_tool = event_payload.get("tool_name")
                    if reported_tool is not None and reported_tool != latest_step.tool:
                        raise ConcurrentRunTransition(
                            "Run event tool does not match the active step checkpoint."
                        )
                    latest_step.status = (
                        "SUCCEEDED"
                        if event_type == AgentRunEvent.TOOL_RETURNED
                        else "FAILED"
                    )
                    if event_type == AgentRunEvent.TOOL_RETURNED:
                        latest_step.output = {"result": event_payload.get("result")}
                    latest_step.ended_at = datetime.now(timezone.utc)
            session.commit()
            return {
                "run_id": str(run_uuid),
                "seq": sequence,
                "event": persisted_event_type.value,
                "from_state": current_state.value,
                "state": next_state.value,
                "terminal": next_state in TERMINAL_RUN_STATES,
                "payload": persisted_payload,
            }

    def reserve_budget(
        self,
        run_id: Union[str, uuid.UUID],
        reservation: RunBudgetReservation,
        *,
        checkpoint: Optional[RunStepCheckpoint] = None,
    ) -> RunBudgetDecision:
        """Atomically reserve bounded run usage or persist BUDGET_EXHAUSTED."""
        if not isinstance(reservation, RunBudgetReservation):
            raise TypeError("reservation must be a RunBudgetReservation.")
        if checkpoint is not None and not isinstance(checkpoint, RunStepCheckpoint):
            raise TypeError("checkpoint must be a RunStepCheckpoint.")
        if checkpoint is not None and reservation.steps != 1:
            raise ValueError("A persisted step checkpoint must reserve exactly one step.")

        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            model = session.execute(
                select(AgentRunModel)
                .where(AgentRunModel.id == run_uuid)
                .with_for_update()
            ).scalar_one_or_none()
            if model is None:
                raise KeyError(f"Agent run {run_id!s} was not found.")

            current_state = AgentRunState(model.state)
            if current_state in TERMINAL_RUN_STATES:
                raise IllegalRunTransition(
                    f"Budget cannot be reserved for terminal run {current_state.value}."
                )

            current_cost = Decimal(model.cost_usd)
            candidate_usage = (
                ("steps", model.steps_used + reservation.steps, self._budget_limits.max_steps),
                (
                    "model_calls",
                    model.model_calls_used + reservation.model_calls,
                    self._budget_limits.max_model_calls,
                ),
                (
                    "cost_usd",
                    current_cost + reservation.cost_usd,
                    self._budget_limits.max_cost_usd,
                ),
            )
            exhausted = next(
                (
                    (name, requested, limit)
                    for name, requested, limit in candidate_usage
                    if requested > limit
                ),
                None,
            )

            last_sequence = session.execute(
                select(func.coalesce(func.max(RunEventModel.seq), 0)).where(
                    RunEventModel.run_id == run_uuid
                )
            ).scalar_one()
            sequence = int(last_sequence) + 1
            if exhausted is not None:
                budget_name, requested, limit = exhausted
                model.state = AgentRunState.BUDGET_EXHAUSTED.value
                event_payload = {
                    "budget": budget_name,
                    "requested": str(requested),
                    "limit": str(limit),
                    "from_state": current_state.value,
                    "to_state": AgentRunState.BUDGET_EXHAUSTED.value,
                }
                session.add(
                    RunEventModel(
                        run_id=run_uuid,
                        seq=sequence,
                        type=AgentRunEvent.BUDGET_LIMIT_HIT.value,
                        payload=event_payload,
                    )
                )
                session.commit()
                return RunBudgetDecision(
                    allowed=False,
                    exhausted_budget=budget_name,
                    steps_used=model.steps_used,
                    replans_used=model.replans_used,
                    model_calls_used=model.model_calls_used,
                    cost_usd=current_cost,
                )

            checkpoint_sequence = None
            model.steps_used += reservation.steps
            model.model_calls_used += reservation.model_calls
            model.cost_usd = current_cost + reservation.cost_usd
            if checkpoint is not None:
                latest_step_sequence = session.execute(
                    select(func.coalesce(func.max(AgentRunStepModel.seq), 0)).where(
                        AgentRunStepModel.run_id == run_uuid
                    )
                ).scalar_one()
                checkpoint_sequence = int(latest_step_sequence) + 1
                session.add(
                    AgentRunStepModel(
                        run_id=run_uuid,
                        seq=checkpoint_sequence,
                        tool=checkpoint.tool,
                        input=checkpoint.input,
                        output=checkpoint.output,
                        memento=checkpoint.memento,
                        status=checkpoint.status,
                        started_at=checkpoint.started_at,
                        ended_at=checkpoint.ended_at,
                    )
                )
                event_payload = {
                    "step_seq": checkpoint_sequence,
                    "status": checkpoint.status,
                    "tool": checkpoint.tool,
                    "from_state": current_state.value,
                    "to_state": current_state.value,
                }
                session.add(
                    RunEventModel(
                        run_id=run_uuid,
                        seq=sequence,
                        type=AgentRunEvent.CHECKPOINT_SAVED.value,
                        payload=event_payload,
                    )
                )
            session.commit()
            return RunBudgetDecision(
                allowed=True,
                exhausted_budget=None,
                steps_used=model.steps_used,
                replans_used=model.replans_used,
                model_calls_used=model.model_calls_used,
                cost_usd=Decimal(model.cost_usd),
                checkpoint_seq=checkpoint_sequence,
            )

    def get_latest_checkpoint(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Return the newest committed step memento, optionally scoped to its owner."""
        run_uuid = _to_uuid(run_id)
        statement = (
            select(AgentRunStepModel)
            .join(AgentRunModel, AgentRunStepModel.run_id == AgentRunModel.id)
            .where(AgentRunStepModel.run_id == run_uuid)
            .order_by(AgentRunStepModel.seq.desc())
            .limit(1)
        )
        if owner_id is not None:
            statement = statement.where(AgentRunModel.owner_id == _to_uuid(owner_id))
        with self._get_session() as session:
            checkpoint = session.execute(statement).scalar_one_or_none()
            if checkpoint is None:
                return None
            return {
                "run_id": str(checkpoint.run_id),
                "seq": checkpoint.seq,
                "tool": checkpoint.tool,
                "input": checkpoint.input,
                "output": checkpoint.output,
                "memento": checkpoint.memento,
                "status": checkpoint.status,
                "started_at": checkpoint.started_at,
                "ended_at": checkpoint.ended_at,
            }

    def list_events(
        self,
        run_id: Union[str, uuid.UUID],
        *,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative.")
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000.")

        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            rows = session.execute(
                select(RunEventModel)
                .where(
                    RunEventModel.run_id == run_uuid,
                    RunEventModel.seq > after_sequence,
                )
                .order_by(RunEventModel.seq)
                .limit(limit)
            ).scalars().all()
            return [
                {
                    "seq": row.seq,
                    "type": row.type,
                    "payload": row.payload,
                    "at": row.at,
                }
                for row in rows
            ]

    def record_event(
        self,
        run_id: Union[str, uuid.UUID],
        event_type: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist a non-state-changing event into the run's audit/telemetry stream."""
        run_uuid = _to_uuid(run_id)
        sanitized_payload = {} if payload is None else payload
        with self._get_session() as session:
            last_seq = session.execute(
                select(func.coalesce(func.max(RunEventModel.seq), 0)).where(
                    RunEventModel.run_id == run_uuid
                )
            ).scalar_one()
            seq = int(last_seq) + 1
            session.add(
                RunEventModel(
                    run_id=run_uuid,
                    seq=seq,
                    type=event_type,
                    payload=sanitized_payload,
                )
            )
            session.commit()
            return {
                "run_id": str(run_uuid),
                "seq": seq,
                "event": event_type,
                "payload": sanitized_payload,
            }


class PostgresFollowupTaskRepository:
    """Persist and list run follow-up tasks without crossing run ownership."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def create_for_run(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
        tasks: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not tasks:
            raise ValueError("At least one follow-up task is required.")
        run_uuid = _to_uuid(run_id)
        owner_uuid = _to_uuid(owner_id)
        prepared: list[TaskModel] = []
        for task in tasks:
            if not isinstance(task, dict):
                raise TypeError("Each follow-up task must be an object.")
            text = task.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Follow-up task text must be a non-empty string.")
            linked_quantity_id = task.get("linked_gap_quantity_id")
            if linked_quantity_id is not None:
                try:
                    linked_quantity_id = uuid.UUID(str(linked_quantity_id))
                except (ValueError, AttributeError) as exc:
                    raise ValueError("linked_gap_quantity_id must be a UUID.") from exc
            raw_priority = task.get("priority", "MEDIUM")
            priority = str(raw_priority if raw_priority is not None else "MEDIUM").strip().upper()
            if priority not in {"HIGH", "MEDIUM", "LOW"}:
                raise ValueError(f"Invalid task priority: {priority}")
            raw_status = task.get("status", "OPEN")
            status = str(raw_status if raw_status is not None else "OPEN").strip().upper()
            if status not in {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}:
                raise ValueError(f"Invalid task status: {status}")
            prepared.append(
                TaskModel(
                    run_id=run_uuid,
                    text=text.strip(),
                    linked_gap_quantity_id=linked_quantity_id,
                    priority=priority,
                    status=status,
                )
            )

        with self._session_factory() as session:
            run = session.execute(
                select(AgentRunModel)
                .where(
                    AgentRunModel.id == run_uuid,
                    AgentRunModel.owner_id == owner_uuid,
                )
                .with_for_update()
            ).scalar_one_or_none()
            if run is None:
                raise KeyError(f"Agent run {run_id!s} was not found for this owner.")
            session.add_all(prepared)
            session.flush()
            result = [self._serialize(task) for task in prepared]
            session.commit()
            return result

    def list_for_run(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Optional[Union[str, uuid.UUID]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        run_uuid = _to_uuid(run_id)
        with self._session_factory() as session:
            run_statement = select(AgentRunModel.id).where(
                AgentRunModel.id == run_uuid
            )
            if owner_id is not None:
                run_statement = run_statement.where(
                    AgentRunModel.owner_id == _to_uuid(owner_id)
                )
            if session.execute(run_statement).scalar_one_or_none() is None:
                return None

            tasks = session.execute(
                select(TaskModel)
                .where(TaskModel.run_id == run_uuid)
                .order_by(TaskModel.created_at, TaskModel.id)
            ).scalars().all()
            return [self._serialize(task) for task in tasks]

    def update_task(
        self,
        run_id: Union[str, uuid.UUID],
        task_id: Union[str, uuid.UUID],
        owner_id: Optional[Union[str, uuid.UUID]] = None,
        *,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        run_uuid = _to_uuid(run_id)
        task_uuid = _to_uuid(task_id)
        with self._session_factory() as session:
            run_statement = select(AgentRunModel.id).where(AgentRunModel.id == run_uuid)
            if owner_id is not None:
                run_statement = run_statement.where(AgentRunModel.owner_id == _to_uuid(owner_id))
            if session.execute(run_statement).scalar_one_or_none() is None:
                raise KeyError(f"Agent run {run_id!s} was not found for this owner.")

            task = session.execute(
                select(TaskModel)
                .where(TaskModel.id == task_uuid, TaskModel.run_id == run_uuid)
                .with_for_update()
            ).scalar_one_or_none()
            if task is None:
                raise KeyError(f"Task {task_id!s} was not found for run {run_id!s}.")

            if status is not None:
                norm_status = status.strip().upper()
                if norm_status not in {"OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"}:
                    raise ValueError(f"Invalid task status: {status}")
                task.status = norm_status

            if priority is not None:
                norm_priority = priority.strip().upper()
                if norm_priority not in {"HIGH", "MEDIUM", "LOW"}:
                    raise ValueError(f"Invalid task priority: {priority}")
                task.priority = norm_priority

            session.commit()
            return self._serialize(task)

    @staticmethod
    def _serialize(task: TaskModel) -> Dict[str, Any]:
        return {
            "id": str(task.id),
            "run_id": str(task.run_id),
            "text": task.text,
            "linked_gap_quantity_id": (
                str(task.linked_gap_quantity_id)
                if task.linked_gap_quantity_id is not None
                else None
            ),
            "status": task.status,
            "priority": getattr(task, "priority", "MEDIUM") or "MEDIUM",
            "created_at": task.created_at,
        }


class PostgresQuantityRepository(QuantityRepository):
    """
    PostgreSQL-backed implementation of QuantityRepository.

    Enforces immutable quantity semantics and persists full lineage, JSONB uncertainty,
    quality flags, and P1-4 SimulationMetadata.
    """

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def _to_model(self, q: Quantity) -> QuantityModel:
        """Convert a domain Quantity into a SQLAlchemy QuantityModel."""
        q_id = _to_uuid(q.id)
        kind_str = q.kind.value if isinstance(q.kind, Kind) else str(q.kind)

        # Parse date for as_of if string
        as_of_date = None
        if q.as_of:
            if isinstance(q.as_of, date):
                as_of_date = q.as_of
            elif isinstance(q.as_of, str):
                try:
                    as_of_date = date.fromisoformat(q.as_of)
                except ValueError:
                    as_of_date = None

        # Format parent_ids as UUID list for Postgres UUID[]
        parent_uuids = [_to_uuid(pid) for pid in q.parent_ids]

        # Format source_refs for JSONB
        source_refs_json = [
            list(ref) if isinstance(ref, (tuple, list)) else ref
            for ref in q.source_refs
        ]

        # Serialize SimulationMetadata if present
        sim_meta_json = None
        if q.simulation_meta is not None:
            sim_meta_json = {
                "scenario_id": q.simulation_meta.scenario_id,
                "model_version": q.simulation_meta.model_version,
                "seed": q.simulation_meta.seed,
                "sample_count": q.simulation_meta.sample_count,
                "data_versions": list(q.simulation_meta.data_versions),
            }

        return QuantityModel(
            id=q_id,
            definition_key=q.definition_key,
            value=float(q.value) if q.value is not None else None,
            unit=q.unit,
            kind=kind_str,
            evidence_floor=int(q.evidence_floor),
            geo_unit_id=q.geo_unit_id,
            resolution=int(q.resolution),
            as_of=as_of_date,
            uncertainty=q.uncertainty,
            source_refs=source_refs_json,
            method_id=q.method_id or "",
            model_version=q.model_version or "",
            parent_ids=parent_uuids,
            quality_flags=list(q.quality_flags),
            license_meta=q.license_meta or "",
            owner_id=_to_uuid(q.owner_id) if q.owner_id else None,
            simulation_meta=sim_meta_json,
        )

    def _from_model(self, m: QuantityModel) -> Quantity:
        """Reconstruct a domain Quantity from a SQLAlchemy QuantityModel."""
        # Restore kind enum
        kind_enum = Kind(m.kind)

        # Restore as_of string
        as_of_str = m.as_of.isoformat() if m.as_of is not None else ""

        # Restore parent_ids tuple of UUID strings
        parent_ids_tuple = tuple(str(pid) for pid in (m.parent_ids or []))

        # Restore quality_flags frozenset
        quality_flags_set = frozenset(m.quality_flags or [])

        # Restore source_refs tuple
        source_refs_tuple = tuple(
            tuple(item) if isinstance(item, list) else item
            for item in (m.source_refs or [])
        )

        # Restore SimulationMetadata if present
        sim_meta_obj = None
        if m.simulation_meta:
            sm = m.simulation_meta
            sim_meta_obj = SimulationMetadata(
                scenario_id=sm["scenario_id"],
                model_version=sm["model_version"],
                seed=int(sm["seed"]),
                sample_count=int(sm["sample_count"]),
                data_versions=tuple(sm.get("data_versions", ())),
            )

        return Quantity(
            id=str(m.id),
            definition_key=m.definition_key,
            value=float(m.value) if m.value is not None else 0.0,
            unit=m.unit,
            kind=kind_enum,
            evidence_floor=int(m.evidence_floor),
            geo_unit_id=m.geo_unit_id,
            resolution=int(m.resolution),
            as_of=as_of_str,
            uncertainty=m.uncertainty,
            source_refs=source_refs_tuple,
            method_id=m.method_id or "",
            model_version=m.model_version or "",
            parent_ids=parent_ids_tuple,
            quality_flags=quality_flags_set,
            license_meta=m.license_meta or "",
            simulation_meta=sim_meta_obj,
            owner_id=str(m.owner_id) if m.owner_id else None,
        )

    def save(self, quantity: Quantity, session: Optional[Session] = None) -> None:
        target_uuid = _to_uuid(quantity.id)
        kind_str = quantity.kind.value if isinstance(quantity.kind, Kind) else str(quantity.kind)

        sess = session or self._get_session()
        owns_session = session is None
        try:
            parent_uuids = [_to_uuid(parent_id) for parent_id in quantity.parent_ids]
            if len(set(parent_uuids)) != len(parent_uuids):
                raise ValueError(f"Duplicate parent references rejected for Quantity '{quantity.id}'.")
            if target_uuid in parent_uuids:
                raise ValueError(f"Direct self-reference rejected: Quantity '{quantity.id}' cannot be its own parent.")
            if parent_uuids:
                registered_parents = set(
                    sess.execute(
                        select(QuantityModel.id).where(QuantityModel.id.in_(parent_uuids))
                    ).scalars()
                )
                missing_parents = set(parent_uuids) - registered_parents
                if missing_parents:
                    raise ValueError(
                        f"Quantity '{quantity.id}' references unregistered parent quantities: "
                        f"{sorted(map(str, missing_parents))}."
                    )

            existing = sess.get(QuantityModel, target_uuid)
            if existing is not None:
                # Immutability check
                if existing.value != quantity.value or existing.kind != kind_str:
                    raise ImmutableQuantityError(
                        f"Quantity {quantity.id} is immutable: value ({existing.value} -> {quantity.value}) "
                        f"and kind ({existing.kind} -> {quantity.kind}) cannot be modified."
                    )
                # Idempotent update for non-immutable fields (e.g., superseding quality flags)
                existing.quality_flags = list(quantity.quality_flags)
                if owns_session:
                    sess.commit()
                return

            model = self._to_model(quantity)
            sess.add(model)
            if owns_session:
                sess.commit()
            else:
                sess.flush()
        finally:
            if owns_session:
                sess.close()

    def save_many(
        self,
        quantities: Sequence[Quantity],
        session: Optional[Session] = None,
    ) -> None:
        """Persist an ordered quantity batch while enforcing parent and immutability rules."""
        batch = list(quantities)
        if not batch:
            return
        if any(not isinstance(quantity, Quantity) for quantity in batch):
            raise TypeError("Every item in a quantity batch must be a Quantity instance.")

        target_ids = [_to_uuid(quantity.id) for quantity in batch]
        if len(set(target_ids)) != len(target_ids):
            raise ValueError("Duplicate quantity IDs rejected within a batch.")
        parent_ids = [_to_uuid(parent_id) for quantity in batch for parent_id in quantity.parent_ids]
        query_ids = list(set(target_ids + parent_ids))

        sess = session or self._get_session()
        owns_session = session is None
        try:
            registered = {
                model.id: model
                for model in sess.execute(
                    select(QuantityModel).where(QuantityModel.id.in_(query_ids))
                ).scalars()
            }
            prior_batch_ids: set[uuid.UUID] = set()
            for quantity, target_uuid in zip(batch, target_ids):
                parents = [_to_uuid(parent_id) for parent_id in quantity.parent_ids]
                if len(set(parents)) != len(parents):
                    raise ValueError(f"Duplicate parent references rejected for Quantity '{quantity.id}'.")
                if target_uuid in parents:
                    raise ValueError(f"Direct self-reference rejected: Quantity '{quantity.id}' cannot be its own parent.")
                missing = set(parents) - (registered.keys() | prior_batch_ids)
                if missing:
                    raise ValueError(
                        f"Quantity '{quantity.id}' references unregistered parent quantities: "
                        f"{sorted(map(str, missing))}."
                    )

                existing = registered.get(target_uuid)
                kind_str = quantity.kind.value if isinstance(quantity.kind, Kind) else str(quantity.kind)
                if existing is not None:
                    if existing.value != quantity.value or existing.kind != kind_str:
                        raise ImmutableQuantityError(
                            f"Quantity {quantity.id} is immutable: value ({existing.value} -> {quantity.value}) "
                            f"and kind ({existing.kind} -> {quantity.kind}) cannot be modified."
                        )
                    existing.quality_flags = list(quantity.quality_flags)
                else:
                    sess.add(self._to_model(quantity))
                    prior_batch_ids.add(target_uuid)

            if owns_session:
                sess.commit()
            else:
                sess.flush()
        except Exception:
            if owns_session:
                sess.rollback()
            raise
        finally:
            if owns_session:
                sess.close()

    def get(self, quantity_id: Union[str, uuid.UUID]) -> Optional[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            model = session.get(QuantityModel, target_uuid)
            if model is None:
                return None
            return self._from_model(model)

    def exists(self, quantity_id: Union[str, uuid.UUID]) -> bool:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            stmt = select(func.count()).select_from(QuantityModel).where(QuantityModel.id == target_uuid)
            return bool(session.execute(stmt).scalar() > 0)

    def list_by_definition(self, definition_key: str) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel).where(QuantityModel.definition_key == definition_key)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def list_by_geo_unit(self, geo_unit_id: str) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel).where(QuantityModel.geo_unit_id == geo_unit_id)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def get_parents(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            model = session.get(QuantityModel, target_uuid)
            if not model or not model.parent_ids:
                return []
            stmt = select(QuantityModel).where(QuantityModel.id.in_(model.parent_ids))
            parents = session.execute(stmt).scalars().all()
            return [self._from_model(p) for p in parents]

    def get_children(self, quantity_id: Union[str, uuid.UUID]) -> List[Quantity]:
        target_uuid = _to_uuid(quantity_id)
        with self._get_session() as session:
            # Leverage Postgres GIN index on parent_ids with array containment
            stmt = select(QuantityModel).where(QuantityModel.parent_ids.contains([target_uuid]))
            children = session.execute(stmt).scalars().all()
            return [self._from_model(c) for c in children]

    def list_all(self) -> List[Quantity]:
        with self._get_session() as session:
            stmt = select(QuantityModel)
            models = session.execute(stmt).scalars().all()
            return [self._from_model(m) for m in models]

    def count(self) -> int:
        with self._get_session() as session:
            stmt = select(func.count()).select_from(QuantityModel)
            return int(session.execute(stmt).scalar() or 0)


class PostgresUserRepository(UserRepository):
    """PostgreSQL-backed implementation of UserRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new user record strictly without updating existing accounts.
        Enforces database unique constraint on email.
        """
        user_uuid = _to_uuid(user_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            model = UserModel(
                id=user_uuid,
                email=user_data["email"].strip().lower(),
                password_hash=user_data["password_hash"],
                quota_counters=user_data.get("quota_counters", {"is_active": True}),
            )
            session.add(model)
            if "roles" in user_data:
                for role_id in user_data["roles"]:
                    session.add(UserRoleModel(user_id=user_uuid, role_id=str(role_id)))
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise UserAlreadyExistsError(
                    f"User with email '{user_data['email']}' already exists."
                ) from exc
            return str(user_uuid)

    def save(self, user_data: Dict[str, Any]) -> str:
        user_uuid = _to_uuid(user_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            existing = session.get(UserModel, user_uuid)
            if not existing and "email" in user_data:
                existing = session.execute(
                    select(UserModel).where(UserModel.email == user_data["email"])
                ).scalar_one_or_none()

            if existing:
                user_uuid = existing.id
                existing.email = user_data["email"]
                existing.password_hash = user_data["password_hash"]
                existing.quota_counters = user_data.get("quota_counters", {})
            else:
                existing = UserModel(
                    id=user_uuid,
                    email=user_data["email"],
                    password_hash=user_data["password_hash"],
                    quota_counters=user_data.get("quota_counters", {}),
                )
                session.add(existing)

            # Synchronize roles if specified
            if "roles" in user_data:
                session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_uuid))
                for role_id in user_data["roles"]:
                    session.add(UserRoleModel(user_id=user_uuid, role_id=str(role_id)))

            session.commit()
            return str(user_uuid)

    def get_by_id(self, user_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return None
            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "password_hash": model.password_hash,
                "quota_counters": model.quota_counters,
                "roles": roles,
                "created_at": model.created_at,
            }

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.email == email)
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "password_hash": model.password_hash,
                "quota_counters": model.quota_counters,
                "roles": roles,
                "created_at": model.created_at,
            }

    def increment_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            counters["runs_today"] = counters.get("runs_today", 0) + runs
            counters["cost_today"] = round(float(counters.get("cost_today", 0.0)) + cost, 4)
            model.quota_counters = counters
            session.commit()
            return counters

    def check_and_reserve_quota(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 1,
        cost: float = 0.0,
        max_runs: int = 50,
        max_cost: float = 5.0,
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            current_runs = counters.get("runs_today", 0)
            current_cost = float(counters.get("cost_today", 0.0))

            if current_runs + runs > max_runs:
                return False, counters, f"Daily run quota exceeded ({max_runs} runs per day)."

            if current_cost + cost > max_cost:
                return False, counters, f"Daily budget cap exceeded (${max_cost:.2f} per day)."

            counters["runs_today"] = current_runs + runs
            counters["cost_today"] = round(current_cost + cost, 4)
            model.quota_counters = counters
            session.commit()
            return True, counters, None

    def refund_quota_counters(
        self,
        user_id: Union[str, uuid.UUID],
        runs: int = 0,
        cost: float = 0.0,
    ) -> Dict[str, Any]:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            stmt = select(UserModel).where(UserModel.id == user_uuid).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                raise KeyError(f"User {user_id} not found.")
            counters = dict(model.quota_counters or {})
            counters["runs_today"] = max(0, counters.get("runs_today", 0) - runs)
            counters["cost_today"] = max(0.0, round(float(counters.get("cost_today", 0.0)) - cost, 4))
            model.quota_counters = counters
            session.commit()
            return counters

    def deactivate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["is_active"] = False
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            session.commit()
            return True

    def activate_user(self, user_id: Union[str, uuid.UUID]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["is_active"] = True
            model.quota_counters = counters
            session.commit()
            return True

    def set_user_roles(self, user_id: Union[str, uuid.UUID], roles: List[str]) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_uuid))
            for r_id in roles:
                session.add(UserRoleModel(user_id=user_uuid, role_id=str(r_id)))
            session.commit()
            return True

    def count_active_admins(self) -> int:
        with self._get_session() as session:
            stmt = (
                select(func.count(UserModel.id))
                .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
                .where(
                    UserRoleModel.role_id == "ADMIN",
                    func.coalesce(UserModel.quota_counters["is_active"].astext, "true") != "false",
                )
            )
            return session.execute(stmt).scalar() or 0

    def update_password(self, user_id: Union[str, uuid.UUID], password_hash: str) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["token_valid_after"] = datetime.now(timezone.utc).isoformat()
            model.quota_counters = counters
            model.password_hash = password_hash
            session.commit()
            return True

    def set_password_reset_token(
        self,
        user_id: Union[str, uuid.UUID],
        token_hash: str,
        expires_at: datetime,
    ) -> bool:
        user_uuid = _to_uuid(user_id)
        with self._get_session() as session:
            model = session.get(UserModel, user_uuid)
            if not model:
                return False
            counters = dict(model.quota_counters or {})
            counters["password_reset"] = {
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat(),
                "used": False,
            }
            model.quota_counters = counters
            session.commit()
            return True

    def verify_and_consume_password_reset(
        self,
        token_hash: str,
        new_password_hash: str,
    ) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            # Locate user record with this reset token hash
            stmt = select(UserModel).where(
                UserModel.quota_counters["password_reset"]["token_hash"].astext == token_hash
            ).with_for_update()
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None

            counters = dict(model.quota_counters or {})
            reset_info = dict(counters.get("password_reset") or {})
            if reset_info.get("used") is True:
                return None

            exp_str = reset_info.get("expires_at")
            if not exp_str:
                return None

            try:
                exp_dt = datetime.fromisoformat(exp_str)
                now = datetime.now(timezone.utc)
                if exp_dt.tzinfo is None:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if now > exp_dt:
                    return None
            except Exception:
                return None

            # Mark token as single-use consumed
            reset_info["used"] = True
            counters["password_reset"] = reset_info
            # Invalidate all prior active sessions
            now_iso = datetime.now(timezone.utc).isoformat()
            counters["token_valid_after"] = now_iso
            model.quota_counters = counters
            model.password_hash = new_password_hash
            session.commit()

            roles = [r.id for r in (model.roles or [])]
            return {
                "id": str(model.id),
                "email": model.email,
                "roles": roles,
            }


class PostgresPolicyRuleRepository(PolicyRuleRepository):
    """PostgreSQL policy registry with immutable versions and approval transitions."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_document(self, document_data: Dict[str, Any]) -> str:
        document_uuid = _to_uuid(document_data.get("id") or uuid.uuid4())
        version_id = document_data.get("source_version_id")
        expected_url = document_data.get("document_url")
        expected_hash = str(document_data.get("sha256") or "").lower()
        if not version_id or not expected_url or not _SHA256_RE.fullmatch(expected_hash):
            raise ValueError("Policy documents require an exact registered source version, URL, and SHA-256.")
        with self._get_session() as session:
            if session.get(PolicyDocumentModel, document_uuid) is not None:
                raise ValueError("Policy documents are immutable; register a new source-version document.")
            version = session.get(SourceVersionModel, str(version_id))
            source = session.get(SourceModel, version.source_id) if version else None
            if (
                version is None
                or version.status != "ACTIVE"
                or source is None
                or source.status != "ACTIVE"
                or version.source_url != expected_url
                or str(version.content_hash or "").lower() != expected_hash
            ):
                raise ValueError("Policy document must match an active registered source version exactly.")
            model = PolicyDocumentModel(
                id=document_uuid,
                scheme_id=document_data["scheme_id"],
                document_url=expected_url,
                sha256=expected_hash,
                source_version_id=str(version.id),
                status="PENDING_REVIEW",
            )
            session.add(model)
            session.commit()
            return str(document_uuid)

    def get_document(self, document_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        document_uuid = _to_uuid(document_id)
        with self._get_session() as session:
            model = session.get(PolicyDocumentModel, document_uuid)
            return _policy_document_record(model) if model is not None else None

    def review_document(
        self,
        document_id: Union[str, uuid.UUID],
        *,
        reviewer_id: Union[str, uuid.UUID],
        verified: bool,
        review_note: str,
    ) -> Optional[Dict[str, Any]]:
        document_uuid = _to_uuid(document_id)
        reviewer_uuid = _to_uuid(reviewer_id)
        with self._get_session() as session:
            document = session.get(PolicyDocumentModel, document_uuid)
            if document is None:
                return None
            if document.status != "PENDING_REVIEW":
                raise ValueError("Only a pending policy document can receive its first steward review.")
            version = session.get(SourceVersionModel, document.source_version_id)
            if version is None:
                raise ValueError("The registered source-version record is missing.")
            source = session.get(SourceModel, version.source_id)
            if (
                version.status != "ACTIVE"
                or source is None
                or source.status != "ACTIVE"
                or document.document_url != version.source_url
                or document.sha256 != str(version.content_hash or "").lower()
            ):
                raise ValueError("The document no longer matches its active registered source version.")
            document.status = "VERIFIED" if verified else "REJECTED"
            document.verified_by = reviewer_uuid
            document.verified_at = datetime.now(timezone.utc) if verified else None
            document.review_note = review_note.strip()
            session.commit()
            return _policy_document_record(document)

    def save_rule(self, rule_data: Dict[str, Any]) -> str:
        rule_uuid = _to_uuid(rule_data.get("id") or uuid.uuid4())
        rule_key = str(rule_data.get("rule_key") or "").strip()
        citations = rule_data.get("source_references") or []
        evidence_requirements = rule_data.get("evidence_requirements") or {}
        if not rule_key or not citations:
            raise ValueError("Policy drafts require a key and exact source citations.")
        try:
            node = parse_rule_ast(rule_data.get("rule_ast"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Policy rule AST is invalid: {exc}") from exc
        if rule_facts(node) != frozenset(evidence_requirements):
            raise ValueError("Policy evidence requirements must map exactly to every AST predicate fact.")
        valid_kinds = {kind.value for kind in Kind}
        for fact, requirement in evidence_requirements.items():
            if not isinstance(requirement, dict):
                raise ValueError(f"Evidence requirement for {fact!r} must be an object.")
            allowed_kinds = requirement.get("allowed_kinds")
            minimum_floor = requirement.get("minimum_evidence_floor")
            if (
                not requirement.get("definition_key")
                or not requirement.get("unit")
                or not isinstance(allowed_kinds, list)
                or not allowed_kinds
                or not all(isinstance(kind, str) for kind in allowed_kinds)
                or len(allowed_kinds) != len(set(allowed_kinds))
                or not set(allowed_kinds) <= valid_kinds
                or not isinstance(minimum_floor, int)
                or not 1 <= minimum_floor <= 4
            ):
                raise ValueError(f"Evidence requirement for {fact!r} is incomplete or invalid.")
        effective_from = _as_date(rule_data.get("effective_from"))
        effective_to = _as_date(rule_data.get("effective_to"))
        if effective_from is None or (effective_to is not None and effective_to < effective_from):
            raise ValueError("Policy drafts require a valid effective period.")
        with self._get_session() as session:
            if session.get(PolicyRuleModel, rule_uuid) is not None:
                raise ValueError("Policy rule versions are immutable; create a new version key.")
            duplicate = session.execute(
                select(PolicyRuleModel.id).where(
                    PolicyRuleModel.scheme_id == rule_data["scheme_id"],
                    PolicyRuleModel.rule_key == rule_key,
                    PolicyRuleModel.version == rule_data["version"],
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                raise ValueError("This scheme rule version already exists; policy versions are immutable.")
            document_ids = set()
            for citation in citations:
                try:
                    document_id = _to_uuid(citation["document_id"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("Every rule citation must identify a registered policy document.") from exc
                document = session.get(PolicyDocumentModel, document_id)
                if (
                    document is None
                    or document.scheme_id != rule_data["scheme_id"]
                    or citation.get("source_version_id") != document.source_version_id
                    or citation.get("document_url") != document.document_url
                    or citation.get("sha256") != document.sha256
                    or not str(citation.get("locator") or "").strip()
                ):
                    raise ValueError("Every citation must match an exact registered source document and locator.")
                document_ids.add(document_id)
            if not document_ids:
                raise ValueError("At least one exact registered source document is required.")
            model = PolicyRuleModel(
                id=rule_uuid,
                scheme_id=rule_data["scheme_id"],
                rule_key=rule_key,
                version=rule_data["version"],
                rule_ast=serialize_rule_ast(node),
                evidence_requirements=evidence_requirements,
                source_references=citations,
                document_id=_to_uuid(citations[0]["document_id"]),
                effective_from=effective_from,
                effective_to=effective_to,
                status="DRAFT",
            )
            session.add(model)
            session.commit()
            return str(rule_uuid)

    def get_rule(self, rule_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        rule_uuid = _to_uuid(rule_id)
        with self._get_session() as session:
            model = session.get(PolicyRuleModel, rule_uuid)
            if not model:
                return None
            return _policy_rule_record(model)

    def list_rules_by_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(PolicyRuleModel).where(PolicyRuleModel.scheme_id == scheme_id)
            models = session.execute(stmt).scalars().all()
            return [_policy_rule_record(model) for model in models]

    def approve_rule(
        self,
        rule_id: Union[str, uuid.UUID],
        *,
        steward_id: Union[str, uuid.UUID],
        approval_note: str,
    ) -> Optional[Dict[str, Any]]:
        rule_uuid = _to_uuid(rule_id)
        steward_uuid = _to_uuid(steward_id)
        with self._get_session() as session:
            rule = session.execute(
                select(PolicyRuleModel)
                .where(PolicyRuleModel.id == rule_uuid)
                .with_for_update()
            ).scalar_one_or_none()
            if rule is None:
                return None
            if rule.status != "DRAFT":
                raise ValueError("Only a draft policy rule version can be approved.")
            if rule.effective_from is None:
                raise ValueError("An effective_from date is required before approval.")
            if rule.effective_to is not None and rule.effective_to < rule.effective_from:
                raise ValueError("effective_to must not precede effective_from.")
            citations = rule.source_references or []
            if not citations:
                raise ValueError("At least one exact source-version citation is required before approval.")
            if any(not citation.get("locator", "").strip() for citation in citations):
                raise ValueError("Every policy source citation requires a document locator.")
            document_ids = {_to_uuid(citation["document_id"]) for citation in citations}
            documents = {
                document.id: document
                for document in session.execute(
                    select(PolicyDocumentModel)
                    .where(PolicyDocumentModel.id.in_(document_ids))
                    .with_for_update()
                ).scalars()
            }
            if set(documents) != document_ids:
                raise ValueError("One or more cited policy documents are not registered.")
            citations_by_id = {_to_uuid(citation["document_id"]): citation for citation in citations}
            for document in documents.values():
                version = session.get(SourceVersionModel, document.source_version_id)
                source = session.get(SourceModel, version.source_id) if version else None
                citation = citations_by_id[document.id]
                if (
                    document.scheme_id != rule.scheme_id
                    or document.status != "VERIFIED"
                    or version is None
                    or version.status != "ACTIVE"
                    or source is None
                    or source.status != "ACTIVE"
                    or document.source_version_id != citation.get("source_version_id")
                    or document.document_url != citation.get("document_url")
                    or document.sha256 != citation.get("sha256")
                    or not _SHA256_RE.fullmatch(document.sha256 or "")
                    or str(version.content_hash or "").lower() != document.sha256
                    or version.source_url != document.document_url
                ):
                    raise ValueError("Every cited document must be steward-verified and match an active exact source version.")

            overlaps = session.execute(
                select(PolicyRuleModel)
                .where(
                    PolicyRuleModel.scheme_id == rule.scheme_id,
                    PolicyRuleModel.rule_key == rule.rule_key,
                    PolicyRuleModel.status == "APPROVED",
                )
                .with_for_update()
            ).scalars().all()
            requested_to = rule.effective_to or date.max
            if any(
                existing.id != rule.id
                and existing.effective_from is not None
                and rule.effective_from <= (existing.effective_to or date.max)
                and existing.effective_from <= requested_to
                for existing in overlaps
            ):
                raise ValueError("The effective period overlaps another approved version of this rule.")

            rule.status = "APPROVED"
            rule.approved_by = steward_uuid
            rule.approved_at = datetime.now(timezone.utc)
            rule.approval_note = approval_note.strip()
            session.commit()
            return _policy_rule_record(rule)

    def retire_rule(
        self,
        rule_id: Union[str, uuid.UUID],
        *,
        steward_id: Union[str, uuid.UUID],
        retirement_reason: str,
    ) -> Optional[Dict[str, Any]]:
        rule_uuid = _to_uuid(rule_id)
        with self._get_session() as session:
            rule = session.execute(
                select(PolicyRuleModel)
                .where(PolicyRuleModel.id == rule_uuid)
                .with_for_update()
            ).scalar_one_or_none()
            if rule is None:
                return None
            if rule.status != "APPROVED":
                raise ValueError("Only an approved policy rule version can be retired.")
            rule.status = "RETIRED"
            rule.retired_by = _to_uuid(steward_id)
            rule.retired_at = datetime.now(timezone.utc)
            rule.retirement_reason = retirement_reason.strip()
            session.commit()
            return _policy_rule_record(rule)

    def get_applicable_rules(self, scheme_id: str, rule_key: str, as_of: Any) -> List[Dict[str, Any]]:
        on_date = _as_date(as_of)
        with self._get_session() as session:
            stmt = select(PolicyRuleModel).where(
                PolicyRuleModel.scheme_id == scheme_id,
                PolicyRuleModel.rule_key == rule_key,
                PolicyRuleModel.status == "APPROVED",
                PolicyRuleModel.effective_from <= on_date,
                (PolicyRuleModel.effective_to.is_(None) | (PolicyRuleModel.effective_to >= on_date)),
            )
            return [_policy_rule_record(model) for model in session.execute(stmt).scalars().all()]

    def save_evaluation(self, evaluation_data: Dict[str, Any]) -> str:
        evaluation_uuid = _to_uuid(evaluation_data.get("id") or uuid.uuid4())
        with self._get_session() as session:
            session.add(PolicyEvaluationModel(
                id=evaluation_uuid,
                owner_id=_to_uuid(evaluation_data["owner_id"]),
                scheme_id=evaluation_data["scheme_id"],
                rule_id=_to_uuid(evaluation_data["rule_id"]) if evaluation_data.get("rule_id") else None,
                rule_key=evaluation_data["rule_key"],
                rule_version=evaluation_data.get("rule_version"),
                as_of=_as_date(evaluation_data["as_of"]),
                outcome=evaluation_data["outcome"],
                status=evaluation_data["status"],
                fact_quantity_ids=evaluation_data.get("fact_quantity_ids", {}),
                trace=evaluation_data["trace"],
            ))
            session.commit()
            return str(evaluation_uuid)

    def get_evaluation(
        self,
        evaluation_id: Union[str, uuid.UUID],
        *,
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        evaluation_uuid = _to_uuid(evaluation_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            model = session.execute(
                select(PolicyEvaluationModel).where(
                    PolicyEvaluationModel.id == evaluation_uuid,
                    PolicyEvaluationModel.owner_id == owner_uuid,
                )
            ).scalar_one_or_none()
            if model is None:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "scheme_id": model.scheme_id,
                "rule_id": str(model.rule_id) if model.rule_id else None,
                "rule_key": model.rule_key,
                "rule_version": model.rule_version,
                "as_of": model.as_of.isoformat(),
                "outcome": model.outcome,
                "status": model.status,
                "fact_quantity_ids": model.fact_quantity_ids,
                "trace": model.trace,
                "created_at": model.created_at,
            }


class PostgresScenarioRepository(ScenarioRepository):
    """PostgreSQL-backed implementation of ScenarioRepository."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_scenario(self, scenario_data: Dict[str, Any]) -> str:
        scenario_uuid = _to_uuid(scenario_data.get("id") or uuid.uuid4())
        owner_uuid = _to_uuid(scenario_data["owner_id"])
        with self._get_session() as session:
            existing = session.get(ScenarioModel, scenario_uuid)
            if existing:
                if existing.owner_id != owner_uuid:
                    raise PermissionError("Scenario records may only be updated by their owner.")
                existing.name = scenario_data["name"]
                existing.scenario = scenario_data["scenario"]
                session.commit()
                return str(scenario_uuid)

            model = ScenarioModel(
                id=scenario_uuid,
                owner_id=owner_uuid,
                name=scenario_data["name"],
                scenario=scenario_data["scenario"],
            )
            session.add(model)
            session.commit()
            return str(scenario_uuid)

    def get_scenario(self, scenario_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        scenario_uuid = _to_uuid(scenario_id)
        with self._get_session() as session:
            model = session.get(ScenarioModel, scenario_uuid)
            if not model:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "name": model.name,
                "scenario": model.scenario,
                "created_at": model.created_at,
            }

    def delete_scenario(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> bool:
        scenario_uuid = _to_uuid(scenario_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = select(ScenarioModel).where(
                ScenarioModel.id == scenario_uuid,
                ScenarioModel.owner_id == owner_uuid,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return False
            session.delete(model)
            session.commit()
            return True

    def list_by_owner(self, owner_id: Union[str, uuid.UUID]) -> List[Dict[str, Any]]:
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = select(ScenarioModel).where(ScenarioModel.owner_id == owner_uuid)
            models = session.execute(stmt).scalars().all()
            return [
                {
                    "id": str(m.id),
                    "owner_id": str(m.owner_id),
                    "name": m.name,
                    "scenario": m.scenario,
                    "created_at": m.created_at,
                }
                for m in models
            ]

    def save_simulation_run(self, run_data: Dict[str, Any]) -> str:
        run_uuid = _to_uuid(run_data.get("id") or uuid.uuid4())
        scenario_uuid = _to_uuid(run_data["scenario_id"])
        seed_decimal = validate_and_convert_seed(run_data["seed"])

        with self._get_session() as session:
            existing = session.get(SimulationRunModel, run_uuid)
            if existing:
                existing.seed = seed_decimal
                existing.model_version = run_data["model_version"]
                existing.git_hash = run_data.get("git_hash")
                existing.data_version_ids = list(run_data.get("data_version_ids", []))
                existing.outputs_references = run_data.get("outputs_references", {})
                existing.status = run_data.get("status", "PENDING")
                session.commit()
                return str(run_uuid)

            model = SimulationRunModel(
                id=run_uuid,
                scenario_id=scenario_uuid,
                seed=seed_decimal,
                model_version=run_data["model_version"],
                git_hash=run_data.get("git_hash"),
                data_version_ids=list(run_data.get("data_version_ids", [])),
                outputs_references=run_data.get("outputs_references", {}),
                status=run_data.get("status", "PENDING"),
            )
            session.add(model)
            session.commit()
            return str(run_uuid)

    def get_simulation_run(self, run_id: Union[str, uuid.UUID]) -> Optional[Dict[str, Any]]:
        run_uuid = _to_uuid(run_id)
        with self._get_session() as session:
            model = session.get(SimulationRunModel, run_uuid)
            if not model:
                return None
            seed_int = int(model.seed)
            return {
                "id": str(model.id),
                "scenario_id": str(model.scenario_id),
                "seed": seed_int,
                "model_version": model.model_version,
                "git_hash": model.git_hash,
                "data_version_ids": list(model.data_version_ids or []),
                "outputs_references": model.outputs_references,
                "status": model.status,
                "created_at": model.created_at,
            }

    def get_run_by_id_and_owner(
        self,
        run_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        run_uuid = _to_uuid(run_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = (
                select(SimulationRunModel)
                .join(ScenarioModel, SimulationRunModel.scenario_id == ScenarioModel.id)
                .where(SimulationRunModel.id == run_uuid, ScenarioModel.owner_id == owner_uuid)
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            seed_int = int(model.seed)
            return {
                "id": str(model.id),
                "scenario_id": str(model.scenario_id),
                "seed": seed_int,
                "model_version": model.model_version,
                "git_hash": model.git_hash,
                "data_version_ids": list(model.data_version_ids or []),
                "outputs_references": model.outputs_references,
                "status": model.status,
                "created_at": model.created_at,
            }

    def get_scenario_by_id_and_owner(
        self,
        scenario_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        scenario_uuid = _to_uuid(scenario_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            stmt = select(ScenarioModel).where(
                ScenarioModel.id == scenario_uuid,
                ScenarioModel.owner_id == owner_uuid,
            )
            model = session.execute(stmt).scalar_one_or_none()
            if not model:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "name": model.name,
                "scenario": model.scenario,
                "created_at": model.created_at,
            }

    def save_comparison(self, comparison_data: Dict[str, Any]) -> str:
        comparison_uuid = _to_uuid(comparison_data.get("id") or uuid.uuid4())
        owner_uuid = _to_uuid(comparison_data["owner_id"])
        left_uuid = _to_uuid(comparison_data["left_scenario_id"])
        right_uuid = _to_uuid(comparison_data["right_scenario_id"])
        if left_uuid == right_uuid:
            raise ValueError("A scenario cannot be compared with itself.")
        with self._get_session() as session:
            if session.get(ScenarioComparisonModel, comparison_uuid) is not None:
                raise ValueError("Scenario comparison records are immutable.")
            owned_ids = set(session.execute(
                select(ScenarioModel.id).where(
                    ScenarioModel.id.in_((left_uuid, right_uuid)),
                    ScenarioModel.owner_id == owner_uuid,
                )
            ).scalars().all())
            if owned_ids != {left_uuid, right_uuid}:
                raise ValueError("Both scenarios must exist and belong to the comparison owner.")
            record = ScenarioComparisonModel(
                id=comparison_uuid,
                owner_id=owner_uuid,
                left_scenario_id=left_uuid,
                right_scenario_id=right_uuid,
                status=comparison_data["status"],
                metric_results=comparison_data["metric_results"],
            )
            session.add(record)
            session.commit()
            return str(comparison_uuid)

    def get_comparison_by_id_and_owner(
        self,
        comparison_id: Union[str, uuid.UUID],
        owner_id: Union[str, uuid.UUID],
    ) -> Optional[Dict[str, Any]]:
        comparison_uuid = _to_uuid(comparison_id)
        owner_uuid = _to_uuid(owner_id)
        with self._get_session() as session:
            model = session.execute(select(ScenarioComparisonModel).where(
                ScenarioComparisonModel.id == comparison_uuid,
                ScenarioComparisonModel.owner_id == owner_uuid,
            )).scalar_one_or_none()
            if model is None:
                return None
            return {
                "id": str(model.id),
                "owner_id": str(model.owner_id),
                "left_scenario_id": str(model.left_scenario_id),
                "right_scenario_id": str(model.right_scenario_id),
                "status": model.status,
                "metric_results": model.metric_results,
                "created_at": model.created_at.isoformat() if model.created_at else None,
            }


class PostgresSourceRepository(SourceRepository):
    """PostgreSQL implementation of SourceRepository managing sources and snapshot versions."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def save_source(self, source_data: Dict[str, Any], session: Optional[Session] = None) -> None:
        s_id = str(source_data["id"])
        sess = session or self._get_session()
        owns_session = session is None
        try:
            existing = sess.get(SourceModel, s_id)
            if existing is None:
                model = SourceModel(
                    id=s_id,
                    name=source_data.get("name") or s_id,
                    description=source_data.get("description"),
                    licence_text=source_data.get("licence_text") or source_data.get("license_name"),
                    max_age_days=source_data.get("max_age_days"),
                    status=source_data.get("status", "ACTIVE"),
                )
                sess.add(model)
            else:
                if "name" in source_data:
                    existing.name = source_data["name"]
                if "licence_text" in source_data or "license_name" in source_data:
                    existing.licence_text = source_data.get("licence_text") or source_data.get("license_name")
                if "max_age_days" in source_data:
                    existing.max_age_days = source_data["max_age_days"]
            if owns_session:
                sess.commit()
            else:
                sess.flush()
        finally:
            if owns_session:
                sess.close()

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            m = session.get(SourceModel, str(source_id))
            if not m:
                return None
            return {
                "id": m.id,
                "name": m.name,
                "description": m.description,
                "licence_text": m.licence_text,
                "max_age_days": m.max_age_days,
                "status": m.status,
                "created_at": m.created_at,
            }

    def save_version(self, version_data: Dict[str, Any], session: Optional[Session] = None) -> str:
        s_id = str(version_data["source_id"])
        c_hash = str(version_data["content_hash"])
        sess = session or self._get_session()
        owns_session = session is None
        try:
            stmt = select(SourceVersionModel).where(
                SourceVersionModel.source_id == s_id,
                SourceVersionModel.content_hash == c_hash,
            )
            existing = sess.execute(stmt).scalar_one_or_none()
            if existing is not None:
                return existing.id

            v_id = str(version_data.get("id") or f"{s_id}:{c_hash[:16]}")
            retrieval_date_val = version_data.get("retrieval_date")
            if isinstance(retrieval_date_val, str):
                retrieval_date_val = date.fromisoformat(retrieval_date_val)
            elif retrieval_date_val is None:
                retrieval_date_val = date.today()

            model = SourceVersionModel(
                id=v_id,
                source_id=s_id,
                version=str(version_data.get("version") or version_data.get("version_tag") or c_hash[:8]),
                retrieval_date=retrieval_date_val,
                content_hash=c_hash,
                source_url=version_data.get("source_url"),
                status=version_data.get("status", "ACTIVE"),
            )
            sess.add(model)
            if owns_session:
                sess.commit()
            else:
                sess.flush()
            return v_id
        finally:
            if owns_session:
                sess.close()

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            m = session.get(SourceVersionModel, str(version_id))
            if not m:
                return None
            return {
                "id": m.id,
                "source_id": m.source_id,
                "version": m.version,
                "retrieval_date": m.retrieval_date,
                "content_hash": m.content_hash,
                "source_url": m.source_url,
                "status": m.status,
                "created_at": m.created_at,
            }

    def get_version_by_hash(self, source_id: str, content_hash: str) -> Optional[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = select(SourceVersionModel).where(
                SourceVersionModel.source_id == str(source_id),
                SourceVersionModel.content_hash == str(content_hash),
            )
            m = session.execute(stmt).scalar_one_or_none()
            if not m:
                return None
            return {
                "id": m.id,
                "source_id": m.source_id,
                "version": m.version,
                "retrieval_date": m.retrieval_date,
                "content_hash": m.content_hash,
                "source_url": m.source_url,
                "status": m.status,
                "created_at": m.created_at,
            }

    def list_versions(self, source_id: str) -> List[Dict[str, Any]]:
        with self._get_session() as session:
            stmt = (
                select(SourceVersionModel)
                .where(SourceVersionModel.source_id == str(source_id))
                .order_by(SourceVersionModel.retrieval_date.desc(), SourceVersionModel.created_at.desc())
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "id": m.id,
                    "source_id": m.source_id,
                    "version": m.version,
                    "retrieval_date": m.retrieval_date,
                    "content_hash": m.content_hash,
                    "source_url": m.source_url,
                    "status": m.status,
                    "created_at": m.created_at,
                }
                for m in rows
            ]


class PostgresSourceRecordRepository(SourceRecordRepository):
    """PostgreSQL implementation of SourceRecordRepository for normalized source records."""

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def _to_record(self, m: SourceRecordModel) -> SourceRecord:
        as_of_str = m.as_of.isoformat() if m.as_of is not None else None
        return SourceRecord(
            id=m.id,
            source_id=m.source_id,
            source_version_id=m.source_version_id,
            record_id=m.record_id,
            original_fields=m.original_fields or {},
            normalized_fields=m.normalized_fields or {},
            canonical_units=m.canonical_units or {},
            geo_resolved=bool(m.geo_resolved),
            geo_unit_id=m.geo_unit_id,
            unresolved_raw_id=m.unresolved_raw_id,
            resolution_tier=int(m.resolution_tier) if m.resolution_tier is not None else None,
            as_of=as_of_str,
            temporal_support=m.temporal_support,
            license_name=m.license_name,
            attribution=m.attribution,
        )

    def save_record(self, record: SourceRecord, session: Optional[Session] = None) -> None:
        self.save_records([record], session=session)

    def save_records(self, records: Sequence[SourceRecord], session: Optional[Session] = None) -> int:
        if not records:
            return 0
        sess = session or self._get_session()
        owns_session = session is None
        try:
            values_list = []
            for r in records:
                as_of_val = None
                if r.as_of:
                    try:
                        as_of_val = date.fromisoformat(r.as_of)
                    except ValueError:
                        as_of_val = None
                values_list.append({
                    "id": r.id,
                    "source_id": r.source_id,
                    "source_version_id": r.source_version_id,
                    "record_id": r.record_id,
                    "original_fields": r.original_fields,
                    "normalized_fields": r.normalized_fields,
                    "canonical_units": r.canonical_units,
                    "geo_resolved": r.geo_resolved,
                    "geo_unit_id": r.geo_unit_id,
                    "unresolved_raw_id": r.unresolved_raw_id,
                    "resolution_tier": r.resolution_tier,
                    "as_of": as_of_val,
                    "temporal_support": r.temporal_support,
                    "license_name": r.license_name,
                    "attribution": r.attribution,
                })

            stmt = postgresql.insert(SourceRecordModel).values(values_list)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["source_version_id", "record_id"]
            )
            result = sess.execute(stmt)
            if owns_session:
                sess.commit()
            return result.rowcount
        finally:
            if owns_session:
                sess.close()

    def get_record(self, source_version_id: str, record_id: str) -> Optional[SourceRecord]:
        with self._get_session() as session:
            stmt = select(SourceRecordModel).where(
                SourceRecordModel.source_version_id == str(source_version_id),
                SourceRecordModel.record_id == str(record_id),
            )
            m = session.execute(stmt).scalar_one_or_none()
            if not m:
                return None
            return self._to_record(m)

    def get_by_id(self, source_record_id: str) -> Optional[SourceRecord]:
        """Resolve an exact source-record primary key for geometry/provenance checks."""
        with self._get_session() as session:
            model = session.get(SourceRecordModel, str(source_record_id))
            return self._to_record(model) if model is not None else None

    def list_by_version(self, source_version_id: str) -> List[SourceRecord]:
        with self._get_session() as session:
            stmt = (
                select(SourceRecordModel)
                .where(SourceRecordModel.source_version_id == str(source_version_id))
                .order_by(SourceRecordModel.record_id)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_record(m) for m in rows]

    def list_by_source(self, source_id: str) -> List[SourceRecord]:
        with self._get_session() as session:
            stmt = (
                select(SourceRecordModel)
                .where(SourceRecordModel.source_id == str(source_id))
                .order_by(SourceRecordModel.created_at.desc(), SourceRecordModel.record_id)
            )
            rows = session.execute(stmt).scalars().all()
            return [self._to_record(m) for m in rows]


# ==============================================================================
# 7. Geographic Repository Implementation (P2-2.1)
# ==============================================================================

def _codes_differ(code1: Optional[str], code2: Optional[str]) -> bool:
    """Check if two codes differ, treating leading-zero numeric strings as matching."""
    if code1 == code2:
        return False
    if code1 is not None and code2 is not None:
        c1, c2 = str(code1).strip(), str(code2).strip()
        if c1.isdigit() and c2.isdigit():
            return int(c1) != int(c2)
    return True


class PostgresGeoUnitRepository(GeoUnitRepository):
    """
    PostgreSQL/PostGIS-backed implementation of GeoUnitRepository.
    Enforces referential integrity, hierarchy constraints, and idempotency.
    """

    def __init__(self, session_factory: Optional[Callable[[], Session]] = None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def _get_session(self) -> Session:
        return self._session_factory()

    def _to_model(self, u: GeoUnit) -> GeoUnitModel:
        """Convert a domain GeoUnit entity to a SQLAlchemy GeoUnitModel."""
        geom_status_val = (
            u.geometry_status.value
            if isinstance(u.geometry_status, GeometryStatus)
            else str(u.geometry_status)
        )
        analytical_status_val = (
            u.analytical_status.value
            if isinstance(u.analytical_status, AnalyticalStatus)
            else str(u.analytical_status)
        )
        coverage_status_val = (
            u.navigation_status.value
            if isinstance(u.navigation_status, NavigationStatus)
            else (u.coverage_status or "NAVIGABLE")
        )

        geom_val = None
        if u.geometry is not None:
            geom_json = json.dumps(u.geometry) if isinstance(u.geometry, dict) else str(u.geometry)
            geom_val = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geom_json), 4326)

        return GeoUnitModel(
            id=u.id,
            parent_id=u.parent_id,
            level=int(u.level),
            name=u.name,
            lgd_code=u.lgd_code,
            geometry=geom_val,
            coverage_status=coverage_status_val,
            geometry_status=geom_status_val,
            analytical_status=analytical_status_val,
            census_code=u.census_code,
            geometry_source_record_id=u.geometry_source_record_id,
        )

    def _to_unit(self, m: GeoUnitModel, geom_dict: Optional[Dict[str, Any]] = None) -> GeoUnit:
        """Convert a SQLAlchemy GeoUnitModel to an immutable domain GeoUnit."""
        level = ResolutionTier(m.level)
        nav_status = (
            NavigationStatus(m.coverage_status)
            if m.coverage_status in NavigationStatus._value2member_map_
            else NavigationStatus.NAVIGABLE
        )
        geom_status = (
            GeometryStatus(m.geometry_status)
            if m.geometry_status in GeometryStatus._value2member_map_
            else GeometryStatus.GEOMETRY_MISSING
        )
        analytical_status = (
            AnalyticalStatus(m.analytical_status)
            if m.analytical_status in AnalyticalStatus._value2member_map_
            else AnalyticalStatus.ANALYSIS_UNAVAILABLE
        )

        return GeoUnit(
            id=m.id,
            parent_id=m.parent_id,
            level=level,
            name=m.name,
            lgd_code=m.lgd_code,
            geometry=geom_dict,
            navigation_status=nav_status,
            geometry_status=geom_status,
            analytical_status=analytical_status,
            census_code=m.census_code,
            geometry_source_record_id=getattr(m, "geometry_source_record_id", None),
        )

    def save_unit(self, unit: GeoUnit) -> None:
        """
        Persist a GeoUnit domain entity.
        Validates parent existence (preventing orphans) and idempotency.
        Raises OrphanedGeoUnitError if parent does not exist.
        Raises ConflictingGeoUnitError if existing ID has conflicting attributes.
        Guarantees complete rollback on error.
        """
        with self._get_session() as session:
            try:
                # Check parent existence
                if unit.parent_id is not None:
                    parent = session.get(GeoUnitModel, unit.parent_id)
                    if not parent:
                        raise OrphanedGeoUnitError(
                            f"Parent unit '{unit.parent_id}' does not exist in repository for child '{unit.id}'."
                        )

                # Check existing unit
                existing = session.get(GeoUnitModel, unit.id)
                if existing:
                    if (
                        existing.name != unit.name
                        or existing.level != int(unit.level)
                        or _codes_differ(existing.lgd_code, unit.lgd_code)
                        or existing.parent_id != unit.parent_id
                    ):
                        raise ConflictingGeoUnitError(
                            f"GeoUnit '{unit.id}' already exists with conflicting definition: "
                            f"existing (name={existing.name}, level={existing.level}, lgd={existing.lgd_code}), "
                            f"new (name={unit.name}, level={unit.level}, lgd={unit.lgd_code})."
                        )
                    # Enrich attributes if new unit brings verified geometry or census code
                    if unit.census_code and not existing.census_code:
                        existing.census_code = unit.census_code
                    if unit.geometry is not None:
                        existing.geometry = func.ST_SetSRID(
                            func.ST_GeomFromGeoJSON(json.dumps(unit.geometry)), 4326
                        )
                        existing.geometry_status = (
                            unit.geometry_status.value
                            if isinstance(unit.geometry_status, GeometryStatus)
                            else str(unit.geometry_status)
                        )
                    if (
                        unit.analytical_status == AnalyticalStatus.ANALYSABLE
                        and existing.analytical_status != AnalyticalStatus.ANALYSABLE.value
                    ):
                        existing.analytical_status = AnalyticalStatus.ANALYSABLE.value
                    session.commit()
                    return

                model = self._to_model(unit)
                session.add(model)
                session.commit()
            except Exception:
                session.rollback()
                raise

    def save_units(self, units: Sequence[GeoUnit]) -> int:
        """
        Persist multiple GeoUnits in order, checking constraints within a single transaction.
        Returns the number of newly inserted units.
        Guarantees complete rollback on any error so no partial records remain.
        """
        with self._get_session() as session:
            try:
                count = 0
                for unit in units:
                    if unit.parent_id is not None:
                        parent = session.get(GeoUnitModel, unit.parent_id)
                        if not parent:
                            raise OrphanedGeoUnitError(
                                f"Parent unit '{unit.parent_id}' does not exist in repository for child '{unit.id}'."
                            )

                    existing = session.get(GeoUnitModel, unit.id)
                    if existing:
                        if (
                            existing.name != unit.name
                            or existing.level != int(unit.level)
                            or _codes_differ(existing.lgd_code, unit.lgd_code)
                            or existing.parent_id != unit.parent_id
                        ):
                            raise ConflictingGeoUnitError(
                                f"GeoUnit '{unit.id}' already exists with conflicting definition: "
                                f"existing (name={existing.name}, level={existing.level}, lgd={existing.lgd_code}), "
                                f"new (name={unit.name}, level={unit.level}, lgd={unit.lgd_code})."
                            )
                        # Enrich attributes if new unit brings verified geometry or census code
                        if unit.census_code and not existing.census_code:
                            existing.census_code = unit.census_code
                        if unit.geometry is not None:
                            existing.geometry = func.ST_SetSRID(
                                func.ST_GeomFromGeoJSON(json.dumps(unit.geometry)), 4326
                            )
                            existing.geometry_status = (
                                unit.geometry_status.value
                                if isinstance(unit.geometry_status, GeometryStatus)
                                else str(unit.geometry_status)
                            )
                        if (
                            unit.analytical_status == AnalyticalStatus.ANALYSABLE
                            and existing.analytical_status != AnalyticalStatus.ANALYSABLE.value
                        ):
                            existing.analytical_status = AnalyticalStatus.ANALYSABLE.value
                        continue

                    model = self._to_model(unit)
                    session.add(model)
                    session.flush()
                    count += 1

                session.commit()
                return count
            except Exception:
                session.rollback()
                raise

    def get_unit(self, unit_id: str) -> Optional[GeoUnit]:
        with self._get_session() as session:
            stmt = select(
                GeoUnitModel,
                func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
            ).where(GeoUnitModel.id == str(unit_id))
            row = session.execute(stmt).first()
            if not row:
                return None
            m, g_str = row
            geom_dict = json.loads(g_str) if g_str else None
            return self._to_unit(m, geom_dict)

    def get_by_id(self, unit_id: str) -> Optional[GeoUnit]:
        return self.get_unit(unit_id)

    def get_unit_by_lgd_code(self, level: ResolutionTier, lgd_code: str) -> Optional[GeoUnit]:
        with self._get_session() as session:
            stmt = select(
                GeoUnitModel,
                func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
            ).where(
                GeoUnitModel.level == int(level),
                GeoUnitModel.lgd_code == str(lgd_code).strip(),
            )
            row = session.execute(stmt).first()
            if not row:
                return None
            m, g_str = row
            geom_dict = json.loads(g_str) if g_str else None
            return self._to_unit(m, geom_dict)

    def list_by_parent(self, parent_id: Optional[str]) -> List[GeoUnit]:
        with self._get_session() as session:
            if parent_id is None:
                stmt = select(
                    GeoUnitModel,
                    func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
                ).where(GeoUnitModel.parent_id.is_(None)).order_by(GeoUnitModel.id)
            else:
                stmt = select(
                    GeoUnitModel,
                    func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
                ).where(GeoUnitModel.parent_id == str(parent_id)).order_by(GeoUnitModel.id)
            rows = session.execute(stmt).all()
            return [self._to_unit(m, json.loads(g_str) if g_str else None) for m, g_str in rows]
    def list_by_level(self, level: ResolutionTier) -> List[GeoUnit]:
        with self._get_session() as session:
            stmt = select(
                GeoUnitModel,
                func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
            ).where(GeoUnitModel.level == int(level)).order_by(GeoUnitModel.id)
            rows = session.execute(stmt).all()
            return [self._to_unit(m, json.loads(g_str) if g_str else None) for m, g_str in rows]
    def search(self, query: str, limit: int = 50) -> List[GeoUnit]:
        q = query.strip()
        if not q:
            return []
        with self._get_session() as session:
            stmt = (
                select(
                    GeoUnitModel,
                    func.ST_AsGeoJSON(GeoUnitModel.geometry).label("geom_json"),
                )
                .where(GeoUnitModel.name.ilike(f"%{q}%"))
                .order_by(GeoUnitModel.level, GeoUnitModel.name)
                .limit(limit)
            )
            rows = session.execute(stmt).all()
            return [self._to_unit(m, json.loads(g_str) if g_str else None) for m, g_str in rows]

    def update_geometry(
        self,
        unit_id: str,
        geometry: Optional[Dict[str, Any]],
        geometry_status: Union[str, GeometryStatus],
        preserve_existing: bool = True,
        geometry_source_record_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> bool:
        """
        Update boundary geometry and status for an existing geographic unit in PostGIS.
        Enforces strict domain and PostGIS invariants:
        - Only Polygon and MultiPolygon administrative geometries.
        - Valid GeoJSON structure, coordinates, and topology.
        - No geometry stored with GEOMETRY_MISSING.
        - No missing geometry represented as verified/historical/simplified.
        - No implicit verified defaults; explicit status is required.
        - Preserves higher-evidence existing geometry when a weaker candidate is received.
        - Validates ST_GeometryType and ST_IsValid in the active transaction session.
        """
        from backend.arthlens.data.adapters.admin_boundaries import validate_boundary_geometry

        # 1. Validate explicit geometry_status enum
        if geometry_status is None:
            return False
        if isinstance(geometry_status, GeometryStatus):
            status_enum = geometry_status
        elif isinstance(geometry_status, str) and geometry_status in GeometryStatus._value2member_map_:
            status_enum = GeometryStatus(geometry_status)
        else:
            return False

        # 2. Status / Geometry consistency invariants
        # No geometry stored with GEOMETRY_MISSING
        if geometry is not None and status_enum == GeometryStatus.GEOMETRY_MISSING:
            return False
        # No missing geometry represented as verified/historical/simplified
        if geometry is None and status_enum in (
            GeometryStatus.GEOMETRY_VERIFIED,
            GeometryStatus.GEOMETRY_HISTORICAL,
            GeometryStatus.GEOMETRY_SIMPLIFIED,
        ):
            return False

        # 3. GeoJSON structural and areal geometry validation
        if geometry is not None:
            is_valid, _ = validate_boundary_geometry(geometry)
            if not is_valid:
                return False

        def _do_update(sess: Session) -> bool:
            m = sess.get(GeoUnitModel, str(unit_id))
            if not m:
                return False

            existing_status = m.geometry_status or GeometryStatus.GEOMETRY_MISSING.value
            existing_rank = GEOMETRY_STATUS_RANK.get(existing_status, 0)
            candidate_rank = GEOMETRY_STATUS_RANK.get(status_enum.value, 0)

            # Preserve existing geometry invariants
            if preserve_existing and m.geometry is not None:
                if geometry is None:
                    return False
                if existing_rank > candidate_rank:
                    return False

            if geometry is None:
                m.geometry = None
                m.geometry_status = status_enum.value
                m.geometry_source_record_id = None
                return True

            # Perform actual database validation using PostGIS ST_GeometryType and ST_IsValid
            geom_json = json.dumps(geometry) if isinstance(geometry, dict) else str(geometry)
            geom_expr = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geom_json), 4326)

            stmt = select(
                func.ST_GeometryType(geom_expr),
                func.ST_IsValid(geom_expr),
                func.ST_IsValidReason(geom_expr),
            )
            row = sess.execute(stmt).first()
            if not row:
                return False
            pg_geom_type, is_pg_valid, _ = row
            if pg_geom_type not in ("ST_Polygon", "ST_MultiPolygon"):
                return False
            if not is_pg_valid:
                return False

            m.geometry = geom_expr
            m.geometry_status = status_enum.value
            if geometry_source_record_id is not None:
                m.geometry_source_record_id = geometry_source_record_id
            return True

        if session is not None:
            return _do_update(session)
        else:
            with self._get_session() as sess:
                res = _do_update(sess)
                if res:
                    sess.commit()
                return res

    def verify_geometry_validity(self, geometry: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Verify candidate GeoJSON geometry validity directly in PostGIS."""
        if not geometry:
            return False, "Geometry is empty or None."
        try:
            geom_json = json.dumps(geometry) if isinstance(geometry, dict) else str(geometry)
            with self._get_session() as session:
                stmt = select(
                    func.ST_IsValid(func.ST_SetSRID(func.ST_GeomFromGeoJSON(geom_json), 4326)),
                    func.ST_IsValidReason(func.ST_SetSRID(func.ST_GeomFromGeoJSON(geom_json), 4326)),
                )
                row = session.execute(stmt).first()
                if not row:
                    return False, "No response from PostGIS ST_IsValid."
                is_valid, reason = row
                return bool(is_valid), reason
        except Exception as e:
            return False, f"PostGIS validation error: {e}"

    def get_coverage_summary(self) -> Dict[str, Any]:
        """Query nationwide geographic database and calculate comprehensive coverage metrics."""
        with self._get_session() as session:
            total_units = session.execute(select(func.count(GeoUnitModel.id))).scalar() or 0
            units_with_geom = session.execute(
                select(func.count(GeoUnitModel.id)).where(GeoUnitModel.geometry.isnot(None))
            ).scalar() or 0

            status_stmt = select(
                GeoUnitModel.geometry_status,
                func.count(GeoUnitModel.id),
            ).group_by(GeoUnitModel.geometry_status)
            status_counts = dict(session.execute(status_stmt).all())

            tier_stmt = select(
                GeoUnitModel.level,
                func.count(GeoUnitModel.id),
                func.count(GeoUnitModel.geometry),
            ).group_by(GeoUnitModel.level)
            tier_counts = {}
            for level, count, geom_count in session.execute(tier_stmt).all():
                tier_counts[f"level_{level}"] = {"total": count, "with_geometry": geom_count}

            ds09_records = session.execute(
                select(func.count(SourceRecordModel.id)).where(SourceRecordModel.source_id == "DS-09")
            ).scalar() or 0

            return {
                "total_units": total_units,
                "units_with_geometry": units_with_geom,
                "units_missing_geometry": total_units - units_with_geom,
                "status_breakdown": status_counts,
                "geometry_status_breakdown": status_counts,
                "tier_breakdown": tier_counts,
                "ds09_source_records": ds09_records,
            }

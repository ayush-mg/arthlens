"""Application service for persisted, explicitly confirmed agent actions."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
import uuid

from sqlalchemy import select

from backend.arthlens.domain.business import GoalStatus, GoalType
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    ActionPlanModel,
    ActionTaskModel,
    AgentProposedActionModel,
    AgentSessionModel,
    BusinessMembershipModel,
    GoalModel,
)


class AgentActionNotFoundError(LookupError):
    pass


class AgentActionStateError(ValueError):
    pass


def _action_dict(row: AgentProposedActionModel) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "business_id": str(row.business_id),
        "session_id": str(row.session_id),
        "action_type": row.action_type,
        "payload": dict(row.payload or {}),
        "status": row.status,
        "created_by_user_id": str(row.created_by_user_id) if row.created_by_user_id else None,
        "confirmed_by_user_id": str(row.confirmed_by_user_id) if row.confirmed_by_user_id else None,
        "result": dict(row.result or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class AgentActionService:
    ALLOWED_TYPES = {"CREATE_GOAL", "CREATE_TASK", "GENERATE_REPORT"}
    GOAL_TYPES = {item.value for item in GoalType if item in {
        GoalType.REVENUE, GoalType.PROFIT, GoalType.DEBT_REDUCTION, GoalType.CASH_RESERVE,
    }}

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    @classmethod
    def _normalize_payload(cls, action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if action_type not in cls.ALLOWED_TYPES:
            raise ValueError("Unsupported proposed action type.")
        if action_type == "CREATE_GOAL":
            goal_type = str(payload.get("goal_type", "")).upper()
            title = str(payload.get("title", "")).strip()
            if goal_type not in cls.GOAL_TYPES or not title:
                raise ValueError("A supported goal type and title are required.")
            try:
                target_value = Decimal(str(payload.get("target_value")))
                target_date = date.fromisoformat(str(payload.get("target_date")))
                start_date = date.fromisoformat(str(payload.get("start_date") or date.today().isoformat()))
            except (InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError("Goal target value and ISO dates must be valid.") from exc
            if not target_value.is_finite() or target_value <= 0 or target_date < start_date:
                raise ValueError("Goal target must be positive and its target date cannot precede its start date.")
            return {
                "goal_type": goal_type, "title": title, "target_value": f"{target_value:.2f}",
                "start_date": start_date.isoformat(), "target_date": target_date.isoformat(),
                "plan_details": dict(payload.get("plan_details") or {}),
            }
        if action_type == "CREATE_TASK":
            title = str(payload.get("title", "")).strip()
            if not title:
                raise ValueError("A task title is required.")
            try:
                goal_id = uuid.UUID(str(payload.get("goal_id")))
                plan_id = uuid.UUID(str(payload.get("plan_id")))
                priority = int(payload.get("priority", 3))
                expected_impact = Decimal(str(payload["expected_financial_impact"]))
                assigned = uuid.UUID(str(payload["assigned_member_id"])) if payload.get("assigned_member_id") else None
                due_date = date.fromisoformat(str(payload["due_date"])) if payload.get("due_date") else None
            except (InvalidOperation, ValueError, TypeError, KeyError) as exc:
                raise ValueError("Task goal/plan identifiers, impact, priority, assignee, or due date are invalid.") from exc
            task_status = str(payload.get("status", "TODO")).upper()
            if not 1 <= priority <= 5 or task_status not in {"TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"}:
                raise ValueError("Task priority or status is not supported.")
            if not expected_impact.is_finite():
                raise ValueError("Expected financial impact must be finite.")
            return {
                "goal_id": str(goal_id), "plan_id": str(plan_id), "title": title,
                "description": str(payload.get("description", "")),
                "assigned_member_id": str(assigned) if assigned else None,
                "priority": priority, "status": task_status,
                "due_date": due_date.isoformat() if due_date else None,
                "expected_financial_impact": f"{expected_impact:.2f}",
            }
        report_type = str(payload.get("report_type", "")).upper()
        if report_type not in {"EXECUTIVE_DOSSIER", "DECISION_BRIEF"}:
            raise ValueError("Report type must be EXECUTIVE_DOSSIER or DECISION_BRIEF.")
        evaluation_id = None
        if report_type == "DECISION_BRIEF":
            try:
                evaluation_id = str(uuid.UUID(str(payload.get("evaluation_id"))))
            except (ValueError, TypeError) as exc:
                raise ValueError("A valid evaluation_id is required for a decision brief.") from exc
        return {"report_type": report_type, "evaluation_id": evaluation_id}

    def create(self, business_id: uuid.UUID, session_id: uuid.UUID, user_id: uuid.UUID,
               action_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(action_type, payload)
        with self.session_factory() as session, session.begin():
            agent_session = session.scalar(select(AgentSessionModel).where(
                AgentSessionModel.id == session_id,
                AgentSessionModel.business_id == business_id,
                AgentSessionModel.user_id == user_id,
            ))
            if agent_session is None:
                raise AgentActionNotFoundError("Agent session was not found in this workspace.")
            row = AgentProposedActionModel(
                business_id=business_id, session_id=session_id, action_type=action_type,
                payload=normalized, status="PENDING_CONFIRMATION", created_by_user_id=user_id,
            )
            session.add(row)
            session.flush()
            return _action_dict(row)

    def list_for_session(self, business_id: uuid.UUID, session_id: uuid.UUID) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            agent_session = session.scalar(select(AgentSessionModel.id).where(
                AgentSessionModel.id == session_id, AgentSessionModel.business_id == business_id,
            ))
            if agent_session is None:
                raise AgentActionNotFoundError("Agent session was not found in this workspace.")
            rows = session.scalars(select(AgentProposedActionModel).where(
                AgentProposedActionModel.business_id == business_id,
                AgentProposedActionModel.session_id == session_id,
            ).order_by(AgentProposedActionModel.created_at.asc())).all()
            return [_action_dict(row) for row in rows]

    def get(self, business_id: uuid.UUID, session_id: uuid.UUID, action_id: uuid.UUID) -> dict[str, Any]:
        with self.session_factory() as session:
            row = session.scalar(select(AgentProposedActionModel).where(
                AgentProposedActionModel.id == action_id,
                AgentProposedActionModel.business_id == business_id,
                AgentProposedActionModel.session_id == session_id,
            ))
            if row is None:
                raise AgentActionNotFoundError("Proposed action was not found in this workspace.")
            return _action_dict(row)

    def confirm(self, business_id: uuid.UUID, session_id: uuid.UUID, action_id: uuid.UUID,
                user_id: uuid.UUID) -> dict[str, Any]:
        with self.session_factory() as session, session.begin():
            row = session.scalar(select(AgentProposedActionModel).where(
                AgentProposedActionModel.id == action_id,
                AgentProposedActionModel.business_id == business_id,
                AgentProposedActionModel.session_id == session_id,
            ).with_for_update())
            if row is None:
                raise AgentActionNotFoundError("Proposed action was not found in this workspace.")
            if row.status != "PENDING_CONFIRMATION":
                raise AgentActionStateError(f"Action is already {row.status.lower()}.")

            payload = dict(row.payload or {})
            if row.action_type == "CREATE_GOAL":
                goal_id = uuid.uuid4()
                goal = GoalModel(
                    id=goal_id, business_id=business_id, goal_type=payload["goal_type"],
                    title=payload["title"], target_value=Decimal(payload["target_value"]),
                    current_value=Decimal("0.00"), start_date=date.fromisoformat(payload["start_date"]),
                    target_date=date.fromisoformat(payload["target_date"]), status=GoalStatus.ACTIVE.value,
                    plan_details=payload.get("plan_details", {}),
                )
                session.add(goal)
                result = {"resource_type": "GOAL", "resource_id": str(goal_id), "title": goal.title}
            elif row.action_type == "CREATE_TASK":
                goal_id = uuid.UUID(payload["goal_id"])
                plan_id = uuid.UUID(payload["plan_id"])
                goal = session.scalar(select(GoalModel).where(
                    GoalModel.id == goal_id, GoalModel.business_id == business_id,
                ))
                plan = session.scalar(select(ActionPlanModel).where(
                    ActionPlanModel.id == plan_id, ActionPlanModel.goal_id == goal_id,
                    ActionPlanModel.business_id == business_id,
                ))
                if goal is None or plan is None:
                    raise AgentActionNotFoundError("The task goal or action plan was not found in this workspace.")
                assigned_id = uuid.UUID(payload["assigned_member_id"]) if payload.get("assigned_member_id") else None
                if assigned_id is not None:
                    membership = session.scalar(select(BusinessMembershipModel.id).where(
                        BusinessMembershipModel.business_id == business_id,
                        BusinessMembershipModel.user_id == assigned_id,
                        BusinessMembershipModel.is_active.is_(True),
                    ))
                    if membership is None:
                        raise ValueError("Assigned user must be an active member of this workspace.")
                task_id = uuid.uuid4()
                task = ActionTaskModel(
                    id=task_id, business_id=business_id, goal_id=goal_id, plan_id=plan_id,
                    title=payload["title"], description=payload["description"],
                    assigned_member_id=assigned_id, priority=payload["priority"], status=payload["status"],
                    due_date=date.fromisoformat(payload["due_date"]) if payload["due_date"] else None,
                    expected_financial_impact=Decimal(payload["expected_financial_impact"]),
                    created_by_user_id=user_id,
                )
                session.add(task)
                result = {"resource_type": "ACTION_TASK", "resource_id": str(task_id), "title": task.title}
            else:
                result = {
                    "resource_type": "REPORT", "report_type": payload["report_type"],
                    "evaluation_id": payload.get("evaluation_id"),
                    "download_path": (
                        f"/businesses/{business_id}/agent/sessions/{session_id}/actions/{action_id}/download"
                    ),
                }

            row.status = "CONFIRMED"
            row.confirmed_by_user_id = user_id
            row.result = result
            row.updated_at = datetime.now(timezone.utc)
            session.flush()
            return _action_dict(row)

    def reject(self, business_id: uuid.UUID, session_id: uuid.UUID, action_id: uuid.UUID,
               user_id: uuid.UUID) -> dict[str, Any]:
        with self.session_factory() as session, session.begin():
            row = session.scalar(select(AgentProposedActionModel).where(
                AgentProposedActionModel.id == action_id,
                AgentProposedActionModel.business_id == business_id,
                AgentProposedActionModel.session_id == session_id,
            ).with_for_update())
            if row is None:
                raise AgentActionNotFoundError("Proposed action was not found in this workspace.")
            if row.status != "PENDING_CONFIRMATION":
                raise AgentActionStateError(f"Action is already {row.status.lower()}.")
            row.status = "REJECTED"
            row.confirmed_by_user_id = user_id
            row.updated_at = datetime.now(timezone.utc)
            session.flush()
            return _action_dict(row)


_agent_action_service: AgentActionService | None = None


def get_agent_action_service() -> AgentActionService:
    global _agent_action_service
    if _agent_action_service is None:
        _agent_action_service = AgentActionService()
    return _agent_action_service

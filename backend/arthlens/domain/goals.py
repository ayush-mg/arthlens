"""Goal planning domain records; persistence and orchestration live in services/infra."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
import uuid


@dataclass(frozen=True)
class GoalMilestone:
    id: uuid.UUID
    goal_id: uuid.UUID
    target_date: date
    target_value: Decimal
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ActionPlan:
    id: uuid.UUID
    business_id: uuid.UUID
    goal_id: uuid.UUID
    title: str
    description: str = ""
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ActionTask:
    id: uuid.UUID
    business_id: uuid.UUID
    goal_id: uuid.UUID
    plan_id: uuid.UUID
    title: str
    description: str = ""
    assigned_member_id: uuid.UUID | None = None
    priority: int = 3
    status: str = "TODO"
    due_date: date | None = None
    expected_financial_impact: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class GoalProgressSnapshot:
    id: uuid.UUID
    business_id: uuid.UUID
    goal_id: uuid.UUID
    as_of_date: date
    actual_value: Decimal
    planned_value: Decimal
    deviation_value: Decimal
    status: str
    explanation: dict[str, Any]
    evidence_items: tuple[dict[str, Any], ...]

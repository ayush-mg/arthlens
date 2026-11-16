"""Agent plan and user-confirmed action domain records."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(frozen=True)
class AgentPlanStep:
    step_id: int
    tool_name: str
    depends_on_step_ids: tuple[int, ...] = ()
    rationale: str = ""
    status: str = "PENDING"


@dataclass(frozen=True)
class ProposedAction:
    id: uuid.UUID
    business_id: uuid.UUID
    session_id: uuid.UUID
    action_type: str
    payload: dict[str, Any]
    status: str = "PENDING_CONFIRMATION"
    created_by_user_id: uuid.UUID | None = None
    confirmed_by_user_id: uuid.UUID | None = None
    result: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


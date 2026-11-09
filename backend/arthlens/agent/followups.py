"""Validated conversion of unresolved evidence gaps into follow-up tasks."""

from enum import Enum
from typing import Any, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UnresolvedGap(BaseModel):
    """An explicit evidence gap from a verifier or orchestration step."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=4000)
    linked_gap_quantity_id: UUID | None = None
    priority: str | None = None

    @field_validator("description")
    @classmethod
    def require_non_whitespace_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Gap description must contain non-whitespace characters.")
        return normalized

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        norm = value.strip().upper()
        if norm not in {p.value for p in TaskPriority}:
            raise ValueError(f"Priority must be one of {[p.value for p in TaskPriority]}.")
        return norm


def tasks_from_unresolved_gaps(
    gaps: Sequence[UnresolvedGap],
) -> list[dict[str, Any]]:
    """Create neutral task records without asserting facts or resolving the gap."""
    if not gaps:
        raise ValueError("At least one unresolved gap is required.")
    results: list[dict[str, Any]] = []
    for gap in gaps:
        item: dict[str, Any] = {
            "text": f"Resolve this evidence gap: {gap.description}",
            "linked_gap_quantity_id": gap.linked_gap_quantity_id,
        }
        if gap.priority is not None:
            item["priority"] = gap.priority.upper()
        results.append(item)
    return results


def extract_evidence_gaps(outputs: Sequence[dict[str, Any]]) -> list[UnresolvedGap]:
    """Scan plan execution outputs for explicit evidence gaps and missing data."""
    gaps: list[UnresolvedGap] = []
    for item in outputs:
        if not isinstance(item, dict):
            continue
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        # Direct list of unresolved gaps
        if "unresolved_gaps" in result and isinstance(result["unresolved_gaps"], list):
            for g in result["unresolved_gaps"]:
                if isinstance(g, UnresolvedGap):
                    gaps.append(g)
                elif isinstance(g, dict) and "description" in g:
                    gaps.append(UnresolvedGap(**g))
        # Missing evidence strings
        if "missing_evidence" in result and isinstance(result["missing_evidence"], list):
            for missing in result["missing_evidence"]:
                if isinstance(missing, str) and missing.strip():
                    gaps.append(
                        UnresolvedGap(
                            description=f"Missing evidence: {missing.strip()}",
                            priority="HIGH",
                        )
                    )
        # INSUFFICIENT_DATA status without specific missing_evidence
        if result.get("status") == "INSUFFICIENT_DATA" and not result.get("missing_evidence"):
            detail = result.get("detail") or result.get("reason") or "Insufficient data to verify tool output"
            gaps.append(UnresolvedGap(description=str(detail), priority="HIGH"))
    return gaps

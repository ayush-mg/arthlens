"""Validated conversion of unresolved evidence gaps into follow-up tasks."""

from typing import Any, Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UnresolvedGap(BaseModel):
    """An explicit evidence gap from a verifier or orchestration step."""

    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=4000)
    linked_gap_quantity_id: UUID | None = None

    @field_validator("description")
    @classmethod
    def require_non_whitespace_description(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Gap description must contain non-whitespace characters.")
        return normalized


def tasks_from_unresolved_gaps(
    gaps: Sequence[UnresolvedGap],
) -> list[dict[str, Any]]:
    """Create neutral task records without asserting facts or resolving the gap."""
    if not gaps:
        raise ValueError("At least one unresolved gap is required.")
    return [
        {
            "text": f"Resolve this evidence gap: {gap.description}",
            "linked_gap_quantity_id": gap.linked_gap_quantity_id,
        }
        for gap in gaps
    ]

import pytest
from backend.arthlens.agent.followups import (
    UnresolvedGap,
    tasks_from_unresolved_gaps,
)
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from pydantic import ValidationError


@pytest.mark.unit
def test_unresolved_gaps_generate_neutral_followup_tasks():
    gap = UnresolvedGap(
        description="  Confirm the source vintage. ",
        linked_gap_quantity_id="f4183670-47fb-4c64-98a8-932b138f57b9",
    )

    assert tasks_from_unresolved_gaps([gap]) == [
        {
            "text": "Resolve this evidence gap: Confirm the source vintage.",
            "linked_gap_quantity_id": gap.linked_gap_quantity_id,
        }
    ]


@pytest.mark.unit
def test_followup_gap_input_is_strict_and_requires_a_real_description():
    with pytest.raises(ValidationError):
        UnresolvedGap(description="  ")
    with pytest.raises(ValidationError):
        UnresolvedGap(description="Verify the source.", unsupported="field")
    with pytest.raises(ValidationError):
        UnresolvedGap(description="Verify the source.", linked_gap_quantity_id="not-a-uuid")
    with pytest.raises(ValueError, match="At least one unresolved gap"):
        tasks_from_unresolved_gaps([])


@pytest.mark.unit
def test_create_followup_tasks_tool_schema_uses_typed_gap_inputs():
    parsed = build_default_tool_registry().validate_input(
        "create_followup_tasks",
        {
            "unresolved_gaps": [
                {"description": "Supply the missing user assumption."}
            ]
        },
    )

    assert parsed.unresolved_gaps[0].description == (
        "Supply the missing user assumption."
    )

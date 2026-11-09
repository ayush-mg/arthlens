import pytest
from backend.arthlens.agent.followups import (
    TaskPriority,
    TaskStatus,
    UnresolvedGap,
    extract_evidence_gaps,
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
def test_unresolved_gaps_with_priority_and_status():
    gap = UnresolvedGap(
        description="Verify power grid availability.",
        priority="HIGH",
    )
    tasks = tasks_from_unresolved_gaps([gap])
    assert len(tasks) == 1
    assert tasks[0]["text"] == "Resolve this evidence gap: Verify power grid availability."
    assert tasks[0]["priority"] == "HIGH"
    assert TaskPriority.HIGH.value == "HIGH"
    assert TaskStatus.COMPLETED.value == "COMPLETED"


@pytest.mark.unit
def test_followup_gap_input_is_strict_and_requires_a_real_description():
    with pytest.raises(ValidationError):
        UnresolvedGap(description="  ")
    with pytest.raises(ValidationError):
        UnresolvedGap(description="Verify the source.", unsupported="field")
    with pytest.raises(ValidationError):
        UnresolvedGap(description="Verify the source.", linked_gap_quantity_id="not-a-uuid")
    with pytest.raises(ValidationError):
        UnresolvedGap(description="Verify the source.", priority="INVALID_PRIORITY")
    with pytest.raises(ValueError, match="At least one unresolved gap"):
        tasks_from_unresolved_gaps([])


@pytest.mark.unit
def test_extract_evidence_gaps_from_tool_outputs():
    outputs = [
        {
            "tool_name": "allocate_spatial_demand",
            "result": {
                "status": "INSUFFICIENT_DATA",
                "missing_evidence": ["ledger provenance for zone demand Z1"],
            },
        },
        {
            "tool_name": "fetch_economic_indicator",
            "result": {
                "status": "INSUFFICIENT_DATA",
                "detail": "Indicator mandi_prices unavailable for district",
            },
        },
        {
            "tool_name": "calculate_break_even",
            "result": {
                "break_even_units": 100,
            },
        },
    ]

    gaps = extract_evidence_gaps(outputs)
    assert len(gaps) == 2
    assert "Missing evidence: ledger provenance for zone demand Z1" in gaps[0].description
    assert gaps[0].priority == "HIGH"
    assert "Indicator mandi_prices unavailable for district" in gaps[1].description


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

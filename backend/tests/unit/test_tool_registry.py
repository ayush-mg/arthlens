from datetime import date

import pytest
from backend.arthlens.agent.tool_registry import (
    CalculateBreakEvenOutput,
    FetchEconomicIndicatorInput,
    ToolSchema,
    ToolSchemaRegistry,
    build_default_tool_registry,
)
from pydantic import ValidationError


@pytest.mark.unit
def test_default_registry_contains_all_handbook_tools():
    registry = build_default_tool_registry()

    assert len(registry.names()) == 14
    assert registry.names() == (
        "fetch_economic_indicator",
        "search_policy_documents",
        "verify_claim",
        "evaluate_scheme_eligibility",
        "calculate_loan_schedule",
        "calculate_break_even",
        "compute_catchment",
        "allocate_spatial_demand",
        "run_business_scenario",
        "run_sensitivity_analysis",
        "compare_scenarios",
        "generate_report",
        "create_followup_tasks",
        "publish_to_shared_view",
    )


@pytest.mark.unit
def test_tool_registry_exposes_input_json_schema_and_validates():
    registry = build_default_tool_registry()
    schema = registry.input_json_schema("fetch_economic_indicator")
    parsed = registry.validate_input(
        "fetch_economic_indicator",
        {"source": "data.gov.in", "geo_id": "IN-UP-XXX", "series": "mandi.price"},
    )

    assert schema["additionalProperties"] is False
    assert parsed == FetchEconomicIndicatorInput(
        source="data.gov.in",
        geo_id="IN-UP-XXX",
        series="mandi.price",
    )


@pytest.mark.unit
def test_tool_input_rejects_unregistered_fields():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FetchEconomicIndicatorInput(
            source="data.gov.in",
            geo_id="IN-UP-XXX",
            series="mandi.price",
            extra="not allowed",
        )


@pytest.mark.unit
def test_eligibility_input_parses_as_of_as_calendar_date():
    parsed = build_default_tool_registry().validate_input(
        "evaluate_scheme_eligibility",
        {"scheme": "candidate", "facts": {}, "as_of": "2026-11-07"},
    )

    assert parsed.as_of == date(2026, 11, 7)


@pytest.mark.unit
def test_only_publish_tool_requires_approval():
    registry = build_default_tool_registry()

    assert registry.get("publish_to_shared_view").approval_required
    assert all(
        not tool.approval_required
        for name in registry.names()
        if name != "publish_to_shared_view"
        for tool in (registry.get(name),)
    )
    assert registry.get("publish_to_shared_view").writes == ("shared view",)


@pytest.mark.unit
def test_registry_rejects_duplicate_or_malformed_definitions():
    registry = ToolSchemaRegistry()
    definition = ToolSchema("sample", FetchEconomicIndicatorInput, "sample output")
    registry.register(definition)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(definition)
    with pytest.raises(ValueError, match="trimmed"):
        registry.register(ToolSchema(" sample ", FetchEconomicIndicatorInput, "output"))
    with pytest.raises(KeyError, match="not registered"):
        registry.get("missing")


@pytest.mark.unit
def test_registry_rejects_non_tool_input_models():
    class NotToolInput:
        pass

    registry = ToolSchemaRegistry()
    with pytest.raises(TypeError, match="inherit from ToolInput"):
        registry.register(ToolSchema("sample", NotToolInput, "output"))
    assert registry.names() == ()


@pytest.mark.unit
def test_registry_exposes_bound_tool_output_schema():
    registry = build_default_tool_registry()

    schema = registry.output_json_schema("calculate_break_even")
    parsed = registry.validate_output(
        "calculate_break_even",
        {"break_even_quantity": 5, "quality_flags": []},
    )

    assert schema is not None
    assert isinstance(parsed, CalculateBreakEvenOutput)
    assert parsed.break_even_quantity == 5.0
    assert registry.output_json_schema("fetch_economic_indicator") is None


@pytest.mark.unit
def test_registry_rejects_invalid_tool_output_models():
    class NotToolOutput:
        pass

    registry = ToolSchemaRegistry()
    with pytest.raises(TypeError, match="inherit from ToolOutput"):
        registry.register(
            ToolSchema(
                "sample",
                FetchEconomicIndicatorInput,
                "sample output",
                output_model=NotToolOutput,
            )
        )
    with pytest.raises(ValueError, match="no output schema"):
        build_default_tool_registry().validate_output("fetch_economic_indicator", {})


@pytest.mark.unit
def test_registry_rejects_invalid_tool_arguments():
    registry = build_default_tool_registry()

    with pytest.raises(ValidationError):
        registry.validate_input(
            "fetch_economic_indicator",
            {"source": "", "geo_id": "IN-UP-XXX", "series": "mandi.price"},
        )


@pytest.mark.unit
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_tool_registry_rejects_non_finite_numbers_in_direct_inputs(value):
    with pytest.raises(ValidationError, match="finite numbers"):
        build_default_tool_registry().validate_input(
            "calculate_break_even",
            {"price": value, "variable_cost": 0, "fixed_costs": 1},
        )


@pytest.mark.unit
def test_tool_registry_rejects_non_finite_nested_values():
    with pytest.raises(ValidationError, match="finite numbers"):
        build_default_tool_registry().validate_input(
            "run_business_scenario",
            {"scenario": {"assumption": {"value": float("inf")}}},
        )

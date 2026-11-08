"""Validated schemas and metadata for the handbook's registered tools."""

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

from backend.arthlens.agent.followups import UnresolvedGap
from backend.arthlens.finance.loans import (
    MoratoriumInterestTreatment,
    SubsidyTreatment,
)


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_non_finite_numbers(cls, value: Any) -> Any:
        def validate(item: Any) -> None:
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError("Tool inputs must contain only finite numbers.")
            if isinstance(item, dict):
                for nested in item.values():
                    validate(nested)
            elif isinstance(item, (list, tuple)):
                for nested in item:
                    validate(nested)

        validate(value)
        return value


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class CalculateBreakEvenOutput(ToolOutput):
    break_even_quantity: StrictFloat | None
    quality_flags: list[StrictStr]


class LoanScheduleRowOutput(ToolOutput):
    month: StrictInt
    opening_balance: StrictFloat
    interest: StrictFloat
    principal_paid: StrictFloat
    subsidy_principal_adjustment: StrictFloat
    subsidy_cash_release: StrictFloat
    debt_service: StrictFloat
    closing_balance: StrictFloat


class CalculateLoanScheduleOutput(ToolOutput):
    financed_principal: StrictFloat
    total_repaid: StrictFloat
    rows: list[LoanScheduleRowOutput]


class FetchEconomicIndicatorInput(ToolInput):
    source: str = Field(min_length=1)
    geo_id: str = Field(min_length=1)
    series: str = Field(min_length=1)


class SearchPolicyDocumentsInput(ToolInput):
    scheme: str = Field(min_length=1)
    query: str = Field(min_length=1)


class VerifyClaimInput(ToolInput):
    claim: str = Field(min_length=1)


class EvaluateSchemeEligibilityInput(ToolInput):
    scheme: str = Field(min_length=1)
    facts: dict[str, Any]
    as_of: date


class MoratoriumInput(ToolInput):
    months: int = Field(ge=0)
    interest_treatment: MoratoriumInterestTreatment


class SubsidyParametersInput(ToolInput):
    amount: float = Field(ge=0)
    treatment: SubsidyTreatment
    release_month: int | None


class CalculateLoanScheduleInput(ToolInput):
    principal: float = Field(gt=0)
    rate: float = Field(
        ge=0,
        description="Annual interest rate as a decimal fraction (for example 0.12 for 12%).",
    )
    term: int = Field(gt=0)
    moratorium: MoratoriumInput
    subsidy_params: SubsidyParametersInput


class CalculateBreakEvenInput(ToolInput):
    price: float = Field(gt=0)
    variable_cost: float = Field(ge=0)
    fixed_costs: float = Field(ge=0)


class ComputeCatchmentInput(ToolInput):
    site: dict[str, Any]
    minutes: float = Field(gt=0)
    mode: str = Field(min_length=1)


class TravelTimeProvenanceInput(ToolInput):
    zone_id: str = Field(min_length=1)
    facility_id: str = Field(min_length=1)
    quantity_id: str = Field(min_length=1)


class SpatialDemandProvenanceInput(ToolInput):
    """Per-input ledger links required for a spatial demand allocation."""

    zone_demand_quantity_ids: dict[str, str] = Field(default_factory=dict)
    facility_attractiveness_quantity_ids: dict[str, str] = Field(default_factory=dict)
    travel_time_quantity_ids: list[TravelTimeProvenanceInput] = Field(default_factory=list)
    distance_decay_quantity_id: str | None = None


class AllocateSpatialDemandInput(ToolInput):
    zones: list[dict[str, Any]] = Field(min_length=1)
    facilities: list[dict[str, Any]] = Field(min_length=1)
    allocator: str = Field(min_length=1)
    params: dict[str, Any]
    seed: int = Field(ge=0)
    provenance: SpatialDemandProvenanceInput = Field(default_factory=SpatialDemandProvenanceInput)


class RunBusinessScenarioInput(ToolInput):
    scenario: dict[str, Any]


class RunSensitivityAnalysisInput(ToolInput):
    scenario: dict[str, Any] = Field(
        description="Explicit projection_inputs matching every FinancialScenario field."
    )
    inputs: dict[str, Any] = Field(
        description=(
            "Explicit sensitivity_parameter_values plus baseline_quantity_ids and "
            "sensitivity_quantity_ids for matching ledger assumptions."
        )
    )


class CompareScenariosInput(ToolInput):
    run_ids: list[str] = Field(min_length=1)


class GenerateReportInput(ToolInput):
    verified_claim_graph: dict[str, Any]


class CreateFollowupTasksInput(ToolInput):
    unresolved_gaps: list[UnresolvedGap] = Field(min_length=1, max_length=100)


class PublishToSharedViewInput(ToolInput):
    run_id: str = Field(min_length=1)


@dataclass(frozen=True)
class ToolSchema:
    name: str
    input_model: type[BaseModel]
    output_description: str
    writes: tuple[str, ...] = ()
    approval_required: bool = False
    output_model: type[ToolOutput] | None = None


class ToolSchemaRegistry:
    """Registry for planner-visible tool input schemas and effects metadata."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSchema] = {}

    def register(self, tool: ToolSchema) -> None:
        if not tool.name or tool.name.strip() != tool.name:
            raise ValueError("Tool name must be a non-empty trimmed string")
        if tool.name in self._tools:
            raise ValueError(f"Tool {tool.name!r} is already registered")
        if not issubclass(tool.input_model, ToolInput):
            raise TypeError("Tool input model must inherit from ToolInput")
        if tool.output_model is not None and (
            not isinstance(tool.output_model, type) or not issubclass(tool.output_model, ToolOutput)
        ):
            raise TypeError("Tool output model must inherit from ToolOutput")
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolSchema:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool {name!r} is not registered") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def input_json_schema(self, name: str) -> dict[str, Any]:
        return self.get(name).input_model.model_json_schema()

    def output_json_schema(self, name: str) -> dict[str, Any] | None:
        output_model = self.get(name).output_model
        return None if output_model is None else output_model.model_json_schema()

    def validate_input(self, name: str, raw_input: Any) -> BaseModel:
        return self.get(name).input_model.model_validate(raw_input)

    def validate_output(self, name: str, raw_output: Any) -> ToolOutput:
        output_model = self.get(name).output_model
        if output_model is None:
            raise ValueError(f"Tool {name!r} has no output schema.")
        return output_model.model_validate(raw_output)


def build_default_tool_registry() -> ToolSchemaRegistry:
    """Register all 14 tool contracts listed in Handbook Section 8.5."""
    registry = ToolSchemaRegistry()
    definitions = (
        ToolSchema(
            "fetch_economic_indicator",
            FetchEconomicIndicatorInput,
            "Quantity list",
            writes=("ledger",),
        ),
        ToolSchema(
            "search_policy_documents",
            SearchPolicyDocumentsInput,
            "Policy passages with locators",
        ),
        ToolSchema("verify_claim", VerifyClaimInput, "Verdict and evidence"),
        ToolSchema(
            "evaluate_scheme_eligibility",
            EvaluateSchemeEligibilityInput,
            "Status, unknown facts, and trace",
        ),
        ToolSchema(
            "calculate_loan_schedule",
            CalculateLoanScheduleInput,
            "Schedule quantity list",
            writes=("ledger",),
            output_model=CalculateLoanScheduleOutput,
        ),
        ToolSchema(
            "calculate_break_even",
            CalculateBreakEvenInput,
            "Break-even quantity",
            writes=("ledger",),
            output_model=CalculateBreakEvenOutput,
        ),
        ToolSchema(
            "compute_catchment",
            ComputeCatchmentInput,
            "Polygon, zones, and travel times",
            writes=("ledger",),
        ),
        ToolSchema(
            "allocate_spatial_demand",
            AllocateSpatialDemandInput,
            "Spatial allocations",
            writes=("ledger",),
        ),
        ToolSchema(
            "run_business_scenario",
            RunBusinessScenarioInput,
            "Cash-flow quantity list",
            writes=("run artifact",),
        ),
        ToolSchema(
            "run_sensitivity_analysis",
            RunSensitivityAnalysisInput,
            "Deterministic one-at-a-time sensitivity results; requires explicit scenario assumptions and matching ledger quantities",
            writes=("run artifact",),
        ),
        ToolSchema(
            "compare_scenarios",
            CompareScenariosInput,
            "Scenario comparison with reasons",
        ),
        ToolSchema(
            "generate_report",
            GenerateReportInput,
            "Report document",
            writes=("report artifact",),
        ),
        ToolSchema(
            "create_followup_tasks",
            CreateFollowupTasksInput,
            "Persisted task objects",
            writes=("tasks",),
        ),
        ToolSchema(
            "publish_to_shared_view",
            PublishToSharedViewInput,
            "Shared record",
            writes=("shared view",),
            approval_required=True,
        ),
    )
    for definition in definitions:
        registry.register(definition)
    return registry

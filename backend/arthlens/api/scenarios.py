"""
Scenarios API Endpoints (/scenarios, /scenarios/{id}/branch).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.1, Part 11, Part 13.1 P1-6).
Phase: P1-6 (Authentication, Roles, RBAC, Audit Events and Rate Limiting).
"""

import uuid
from dataclasses import replace
from datetime import date, datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from shapely.geometry import Point, shape

from backend.arthlens.api.policy import PolicyEvaluationRequest, evaluate_scheme_eligibility
from backend.arthlens.demand.allocator import AllocationParameters, DemandZone, Facility
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.finance import (
    FinancialScenario,
    calculate_financial_shortfall,
    calculate_repayment_capacity,
    calculate_working_capital_requirement,
    project_monthly_cash_flow,
)
from backend.arthlens.finance.loans import (
    LoanTerms,
    MoratoriumInterestTreatment,
    SubsidyTreatment,
    build_loan_schedule,
)
from backend.arthlens.finance.projection import calculate_break_even_quantity
from backend.arthlens.geo.road_graph import RoadSpeedScenario
from backend.arthlens.geo.road_repository import (
    PostgresRoadGraphRepository,
    RoadGraphProvenanceError,
)
from backend.arthlens.infra.provenance import resolve_quantity_provenance
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
    PostgresScenarioRepository,
    PostgresSourceRecordRepository,
    PostgresSourceRepository,
)
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.quality import DataQualityEvaluator
from backend.arthlens.reporting.dossier_generator import (
    generate_dossier_csv,
    generate_dossier_json,
    generate_dossier_pdf,
    generate_dossier_xlsx,
)
from backend.arthlens.security.rbac import AuthenticatedUser, require_roles
from backend.arthlens.security.roles import Role
from backend.arthlens.simulation import run_financial_uncertainty_analysis
from backend.arthlens.finance.loans import MoratoriumInterestTreatment, SubsidyTreatment
from backend.arthlens.workflows import (
    SpatialDemandInputs,
    run_loop_a_spatial_siting,
    run_loop_b_corridor_accessibility,
    run_loop_c_scheme_viability,
)

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


class FinancialProjectionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    initial_quantity: float = Field(ge=0)
    monthly_growth_rate: float
    seasonality_factors: List[float] = Field(min_length=1)
    price_per_unit_by_month: List[float] = Field(min_length=1)
    variable_cost_per_unit_by_month: List[float] = Field(min_length=1)
    operating_expenses_by_month: List[float] = Field(min_length=1)
    debt_service_by_month: List[float] = Field(min_length=1)
    taxes_by_month: List[float] = Field(min_length=1)
    other_payments_by_month: List[float] = Field(min_length=1)
    subsidy_cash_release_by_month: List[float] = Field(min_length=1)
    working_capital_need_by_month: List[float] = Field(min_length=1)
    opening_working_capital_need: float = Field(ge=0)
    equity: float = Field(ge=0)
    disbursed_loan: float = Field(ge=0)
    capex: float = Field(ge=0)
    days_inventory: float = Field(ge=0)
    days_receivable: float = Field(ge=0)
    days_payable: float = Field(ge=0)
    minimum_dscr: float = Field(gt=0)
    repayment_capacity_annual_interest_rate: float = Field(ge=0)
    repayment_capacity_months: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_schedule_lengths(self) -> "FinancialProjectionRequest":
        schedule_names = (
            "price_per_unit_by_month",
            "variable_cost_per_unit_by_month",
            "operating_expenses_by_month",
            "debt_service_by_month",
            "taxes_by_month",
            "other_payments_by_month",
            "subsidy_cash_release_by_month",
            "working_capital_need_by_month",
        )
        lengths = {len(getattr(self, name)) for name in schedule_names}
        if len(lengths) != 1:
            raise ValueError("All explicit monthly financial schedules must have equal lengths.")
        if self.monthly_growth_rate <= -1:
            raise ValueError("monthly_growth_rate must be greater than -1.")
        if any(value < 0 for value in self.seasonality_factors):
            raise ValueError("seasonality_factors values must be non-negative.")
        if any(
            value < 0
            for name in schedule_names
            for value in getattr(self, name)
        ):
            raise ValueError("Monthly financial schedule values must be non-negative.")
        return self


class WorkingCapitalRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    inventory_value: float = Field(ge=0)
    accounts_receivable: float = Field(ge=0)
    accounts_payable: float = Field(ge=0)


class CalculateScenarioRequest(BaseModel):
    """Explicit user inputs. Omitted inputs remain unavailable; none are defaulted."""

    model_config = ConfigDict(allow_inf_nan=False)

    price_per_unit: Optional[float] = Field(default=None, gt=0)
    variable_cost_per_unit: Optional[float] = Field(default=None, ge=0)
    fixed_costs_per_month: Optional[float] = Field(default=None, ge=0)
    loan_principal: Optional[float] = Field(default=None, ge=0)
    annual_interest_rate: Optional[float] = Field(default=None, ge=0)
    loan_term_months: Optional[int] = Field(default=None, gt=0)
    moratorium_months: Optional[int] = Field(default=None, ge=0)
    moratorium_interest_treatment: Optional[MoratoriumInterestTreatment] = None
    subsidy_amount: Optional[float] = Field(default=None, ge=0)
    subsidy_treatment: Optional[SubsidyTreatment] = None
    subsidy_release_month: Optional[int] = Field(default=None, gt=0)
    target_monthly_units: Optional[float] = Field(default=None, ge=0)
    working_capital: Optional[WorkingCapitalRequest] = None
    projection: Optional[FinancialProjectionRequest] = None

    @model_validator(mode="after")
    def validate_subsidy_parameters(self) -> "CalculateScenarioRequest":
        if (
            self.loan_principal is not None
            and self.subsidy_amount is not None
            and self.subsidy_amount > self.loan_principal
        ):
            raise ValueError("subsidy_amount must not exceed loan_principal.")
        if (
            self.subsidy_release_month is not None
            and self.moratorium_months is not None
            and self.loan_term_months is not None
            and self.subsidy_release_month > self.moratorium_months + self.loan_term_months
        ):
            raise ValueError("subsidy_release_month must fall within the explicit loan schedule.")
        if self.subsidy_release_month is not None and self.subsidy_treatment not in {
            SubsidyTreatment.BACK_ENDED_RELEASE,
            SubsidyTreatment.LOCKED_DEPOSIT,
        }:
            raise ValueError("subsidy_release_month is only valid for a release-based subsidy treatment.")
        if self.subsidy_treatment in {
            SubsidyTreatment.BACK_ENDED_RELEASE,
            SubsidyTreatment.LOCKED_DEPOSIT,
        } and self.subsidy_release_month is None:
            raise ValueError("Release-based subsidy treatments require an explicit subsidy_release_month.")
        return self


class CreateScenarioRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: str = Field(..., min_length=1, max_length=255)
    scenario: Dict[str, Any] = Field(default_factory=dict)


class UpdateScenarioRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    scenario: Optional[Dict[str, Any]] = None


class BranchScenarioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ScenarioComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_scenario_id: uuid.UUID
    right_scenario_id: uuid.UUID

    @model_validator(mode="after")
    def require_distinct_scenarios(self) -> "ScenarioComparisonRequest":
        if self.left_scenario_id == self.right_scenario_id:
            raise ValueError("A scenario cannot be compared with itself.")
        return self


class ZoneDemandQuantityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zone_id: str = Field(min_length=1, max_length=200)
    quantity_id: uuid.UUID


class FacilityAttractivenessQuantityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    facility_id: str = Field(min_length=1, max_length=200)
    quantity_id: uuid.UUID


class SpatialScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    allocator_type: str = Field(pattern="^(huff|nearest)$")
    candidate_facility_id: str = Field(min_length=1, max_length=200)
    zones: List[ZoneDemandQuantityRequest] = Field(min_length=1)
    facilities: List[FacilityAttractivenessQuantityRequest] = Field(min_length=1)
    travel_time_quantity_ids: Dict[str, Dict[str, uuid.UUID]]
    distance_decay_quantity_id: Optional[uuid.UUID] = None

    @model_validator(mode="after")
    def validate_complete_spatial_matrix(self) -> "SpatialScenarioRequest":
        zone_ids = [zone.zone_id for zone in self.zones]
        facility_ids = [facility.facility_id for facility in self.facilities]
        if len(set(zone_ids)) != len(zone_ids) or len(set(facility_ids)) != len(facility_ids):
            raise ValueError("Zone and facility IDs must be unique.")
        if self.candidate_facility_id not in facility_ids:
            raise ValueError("candidate_facility_id must identify one supplied facility.")
        if set(self.travel_time_quantity_ids) != set(zone_ids):
            raise ValueError("Travel-time mappings must cover each supplied zone exactly.")
        for zone_id in zone_ids:
            if set(self.travel_time_quantity_ids[zone_id]) != set(facility_ids):
                raise ValueError(f"Travel-time mappings for {zone_id!r} must cover each facility exactly.")
        if self.allocator_type == "huff" and self.distance_decay_quantity_id is None:
            raise ValueError("Huff allocation requires an explicitly linked decay-parameter quantity.")
        if self.allocator_type == "nearest" and self.distance_decay_quantity_id is not None:
            raise ValueError("Nearest allocation does not use a Huff decay parameter.")
        return self


class AccessibilityScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    road_graph_source_version_id: str = Field(min_length=1, max_length=300)
    extraction_radius_m: float = Field(gt=0)
    longitude_quantity_id: uuid.UUID
    latitude_quantity_id: uuid.UUID
    road_speed_scenario_id: str = Field(min_length=1, max_length=200)
    speed_quantity_ids: Dict[str, uuid.UUID]
    thresholds_minutes: List[float] = Field(min_length=1)
    corridor_width_m: float = Field(gt=0)
    model_version: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_accessibility_assumptions(self) -> "AccessibilityScenarioRequest":
        if not self.speed_quantity_ids:
            raise ValueError("Explicit road-speed quantity IDs for each road class are required.")
        if any(value <= 0 for value in self.thresholds_minutes):
            raise ValueError("Catchment thresholds must be positive explicit minutes.")
        if len(set(self.thresholds_minutes)) != len(self.thresholds_minutes):
            raise ValueError("Catchment thresholds must be unique.")
        return self


class ScenarioPolicyEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scheme_id: str = Field(min_length=1, max_length=100)
    rule_key: str = Field(min_length=1, max_length=200)
    as_of: date
    fact_quantity_ids: Dict[str, uuid.UUID]


SCENARIO_RESULT_FIELDS = frozenset({
    "calculations",
    "financial_assumptions",
    "financial_simulation",
    "spatial_demand",
    "accessibility",
    "policy_evaluation",
    "assumption_quantity_ids",
})


def _validate_json_tree(value: Any, path: str = "scenario") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise HTTPException(status_code=422, detail=f"{path} contains a non-finite number.")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_tree(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise HTTPException(status_code=422, detail=f"{path} keys must be strings.")
            _validate_json_tree(item, f"{path}.{key}")
        return
    raise HTTPException(status_code=422, detail=f"{path} contains an unsupported JSON value.")


def _json_compatible(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


def _current_analysis_date() -> date:
    """Return effective analysis date, supporting both UTC and local timezone dates."""
    return max(datetime.now(timezone.utc).date(), date.today())


def _validate_scenario_quantity(
    quantity: Optional[Quantity],
    *,
    quantity_id: Any,
    definition_key: str,
    unit: str,
    owner_id: str,
    as_of: date,
    allowed_kinds: tuple[Kind, ...],
    source_repo: PostgresSourceRepository,
) -> Optional[str]:
    if quantity is None:
        return f"ledger quantity {quantity_id} is not registered"
    if quantity.definition_key != definition_key or quantity.unit != unit:
        return f"ledger quantity {quantity.id} does not match {definition_key} [{unit}]"
    if quantity.kind not in allowed_kinds:
        return f"ledger quantity {quantity.id} has unsupported evidence kind {quantity.kind.value}"
    if quantity.owner_id not in (None, owner_id):
        return f"ledger quantity {quantity.id} belongs to another user"
    if "STALE" in quantity.quality_flags:
        return f"ledger quantity {quantity.id} is stale"
    if not quantity.as_of:
        return f"ledger quantity {quantity.id} has no as-of date"
    try:
        quantity_as_of = date.fromisoformat(quantity.as_of)
    except ValueError:
        return f"ledger quantity {quantity.id} has an invalid as-of date"
    if quantity_as_of > as_of:
        return f"ledger quantity {quantity.id} is later than the analysis date"
    refs = list(quantity.source_refs or ())
    if quantity.kind in (Kind.USER_ASSUMED, Kind.SCENARIO):
        if not any(
            isinstance(ref, (tuple, list))
            and len(ref) >= 2
            and str(ref[0]) == f"user:{owner_id}"
            for ref in refs
        ):
            return f"user assumption quantity {quantity.id} lacks its owner's input provenance"
    elif quantity.kind in (Kind.OBSERVED, Kind.POLICY_RULE):
        if not refs:
            return f"source-backed quantity {quantity.id} lacks source-version provenance"
        for ref in refs:
            version_id = ref[0] if isinstance(ref, (tuple, list)) and ref else None
            version = source_repo.get_version(str(version_id)) if version_id else None
            source = source_repo.get_source(version["source_id"]) if version else None
            source_record = (
                PostgresSourceRecordRepository().get_by_id(str(ref[1]))
                if isinstance(ref, (tuple, list)) and len(ref) >= 2
                else None
            )
            if (
                not isinstance(ref, (tuple, list))
                or len(ref) < 2
                or not str(ref[1]).strip()
                or version is None
                or version.get("status") != "ACTIVE"
                or source is None
                or source.get("status") != "ACTIVE"
                or source_record is None
                or source_record.source_version_id != str(version_id)
                or source_record.source_id != version.get("source_id")
            ):
                return f"source-backed quantity {quantity.id} references an unregistered source record or inactive source version"
    elif quantity.kind in (Kind.ESTIMATED, Kind.CALCULATED, Kind.SIMULATED):
        if not quantity.parent_ids and not refs:
            return f"derived quantity {quantity.id} has no registered inputs or sources"
    return None


def _load_quantities_into_ledger(
    ledger: Ledger,
    repository: PostgresQuantityRepository,
    quantity_ids: List[str],
) -> Dict[str, Quantity]:
    loaded: Dict[str, Quantity] = {}
    visiting: set[str] = set()

    def visit(quantity_id: str) -> Quantity:
        if quantity_id in loaded:
            return loaded[quantity_id]
        if quantity_id in visiting:
            raise ValueError(f"Cycle in registered quantity lineage at {quantity_id}.")
        quantity = repository.get(quantity_id)
        if quantity is None:
            raise ValueError(f"Registered ledger quantity {quantity_id} is missing.")
        visiting.add(quantity_id)
        for parent_id in quantity.parent_ids:
            visit(parent_id)
        ledger.register(quantity)
        visiting.remove(quantity_id)
        loaded[quantity_id] = quantity
        return quantity

    for quantity_id in quantity_ids:
        visit(quantity_id)
    return loaded


def _scenario_output_quantity_ids(scenario_data: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}

    def add(key: str, value: Any) -> None:
        if isinstance(value, str):
            result[key] = value

    calculations = scenario_data.get("calculations") or {}
    for key, quantity_id in (calculations.get("quantity_ids") or {}).items():
        add(f"financial.{key}", quantity_id)
    projection = calculations.get("financial_projection") or {}
    for key, quantity_id in (projection.get("quantity_ids") or {}).items():
        add(f"financial.projection.{key}", quantity_id)
    for month in calculations.get("loan_schedule") or []:
        month_number = month.get("month")
        for key, quantity_id in (month.get("quantity_ids") or {}).items():
            add(f"financial.loan_schedule.month_{month_number}.{key}", quantity_id)
    for month in projection.get("months") or []:
        month_number = month.get("month")
        for key, quantity_id in (month.get("quantity_ids") or {}).items():
            add(f"financial.projection.month_{month_number}.{key}", quantity_id)

    simulation = scenario_data.get("financial_simulation") or {}
    for metric, summary in (simulation.get("metrics") or {}).items():
        add(f"simulation.monte_carlo.{metric}.mean", summary.get("mean_quantity_id"))
        add(f"simulation.monte_carlo.{metric}.standard_error", summary.get("standard_error_quantity_id"))
        for level, quantile in (summary.get("quantiles") or {}).items():
            add(f"simulation.monte_carlo.{metric}.quantile.{level}", quantile.get("quantity_id"))
    shortfall = simulation.get("cash_shortfall_probability") or {}
    add("simulation.cash_shortfall_probability", shortfall.get("quantity_id"))
    add("simulation.cash_shortfall_probability.standard_error", shortfall.get("standard_error_quantity_id"))
    sensitivity = simulation.get("sensitivity") or {}
    for metric, output in (sensitivity.get("baseline_outputs") or {}).items():
        add(f"simulation.sensitivity.baseline.{metric}", output.get("quantity_id"))
    for index, point in enumerate(sensitivity.get("points") or [], start=1):
        for metric, output in (point.get("outputs") or {}).items():
            add(f"simulation.sensitivity.point_{index}.{metric}.value", output.get("quantity_id"))
            add(f"simulation.sensitivity.point_{index}.{metric}.delta", output.get("delta_quantity_id"))

    for key, quantity_id in ((scenario_data.get("spatial_demand") or {}).get("quantity_ids") or {}).items():
        add(f"spatial.{key}", quantity_id)
    for key, quantity_id in ((scenario_data.get("accessibility") or {}).get("quantity_ids") or {}).items():
        add(f"accessibility.{key}", quantity_id)
    return result


def _scenario_metric_definition(
    metric_key: str,
    left_data: Dict[str, Any],
    right_data: Dict[str, Any],
) -> Optional[str]:
    if metric_key.startswith("financial."):
        return f"finance.result.{metric_key.removeprefix('financial.')}"
    if metric_key.startswith("simulation."):
        return f"finance.simulation.result.{metric_key.removeprefix('simulation.')}"
    if metric_key.startswith("accessibility."):
        return metric_key.removeprefix("accessibility.")
    if metric_key.startswith("spatial."):
        key = metric_key.removeprefix("spatial.")
        left_definition = ((left_data.get("spatial_demand") or {}).get("quantity_definition_keys") or {}).get(key)
        right_definition = ((right_data.get("spatial_demand") or {}).get("quantity_definition_keys") or {}).get(key)
        return left_definition if left_definition and left_definition == right_definition else None
    return None


def _scenario_metric_kinds(metric_key: str) -> tuple[Kind, ...]:
    if metric_key.startswith("financial."):
        return (Kind.CALCULATED,)
    if metric_key.startswith("simulation.monte_carlo.") or metric_key.startswith("simulation.cash_shortfall_probability"):
        return (Kind.SIMULATED,)
    if metric_key.startswith("simulation.sensitivity."):
        return (Kind.CALCULATED,)
    if metric_key.startswith("spatial."):
        return (Kind.ESTIMATED,)
    if metric_key.startswith("accessibility."):
        return (Kind.CALCULATED,)
    return ()


def _safe_quantity_key(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "_" for character in value)


def _is_geo_in_scope(geo_repo: PostgresGeoUnitRepository, child_id: str, parent_id: str) -> bool:
    current_id: Optional[str] = child_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        if current_id == parent_id:
            return True
        seen.add(current_id)
        current = geo_repo.get_by_id(current_id)
        current_id = current.parent_id if current else None
    return False


def _validate_loaded_lineage(
    quantities: Dict[str, Quantity],
    *,
    owner_id: str,
    as_of: date,
    source_repo: PostgresSourceRepository,
) -> List[str]:
    issues = []
    for quantity in quantities.values():
        if quantity.value is None or not isfinite(float(quantity.value)):
            issues.append(f"ledger quantity {quantity.id} has a non-finite value")
            continue
        issue = _validate_scenario_quantity(
            quantity,
            quantity_id=quantity.id,
            definition_key=quantity.definition_key,
            unit=quantity.unit,
            owner_id=owner_id,
            as_of=as_of,
            allowed_kinds=tuple(Kind),
            source_repo=source_repo,
        )
        if issue:
            issues.append(issue)
    return issues


def _save_scenario_results(
    repository: PostgresScenarioRepository,
    scenario: Dict[str, Any],
    *,
    owner_id: str,
    scenario_id: str,
    scenario_data: Dict[str, Any],
) -> None:
    _validate_json_tree(scenario_data)
    repository.save_scenario({
        "id": scenario_id,
        "owner_id": owner_id,
        "name": scenario["name"],
        "scenario": scenario_data,
    })


class SimulationProjectionRequest(BaseModel):
    """Complete explicit inputs for stochastic monthly cash-flow projections."""

    model_config = ConfigDict(allow_inf_nan=False)

    initial_quantity: float = Field(ge=0)
    monthly_growth_rate: float
    seasonality_factors: List[float] = Field(min_length=1)
    price_per_unit_by_month: List[float] = Field(min_length=1)
    variable_cost_per_unit_by_month: List[float] = Field(min_length=1)
    operating_expenses_by_month: List[float] = Field(min_length=1)
    debt_service_by_month: List[float] = Field(min_length=1)
    taxes_by_month: List[float] = Field(min_length=1)
    other_payments_by_month: List[float] = Field(min_length=1)
    subsidy_cash_release_by_month: List[float] = Field(min_length=1)
    working_capital_need_by_month: List[float] = Field(min_length=1)
    opening_working_capital_need: float = Field(ge=0)
    equity: float = Field(ge=0)
    disbursed_loan: float = Field(ge=0)
    capex: float = Field(ge=0)
    days_inventory: float = Field(ge=0)
    days_receivable: float = Field(ge=0)
    days_payable: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_projection(self) -> "SimulationProjectionRequest":
        schedule_names = (
            "price_per_unit_by_month",
            "variable_cost_per_unit_by_month",
            "operating_expenses_by_month",
            "debt_service_by_month",
            "taxes_by_month",
            "other_payments_by_month",
            "subsidy_cash_release_by_month",
            "working_capital_need_by_month",
        )
        lengths = {len(getattr(self, name)) for name in schedule_names}
        if len(lengths) != 1:
            raise ValueError("All explicit monthly financial schedules must have equal lengths.")
        if self.monthly_growth_rate <= -1:
            raise ValueError("monthly_growth_rate must be greater than -1.")
        if any(value < 0 for value in self.seasonality_factors):
            raise ValueError("seasonality_factors values must be non-negative.")
        if any(value < 0 for name in schedule_names for value in getattr(self, name)):
            raise ValueError("Monthly financial schedule values must be non-negative.")
        return self


class DistributionRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    parameter: str = Field(min_length=1)
    distribution: str
    parameters: Dict[str, float]


class FinancialSimulationRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    projection: SimulationProjectionRequest
    distributions: List[DistributionRequest] = Field(min_length=1)
    sensitivity_parameter_values: Dict[str, List[float]]
    seed: int = Field(ge=0, le=18446744073709551615)
    sample_count: int = Field(ge=2, le=100000)
    minimum_sample_count: int = Field(ge=2)
    quantile_levels: List[float] = Field(min_length=1)
    convergence_tolerances: Dict[str, float]
    shortfall_probability_tolerance: float = Field(ge=0)

    @model_validator(mode="before")
    @classmethod
    def reject_boolean_numbers(cls, value: Any) -> Any:
        def contains_boolean(item: Any) -> bool:
            if isinstance(item, bool):
                return True
            if isinstance(item, dict):
                return any(contains_boolean(nested) for nested in item.values())
            if isinstance(item, list):
                return any(contains_boolean(nested) for nested in item)
            return False

        if contains_boolean(value):
            raise ValueError("Boolean values are not valid financial simulation inputs.")
        return value

    @model_validator(mode="after")
    def validate_simulation_contract(self) -> "FinancialSimulationRequest":
        if self.minimum_sample_count > self.sample_count:
            raise ValueError("minimum_sample_count must not exceed sample_count.")
        if self.sensitivity_parameter_values == {}:
            raise ValueError("sensitivity_parameter_values must contain explicit alternatives.")
        if set(self.convergence_tolerances) != {
            "total_revenue",
            "total_debt_service",
            "minimum_cash",
        }:
            raise ValueError(
                "convergence_tolerances must specify total_revenue, total_debt_service, and minimum_cash."
            )
        return self


@router.post("", status_code=status.HTTP_201_CREATED)
def create_scenario(
    body: CreateScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Create a new user scenario (Entrepreneur only)."""
    forbidden_fields = SCENARIO_RESULT_FIELDS & set(body.scenario)
    if forbidden_fields or "branch_lineage" in body.scenario:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Scenario result and lineage fields are server-managed: {sorted(forbidden_fields | ({'branch_lineage'} if 'branch_lineage' in body.scenario else set()))}.",
        )
    _validate_json_tree(body.scenario)
    geo_id = body.scenario.get("geo_id")
    if geo_id is not None and PostgresGeoUnitRepository().get_by_id(str(geo_id)) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario geographic unit not found.")
    repo = PostgresScenarioRepository()
    scenario_id = str(uuid.uuid4())
    scenario_id = repo.save_scenario(
        {
            "id": scenario_id,
            "owner_id": current_user.id,
            "name": body.name,
            "scenario": body.scenario,
        }
    )
    return {
        "id": scenario_id,
        "name": body.name,
        "owner_id": current_user.id,
        "scenario": body.scenario,
    }


@router.get("")
def list_scenarios(
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> list[Dict[str, Any]]:
    """List only scenarios owned by the authenticated entrepreneur."""
    repo = PostgresScenarioRepository()
    return repo.list_by_owner(current_user.id)


@router.get("/{scenario_id}")
def get_scenario_detail(
    scenario_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Retrieve scenario details (Owner only, returns 404 on ownership mismatch)."""
    repo = PostgresScenarioRepository()
    scenario = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )
    return scenario


@router.put("/{scenario_id}")
def update_scenario(
    scenario_id: str,
    body: UpdateScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Update an existing scenario (Owner only)."""
    repo = PostgresScenarioRepository()
    existing = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    updated_name = body.name if body.name is not None else existing["name"]
    if body.scenario is not None:
        forbidden_fields = SCENARIO_RESULT_FIELDS & set(body.scenario)
        if forbidden_fields or "branch_lineage" in body.scenario:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Scenario result and lineage fields are server-managed.",
            )
        _validate_json_tree(body.scenario)
        existing_data = dict(existing.get("scenario") or {})
        existing_inputs = {
            key: value
            for key, value in existing_data.items()
            if key not in SCENARIO_RESULT_FIELDS and key != "branch_lineage"
        }
        if body.scenario == existing_inputs:
            updated_data = existing_data
        else:
            updated_data = dict(body.scenario)
            if "branch_lineage" in existing_data:
                updated_data["branch_lineage"] = existing_data["branch_lineage"]
            geo_id = updated_data.get("geo_id")
            if geo_id is not None and PostgresGeoUnitRepository().get_by_id(str(geo_id)) is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario geographic unit not found.")
    else:
        updated_data = existing.get("scenario") or {}
    repo.save_scenario(
        {
            "id": scenario_id,
            "owner_id": current_user.id,
            "name": updated_name,
            "scenario": updated_data,
        }
    )
    return {
        "id": scenario_id,
        "name": updated_name,
        "owner_id": current_user.id,
        "scenario": updated_data,
    }


@router.delete("/{scenario_id}")
def delete_scenario(
    scenario_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, str]:
    """Delete a scenario (Owner only)."""
    repo = PostgresScenarioRepository()
    deleted = repo.delete_scenario(scenario_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )
    return {"status": "deleted", "id": scenario_id}


@router.post("/{scenario_id}/branch", status_code=status.HTTP_201_CREATED)
def branch_scenario(
    scenario_id: str,
    body: BranchScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Branch an existing scenario (Owner only, IDOR safe: returns 404 on ownership mismatch)."""
    repo = PostgresScenarioRepository()
    parent = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    branch_data = dict(parent.get("scenario") or {})
    branch_data["branch_lineage"] = {
        "parent_scenario_id": scenario_id,
        "branched_at": datetime.now(timezone.utc).isoformat(),
    }
    branch_id = repo.save_scenario(
        {
            "owner_id": current_user.id,
            "name": body.name,
            "scenario": branch_data,
        }
    )
    return {
        "id": branch_id,
        "parent_id": scenario_id,
        "name": body.name,
        "owner_id": current_user.id,
        "scenario": branch_data,
    }


@router.post("/compare", status_code=status.HTTP_201_CREATED)
def compare_scenarios(
    body: ScenarioComparisonRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Compare only persisted, owner-scoped ledger outputs and save the exact comparison snapshot."""
    repo = PostgresScenarioRepository()
    left = repo.get_scenario_by_id_and_owner(body.left_scenario_id, current_user.id)
    right = repo.get_scenario_by_id_and_owner(body.right_scenario_id, current_user.id)
    if left is None or right is None:
        raise HTTPException(status_code=404, detail="Both scenarios must exist and belong to the current user.")
    left_data = left.get("scenario") or {}
    right_data = right.get("scenario") or {}
    left_geo = left_data.get("geo_id")
    right_geo = right_data.get("geo_id")
    if not left_geo or not right_geo or left_geo != right_geo:
        raise HTTPException(
            status_code=422,
            detail="Scenario comparison requires both scenarios to use the same registered geographic unit.",
        )

    left_ids = _scenario_output_quantity_ids(left_data)
    right_ids = _scenario_output_quantity_ids(right_data)
    all_keys = sorted(set(left_ids) | set(right_ids))
    quantity_repo = PostgresQuantityRepository()
    today_date = _current_analysis_date()
    today = today_date.isoformat()
    source_repo = PostgresSourceRepository()
    geo_repo = PostgresGeoUnitRepository()
    metric_results: Dict[str, Any] = {}
    missing: Dict[str, str] = {}
    delta_quantities: List[Quantity] = []
    for key in all_keys:
        left_id = left_ids.get(key)
        right_id = right_ids.get(key)
        if left_id is None or right_id is None:
            missing[key] = "metric is not available in both saved scenarios"
            continue
        left_quantity = quantity_repo.get(left_id)
        right_quantity = quantity_repo.get(right_id)
        if left_quantity is None or right_quantity is None:
            missing[key] = "one or both linked ledger quantities are missing"
            continue
        expected_definition = _scenario_metric_definition(key, left_data, right_data)
        allowed_kinds = _scenario_metric_kinds(key)
        if (
            expected_definition is None
            or left_quantity.definition_key != expected_definition
            or right_quantity.definition_key != expected_definition
            or left_quantity.unit != right_quantity.unit
            or left_quantity.kind not in allowed_kinds
            or right_quantity.kind not in allowed_kinds
            or left_quantity.owner_id != current_user.id
            or right_quantity.owner_id != current_user.id
            or left_quantity.geo_unit_id != left_geo
            or right_quantity.geo_unit_id != right_geo
            or left_quantity.resolution != right_quantity.resolution
            or left_quantity.value is None
            or right_quantity.value is None
            or not isfinite(float(left_quantity.value))
            or not isfinite(float(right_quantity.value))
        ):
            missing[key] = "linked quantities do not match the scenario metric, owner, unit, geography, or evidence kind"
            continue
        lineage_issue = None
        for quantity in (left_quantity, right_quantity):
            quantity_issue = _validate_scenario_quantity(
                quantity,
                quantity_id=quantity.id,
                definition_key=expected_definition,
                unit=quantity.unit,
                owner_id=current_user.id,
                as_of=today_date,
                allowed_kinds=allowed_kinds,
                source_repo=source_repo,
            )
            if quantity_issue:
                lineage_issue = quantity_issue
                break
            try:
                lineage = _load_quantities_into_ledger(Ledger(), quantity_repo, [quantity.id])
            except (TypeError, ValueError, KeyError) as exc:
                lineage_issue = f"linked quantity lineage is incomplete: {exc}"
                break
            lineage_issues = _validate_loaded_lineage(
                lineage,
                owner_id=current_user.id,
                as_of=today_date,
                source_repo=source_repo,
            )
            if lineage_issues:
                lineage_issue = "; ".join(lineage_issues)
                break
            if any(
                not (
                    _is_geo_in_scope(geo_repo, item.geo_unit_id, left_geo)
                    or _is_geo_in_scope(geo_repo, left_geo, item.geo_unit_id)
                )
                for item in lineage.values()
            ):
                lineage_issue = "linked quantity lineage contains unrelated geography"
                break
        if lineage_issue:
            missing[key] = lineage_issue
            continue
        delta = float(right_quantity.value - left_quantity.value)
        if not isfinite(delta):
            missing[key] = "comparison delta is non-finite"
            continue
        delta_quantity = Quantity(
            id=str(uuid.uuid4()),
            definition_key=f"scenario.comparison.delta.{_safe_quantity_key(key)}",
            value=delta,
            unit=left_quantity.unit,
            kind=Kind.CALCULATED,
            evidence_floor=min(left_quantity.evidence_floor, right_quantity.evidence_floor),
            geo_unit_id=left_geo,
            resolution=left_quantity.resolution,
            as_of=today,
            uncertainty="EXACT",
            source_refs=(),
            method_id="scenario_comparison:right_minus_left_v1",
            model_version="arthlens-scenario-comparison-v1",
            parent_ids=(left_quantity.id, right_quantity.id),
            owner_id=current_user.id,
        )
        delta_quantities.append(delta_quantity)
        metric_results[key] = {
            "status": "COMPLETED",
            "unit": left_quantity.unit,
            "left": {
                "scenario_id": str(left["id"]),
                "scenario_name": left["name"],
                "quantity_id": left_quantity.id,
                "value": float(left_quantity.value),
                "kind": left_quantity.kind.value,
                "evidence_floor": left_quantity.evidence_floor,
                "as_of": left_quantity.as_of,
            },
            "right": {
                "scenario_id": str(right["id"]),
                "scenario_name": right["name"],
                "quantity_id": right_quantity.id,
                "value": float(right_quantity.value),
                "kind": right_quantity.kind.value,
                "evidence_floor": right_quantity.evidence_floor,
                "as_of": right_quantity.as_of,
            },
            "delta_right_minus_left": {
                "quantity_id": delta_quantity.id,
                "value": delta,
                "kind": delta_quantity.kind.value,
                "evidence_floor": delta_quantity.evidence_floor,
                "parent_quantity_ids": list(delta_quantity.parent_ids),
            },
        }

    status_value = (
        "INSUFFICIENT_DATA"
        if not metric_results
        else ("PARTIAL" if missing else "COMPLETED")
    )
    if delta_quantities:
        quantity_repo.save_many(delta_quantities)
    comparison_id = repo.save_comparison({
        "owner_id": current_user.id,
        "left_scenario_id": str(left["id"]),
        "right_scenario_id": str(right["id"]),
        "status": status_value,
        "metric_results": {
            "status": status_value,
            "left_scenario_id": str(left["id"]),
            "right_scenario_id": str(right["id"]),
            "geographic_unit_id": left_geo,
            "analysis_versions": {
                "left_calculation_execution_id": (left_data.get("calculations") or {}).get("calculation_provenance", {}).get("execution_id"),
                "right_calculation_execution_id": (right_data.get("calculations") or {}).get("calculation_provenance", {}).get("execution_id"),
                "left_simulation_run_id": (left_data.get("financial_simulation") or {}).get("run_id"),
                "right_simulation_run_id": (right_data.get("financial_simulation") or {}).get("run_id"),
                "left_spatial_execution_id": (left_data.get("spatial_demand") or {}).get("execution_id"),
                "right_spatial_execution_id": (right_data.get("spatial_demand") or {}).get("execution_id"),
            },
            "metrics": metric_results,
            "unavailable_metrics": missing,
        },
    })
    persisted = repo.get_comparison_by_id_and_owner(comparison_id, current_user.id)
    return {
        "id": comparison_id,
        "status": status_value,
        "left_scenario_id": str(left["id"]),
        "right_scenario_id": str(right["id"]),
        "metrics": metric_results,
        "unavailable_metrics": missing,
        "created_at": persisted.get("created_at") if persisted else None,
    }


@router.get("/comparisons/{comparison_id}")
def get_scenario_comparison(
    comparison_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    comparison = PostgresScenarioRepository().get_comparison_by_id_and_owner(comparison_id, current_user.id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Scenario comparison not found.")
    return comparison


@router.post("/{scenario_id}/spatial-demand")
def allocate_scenario_spatial_demand(
    scenario_id: str,
    body: SpatialScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Allocate demand from individually mapped, registered ledger quantities only."""
    scenario_repo = PostgresScenarioRepository()
    scenario = scenario_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    scenario_data = dict(scenario.get("scenario") or {})
    geo_id = scenario_data.get("geo_id")
    geo_repo = PostgresGeoUnitRepository()
    scenario_geo = geo_repo.get_by_id(str(geo_id)) if geo_id else None
    if scenario_geo is None:
        raise HTTPException(
            status_code=422,
            detail="INSUFFICIENT_DATA: select a registered geographic unit before allocating spatial demand.",
        )

    today = _current_analysis_date()
    source_repo = PostgresSourceRepository()
    quantity_repo = PostgresQuantityRepository()
    role_inputs: List[tuple[str, str, uuid.UUID, str, str, tuple[Kind, ...]]] = []
    for zone in body.zones:
        role_inputs.append((
            "zone_demand", zone.zone_id, zone.quantity_id,
            "demand.zone.monthly", "INR/month",
            (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED),
        ))
    for facility in body.facilities:
        role_inputs.append((
            "facility_attractiveness", facility.facility_id, facility.quantity_id,
            "facility.attractiveness", "dimensionless",
            (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED),
        ))
    for zone_id, facilities in body.travel_time_quantity_ids.items():
        for facility_id, quantity_id in facilities.items():
            role_inputs.append((
                "travel_time", f"{zone_id}:{facility_id}", quantity_id,
                "travel_time.minutes", "minute",
                (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED, Kind.CALCULATED),
            ))
    if body.distance_decay_quantity_id is not None:
        role_inputs.append((
            "distance_decay", "distance_decay_exponent", body.distance_decay_quantity_id,
            "demand.huff.lambda", "dimensionless", (Kind.USER_ASSUMED, Kind.SCENARIO),
        ))

    issues: List[str] = []
    ids = [str(item[2]) for item in role_inputs]
    if len(ids) != len(set(ids)):
        issues.append("Each spatial input mapping must use its own ledger quantity ID.")
    quantities_by_role: Dict[tuple[str, str], Quantity] = {}
    for role, entity_id, quantity_id, definition_key, unit, allowed_kinds in role_inputs:
        key = (role, entity_id)
        quantity = quantity_repo.get(quantity_id)
        issue = _validate_scenario_quantity(
            quantity,
            quantity_id=quantity_id,
            definition_key=definition_key,
            unit=unit,
            owner_id=current_user.id,
            as_of=today,
            allowed_kinds=allowed_kinds,
            source_repo=source_repo,
        )
        if issue:
            issues.append(f"{role} {entity_id}: {issue}.")
            continue
        assert quantity is not None
        if quantity.value is None or not isfinite(float(quantity.value)) or quantity.value < 0:
            issues.append(f"{role} {entity_id}: quantity value must be finite and non-negative.")
        represented_geo = geo_repo.get_by_id(quantity.geo_unit_id)
        if represented_geo is None or not _is_geo_in_scope(geo_repo, quantity.geo_unit_id, str(geo_id)):
            issues.append(f"{role} {entity_id}: quantity geography is not registered within the scenario geography.")
        if role == "zone_demand":
            zone_geo = geo_repo.get_by_id(entity_id)
            if zone_geo is None or not _is_geo_in_scope(geo_repo, entity_id, str(geo_id)):
                issues.append(f"zone demand {entity_id}: zone is not a registered unit within the scenario geography.")
            elif quantity.geo_unit_id != entity_id:
                issues.append(f"zone demand {entity_id}: ledger quantity must represent that exact zone.")
        if role == "travel_time":
            zone_id = entity_id.split(":", 1)[0]
            zone_quantity = quantities_by_role.get(("zone_demand", zone_id))
            if zone_quantity is not None and quantity.geo_unit_id != zone_quantity.geo_unit_id:
                issues.append(f"travel time {entity_id}: ledger quantity geography does not match its demand zone.")
        if role == "distance_decay" and quantity.geo_unit_id != str(geo_id):
            issues.append("distance-decay quantity must represent the scenario geographic unit.")
        quantities_by_role[key] = quantity

    root_ids = list(dict.fromkeys(ids))
    loaded: Dict[str, Quantity] = {}
    try:
        loaded = _load_quantities_into_ledger(Ledger(), quantity_repo, root_ids)
    except (TypeError, ValueError, KeyError) as exc:
        issues.append(f"ledger input lineage is incomplete: {exc}")
    if loaded:
        issues.extend(_validate_loaded_lineage(
            loaded,
            owner_id=current_user.id,
            as_of=today,
            source_repo=source_repo,
        ))

    execution_id = str(uuid.uuid4())
    input_quantity_ids = {
        f"{role}:{entity_id}": str(quantity_id)
        for role, entity_id, quantity_id, *_ in role_inputs
    }
    output: Dict[str, Any] = {
        "scenario_id": scenario_id,
        "execution_id": execution_id,
        "status": "INSUFFICIENT_DATA" if issues else "PENDING",
        "allocator": body.allocator_type,
        "request": body.model_dump(mode="json"),
        "input_quantity_ids": input_quantity_ids,
        "input_quantities": {
            f"{key[0]}:{key[1]}": {
                "quantity_id": quantity.id,
                "definition_key": quantity.definition_key,
                "value": quantity.value,
                "unit": quantity.unit,
                "kind": quantity.kind.value,
                "evidence_floor": quantity.evidence_floor,
                "as_of": quantity.as_of,
                "source_refs": [list(ref) if isinstance(ref, tuple) else ref for ref in quantity.source_refs],
                "parent_ids": list(quantity.parent_ids),
            }
            for key, quantity in sorted(quantities_by_role.items())
        },
        "quantity_ids": {},
        "quantity_definition_keys": {},
        "missing_evidence": issues,
    }
    if not issues:
        zone_inputs = tuple(
            DemandZone(zone.zone_id, quantities_by_role[("zone_demand", zone.zone_id)].value)
            for zone in body.zones
        )
        facility_inputs = tuple(
            Facility(item.facility_id, quantities_by_role[("facility_attractiveness", item.facility_id)].value)
            for item in body.facilities
        )
        travel_times = {
            (zone_id, facility_id): quantities_by_role[("travel_time", f"{zone_id}:{facility_id}")].value
            for zone_id, facilities in body.travel_time_quantity_ids.items()
            for facility_id in facilities
        }
        total_demand = sum(zone.demand for zone in zone_inputs)
        if total_demand <= 0:
            output["status"] = "INSUFFICIENT_DATA"
            output["missing_evidence"] = ["positive total market demand is required to calculate a market share"]
        else:
            decay = (
                quantities_by_role[("distance_decay", "distance_decay_exponent")].value
                if body.distance_decay_quantity_id is not None else None
            )
            if decay is not None and decay <= 0:
                output["status"] = "INSUFFICIENT_DATA"
                output["missing_evidence"] = ["Huff distance-decay quantity must be positive"]
            else:
                try:
                    spatial_ledger = Ledger()
                    for quantity in loaded.values():
                        spatial_ledger.register(quantity)
                    result = run_loop_a_spatial_siting(
                        spatial_ledger,
                        geo_unit_id=str(geo_id),
                        enterprise_id=body.candidate_facility_id,
                        allocator_type=body.allocator_type,
                        allocation_inputs=SpatialDemandInputs(
                            zones=zone_inputs,
                            facilities=facility_inputs,
                            parameters=AllocationParameters(travel_times, decay),
                            provenance_by_input={
                                **{
                                    f"zone_demand:{zone.zone_id}": str(zone.quantity_id)
                                    for zone in body.zones
                                },
                                **{
                                    f"facility_attractiveness:{facility.facility_id}": str(facility.quantity_id)
                                    for facility in body.facilities
                                },
                                **{
                                    f"travel_time:{zone_id}:{facility_id}": str(quantity_id)
                                    for zone_id, facilities in body.travel_time_quantity_ids.items()
                                    for facility_id, quantity_id in facilities.items()
                                },
                                **({"distance_decay_exponent": str(body.distance_decay_quantity_id)} if body.distance_decay_quantity_id else {}),
                            },
                        ),
                    )
                except (TypeError, ValueError, ArithmeticError) as exc:
                    output["status"] = "INSUFFICIENT_DATA"
                    output["missing_evidence"] = [f"spatial allocator could not use the supplied evidence: {exc}"]
                else:
                    if result.status != "COMPLETED":
                        output["status"] = result.status
                        output["missing_evidence"] = list(result.missing_evidence)
                    else:
                        output_quantities: List[Quantity] = []
                        definitions: Dict[str, str] = {}
                        output_ids: Dict[str, str] = {}
                        for index, quantity in enumerate(result.quantities):
                            output_id = str(uuid.uuid4())
                            parent_ids = tuple(input_quantity_ids.values()) if index == 0 else (output_quantities[0].id,)
                            persisted_quantity = replace(
                                quantity,
                                id=output_id,
                                geo_unit_id=str(geo_id),
                                resolution=int(scenario_geo.level),
                                as_of=today.isoformat(),
                                parent_ids=parent_ids,
                                owner_id=current_user.id,
                                method_id=f"arthlens.spatial_demand.{body.allocator_type}_v1",
                                model_version="arthlens-demand-allocation-v1",
                            )
                            output_quantities.append(persisted_quantity)
                            key = "captured_demand" if quantity.definition_key == "demand.monthly" else "market_share"
                            output_ids[key] = output_id
                            definitions[key] = quantity.definition_key
                        quantity_repo.save_many(output_quantities)
                        output.update({
                            "status": "COMPLETED",
                            "captured_demand_inr_monthly": result.captured_demand_inr_monthly,
                            "market_share_fraction": result.market_share_fraction,
                            "total_market_demand_inr_monthly": result.total_market_demand_inr,
                            "quantity_ids": output_ids,
                            "quantity_definition_keys": definitions,
                            "method_id": f"arthlens.spatial_demand.{body.allocator_type}_v1",
                            "model_version": "arthlens-demand-allocation-v1",
                            "missing_evidence": [],
                        })
    scenario_data["spatial_demand"] = output
    _save_scenario_results(
        scenario_repo, scenario, owner_id=current_user.id, scenario_id=scenario_id, scenario_data=scenario_data
    )
    return output


@router.post("/{scenario_id}/accessibility")
def calculate_scenario_accessibility(
    scenario_id: str,
    body: AccessibilityScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Compute and persist corridor accessibility from a registered road snapshot and ledger inputs."""
    scenario_repo = PostgresScenarioRepository()
    scenario = scenario_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    scenario_data = dict(scenario.get("scenario") or {})
    geo_id = scenario_data.get("geo_id")
    geo_repo = PostgresGeoUnitRepository()
    scenario_geo = geo_repo.get_by_id(str(geo_id)) if geo_id else None
    if scenario_geo is None:
        raise HTTPException(
            status_code=422,
            detail="INSUFFICIENT_DATA: select a registered geographic unit before analyzing accessibility.",
        )

    today = _current_analysis_date()
    source_repo = PostgresSourceRepository()
    quantity_repo = PostgresQuantityRepository()
    graph_repo = PostgresRoadGraphRepository()
    execution_id = str(uuid.uuid4())
    missing: List[str] = []
    road_version = source_repo.get_version(body.road_graph_source_version_id)
    road_source = source_repo.get_source(road_version["source_id"]) if road_version else None
    if (
        road_version is None
        or road_version.get("status") != "ACTIVE"
        or road_version.get("source_id") != "DS-04"
        or road_source is None
        or road_source.get("status") != "ACTIVE"
    ):
        missing.append("active registered DS-04 road graph source version")

    quantity_ids = {
        "site.longitude": str(body.longitude_quantity_id),
        "site.latitude": str(body.latitude_quantity_id),
        **{f"routing.speed.{road_class}": str(quantity_id) for road_class, quantity_id in body.speed_quantity_ids.items()},
    }
    roots = [body.longitude_quantity_id, body.latitude_quantity_id, *body.speed_quantity_ids.values()]
    if len({str(item) for item in roots}) != len(roots):
        missing.append("each coordinate and road-class speed requires its own ledger quantity")
    expected_inputs: List[tuple[str, uuid.UUID, str, str, tuple[Kind, ...]]] = [
        ("site.longitude", body.longitude_quantity_id, "site.longitude", "degree", (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED)),
        ("site.latitude", body.latitude_quantity_id, "site.latitude", "degree", (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED)),
    ]
    expected_inputs.extend(
        (f"routing.speed.{road_class}", quantity_id, f"routing.speed.{road_class}", "km/hour", (Kind.OBSERVED, Kind.USER_ASSUMED, Kind.ESTIMATED, Kind.CALCULATED))
        for road_class, quantity_id in body.speed_quantity_ids.items()
    )
    input_quantities: Dict[str, Quantity] = {}
    for key, quantity_id, definition_key, unit, kinds in expected_inputs:
        quantity = quantity_repo.get(quantity_id)
        issue = _validate_scenario_quantity(
            quantity,
            quantity_id=quantity_id,
            definition_key=definition_key,
            unit=unit,
            owner_id=current_user.id,
            as_of=today,
            allowed_kinds=kinds,
            source_repo=source_repo,
        )
        if issue:
            missing.append(f"{key}: {issue}")
            continue
        assert quantity is not None
        if not isfinite(float(quantity.value)):
            missing.append(f"{key}: quantity value is not finite")
        if not _is_geo_in_scope(geo_repo, quantity.geo_unit_id, str(geo_id)):
            missing.append(f"{key}: coordinate/speed quantity geography is outside the scenario unit")
        input_quantities[key] = quantity

    longitude = input_quantities.get("site.longitude")
    latitude = input_quantities.get("site.latitude")
    if longitude and not -180 <= longitude.value <= 180:
        missing.append("site longitude quantity is outside WGS84 bounds")
    if latitude and not -90 <= latitude.value <= 90:
        missing.append("site latitude quantity is outside WGS84 bounds")
    if longitude and latitude:
        geometry_status = getattr(scenario_geo.geometry_status, "value", scenario_geo.geometry_status)
        if geometry_status != "GEOMETRY_VERIFIED" or not scenario_geo.geometry_source_record_id:
            missing.append("site validation requires a source-linked verified scenario boundary")
        else:
            geometry_record = PostgresSourceRecordRepository().get_by_id(scenario_geo.geometry_source_record_id)
            geometry_version = (
                source_repo.get_version(geometry_record.source_version_id)
                if geometry_record is not None else None
            )
            geometry_source = (
                source_repo.get_source(geometry_record.source_id)
                if geometry_record is not None else None
            )
            if (
                geometry_record is None
                or geometry_record.geo_unit_id != str(geo_id)
                or geometry_record.source_id != "DS-09"
                or geometry_version is None
                or geometry_version.get("status") != "ACTIVE"
                or geometry_version.get("source_id") != "DS-09"
                or geometry_source is None
                or geometry_source.get("status") != "ACTIVE"
            ):
                missing.append("scenario boundary source record and active DS-09 version cannot be verified")
        if not scenario_geo.geometry:
            missing.append("registered scenario boundary geometry is unavailable for site-coordinate validation")
        else:
            try:
                boundary = shape(scenario_geo.geometry)
                site_point = Point(longitude.value, latitude.value)
                if boundary.is_empty or not boundary.is_valid:
                    missing.append("registered scenario boundary geometry is empty or invalid")
                elif not boundary.covers(site_point):
                    missing.append("site-coordinate quantities fall outside the selected scenario geography")
            except (TypeError, ValueError) as exc:
                missing.append(f"registered scenario boundary geometry cannot validate the site: {exc}")
    if body.model_version != "arthlens-routing-v1":
        missing.append("requested model version is not the registered routing model version")

    graph = None
    if not missing and longitude and latitude:
        try:
            graph = graph_repo.extract_local_subgraph(
                source_version_id=body.road_graph_source_version_id,
                site=(longitude.value, latitude.value),
                radius_m=body.extraction_radius_m,
            )
        except (RoadGraphProvenanceError, TypeError, ValueError) as exc:
            missing.append(f"source-versioned local road graph is unavailable: {exc}")
        if graph is not None:
            if graph.source_version_ids != frozenset({body.road_graph_source_version_id}):
                missing.append("extracted road graph does not retain the exact requested source version")
            if not graph.edges:
                missing.append("no source-versioned road edges are available in the selected radius")
            graph_classes = {edge.road_class for edge in graph.edges}
            if graph_classes != set(body.speed_quantity_ids):
                missing.append("speed quantity mappings must cover exactly the road classes in the extracted graph")

    assumptions: List[Quantity] = []
    assumption_specs = [
        ("routing.extraction_radius_m", body.extraction_radius_m, "meter"),
        ("routing.corridor_width_m", body.corridor_width_m, "meter"),
        *[(f"routing.catchment_threshold_minutes.{value:g}", value, "minute") for value in body.thresholds_minutes],
    ]
    for definition, value, unit in assumption_specs:
        assumptions.append(Quantity(
            id=str(uuid.uuid4()),
            definition_key=definition,
            value=float(value),
            unit=unit,
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id=str(geo_id),
            resolution=int(scenario_geo.level),
            as_of=today.isoformat(),
            uncertainty="EXACT",
            source_refs=((
                f"user:{current_user.id}",
                f"scenario:{scenario_id}/accessibility:{execution_id}/input:{definition}",
                today.isoformat(),
            ),),
            method_id="explicit_user_input",
            model_version="1",
            parent_ids=(),
            owner_id=current_user.id,
        ))

    output: Dict[str, Any] = {
        "scenario_id": scenario_id,
        "execution_id": execution_id,
        "status": "INSUFFICIENT_DATA" if missing else "PENDING",
        "request": body.model_dump(mode="json"),
        "input_quantity_ids": quantity_ids,
        "assumption_quantity_ids": {q.definition_key: q.id for q in assumptions},
        "quantity_ids": {},
        "missing_evidence": missing,
    }
    if not missing and graph is not None and longitude is not None and latitude is not None:
        loaded: Dict[str, Quantity] = {}
        try:
            loaded = _load_quantities_into_ledger(Ledger(), quantity_repo, list(quantity_ids.values()))
        except (TypeError, ValueError, KeyError) as exc:
            missing.append(f"ledger input lineage is incomplete: {exc}")
        if loaded:
            missing.extend(_validate_loaded_lineage(
                loaded,
                owner_id=current_user.id,
                as_of=today,
                source_repo=source_repo,
            ))
        if missing:
            output["status"] = "INSUFFICIENT_DATA"
            output["missing_evidence"] = missing
        else:
            all_parents = tuple(dict.fromkeys([*quantity_ids.values(), *(q.id for q in assumptions)]))
            ledger = Ledger()
            for quantity in loaded.values():
                ledger.register(quantity)
            for assumption in assumptions:
                ledger.register(assumption)
            speed_values = {
                road_class: input_quantities[f"routing.speed.{road_class}"].value
                for road_class in body.speed_quantity_ids
            }
            try:
                result = run_loop_b_corridor_accessibility(
                    ledger,
                    graph=graph,
                    site_coordinate=(longitude.value, latitude.value),
                    thresholds_minutes=body.thresholds_minutes,
                    site_geo_unit_id=str(geo_id),
                    speed_scenario=RoadSpeedScenario(body.road_speed_scenario_id, speed_values),
                    corridor_width_m=body.corridor_width_m,
                    parent_quantities=tuple([*loaded.values(), *assumptions]),
                    as_of=today.isoformat(),
                    model_version="arthlens-routing-v1",
                )
            except (TypeError, ValueError, ArithmeticError) as exc:
                output["status"] = "INSUFFICIENT_DATA"
                output["missing_evidence"] = [f"accessibility calculation could not use the supplied evidence: {exc}"]
            else:
                if result.status != "COMPLETED" or result.analysis is None:
                    output["status"] = "INSUFFICIENT_DATA"
                    output["missing_evidence"] = list(result.missing_evidence)
                else:
                    persisted_outputs = [
                        replace(quantity, owner_id=current_user.id, parent_ids=all_parents)
                        for quantity in ledger.quantities
                        if quantity.id in set(result.registered_quantity_ids.values())
                    ]
                    quantity_repo.save_many([*assumptions, *persisted_outputs])
                    output.update({
                        "status": "COMPLETED",
                        "site_coordinate": [longitude.value, latitude.value],
                        "snapped_node_id": result.snapped_node_id,
                        "snap_distance_m": result.snap_distance_m,
                        "source_version_id": body.road_graph_source_version_id,
                        "road_speed_scenario_id": body.road_speed_scenario_id,
                        "model_version": "arthlens-routing-v1",
                        "quantity_ids": result.registered_quantity_ids,
                        "catchments": [
                            {
                                "threshold_minutes": catchment.threshold_minutes,
                                "reachable_node_ids": list(catchment.reachable_node_ids),
                                "travel_time_minutes": dict(catchment.travel_time_minutes),
                                "geometry": _json_compatible(catchment.geometry),
                                "is_corridor_approximation": catchment.is_corridor_approximation,
                            }
                            for catchment in result.analysis.catchments
                        ],
                        "missing_evidence": [],
                    })
    if assumptions and output["status"] == "INSUFFICIENT_DATA":
        quantity_repo.save_many(assumptions)
    scenario_data["accessibility"] = output
    _save_scenario_results(
        scenario_repo, scenario, owner_id=current_user.id, scenario_id=scenario_id, scenario_data=scenario_data
    )
    return output


class SchemeViabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_cost_inr: float = Field(gt=0)
    promoter_contribution_fraction: float = Field(ge=0, le=1)
    subsidy_fraction: float = Field(ge=0, le=1)
    annual_interest_rate: float = Field(ge=0)
    loan_term_months: int = Field(gt=0)
    moratorium_months: int = Field(ge=0)
    moratorium_interest_treatment: str = Field(default="CAPITALIZED")
    subsidy_treatment: str = Field(default="ADJUSTS_PRINCIPAL")
    subsidy_release_month: Optional[int] = None
    unit_price: float = Field(gt=0)
    unit_variable_cost: float = Field(ge=0)
    fixed_operating_costs_monthly: float = Field(ge=0)
    monthly_sales_units: float = Field(ge=0)
    monthly_growth_rate: float = Field(default=0.0)
    seasonality_factors: Optional[List[float]] = None
    taxes_by_month: Optional[List[float]] = None
    other_payments_by_month: Optional[List[float]] = None
    working_capital_need_by_month: Optional[List[float]] = None
    opening_working_capital_need: float = Field(default=0.0)
    days_inventory: float = Field(default=30.0)
    days_receivable: float = Field(default=30.0)
    days_payable: float = Field(default=30.0)


@router.post("/{scenario_id}/scheme-viability")
def calculate_scenario_scheme_viability(
    scenario_id: str,
    body: SchemeViabilityRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Execute Loop C: Scheme eligibility, financial projection, verified reporting, and ledger quantities."""
    scenario_repo = PostgresScenarioRepository()
    scenario = scenario_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    scenario_data = dict(scenario.get("scenario") or {})
    geo_id = scenario_data.get("geo_id") or "in:district:120"
    geo_repo = PostgresGeoUnitRepository()
    scenario_geo = geo_repo.get_by_id(str(geo_id))
    resolution = scenario_geo.level if scenario_geo else ResolutionTier.DISTRICT

    ledger = Ledger()
    treatment_str = body.moratorium_interest_treatment.upper().replace("CAPITALIZED", "CAPITALISED")
    try:
        morat_treatment = MoratoriumInterestTreatment(treatment_str)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid moratorium_interest_treatment.")
    try:
        sub_treatment = SubsidyTreatment(body.subsidy_treatment.upper())
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid subsidy_treatment.")

    horizon = body.loan_term_months + body.moratorium_months
    seasonality = tuple(
        (body.seasonality_factors * ((horizon // len(body.seasonality_factors)) + 1))[:horizon]
        if body.seasonality_factors
        else [1.0] * horizon
    )
    taxes = tuple(
        (body.taxes_by_month * ((horizon // len(body.taxes_by_month)) + 1))[:horizon]
        if body.taxes_by_month
        else [0.0] * horizon
    )
    other = tuple(
        (body.other_payments_by_month * ((horizon // len(body.other_payments_by_month)) + 1))[:horizon]
        if body.other_payments_by_month
        else [0.0] * horizon
    )
    wc = tuple(
        (body.working_capital_need_by_month * ((horizon // len(body.working_capital_need_by_month)) + 1))[:horizon]
        if body.working_capital_need_by_month
        else [0.0] * horizon
    )

    try:
        result = run_loop_c_scheme_viability(
            ledger,
            owner_id=current_user.id,
            geo_unit_id=str(geo_id),
            resolution=resolution,
            project_cost_inr=body.project_cost_inr,
            promoter_contribution_fraction=body.promoter_contribution_fraction,
            subsidy_fraction=body.subsidy_fraction,
            annual_interest_rate=body.annual_interest_rate,
            loan_term_months=body.loan_term_months,
            moratorium_months=body.moratorium_months,
            moratorium_interest_treatment=morat_treatment,
            subsidy_treatment=sub_treatment,
            subsidy_release_month=body.subsidy_release_month,
            unit_price=body.unit_price,
            unit_variable_cost=body.unit_variable_cost,
            fixed_operating_costs_monthly=body.fixed_operating_costs_monthly,
            monthly_sales_units=body.monthly_sales_units,
            monthly_growth_rate=body.monthly_growth_rate,
            seasonality_factors=seasonality,
            taxes_by_month=taxes,
            other_payments_by_month=other,
            working_capital_need_by_month=wc,
            opening_working_capital_need=body.opening_working_capital_need,
            days_inventory=body.days_inventory,
            days_receivable=body.days_receivable,
            days_payable=body.days_payable,
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Scheme viability error: {exc}")

    quantity_repo = PostgresQuantityRepository()
    quantity_repo.save_many(list(ledger.quantities))

    summary = {
        "status": "COMPLETED",
        "scheme_eligibility_status": result.scheme_eligibility_status.value,
        "break_even_quantity": result.break_even_quantity,
        "total_revenue": result.projection_summary.total_revenue,
        "total_debt_service": result.projection_summary.total_debt_service,
        "minimum_cash": result.projection_summary.minimum_cash,
        "minimum_dscr": result.projection_summary.minimum_dscr,
        "months_projected": len(result.projection_summary.months),
        "report_json": result.report_json,
        "report_csv": result.report_csv,
        "calculation_provenance": result.calculation_provenance,
        "registered_quantities_count": len(ledger.quantities),
    }

    # Update scenario record metrics
    scenario_data["scheme_viability"] = summary
    scenario_data["break_even_units"] = result.break_even_quantity
    scenario_data["viability_status"] = (
        "FEASIBLE"
        if (result.projection_summary.minimum_cash >= 0 and (result.projection_summary.minimum_dscr or 1.0) >= 1.0)
        else "MARGINAL"
    )
    _save_scenario_results(
        scenario_repo, scenario, owner_id=current_user.id, scenario_id=scenario_id, scenario_data=scenario_data
    )
    return summary


@router.post("/{scenario_id}/policy")
def evaluate_scenario_policy(
    scenario_id: str,
    body: ScenarioPolicyEvaluationRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR, Role.STEWARD, Role.ADMIN)),
) -> Dict[str, Any]:
    """Persist an auditable three-valued policy evaluation alongside its scenario."""
    scenario_repo = PostgresScenarioRepository()
    scenario = scenario_repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found.")
    policy_result = evaluate_scheme_eligibility(
        body.scheme_id,
        PolicyEvaluationRequest(
            rule_key=body.rule_key,
            as_of=body.as_of,
            fact_quantity_ids=body.fact_quantity_ids,
        ),
        current_user,
    )
    scenario_data = dict(scenario.get("scenario") or {})
    scenario_data["policy_evaluation"] = {
        **policy_result,
        "scenario_id": scenario_id,
        "request": body.model_dump(mode="json"),
    }
    _save_scenario_results(
        scenario_repo, scenario, owner_id=current_user.id, scenario_id=scenario_id, scenario_data=scenario_data
    )
    return scenario_data["policy_evaluation"]


@router.post("/{scenario_id}/calculate")
def calculate_scenario(
    scenario_id: str,
    body: CalculateScenarioRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """
    Run deterministic financial submodels from explicit user assumptions.
    Spatial demand remains evidence-gated until its required inputs are supplied.
    Persist assumptions, calculation lineage, and outcomes in the scenario and ledger.
    """
    repo = PostgresScenarioRepository()
    scenario = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    scenario_data = scenario.get("scenario") or {}
    geo_id = scenario_data.get("geo_id")
    if not geo_id and _request_has_numeric_financial_inputs(body):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INSUFFICIENT_DATA: select a registered geographic unit before recording financial assumptions and results.",
        )
    geo_unit = PostgresGeoUnitRepository().get_by_id(geo_id) if geo_id else None
    if geo_id and geo_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario geographic unit not found.")

    # Each calculation is gated independently; absent assumptions never become zero.
    calculation_values: Dict[str, tuple[float, str, List[str]]] = {}
    quantity_ids: Dict[str, str] = {}
    input_quantity_ids: Dict[str, str] = {}
    execution_id = str(uuid.uuid4())
    calculation_parameters = body.model_dump(mode="json", exclude_none=True)

    price = body.price_per_unit
    variable_cost = body.variable_cost_per_unit
    fixed_costs = body.fixed_costs_per_month
    break_even_missing = [
        name
        for name, value in (
            ("price_per_unit", price),
            ("variable_cost_per_unit", variable_cost),
            ("fixed_costs_per_month", fixed_costs),
        )
        if value is None
    ]
    contribution_margin = None
    margin_percentage = None
    break_even_units = None
    if price is not None and variable_cost is not None:
        contribution_margin = round(price - variable_cost, 2)
        calculation_values["contribution_margin"] = (
            contribution_margin,
            "INR/count",
            ["price_per_unit", "variable_cost_per_unit"],
        )
        margin_percentage = round((contribution_margin / price) * 100, 1)
        calculation_values["margin_percentage"] = (
            margin_percentage,
            "percent",
            ["price_per_unit", "variable_cost_per_unit"],
        )
    if not break_even_missing:
        break_even_units = calculate_break_even_quantity(price, variable_cost, fixed_costs)
        if break_even_units is not None:
            calculation_values["break_even_units"] = (
                break_even_units,
                "count/month",
                ["price_per_unit", "variable_cost_per_unit", "fixed_costs_per_month"],
            )

    loan_required_fields = (
        "loan_principal",
        "annual_interest_rate",
        "loan_term_months",
        "moratorium_months",
        "moratorium_interest_treatment",
        "subsidy_amount",
        "subsidy_treatment",
    )
    loan_missing = [
        name for name in loan_required_fields if getattr(body, name) is None
    ]
    schedule = None
    monthly_emi = None
    total_repaid = None
    total_interest = None
    financed_principal = None
    if not loan_missing:
        try:
            loan_terms = LoanTerms(
                principal=body.loan_principal,
                annual_rate=body.annual_interest_rate,
                repayment_months=body.loan_term_months,
                moratorium_months=body.moratorium_months,
                moratorium_interest_treatment=body.moratorium_interest_treatment,
                subsidy_amount=body.subsidy_amount,
                subsidy_treatment=body.subsidy_treatment,
                subsidy_release_month=body.subsidy_release_month,
            )
            schedule = build_loan_schedule(loan_terms)
        except (TypeError, ValueError, ArithmeticError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid explicit loan assumptions: {exc}",
            ) from exc
        monthly_emi = next(
            (
                row.debt_service
                for row in schedule.rows
                if row.month > body.moratorium_months and row.debt_service > 0
            ),
            0.0,
        )
        total_repaid = schedule.total_repaid
        total_interest = sum(row.interest for row in schedule.rows)
        financed_principal = schedule.financed_principal
        loan_parent_keys = list(loan_required_fields)
        if body.subsidy_release_month is not None:
            loan_parent_keys.append("subsidy_release_month")
        for key, value, unit in (
            ("monthly_emi", monthly_emi, "INR/month"),
            ("total_repaid", total_repaid, "INR"),
            ("total_interest", total_interest, "INR"),
            ("financed_principal", financed_principal, "INR"),
            ("subsidy_applied", body.subsidy_amount, "INR"),
        ):
            calculation_values[key] = (value, unit, loan_parent_keys)

    working_capital_requirement = None
    working_capital_status = "INSUFFICIENT_DATA"
    if body.working_capital is not None:
        working_capital_requirement = calculate_working_capital_requirement(
            inventory_value=body.working_capital.inventory_value,
            accounts_receivable=body.working_capital.accounts_receivable,
            accounts_payable=body.working_capital.accounts_payable,
        )
        working_capital_status = "COMPLETED"
        calculation_values["working_capital_requirement"] = (
            working_capital_requirement,
            "INR",
            [
                "working_capital.inventory_value",
                "working_capital.accounts_receivable",
                "working_capital.accounts_payable",
            ],
        )

    projection = None
    projection_results: Dict[str, Any] = {
        "status": "INSUFFICIENT_DATA",
        "missing_evidence": [
            "explicit monthly volume, price, cost, debt-service, tax, payment, and working-capital schedules"
        ],
        "quantity_ids": {},
    }
    if body.projection is not None:
        projection_inputs = body.projection.model_dump()
        projection = project_monthly_cash_flow(
            FinancialScenario(
                **{
                    key: value
                    for key, value in projection_inputs.items()
                    if key
                    not in {
                        "minimum_dscr",
                        "repayment_capacity_annual_interest_rate",
                        "repayment_capacity_months",
                    }
                }
            )
        )
        def projection_keys(*field_names: str, through_month: int | None = None) -> List[str]:
            selected: List[str] = []
            for field_name in field_names:
                value = projection_inputs[field_name]
                if isinstance(value, list):
                    end = len(value) if through_month is None else min(len(value), through_month)
                    selected.extend(
                        f"projection.{field_name}.{index + 1}" for index in range(end)
                    )
                else:
                    selected.append(f"projection.{field_name}")
            return selected

        volume_keys = projection_keys(
            "initial_quantity", "monthly_growth_rate", "seasonality_factors"
        )
        cash_available_keys = volume_keys + projection_keys(
            "price_per_unit_by_month",
            "variable_cost_per_unit_by_month",
            "operating_expenses_by_month",
            "taxes_by_month",
            "other_payments_by_month",
            "working_capital_need_by_month",
            "opening_working_capital_need",
        )
        cash_balance_keys = cash_available_keys + projection_keys(
            "debt_service_by_month",
            "subsidy_cash_release_by_month",
            "equity",
            "disbursed_loan",
            "capex",
        )
        dscr_parent_keys = cash_available_keys + projection_keys("debt_service_by_month")
        capacity_parent_keys = cash_available_keys + projection_keys(
            "minimum_dscr",
            "repayment_capacity_annual_interest_rate",
            "repayment_capacity_months",
        )
        min_cash = projection.minimum_cash
        funding_shortfall = calculate_financial_shortfall(min_cash)
        cfads = [month.cash_available_for_debt_service for month in projection.months]
        capacity = calculate_repayment_capacity(
            cash_available_for_debt_service=min(cfads),
            minimum_dscr=body.projection.minimum_dscr,
            annual_interest_rate=body.projection.repayment_capacity_annual_interest_rate,
            repayment_months=body.projection.repayment_capacity_months,
        )
        projection_results = {
            "status": "COMPLETED",
            "cash_flow_status": "COMPLETED",
            "initial_cash": projection.initial_cash,
            "total_revenue": projection.total_revenue,
            "total_debt_service": projection.total_debt_service,
            "cash_conversion_cycle_days": projection.cash_conversion_cycle_days,
            "minimum_dscr": projection.minimum_dscr,
            "dscr_status": "COMPLETED" if projection.minimum_dscr is not None else "INSUFFICIENT_DATA",
            "minimum_cash": min_cash,
            "first_shortfall_month": projection.first_shortfall_month,
            "funding_shortfall": funding_shortfall,
            "financial_shortfall_status": "COMPLETED",
            "repayment_capacity_monthly_debt_service": capacity.monthly_debt_service,
            "repayment_capacity_supported_principal": capacity.supported_principal,
            "repayment_capacity_status": "COMPLETED",
            "debt_service_source": "EXPLICIT_USER_ASSUMPTION",
            "quality_flags": sorted(projection.quality_flags),
            "months": [],
            "quantity_ids": {},
        }
        projection_metric_specs = (
            ("initial_cash", projection.initial_cash, "INR", projection_keys("equity", "disbursed_loan", "capex")),
            ("total_revenue", projection.total_revenue, "INR", volume_keys + projection_keys("price_per_unit_by_month")),
            ("total_debt_service", projection.total_debt_service, "INR", projection_keys("debt_service_by_month")),
            ("cash_conversion_cycle_days", projection.cash_conversion_cycle_days, "day", projection_keys("days_inventory", "days_receivable", "days_payable")),
            ("minimum_cash", min_cash, "INR", cash_balance_keys),
            ("funding_shortfall", funding_shortfall, "INR", cash_balance_keys),
            ("repayment_capacity_monthly_debt_service", capacity.monthly_debt_service, "INR/month", capacity_parent_keys),
            ("repayment_capacity_supported_principal", capacity.supported_principal, "INR", capacity_parent_keys),
        )
        if projection.first_shortfall_month is not None:
            projection_metric_specs += ((
                "first_shortfall_month",
                projection.first_shortfall_month,
                "month",
                cash_balance_keys,
            ),)
        for key, value, unit, parent_keys in projection_metric_specs:
            calculation_values[f"projection.{key}"] = (value, unit, parent_keys)
        if projection.minimum_dscr is not None:
            calculation_values["projection.minimum_dscr"] = (
                projection.minimum_dscr,
                "dimensionless",
                dscr_parent_keys,
            )
        for month in projection.months:
            month_payload: Dict[str, Any] = {"month": month.month, "quantity_ids": {}}
            month_index = month.month
            price_key = f"projection.price_per_unit_by_month.{month_index}"
            variable_cost_key = f"projection.variable_cost_per_unit_by_month.{month_index}"
            operating_cost_key = f"projection.operating_expenses_by_month.{month_index}"
            debt_service_key = f"projection.debt_service_by_month.{month_index}"
            tax_key = f"projection.taxes_by_month.{month_index}"
            other_payment_key = f"projection.other_payments_by_month.{month_index}"
            subsidy_release_key = f"projection.subsidy_cash_release_by_month.{month_index}"
            current_working_capital_key = f"projection.working_capital_need_by_month.{month_index}"
            working_capital_change_keys = [current_working_capital_key]
            if month_index == 1:
                working_capital_change_keys.append("projection.opening_working_capital_need")
            else:
                working_capital_change_keys.append(
                    f"projection.working_capital_need_by_month.{month_index - 1}"
                )
            month_cfads_keys = (
                volume_keys
                + [price_key, variable_cost_key, operating_cost_key, tax_key, other_payment_key]
                + working_capital_change_keys
            )
            cash_flow_fields = (
                "price_per_unit_by_month",
                "variable_cost_per_unit_by_month",
                "operating_expenses_by_month",
                "debt_service_by_month",
                "taxes_by_month",
                "other_payments_by_month",
                "subsidy_cash_release_by_month",
                "working_capital_need_by_month",
            )
            prior_cash_keys = projection_keys(
                "initial_quantity",
                "monthly_growth_rate",
                "seasonality_factors",
                *cash_flow_fields,
                "opening_working_capital_need",
                "equity",
                "disbursed_loan",
                "capex",
                through_month=max(month_index - 1, 0),
            )
            closing_cash_keys = projection_keys(
                "initial_quantity",
                "monthly_growth_rate",
                "seasonality_factors",
                *cash_flow_fields,
                "opening_working_capital_need",
                "equity",
                "disbursed_loan",
                "capex",
                through_month=month_index,
            )
            if month_index == 1:
                prior_cash_keys = projection_keys("equity", "disbursed_loan", "capex")
            for field_name, value, unit in (
                ("quantity", month.quantity, "count/month"),
                ("revenue", month.revenue, "INR"),
                ("cost_of_goods_sold", month.cost_of_goods_sold, "INR"),
                ("contribution_per_unit", month.contribution_per_unit, "INR/count"),
                ("break_even_quantity", month.break_even_quantity, "count/month"),
                ("operating_expenses", month.operating_expenses, "INR"),
                ("debt_service", month.debt_service, "INR"),
                ("taxes", month.taxes, "INR"),
                ("other_payments", month.other_payments, "INR"),
                ("subsidy_cash_release", month.subsidy_cash_release, "INR"),
                ("working_capital_need", month.working_capital_need, "INR"),
                ("working_capital_change", month.working_capital_change, "INR"),
                ("cash_available_for_debt_service", month.cash_available_for_debt_service, "INR"),
                ("dscr", month.dscr, "dimensionless"),
                ("cash_flow", month.cash_flow, "INR"),
                ("opening_cash", month.opening_cash, "INR"),
                ("closing_cash", month.closing_cash, "INR"),
            ):
                if value is None:
                    continue
                output_key = f"projection.month_{month.month}.{field_name}"
                parent_keys = {
                    "quantity": volume_keys,
                    "revenue": volume_keys + [price_key],
                    "cost_of_goods_sold": volume_keys + [variable_cost_key],
                    "contribution_per_unit": [price_key, variable_cost_key],
                    "break_even_quantity": [price_key, variable_cost_key, operating_cost_key],
                    "operating_expenses": [operating_cost_key],
                    "debt_service": [debt_service_key],
                    "taxes": [tax_key],
                    "other_payments": [other_payment_key],
                    "subsidy_cash_release": [subsidy_release_key],
                    "working_capital_need": [current_working_capital_key],
                    "working_capital_change": working_capital_change_keys,
                    "cash_available_for_debt_service": month_cfads_keys,
                    "dscr": month_cfads_keys + [debt_service_key],
                    "cash_flow": month_cfads_keys + [debt_service_key, subsidy_release_key],
                    "opening_cash": prior_cash_keys,
                    "closing_cash": closing_cash_keys,
                }[field_name]
                calculation_values[output_key] = (value, unit, parent_keys)
                month_payload[field_name] = value
            projection_results["months"].append(month_payload)

    # 3. Spatial demand allocation is deliberately not inferred from a district
    # population total. It needs observed/registered zone demand, facility
    # attributes, route-derived travel times, and an explicit Huff parameter.
    # None of those are available on this endpoint's request contract yet.
    allocated_demand = None
    spatial_demand_status = "INSUFFICIENT_DATA"
    spatial_demand_missing_evidence = [
        "zone demand quantities or explicitly labelled user assumptions",
        "candidate and competitor attractiveness quantities or explicitly labelled user assumptions",
        "route-derived travel-time quantity for every zone/facility pair",
        "explicit distance-decay scenario assumption",
    ]

    # 4. Feasibility verdict
    target_vol = body.target_monthly_units
    if break_even_missing or target_vol is None:
        feasibility_status = "INSUFFICIENT_DATA"
    elif break_even_units is None:
        feasibility_status = "NO_BREAK_EVEN"
    else:
        feasibility_status = "FEASIBLE" if target_vol >= break_even_units else "BELOW_BREAK_EVEN"

    loan_parent_keys = list(loan_required_fields)
    if body.subsidy_release_month is not None:
        loan_parent_keys.append("subsidy_release_month")
    if schedule is not None:
        for row in schedule.rows:
            for field_name, value in (
                ("opening_balance", row.opening_balance),
                ("interest", row.interest),
                ("principal_paid", row.principal_paid),
                ("subsidy_principal_adjustment", row.subsidy_principal_adjustment),
                ("subsidy_cash_release", row.subsidy_cash_release),
                ("debt_service", row.debt_service),
                ("closing_balance", row.closing_balance),
            ):
                calculation_values[f"loan_schedule.month_{row.month}.{field_name}"] = (
                    value,
                    "INR",
                    loan_parent_keys,
                )

    if _request_has_numeric_financial_inputs(body) and geo_unit is not None:
        quantity_repo = PostgresQuantityRepository()
        with quantity_repo._get_session() as ledger_session:
            input_quantities, input_quantity_ids = _build_financial_input_quantities(
                body=body,
                scenario_id=scenario_id,
                execution_id=execution_id,
                owner_id=current_user.id,
                geo_id=geo_id,
                resolution=int(geo_unit.level),
            )
            output_quantities, quantity_ids = _build_financial_output_quantities(
                values=calculation_values,
                input_quantity_ids=input_quantity_ids,
                owner_id=current_user.id,
                geo_id=geo_id,
                resolution=int(geo_unit.level),
            )
            quantity_repo.save_many(
                [*input_quantities, *output_quantities],
                session=ledger_session,
            )
            ledger_session.commit()

    for month in projection_results.get("months", []):
        month_number = month.get("month")
        for field_name in list(month):
            if field_name in {"month", "quantity_ids"}:
                continue
            quantity_id = quantity_ids.get(f"projection.month_{month_number}.{field_name}")
            if quantity_id:
                month["quantity_ids"][field_name] = quantity_id
    for metric_name in (
        "initial_cash",
        "total_revenue",
        "total_debt_service",
        "cash_conversion_cycle_days",
        "minimum_dscr",
        "minimum_cash",
        "first_shortfall_month",
        "funding_shortfall",
        "repayment_capacity_monthly_debt_service",
        "repayment_capacity_supported_principal",
    ):
        quantity_id = quantity_ids.get(f"projection.{metric_name}")
        if quantity_id:
            projection_results["quantity_ids"][metric_name] = quantity_id

    loan_schedule_rows = []
    if schedule is not None:
        for row in schedule.rows:
            row_payload: Dict[str, Any] = {"month": row.month, "quantity_ids": {}}
            for field_name, value, unit in (
                ("opening_balance", row.opening_balance, "INR"),
                ("interest", row.interest, "INR"),
                ("principal_paid", row.principal_paid, "INR"),
                ("subsidy_principal_adjustment", row.subsidy_principal_adjustment, "INR"),
                ("subsidy_cash_release", row.subsidy_cash_release, "INR"),
                ("debt_service", row.debt_service, "INR"),
                ("closing_balance", row.closing_balance, "INR"),
            ):
                output_key = f"loan_schedule.month_{row.month}.{field_name}"
                output_id = quantity_ids.get(output_key)
                row_payload[field_name] = value
                if output_id:
                    row_payload["quantity_ids"][field_name] = output_id
            loan_schedule_rows.append(row_payload)

    calculations = {
        "price_per_unit": price,
        "variable_cost_per_unit": variable_cost,
        "fixed_costs_per_month": fixed_costs,
        "contribution_margin": contribution_margin,
        "margin_percentage": margin_percentage,
        "break_even_units": break_even_units,
        "target_monthly_units": target_vol,
        "loan_principal": body.loan_principal,
        "financed_principal": financed_principal,
        "subsidy_applied": body.subsidy_amount,
        "annual_interest_rate": body.annual_interest_rate,
        "monthly_emi": monthly_emi,
        "total_repaid": total_repaid,
        "total_interest": total_interest,
        "repayment_months": body.loan_term_months,
        "moratorium_months": body.moratorium_months,
        "moratorium_interest_treatment": body.moratorium_interest_treatment.value if body.moratorium_interest_treatment else None,
        "subsidy_treatment": body.subsidy_treatment.value if body.subsidy_treatment else None,
        "subsidy_release_month": body.subsidy_release_month,
        "loan_schedule": loan_schedule_rows,
        "loan_schedule_status": "COMPLETED" if schedule is not None else "INSUFFICIENT_DATA",
        "loan_schedule_missing_inputs": loan_missing,
        "break_even_status": (
            "INSUFFICIENT_DATA"
            if break_even_missing
            else ("NO_BREAK_EVEN" if break_even_units is None else "COMPLETED")
        ),
        "break_even_missing_inputs": break_even_missing,
        "working_capital_requirement": working_capital_requirement,
        "working_capital_status": working_capital_status,
        "financial_projection": projection_results,
        "spatial_demand_allocated": allocated_demand,
        "spatial_demand_status": spatial_demand_status,
        "spatial_demand_missing_evidence": spatial_demand_missing_evidence,
        "feasibility_status": feasibility_status,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "epistemic_floor": (
            "FLOOR 3: EXPLICIT USER ASSUMPTIONS"
            if input_quantity_ids
            else "INSUFFICIENT_DATA"
        ),
        "input_quantity_ids": input_quantity_ids,
        "quantity_ids": quantity_ids,
        "calculation_provenance": {
            "execution_id": execution_id,
            "model_id": "arthlens-finance-v1",
            "parameters": calculation_parameters,
            "inputs": input_quantity_ids,
            "outputs": {
                key: {
                    "quantity_id": value,
                    "parent_quantity_ids": [
                        input_quantity_ids[parent_key]
                        for parent_key in calculation_values[key][2]
                        if parent_key in input_quantity_ids
                    ],
                }
                for key, value in quantity_ids.items()
            },
        },
    }

    all_missing = list(
        dict.fromkeys(
            break_even_missing
            + loan_missing
            + ([] if body.projection is not None else ["projection"])
            + ([] if body.working_capital is not None else ["working_capital"])
        )
    )
    calculations["finance_status"] = (
        "COMPLETED" if not all_missing else ("PARTIAL" if calculation_values else "INSUFFICIENT_DATA")
    )
    calculations["missing_financial_inputs"] = all_missing

    # Persist into scenario record in Postgres
    updated_scenario_data = dict(scenario.get("scenario") or {})
    updated_scenario_data["financial_assumptions"] = calculation_parameters
    updated_scenario_data["calculations"] = calculations
    repo.save_scenario(
        {
            "id": scenario_id,
            "owner_id": current_user.id,
            "name": scenario["name"],
            "scenario": updated_scenario_data,
        }
    )

    return {
        "scenario_id": scenario_id,
        "name": scenario["name"],
        "calculations": calculations,
    }


@router.post("/{scenario_id}/simulate", status_code=status.HTTP_201_CREATED)
def simulate_scenario(
    scenario_id: str,
    body: FinancialSimulationRequest,
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Dict[str, Any]:
    """Run reproducible uncertainty and sensitivity analysis on explicit scenario cash flows."""
    repo = PostgresScenarioRepository()
    scenario = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not scenario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found.")
    scenario_data = scenario.get("scenario") or {}
    geo_id = scenario_data.get("geo_id")
    if not geo_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INSUFFICIENT_DATA: select a registered geographic unit before simulating financial results.",
        )
    geo_unit = PostgresGeoUnitRepository().get_by_id(geo_id)
    if geo_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario geographic unit not found.")

    execution_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    projection_inputs = body.projection.model_dump(mode="json")
    try:
        input_quantities, baseline_ids, distribution_ids, sensitivity_ids = _build_simulation_input_quantities(
            body=body,
            scenario_id=scenario_id,
            execution_id=execution_id,
            owner_id=current_user.id,
            geo_id=geo_id,
            resolution=int(geo_unit.level),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid explicit simulation inputs: {exc}",
        ) from exc
    monte_carlo_parent_ids = tuple(dict.fromkeys([
        *baseline_ids.values(),
        *distribution_ids.values(),
    ]))
    all_simulation_input_ids = tuple(dict.fromkeys([
        *baseline_ids.values(),
        *distribution_ids.values(),
        *(
            quantity_id
            for values in sensitivity_ids.values()
            for quantity_id in values
        ),
    ]))
    if not monte_carlo_parent_ids or not all_simulation_input_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INSUFFICIENT_DATA: explicit simulation input quantities are required.",
        )

    model_version = "arthlens-financial-simulation-v1"
    metadata = SimulationMetadata(
        scenario_id=scenario_id,
        model_version=model_version,
        seed=body.seed,
        sample_count=body.sample_count,
        data_versions=tuple(f"quantity:{quantity_id}" for quantity_id in monte_carlo_parent_ids),
    )
    try:
        result = run_financial_uncertainty_analysis(
            projection_inputs=projection_inputs,
            distributions=[item.model_dump() for item in body.distributions],
            sensitivity_parameter_values=body.sensitivity_parameter_values,
            metadata=metadata,
            quantile_levels=body.quantile_levels,
            minimum_sample_count=body.minimum_sample_count,
            convergence_tolerances=body.convergence_tolerances,
            shortfall_probability_tolerance=body.shortfall_probability_tolerance,
        )
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid explicit simulation assumptions: {exc}",
        ) from exc

    today = _current_analysis_date().isoformat()
    output_quantities, output_ids, response = _build_simulation_outputs(
        result=result,
        run_id=run_id,
        owner_id=current_user.id,
        geo_id=geo_id,
        resolution=int(geo_unit.level),
        as_of=today,
        monte_carlo_parent_ids=monte_carlo_parent_ids,
        sensitivity_baseline_parent_ids=tuple(dict.fromkeys(baseline_ids.values())),
        sensitivity_parameter_ids=sensitivity_ids,
    )
    response.update({
        "scenario_id": scenario_id,
        "execution_id": execution_id,
        "status": "COMPLETED",
        "configuration": {
            "minimum_sample_count": body.minimum_sample_count,
            "quantile_levels": body.quantile_levels,
            "convergence_tolerances": body.convergence_tolerances,
            "shortfall_probability_tolerance": body.shortfall_probability_tolerance,
            "distributions": [item.model_dump(mode="json") for item in body.distributions],
            "sensitivity_parameter_values": body.sensitivity_parameter_values,
        },
        "input_quantity_ids": {
            "projection": baseline_ids,
            "distributions": distribution_ids,
            "sensitivity": sensitivity_ids,
        },
    })
    output_references = {
        **response,
        "request": body.model_dump(mode="json"),
        "quantity_ids": output_ids,
    }
    scenario_repo_data = dict(scenario_data)
    scenario_repo_data["financial_simulation"] = response

    try:
        repo.save_simulation_run({
            "id": run_id,
            "scenario_id": scenario_id,
            "seed": body.seed,
            "model_version": model_version,
            "git_hash": None,
            "data_version_ids": list(metadata.data_versions),
            "outputs_references": {},
            "status": "PENDING",
        })
        quantity_repo = PostgresQuantityRepository()
        with quantity_repo._get_session() as ledger_session:
            quantity_repo.save_many(
                [*input_quantities, *output_quantities],
                session=ledger_session,
            )
            ledger_session.commit()
        repo.save_simulation_run({
            "id": run_id,
            "scenario_id": scenario_id,
            "seed": body.seed,
            "model_version": model_version,
            "git_hash": None,
            "data_version_ids": list(metadata.data_versions),
            "outputs_references": output_references,
            "status": "COMPLETED",
        })
        repo.save_scenario({
            "id": scenario_id,
            "owner_id": current_user.id,
            "name": scenario["name"],
            "scenario": scenario_repo_data,
        })
    except Exception:
        try:
            repo.save_simulation_run({
                "id": run_id,
                "scenario_id": scenario_id,
                "seed": body.seed,
                "model_version": model_version,
                "data_version_ids": list(metadata.data_versions),
                "outputs_references": {},
                "status": "FAILED",
            })
        except Exception:
            pass
        raise
    return {"id": run_id, **response}


_SIMULATION_SCALAR_UNITS = {
    "initial_quantity": "count/month",
    "monthly_growth_rate": "dimensionless/month",
    "opening_working_capital_need": "INR",
    "equity": "INR",
    "disbursed_loan": "INR",
    "capex": "INR",
    "days_inventory": "day",
    "days_receivable": "day",
    "days_payable": "day",
}
_SIMULATION_SERIES_UNITS = {
    "seasonality_factors": "dimensionless",
    "price_per_unit_by_month": "INR/count",
    "variable_cost_per_unit_by_month": "INR/count",
    "operating_expenses_by_month": "INR/month",
    "debt_service_by_month": "INR/month",
    "taxes_by_month": "INR/month",
    "other_payments_by_month": "INR/month",
    "subsidy_cash_release_by_month": "INR/month",
    "working_capital_need_by_month": "INR",
}


def _build_simulation_input_quantities(
    *,
    body: FinancialSimulationRequest,
    scenario_id: str,
    execution_id: str,
    owner_id: str,
    geo_id: str,
    resolution: int,
) -> tuple[List[Quantity], Dict[str, str], Dict[str, str], Dict[str, List[str]]]:
    today = _current_analysis_date().isoformat()
    quantities: List[Quantity] = []
    baseline_ids: Dict[str, str] = {}
    distribution_ids: Dict[str, str] = {}
    sensitivity_ids: Dict[str, List[str]] = {}

    def add_input(key: str, value: float, unit: str) -> str:
        quantity_id = str(uuid.uuid4())
        quantities.append(Quantity(
            id=quantity_id,
            definition_key=f"finance.simulation.assumption.{key}",
            value=value,
            unit=unit,
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id=geo_id,
            resolution=resolution,
            as_of=today,
            source_refs=((
                f"user:{owner_id}",
                f"scenario:{scenario_id}/simulation:{execution_id}/input:{key}",
                today,
            ),),
            method_id="explicit_user_input",
            model_version="1",
            parent_ids=(),
            owner_id=owner_id,
        ))
        return quantity_id

    projection_values = body.projection.model_dump(mode="python")
    for field_name, value in projection_values.items():
        if field_name in _SIMULATION_SERIES_UNITS:
            for index, item in enumerate(value, start=1):
                path = f"{field_name}.{index}"
                baseline_ids[path] = add_input(
                    f"projection.{path}",
                    float(item),
                    _SIMULATION_SERIES_UNITS[field_name],
                )
        else:
            baseline_ids[field_name] = add_input(
                f"projection.{field_name}",
                float(value),
                _SIMULATION_SCALAR_UNITS[field_name],
            )

    for distribution in body.distributions:
        unit = _unit_for_simulation_path(distribution.parameter)
        for parameter_name, parameter_value in distribution.parameters.items():
            key = f"{distribution.parameter}.{parameter_name}"
            quantity_key = f"distribution.{key}"
            distribution_ids[key] = add_input(
                quantity_key,
                float(parameter_value),
                unit,
            )

    for path, values in body.sensitivity_parameter_values.items():
        unit = _unit_for_simulation_path(path)
        sensitivity_ids[path] = [
            add_input(f"sensitivity.{path}.{index + 1}", float(value), unit)
            for index, value in enumerate(values)
        ]
    return quantities, baseline_ids, distribution_ids, sensitivity_ids


def _unit_for_simulation_path(path: str) -> str:
    field_name = path.split(".", 1)[0]
    if field_name in _SIMULATION_SCALAR_UNITS:
        return _SIMULATION_SCALAR_UNITS[field_name]
    if field_name in _SIMULATION_SERIES_UNITS:
        return _SIMULATION_SERIES_UNITS[field_name]
    raise ValueError(f"Unknown financial simulation field: {path}.")


def _build_simulation_outputs(
    *,
    result: Any,
    run_id: str,
    owner_id: str,
    geo_id: str,
    resolution: int,
    as_of: str,
    monte_carlo_parent_ids: tuple[str, ...],
    sensitivity_baseline_parent_ids: tuple[str, ...],
    sensitivity_parameter_ids: Dict[str, List[str]],
) -> tuple[List[Quantity], Dict[str, str], Dict[str, Any]]:
    quantities: List[Quantity] = []
    output_ids: Dict[str, str] = {}
    simulation_metadata = result.monte_carlo.metadata

    def add_output(
        key: str,
        value: float,
        unit: str,
        kind: Kind,
        parents: tuple[str, ...],
        *,
        uncertainty: Any = "EXACT",
        simulation_meta: SimulationMetadata | None = None,
    ) -> str:
        quantity_id = str(uuid.uuid4())
        quantities.append(Quantity(
            id=quantity_id,
            definition_key=f"finance.simulation.result.{key}",
            value=value,
            unit=unit,
            kind=kind,
            evidence_floor=3,
            geo_unit_id=geo_id,
            resolution=resolution,
            as_of=as_of,
            uncertainty=uncertainty,
            source_refs=(),
            method_id=f"arthlens.{key}",
            model_version=simulation_metadata.model_version,
            parent_ids=parents,
            simulation_meta=simulation_meta,
            owner_id=owner_id,
        ))
        output_ids[key] = quantity_id
        return quantity_id

    metric_response: Dict[str, Any] = {}
    for metric_name, summary in result.monte_carlo.metrics.items():
        metric_uncertainty = {
            "type": "MONTE_CARLO_SUMMARY",
            "standard_error": summary.standard_error,
            "converged": summary.converged,
        }
        mean_key = f"monte_carlo.{metric_name}.mean"
        mean_id = add_output(
            mean_key,
            summary.mean,
            _unit_for_simulation_metric(metric_name),
            Kind.SIMULATED,
            monte_carlo_parent_ids,
            uncertainty=metric_uncertainty,
            simulation_meta=simulation_metadata,
        )
        standard_error_key = f"monte_carlo.{metric_name}.standard_error"
        standard_error_id = add_output(
            standard_error_key,
            summary.standard_error,
            _unit_for_simulation_metric(metric_name),
            Kind.SIMULATED,
            monte_carlo_parent_ids,
            uncertainty={"type": "MONTE_CARLO_STANDARD_ERROR"},
            simulation_meta=simulation_metadata,
        )
        quantiles: Dict[str, Dict[str, Any]] = {}
        for level, value in summary.quantiles.items():
            level_key = format(level, ".12g")
            quantity_key = f"monte_carlo.{metric_name}.quantile.{level_key}"
            quantity_id = add_output(
                quantity_key,
                value,
                _unit_for_simulation_metric(metric_name),
                Kind.SIMULATED,
                monte_carlo_parent_ids,
                uncertainty={"type": "MONTE_CARLO_QUANTILE", "level": level},
                simulation_meta=simulation_metadata,
            )
            quantiles[level_key] = {"value": value, "quantity_id": quantity_id}
        metric_response[metric_name] = {
            "mean": summary.mean,
            "mean_quantity_id": mean_id,
            "quantiles": quantiles,
            "standard_error": summary.standard_error,
            "standard_error_quantity_id": standard_error_id,
            "converged": summary.converged,
        }

    probability_id = add_output(
        "monte_carlo.cash_shortfall_probability",
        result.monte_carlo.shortfall_probability,
        "probability",
        Kind.SIMULATED,
        monte_carlo_parent_ids,
        uncertainty={"type": "BERNOULLI_MONTE_CARLO"},
        simulation_meta=simulation_metadata,
    )
    probability_error_id = add_output(
        "monte_carlo.cash_shortfall_probability_standard_error",
        result.monte_carlo.shortfall_probability_standard_error,
        "probability",
        Kind.SIMULATED,
        monte_carlo_parent_ids,
        uncertainty={"type": "BERNOULLI_MONTE_CARLO_STANDARD_ERROR"},
        simulation_meta=simulation_metadata,
    )

    sensitivity_response: Dict[str, Any] = {"baseline_outputs": {}, "points": []}
    for metric_name, value in result.sensitivity.baseline_outputs.items():
        key = f"sensitivity.baseline.{metric_name}"
        quantity_id = add_output(
            key,
            value,
            _unit_for_simulation_metric(metric_name),
            Kind.CALCULATED,
            tuple(dict.fromkeys(sensitivity_baseline_parent_ids)),
        )
        sensitivity_response["baseline_outputs"][metric_name] = {
            "value": value,
            "quantity_id": quantity_id,
        }
    point_counts: Dict[str, int] = {}
    for point_index, point in enumerate(result.sensitivity.points, start=1):
        metric_values: Dict[str, Any] = {}
        occurrence = point_counts.get(point.parameter, 0)
        point_counts[point.parameter] = occurrence + 1
        point_parent_ids = tuple(dict.fromkeys((
            *sensitivity_baseline_parent_ids,
            sensitivity_parameter_ids[point.parameter][occurrence],
        )))
        for metric_name, value in point.outputs.items():
            value_key = f"sensitivity.point_{point_index}.{metric_name}.value"
            delta_key = f"sensitivity.point_{point_index}.{metric_name}.delta"
            value_id = add_output(
                value_key,
                value,
                _unit_for_simulation_metric(metric_name),
                Kind.CALCULATED,
                point_parent_ids,
            )
            delta_id = add_output(
                delta_key,
                point.deltas[metric_name],
                _unit_for_simulation_metric(metric_name),
                Kind.CALCULATED,
                point_parent_ids,
            )
            metric_values[metric_name] = {
                "value": value,
                "quantity_id": value_id,
                "delta": point.deltas[metric_name],
                "delta_quantity_id": delta_id,
            }
        sensitivity_response["points"].append({
            "parameter": point.parameter,
            "value": point.value,
            "parameter_quantity_id": sensitivity_parameter_ids[point.parameter][occurrence],
            "outputs": metric_values,
        })

    response = {
        "run_id": run_id,
        "metadata": {
            "scenario_id": simulation_metadata.scenario_id,
            "model_version": simulation_metadata.model_version,
            "seed": simulation_metadata.seed,
            "sample_count": simulation_metadata.sample_count,
            "data_versions": list(simulation_metadata.data_versions),
        },
        "converged": result.monte_carlo.converged,
        "metrics": metric_response,
        "cash_shortfall_probability": {
            "value": result.monte_carlo.shortfall_probability,
            "quantity_id": probability_id,
            "standard_error": result.monte_carlo.shortfall_probability_standard_error,
            "standard_error_quantity_id": probability_error_id,
            "converged": result.monte_carlo.shortfall_probability_converged,
        },
        "sensitivity": sensitivity_response,
    }
    return quantities, output_ids, response


def _unit_for_simulation_metric(metric_name: str) -> str:
    units = {
        "total_revenue": "INR",
        "total_debt_service": "INR",
        "minimum_cash": "INR",
    }
    try:
        return units[metric_name]
    except KeyError as exc:
        raise ValueError(f"Unknown financial simulation metric: {metric_name}.") from exc


_ASSUMPTION_UNITS = {
    "price_per_unit": "INR/count",
    "variable_cost_per_unit": "INR/count",
    "fixed_costs_per_month": "INR/month",
    "loan_principal": "INR",
    "annual_interest_rate": "dimensionless/year",
    "loan_term_months": "month",
    "moratorium_months": "month",
    "subsidy_amount": "INR",
    "subsidy_release_month": "month",
    "target_monthly_units": "count/month",
    "working_capital.inventory_value": "INR",
    "working_capital.accounts_receivable": "INR",
    "working_capital.accounts_payable": "INR",
    "projection.initial_quantity": "count/month",
    "projection.monthly_growth_rate": "dimensionless/month",
    "projection.equity": "INR",
    "projection.disbursed_loan": "INR",
    "projection.capex": "INR",
    "projection.opening_working_capital_need": "INR",
    "projection.days_inventory": "day",
    "projection.days_receivable": "day",
    "projection.days_payable": "day",
    "projection.minimum_dscr": "dimensionless",
    "projection.repayment_capacity_annual_interest_rate": "dimensionless/year",
    "projection.repayment_capacity_months": "month",
}
_PROJECTION_SERIES_UNITS = {
    "seasonality_factors": "dimensionless",
    "price_per_unit_by_month": "INR/count",
    "variable_cost_per_unit_by_month": "INR/count",
    "operating_expenses_by_month": "INR/month",
    "debt_service_by_month": "INR/month",
    "taxes_by_month": "INR/month",
    "other_payments_by_month": "INR/month",
    "subsidy_cash_release_by_month": "INR/month",
    "working_capital_need_by_month": "INR",
}


def _request_has_numeric_financial_inputs(body: CalculateScenarioRequest) -> bool:
    direct_values = (
        body.price_per_unit,
        body.variable_cost_per_unit,
        body.fixed_costs_per_month,
        body.loan_principal,
        body.annual_interest_rate,
        body.loan_term_months,
        body.moratorium_months,
        body.subsidy_amount,
        body.subsidy_release_month,
        body.target_monthly_units,
    )
    return any(value is not None for value in direct_values) or body.working_capital is not None or body.projection is not None


def _financial_input_values(body: CalculateScenarioRequest) -> Dict[str, tuple[float, str]]:
    values: Dict[str, tuple[float, str]] = {}
    for name, unit in _ASSUMPTION_UNITS.items():
        if name.startswith("working_capital."):
            if body.working_capital is None:
                continue
            field_name = name.split(".", 1)[1]
            value = getattr(body.working_capital, field_name)
        elif name.startswith("projection."):
            if body.projection is None:
                continue
            field_name = name.split(".", 1)[1]
            value = getattr(body.projection, field_name)
        else:
            value = getattr(body, name)
        if value is not None:
            values[name] = (float(value), unit)

    if body.projection is not None:
        for field_name, unit in _PROJECTION_SERIES_UNITS.items():
            series = getattr(body.projection, field_name)
            values.update(
                {
                    f"projection.{field_name}.{index + 1}": (float(value), unit)
                    for index, value in enumerate(series)
                }
            )
    return values


def _build_financial_input_quantities(
    *,
    body: CalculateScenarioRequest,
    scenario_id: str,
    execution_id: str,
    owner_id: str,
    geo_id: str,
    resolution: int,
) -> tuple[List[Quantity], Dict[str, str]]:
    values = _financial_input_values(body)
    if not values:
        return [], {}
    today = _current_analysis_date().isoformat()
    quantities: List[Quantity] = []
    quantity_ids: Dict[str, str] = {}
    for name, (value, unit) in values.items():
        quantity_id = str(uuid.uuid4())
        quantity = Quantity(
            id=quantity_id,
            definition_key=f"finance.assumption.{name}",
            value=value,
            unit=unit,
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id=geo_id,
            resolution=resolution,
            as_of=today,
            source_refs=((
                f"user:{owner_id}",
                f"scenario:{scenario_id}/calculation:{execution_id}/input:{name}",
                today,
            ),),
            method_id="explicit_user_input",
            model_version="1",
            parent_ids=(),
            owner_id=owner_id,
        )
        quantities.append(quantity)
        quantity_ids[name] = quantity_id
    return quantities, quantity_ids


def _build_financial_output_quantities(
    *,
    values: Dict[str, tuple[float, str, List[str]]],
    input_quantity_ids: Dict[str, str],
    owner_id: str,
    geo_id: str,
    resolution: int,
) -> tuple[List[Quantity], Dict[str, str]]:
    if not values:
        return [], {}
    today = _current_analysis_date().isoformat()
    quantities: List[Quantity] = []
    output_ids: Dict[str, str] = {}
    for name, (value, unit, input_names) in values.items():
        parent_ids = tuple(
            dict.fromkeys(
                input_quantity_ids[input_name]
                for input_name in input_names
                if input_name in input_quantity_ids
            )
        )
        if not parent_ids:
            continue
        if not isfinite(float(value)):
            raise ValueError(f"Cannot persist non-finite finance result '{name}'.")
        quantity_id = str(uuid.uuid4())
        quantity = Quantity(
            id=quantity_id,
            definition_key=f"finance.result.{name}",
            value=float(value),
            unit=unit,
            kind=Kind.CALCULATED,
            evidence_floor=3,
            geo_unit_id=geo_id,
            resolution=resolution,
            as_of=today,
            source_refs=(),
            method_id=f"arthlens.finance.{name}",
            model_version="arthlens-finance-v1",
            parent_ids=parent_ids,
            owner_id=owner_id,
        )
        quantities.append(quantity)
        output_ids[name] = quantity_id
    return quantities, output_ids


@router.get("/{scenario_id}/report")
def get_scenario_report(
    scenario_id: str,
    format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"),
    current_user: AuthenticatedUser = Depends(require_roles(Role.ENTREPRENEUR)),
) -> Response:
    """
    Generate and download certified Decision Dossier for a user scenario in JSON, CSV, XLSX, or PDF.
    Enforces formula injection protection on CSV and XLSX exports.
    """
    repo = PostgresScenarioRepository()
    scenario = repo.get_scenario_by_id_and_owner(scenario_id, current_user.id)
    if not scenario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found.",
        )

    scenario_data = scenario.get("scenario") or {}
    geo_id = scenario_data.get("geo_id")
    if not geo_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="INSUFFICIENT_DATA: scenario has no selected geographic unit.",
        )
    geo_repo = PostgresGeoUnitRepository()
    unit = geo_repo.get_by_id(geo_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Geographic unit not found.")
    geo_name = unit.name
    lgd_code = unit.lgd_code
    census_code = unit.census_code

    qty_repo = PostgresQuantityRepository()
    saved_calculations = scenario_data.get("calculations") or {}
    scenario_quantity_ids = {
        quantity_id
        for key, quantity_id in saved_calculations.get("quantity_ids", {}).items()
        if not key.startswith(("loan_schedule.month_", "projection.month_"))
    }
    saved_simulation = scenario_data.get("financial_simulation") or {}
    simulation_input_ids = saved_simulation.get("input_quantity_ids") or {}
    scenario_quantity_ids.update((simulation_input_ids.get("projection") or {}).values())
    scenario_quantity_ids.update((simulation_input_ids.get("distributions") or {}).values())
    for quantity_ids in (simulation_input_ids.get("sensitivity") or {}).values():
        scenario_quantity_ids.update(quantity_ids)

    for workflow_key in ("spatial_demand", "accessibility"):
        workflow_result = scenario_data.get(workflow_key) or {}
        scenario_quantity_ids.update((workflow_result.get("input_quantity_ids") or {}).values())
        scenario_quantity_ids.update((workflow_result.get("assumption_quantity_ids") or {}).values())
        scenario_quantity_ids.update((workflow_result.get("quantity_ids") or {}).values())

    def collect_simulation_output_ids(value: Any) -> set[str]:
        collected: set[str] = set()
        if isinstance(value, dict):
            for key, nested in value.items():
                if key.endswith("quantity_id") and isinstance(nested, str):
                    collected.add(nested)
                else:
                    collected.update(collect_simulation_output_ids(nested))
        elif isinstance(value, list):
            for nested in value:
                collected.update(collect_simulation_output_ids(nested))
        return collected

    scenario_quantity_ids.update(collect_simulation_output_ids(saved_simulation))
    raw_quantities = [
        quantity
        for quantity in qty_repo.list_by_geo_unit(geo_id)
        if quantity.owner_id is None or quantity.id in scenario_quantity_ids
    ]
    indicators: List[Dict[str, Any]] = []
    evaluator = DataQualityEvaluator()
    for q in raw_quantities:
        provenance = resolve_quantity_provenance(q, qty_repo)
        assessment = evaluator.evaluate_quantity(
            q,
            q.definition_key,
            geo_id,
            source_id=provenance["source_id"],
            source_version_id=provenance["source_version_id"],
            retrieval_date=provenance["retrieval_date"],
            provenance_complete=provenance["provenance_complete"],
            source_ids=provenance["source_ids"],
        )
        first_source = (
            provenance["lineage_source_provenance"][0]
            if provenance["lineage_source_provenance"]
            else {}
        )
        indicators.append(
            {
                "quantity_id": q.id,
                "definition_key": q.definition_key,
                "value": float(q.value) if q.value is not None else None,
                "unit": q.unit or "",
                "as_of": str(q.as_of or ""),
                "kind": q.kind.value,
                "evidence_floor": q.evidence_floor,
                "quality_status": assessment.primary_status.value,
                "source_name": first_source.get("source_name"),
                "source_id": provenance["source_id"],
                "source_version_id": provenance["source_version_id"],
                "source_provenance": provenance["source_provenance"],
                "lineage_source_provenance": provenance["lineage_source_provenance"],
                "source_refs": list(q.source_refs),
                "parent_ids": list(q.parent_ids),
                "provenance_complete": provenance["provenance_complete"],
            }
        )

    dossier_data: Dict[str, Any] = {
        "geo_id": geo_id,
        "geo_name": geo_name,
        "lgd_code": lgd_code,
        "census_code": census_code,
        "level": unit.level,
        "indicators": indicators,
        "scenario": {
            "id": scenario["id"],
            "name": scenario["name"],
            "capital": scenario.get("scenario", {}).get("capital"),
            "calculations": scenario.get("scenario", {}).get("calculations"),
            "financial_simulation": scenario_data.get("financial_simulation"),
            "spatial_demand": scenario_data.get("spatial_demand"),
            "accessibility": scenario_data.get("accessibility"),
            "policy_evaluation": scenario_data.get("policy_evaluation"),
        },
    }

    if format == "json":
        return Response(
            content=generate_dossier_json(dossier_data),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{scenario_id}.json"'
            },
        )
    elif format == "csv":
        return Response(
            content=generate_dossier_csv(dossier_data),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{scenario_id}.csv"'
            },
        )
    elif format == "xlsx":
        return Response(
            content=generate_dossier_xlsx(dossier_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{scenario_id}.xlsx"'
            },
        )
    else:  # pdf
        return Response(
            content=generate_dossier_pdf(dossier_data),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="arthlens-dossier-{scenario_id}.pdf"'
            },
        )

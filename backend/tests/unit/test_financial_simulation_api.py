from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from backend.arthlens.api import scenarios as scenarios_api
from backend.arthlens.domain.enums import Kind
from fastapi import HTTPException
from pydantic import ValidationError


def _body():
    return scenarios_api.FinancialSimulationRequest.model_validate({
        "projection": {
            "initial_quantity": 100,
            "monthly_growth_rate": 0,
            "seasonality_factors": [1],
            "price_per_unit_by_month": [100],
            "variable_cost_per_unit_by_month": [50],
            "operating_expenses_by_month": [2000],
            "debt_service_by_month": [2000],
            "taxes_by_month": [0],
            "other_payments_by_month": [0],
            "subsidy_cash_release_by_month": [0],
            "working_capital_need_by_month": [0],
            "opening_working_capital_need": 0,
            "equity": 0,
            "disbursed_loan": 0,
            "capex": 0,
            "days_inventory": 0,
            "days_receivable": 0,
            "days_payable": 0,
        },
        "distributions": [{
            "parameter": "price_per_unit_by_month.1",
            "distribution": "UNIFORM",
            "parameters": {"low": 50, "high": 150},
        }],
        "sensitivity_parameter_values": {"price_per_unit_by_month.1": [80, 120]},
        "seed": 23,
        "sample_count": 100,
        "minimum_sample_count": 80,
        "quantile_levels": [0.1, 0.5, 0.9],
        "convergence_tolerances": {
            "total_revenue": 1000,
            "total_debt_service": 0,
            "minimum_cash": 1000,
        },
        "shortfall_probability_tolerance": 0.2,
    })


def _fake_repositories(monkeypatch, *, geo_id="registered-geo"):
    scenario_data = {
        "id": "scenario-1",
        "owner_id": "owner-1",
        "name": "Test enterprise",
        "scenario": {"geo_id": geo_id},
    }
    runs = {}
    quantities = []

    class ScenarioRepository:
        def get_scenario_by_id_and_owner(self, scenario_id, owner_id):
            if scenario_id == scenario_data["id"] and owner_id == scenario_data["owner_id"]:
                return dict(scenario_data)
            return None

        def save_scenario(self, record):
            scenario_data.update(record)
            return record["id"]

        def save_simulation_run(self, record):
            runs[record["id"]] = dict(record)
            return record["id"]

    class GeoRepository:
        def get_by_id(self, requested_geo_id):
            return SimpleNamespace(level=4) if requested_geo_id == geo_id else None

    class Session:
        def commit(self):
            pass

    class QuantityRepository:
        @contextmanager
        def _get_session(self):
            yield Session()

        def save_many(self, items, *, session):
            assert session is not None
            known_ids = {item.id for item in quantities}
            for item in items:
                assert set(item.parent_ids).issubset(known_ids | {other.id for other in items})
            quantities.extend(items)

    monkeypatch.setattr(scenarios_api, "PostgresScenarioRepository", ScenarioRepository)
    monkeypatch.setattr(scenarios_api, "PostgresGeoUnitRepository", GeoRepository)
    monkeypatch.setattr(scenarios_api, "PostgresQuantityRepository", QuantityRepository)
    return scenario_data, runs, quantities


def test_simulation_endpoint_persists_run_scenario_and_ledger_lineage(monkeypatch):
    scenario, runs, quantities = _fake_repositories(monkeypatch)

    result = scenarios_api.simulate_scenario(
        "scenario-1",
        _body(),
        current_user=SimpleNamespace(id="owner-1"),
    )

    assert result["status"] == "COMPLETED"
    assert result["metadata"]["seed"] == 23
    assert result["cash_shortfall_probability"]["quantity_id"] in {item.id for item in quantities}
    assert scenario["scenario"]["financial_simulation"]["run_id"] == result["id"]
    assert runs[result["id"]]["status"] == "COMPLETED"
    assert runs[result["id"]]["outputs_references"]["quantity_ids"]

    by_id = {item.id: item for item in quantities}
    simulated = [item for item in quantities if item.kind == Kind.SIMULATED]
    assumptions = [item for item in quantities if item.kind == Kind.USER_ASSUMED]
    assert simulated and assumptions
    assert all(item.simulation_meta is not None for item in simulated)
    assert all(item.parent_ids and set(item.parent_ids) <= by_id.keys() for item in simulated)
    assert all(item.owner_id == "owner-1" for item in quantities)


def test_simulation_endpoint_returns_insufficient_data_without_registered_geo(monkeypatch):
    _fake_repositories(monkeypatch, geo_id=None)

    with pytest.raises(HTTPException) as error:
        scenarios_api.simulate_scenario(
            "scenario-1",
            _body(),
            current_user=SimpleNamespace(id="owner-1"),
        )

    assert error.value.status_code == 422
    assert "INSUFFICIENT_DATA" in error.value.detail


def test_simulation_contract_requires_explicit_seed_counts_and_model_inputs():
    with pytest.raises(ValidationError):
        scenarios_api.FinancialSimulationRequest.model_validate({
            "projection": {},
            "distributions": [],
            "sensitivity_parameter_values": {},
        })

    payload = _body().model_dump(mode="python")
    payload["seed"] = True
    with pytest.raises(ValidationError, match="Boolean values"):
        scenarios_api.FinancialSimulationRequest.model_validate(payload)

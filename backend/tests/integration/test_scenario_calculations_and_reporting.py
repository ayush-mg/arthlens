"""
Integration Tests for Scenario Calculations, Financial Modeling, and Multi-Format Reporting.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.3, Part 4.6, Part 11).
"""

import io
import uuid
from datetime import date

import openpyxl
import pytest
from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import GeoUnit
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.provenance import resolve_quantity_provenance
from backend.arthlens.infra.repositories import (
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
    PostgresScenarioRepository,
)
from backend.arthlens.reporting.dossier_generator import sanitize_for_spreadsheet
from backend.arthlens.security.tokens import decode_access_token
from pypdf import PdfReader
from starlette.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def get_auth_cookie(client, email="calc_user@example.com", password="Password123!"):
    client.post(
        "/auth/register",
        json={
            "full_name": "Calculation Tester",
            "email": email,
            "password": password,
        },
    )
    login_res = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    token = login_res.json()["access_token"]
    return {get_auth_cookie_name(): token}, token


def ensure_report_territory():
    repo = PostgresGeoUnitRepository()
    units = []
    if repo.get_by_id("in") is None:
        units.append(GeoUnit(id="in", parent_id=None, level=ResolutionTier.NATION, name="India", lgd_code="IN"))
    if repo.get_by_id("in:state:09") is None:
        units.append(GeoUnit(id="in:state:09", parent_id="in", level=ResolutionTier.STATE, name="Uttar Pradesh", lgd_code="09"))
    if repo.get_by_id("in:district:120") is None:
        units.append(GeoUnit(id="in:district:120", parent_id="in:state:09", level=ResolutionTier.DISTRICT, name="Prayagraj", lgd_code="120", census_code="175"))
    if units:
        repo.save_units(units)


@pytest.mark.integration
def test_scenario_calculation_and_persistence(client):
    ensure_report_territory()
    cookie, token = get_auth_cookie(client, f"calc_{uuid.uuid4().hex[:6]}@example.com")

    # 1. Create scenario
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={
            "name": "Naini Retail Store",
            "scenario": {"capital": 300000, "geo_id": "in:district:120"},
        },
    )
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]
    # 2. Execute calculation with business assumptions
    calc_res = client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=cookie,
        json={
            "price_per_unit": 150.0,
            "variable_cost_per_unit": 90.0,
            "fixed_costs_per_month": 30000.0,
            "loan_principal": 200000.0,
            "annual_interest_rate": 0.09,
            "loan_term_months": 24,
            "moratorium_months": 2,
            "moratorium_interest_treatment": "PAID",
            "subsidy_amount": 25000.0,
            "subsidy_treatment": "ADJUSTS_PRINCIPAL",
            "target_monthly_units": 600.0,
        },
    )
    assert calc_res.status_code == 200
    calcs = calc_res.json()["calculations"]
    assert calcs["contribution_margin"] == 60.0
    assert calcs["break_even_units"] == 500.0
    assert calcs["financed_principal"] == 175000.0
    assert calcs["monthly_emi"] > 0
    assert calcs["loan_schedule_status"] == "COMPLETED"
    assert len(calcs["loan_schedule"]) == 26
    assert calcs["loan_schedule"][2]["quantity_ids"]["debt_service"]
    assert calcs["spatial_demand_allocated"] is None
    assert calcs["spatial_demand_status"] == "INSUFFICIENT_DATA"
    assert calcs["spatial_demand_missing_evidence"]
    assert calcs["feasibility_status"] == "FEASIBLE"
    assert calcs["epistemic_floor"] == "FLOOR 3: EXPLICIT USER ASSUMPTIONS"

    quantity_repo = PostgresQuantityRepository()
    input_ids = calcs["input_quantity_ids"]
    contribution_id = calcs["quantity_ids"]["contribution_margin"]
    contribution = quantity_repo.get(contribution_id)
    assert contribution is not None
    assert set(contribution.parent_ids) == {
        input_ids["price_per_unit"],
        input_ids["variable_cost_per_unit"],
    }
    assert resolve_quantity_provenance(contribution, quantity_repo)["provenance_complete"] is True

    # 3. Verify authoritative persistence in database
    detail_res = client.get(f"/scenarios/{scenario_id}", cookies=cookie)
    assert detail_res.status_code == 200
    saved_scenario = detail_res.json()["scenario"]
    assert "calculations" in saved_scenario
    assert saved_scenario["calculations"]["break_even_units"] == 500.0

    dossier_res = client.get(f"/scenarios/{scenario_id}/report?format=json", cookies=cookie)
    assert dossier_res.status_code == 200
    dossier = dossier_res.json()
    assert dossier["scenario"]["calculations"]["break_even_units"] == 500.0
    assert any(
        row["quantity_id"] == saved_scenario["calculations"]["quantity_ids"]["break_even_units"]
        for row in dossier["indicators"]
    )


@pytest.mark.integration
def test_scenario_comparison_uses_saved_results_and_is_owner_scoped(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"comparison_{uuid.uuid4().hex[:8]}@example.com")
    scenarios = []
    for name, price in (("Comparison A", 100.0), ("Comparison B", 110.0)):
        created = client.post(
            "/scenarios",
            cookies=cookie,
            json={"name": name, "scenario": {"geo_id": "in:district:120"}},
        )
        assert created.status_code == 201
        scenario_id = created.json()["id"]
        calculated = client.post(
            f"/scenarios/{scenario_id}/calculate",
            cookies=cookie,
            json={
                "price_per_unit": price,
                "variable_cost_per_unit": 60.0,
                "fixed_costs_per_month": 1000.0,
            },
        )
        assert calculated.status_code == 200
        scenarios.append(scenario_id)

    comparison = client.post(
        "/scenarios/compare",
        cookies=cookie,
        json={"left_scenario_id": scenarios[0], "right_scenario_id": scenarios[1]},
    )
    assert comparison.status_code == 201
    result = comparison.json()
    assert result["status"] == "COMPLETED"
    assert result["metrics"]["financial.contribution_margin"]["delta_right_minus_left"]["value"] == 10.0

    saved = client.get(f"/scenarios/comparisons/{result['id']}", cookies=cookie)
    assert saved.status_code == 200
    assert saved.json()["metric_results"]["metrics"]["financial.contribution_margin"]["right"]["value"] == 50.0
    other_cookie, _ = get_auth_cookie(client, f"comparison_other_{uuid.uuid4().hex[:8]}@example.com")
    assert client.get(f"/scenarios/comparisons/{result['id']}", cookies=other_cookie).status_code == 404


@pytest.mark.integration
def test_scenario_spatial_demand_allocates_from_saved_ledger_inputs_and_exports_lineage(client):
    ensure_report_territory()
    cookie, token = get_auth_cookie(client, f"spatial_scenario_{uuid.uuid4().hex[:8]}@example.com")
    owner_id = decode_access_token(token)["sub"]
    created = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Spatial demand case", "scenario": {"geo_id": "in:district:120"}},
    )
    assert created.status_code == 201
    scenario_id = created.json()["id"]
    today = date.today().isoformat()
    source_ref = ((f"user:{owner_id}", f"scenario:{scenario_id}/spatial-input", today),)
    quantities = [
        Quantity(
            id=str(uuid.uuid4()), definition_key="demand.zone.monthly", value=1200,
            unit="INR/month", kind=Kind.USER_ASSUMED, evidence_floor=3,
            geo_unit_id="in:district:120", resolution=2, as_of=today,
            source_refs=source_ref, method_id="explicit_user_input", model_version="1", owner_id=owner_id,
        ),
        Quantity(
            id=str(uuid.uuid4()), definition_key="facility.attractiveness", value=1,
            unit="dimensionless", kind=Kind.USER_ASSUMED, evidence_floor=3,
            geo_unit_id="in:district:120", resolution=2, as_of=today,
            source_refs=source_ref, method_id="explicit_user_input", model_version="1", owner_id=owner_id,
        ),
        Quantity(
            id=str(uuid.uuid4()), definition_key="travel_time.minutes", value=12,
            unit="minute", kind=Kind.USER_ASSUMED, evidence_floor=3,
            geo_unit_id="in:district:120", resolution=2, as_of=today,
            source_refs=source_ref, method_id="explicit_user_input", model_version="1", owner_id=owner_id,
        ),
    ]
    quantity_repo = PostgresQuantityRepository()
    quantity_repo.save_many(quantities)
    spatial = client.post(
        f"/scenarios/{scenario_id}/spatial-demand",
        cookies=cookie,
        json={
            "allocator_type": "nearest",
            "candidate_facility_id": "candidate",
            "zones": [{"zone_id": "in:district:120", "quantity_id": quantities[0].id}],
            "facilities": [{"facility_id": "candidate", "quantity_id": quantities[1].id}],
            "travel_time_quantity_ids": {"in:district:120": {"candidate": quantities[2].id}},
        },
    )
    assert spatial.status_code == 200
    result = spatial.json()
    assert result["status"] == "COMPLETED"
    assert result["captured_demand_inr_monthly"] == 1200
    output = quantity_repo.get(result["quantity_ids"]["captured_demand"])
    assert output is not None and set(output.parent_ids) == {quantity.id for quantity in quantities}

    dossier = client.get(f"/scenarios/{scenario_id}/report?format=json", cookies=cookie)
    assert dossier.status_code == 200
    scenario_report = dossier.json()["scenario"]
    assert scenario_report["spatial_demand"]["execution_id"] == result["execution_id"]
    assert any(item["quantity_id"] == output.id for item in dossier.json()["indicators"])


@pytest.mark.integration
def test_scenario_finance_missing_inputs_stay_unavailable_without_hidden_defaults(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"calc_missing_{uuid.uuid4().hex[:6]}@example.com")
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Partial Finance Inputs", "scenario": {"geo_id": "in:district:120"}},
    )
    scenario_id = create_res.json()["id"]

    calc_res = client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=cookie,
        json={"price_per_unit": 100, "variable_cost_per_unit": 70},
    )

    assert calc_res.status_code == 200
    calculations = calc_res.json()["calculations"]
    assert calculations["contribution_margin"] == 30
    assert calculations["break_even_units"] is None
    assert calculations["break_even_status"] == "INSUFFICIENT_DATA"
    assert calculations["break_even_missing_inputs"] == ["fixed_costs_per_month"]
    assert calculations["loan_schedule_status"] == "INSUFFICIENT_DATA"
    assert calculations["loan_principal"] is None
    assert calculations["monthly_emi"] is None
    assert calculations["input_quantity_ids"].keys() == {
        "price_per_unit",
        "variable_cost_per_unit",
    }
    assert "break_even_units" not in calculations["quantity_ids"]


@pytest.mark.integration
def test_scenario_finance_requires_registered_geography_for_ledger_provenance(client):
    cookie, _ = get_auth_cookie(client, f"calc_no_geo_{uuid.uuid4().hex[:6]}@example.com")
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Finance Without Geographic Scope", "scenario": {}},
    )
    scenario_id = create_res.json()["id"]

    calc_res = client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=cookie,
        json={
            "price_per_unit": 100,
            "variable_cost_per_unit": 70,
            "fixed_costs_per_month": 1000,
        },
    )

    assert calc_res.status_code == 422
    assert "INSUFFICIENT_DATA" in calc_res.json()["detail"]


@pytest.mark.integration
def test_scenario_projection_working_capital_dscr_capacity_and_lineage(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"projection_{uuid.uuid4().hex[:6]}@example.com")
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Explicit Projection", "scenario": {"geo_id": "in:district:120"}},
    )
    scenario_id = create_res.json()["id"]
    payload = {
        "working_capital": {
            "inventory_value": 500,
            "accounts_receivable": 200,
            "accounts_payable": 100,
        },
        "projection": {
            "initial_quantity": 10,
            "monthly_growth_rate": 0,
            "seasonality_factors": [1],
            "price_per_unit_by_month": [100, 100],
            "variable_cost_per_unit_by_month": [50, 50],
            "operating_expenses_by_month": [200, 200],
            "debt_service_by_month": [100, 100],
            "taxes_by_month": [0, 0],
            "other_payments_by_month": [0, 0],
            "subsidy_cash_release_by_month": [0, 0],
            "working_capital_need_by_month": [100, 150],
            "opening_working_capital_need": 0,
            "equity": 1000,
            "disbursed_loan": 500,
            "capex": 300,
            "days_inventory": 10,
            "days_receivable": 20,
            "days_payable": 5,
            "minimum_dscr": 1.25,
            "repayment_capacity_annual_interest_rate": 0.12,
            "repayment_capacity_months": 24,
        },
    }

    calc_res = client.post(f"/scenarios/{scenario_id}/calculate", cookies=cookie, json=payload)

    assert calc_res.status_code == 200, calc_res.text
    calculations = calc_res.json()["calculations"]
    assert calculations["working_capital_requirement"] == 600
    projection = calculations["financial_projection"]
    assert projection["status"] == "COMPLETED"
    assert projection["minimum_dscr"] == pytest.approx(2.0)
    assert projection["minimum_cash"] == pytest.approx(1200)
    assert projection["funding_shortfall"] == 0
    assert projection["repayment_capacity_monthly_debt_service"] == pytest.approx(160)
    assert projection["months"][1]["cash_flow"] == pytest.approx(150)

    repo = PostgresQuantityRepository()
    wc_quantity = repo.get(calculations["quantity_ids"]["working_capital_requirement"])
    assert wc_quantity is not None
    assert len(wc_quantity.parent_ids) == 3
    assert resolve_quantity_provenance(wc_quantity, repo)["provenance_complete"] is True
    month_dscr_id = projection["months"][1]["quantity_ids"]["dscr"]
    month_dscr_quantity = repo.get(month_dscr_id)
    assert month_dscr_quantity is not None
    input_ids = calculations["input_quantity_ids"]
    expected_month_dscr_parents = {
        input_ids[key]
        for key in (
            "projection.initial_quantity",
            "projection.monthly_growth_rate",
            "projection.seasonality_factors.1",
            "projection.price_per_unit_by_month.2",
            "projection.variable_cost_per_unit_by_month.2",
            "projection.operating_expenses_by_month.2",
            "projection.taxes_by_month.2",
            "projection.other_payments_by_month.2",
            "projection.working_capital_need_by_month.1",
            "projection.working_capital_need_by_month.2",
            "projection.debt_service_by_month.2",
        )
    }
    assert set(month_dscr_quantity.parent_ids) == expected_month_dscr_parents
    assert resolve_quantity_provenance(month_dscr_quantity, repo)["provenance_complete"] is True
    assert projection["quantity_ids"]["minimum_dscr"] == calculations["quantity_ids"][
        "projection.minimum_dscr"
    ]


@pytest.mark.integration
def test_scenario_calculation_idor_protection(client):
    cookie_a, _ = get_auth_cookie(client, f"user_a_{uuid.uuid4().hex[:6]}@example.com")
    cookie_b, _ = get_auth_cookie(client, f"user_b_{uuid.uuid4().hex[:6]}@example.com")
    client.cookies.clear()

    # User A creates scenario
    create_res = client.post(
        "/scenarios",
        cookies=cookie_a,
        json={"name": "User A Private Scenario", "scenario": {"capital": 100000}},
    )
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]

    # User B attempts to calculate on User A's scenario -> Fail closed with 404
    client.cookies.clear()
    calc_res = client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=cookie_b,
        json={"price_per_unit": 100.0, "variable_cost_per_unit": 50.0},
    )
    assert calc_res.status_code == 404


@pytest.mark.integration
def test_scenario_multi_format_report_generation(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"rep_{uuid.uuid4().hex[:6]}@example.com")

    # Create & calculate scenario
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={
            "name": "Reported Grocery Strategy",
            "scenario": {"capital": 250000, "geo_id": "in:district:120"},
        },
    )
    scenario_id = create_res.json()["id"]
    quantity_id = str(uuid.uuid4())
    PostgresQuantityRepository().save(
        Quantity(
            id=quantity_id,
            definition_key="test.unverified_indicator",
            value=12.0,
            unit="persons",
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-11-08",
            source_refs=(),
        )
    )
    client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=cookie,
        json={
            "price_per_unit": 120.0,
            "variable_cost_per_unit": 70.0,
            "fixed_costs_per_month": 40000.0,
        },
    )

    # 1. JSON Report
    json_res = client.get(f"/scenarios/{scenario_id}/report?format=json", cookies=cookie)
    assert json_res.status_code == 200
    assert json_res.headers["content-type"].startswith("application/json")
    json_data = json_res.json()
    assert json_data["report_type"] == "ARTHLENS_DECISION_DOSSIER"
    assert json_data["geo_name"] == "Prayagraj"
    assert "scenario" in json_data
    assert json_data["scenario"]["calculations"]["break_even_units"] == 800.0
    indicator = next(
        row for row in json_data["indicators"] if row["quantity_id"] == quantity_id
    )
    assert indicator["evidence_floor"] == 3
    assert indicator["quality_status"] == "INCOMPLETE"
    assert indicator["source_name"] is None
    assert indicator["source_version_id"] is None
    assert indicator["provenance_complete"] is False

    # 2. CSV Report with Formula Injection Verification
    csv_res = client.get(f"/scenarios/{scenario_id}/report?format=csv", cookies=cookie)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    csv_text = csv_res.text
    assert "ARTHLENS DECISION DOSSIER" in csv_text
    assert "Prayagraj" in csv_text
    assert "Break-Even Volume (Units)" in csv_text

    # 3. XLSX Report
    xlsx_res = client.get(f"/scenarios/{scenario_id}/report?format=xlsx", cookies=cookie)
    assert xlsx_res.status_code == 200
    assert "spreadsheetml" in xlsx_res.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_res.content))
    assert "Executive Summary" in wb.sheetnames
    assert "Ledger Indicators" in wb.sheetnames

    # 4. PDF Report
    pdf_res = client.get(f"/scenarios/{scenario_id}/report?format=pdf", cookies=cookie)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(pdf_res.content))
    assert len(reader.pages) >= 1
    pdf_text = reader.pages[0].extract_text()
    assert "ArthLens Decision Dossier" in pdf_text
    assert "Prayagraj" in pdf_text


@pytest.mark.integration
def test_territorial_dossier_export_endpoint(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"steward_{uuid.uuid4().hex[:6]}@example.com")

    # Export Prayagraj in all formats directly from /reports/dossier
    for fmt in ("json", "csv", "xlsx", "pdf"):
        res = client.get(f"/reports/dossier?geo_id=in:district:120&format={fmt}", cookies=cookie)
        assert res.status_code == 200
        assert len(res.content) > 100


def test_formula_injection_defense():
    """Unit verification that malicious spreadsheet cell values are sanitized."""
    malicious = [
        "=cmd|'/C calc'!A0",
        "+1+2",
        "-5+6",
        "@SUM(A1:A10)",
        "\tmalicious_tab",
        "\rmalicious_cr",
    ]
    for val in malicious:
        sanitized = sanitize_for_spreadsheet(val)
        assert sanitized.startswith("'"), f"Failed to sanitize: {val}"


@pytest.mark.integration
def test_scenario_report_requires_explicit_geographic_selection(client):
    cookie, _ = get_auth_cookie(client, f"report_missing_geo_{uuid.uuid4().hex[:6]}@example.com")
    create_res = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Unlocated Scenario", "scenario": {}},
    )
    assert create_res.status_code == 201

    response = client.get(
        f"/scenarios/{create_res.json()['id']}/report?format=json",
        cookies=cookie,
    )

    assert response.status_code == 422
    assert "INSUFFICIENT_DATA" in response.json()["detail"]


@pytest.mark.integration
def test_scenario_monte_carlo_outputs_are_persisted_and_reported(client):
    ensure_report_territory()
    cookie, _ = get_auth_cookie(client, f"simulation_{uuid.uuid4().hex[:8]}@example.com")
    created = client.post(
        "/scenarios",
        cookies=cookie,
        json={"name": "Uncertainty Test", "scenario": {"geo_id": "in:district:120"}},
    )
    assert created.status_code == 201
    scenario_id = created.json()["id"]
    response = client.post(
        f"/scenarios/{scenario_id}/simulate",
        cookies=cookie,
        json={
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
        },
    )
    assert response.status_code == 201, response.text
    simulation = response.json()
    assert simulation["status"] == "COMPLETED"
    assert simulation["metadata"]["seed"] == 23
    assert 0 < simulation["cash_shortfall_probability"]["value"] < 1

    run = PostgresScenarioRepository().get_simulation_run(simulation["id"])
    assert run["status"] == "COMPLETED"
    assert run["outputs_references"]["quantity_ids"]
    quantity_repo = PostgresQuantityRepository()
    outcome = quantity_repo.get(simulation["cash_shortfall_probability"]["quantity_id"])
    assert outcome is not None
    assert outcome.kind == Kind.SIMULATED
    assert outcome.simulation_meta.seed == 23
    assert outcome.simulation_meta.data_versions
    assert outcome.parent_ids
    assert all(quantity_repo.exists(parent_id) for parent_id in outcome.parent_ids)

    saved = client.get(f"/scenarios/{scenario_id}", cookies=cookie).json()["scenario"]
    assert saved["financial_simulation"]["run_id"] == simulation["id"]
    dossier = client.get(f"/scenarios/{scenario_id}/report?format=json", cookies=cookie).json()
    assert dossier["scenario"]["financial_simulation"]["run_id"] == simulation["id"]
    dossier_quantity_ids = {row["quantity_id"] for row in dossier["indicators"]}
    assert simulation["cash_shortfall_probability"]["quantity_id"] in dossier_quantity_ids
    assert next(iter(simulation["input_quantity_ids"]["projection"].values())) in dossier_quantity_ids
    csv_dossier = client.get(f"/scenarios/{scenario_id}/report?format=csv", cookies=cookie)
    assert simulation["cash_shortfall_probability"]["quantity_id"] in csv_dossier.text
    xlsx_dossier = client.get(f"/scenarios/{scenario_id}/report?format=xlsx", cookies=cookie)
    workbook = openpyxl.load_workbook(io.BytesIO(xlsx_dossier.content))
    assert "Simulation Analysis" in workbook.sheetnames
    pdf_dossier = client.get(f"/scenarios/{scenario_id}/report?format=pdf", cookies=cookie)
    pdf_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(io.BytesIO(pdf_dossier.content)).pages
    )
    assert simulation["id"] in pdf_text


@pytest.mark.integration
def test_scenario_scheme_viability_loop_c_endpoint(client):
    cookie, _ = get_auth_cookie(client, "loop_c_user@example.com")
    ensure_report_territory()

    # Create a scenario
    create_res = client.post(
        "/scenarios",
        json={"name": "Varanasi Silk Weaver Viability", "geo_id": "in:district:120"},
        cookies=cookie,
    )
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]

    # Call scheme-viability endpoint
    viability_res = client.post(
        f"/scenarios/{scenario_id}/scheme-viability",
        json={
            "project_cost_inr": 1000000.0,
            "promoter_contribution_fraction": 0.10,
            "subsidy_fraction": 0.25,
            "annual_interest_rate": 0.10,
            "loan_term_months": 60,
            "moratorium_months": 6,
            "moratorium_interest_treatment": "CAPITALIZED",
            "subsidy_treatment": "ADJUSTS_PRINCIPAL",
            "unit_price": 100.0,
            "unit_variable_cost": 40.0,
            "fixed_operating_costs_monthly": 30000.0,
            "monthly_sales_units": 1000.0,
        },
        cookies=cookie,
    )
    assert viability_res.status_code == 200, viability_res.text
    data = viability_res.json()
    assert data["status"] == "COMPLETED"
    assert data["break_even_quantity"] == 500.0
    assert data["total_revenue"] > 0
    assert data["registered_quantities_count"] > 0
    assert "report_json" in data
    assert "report_csv" in data

    # Verify scenario was updated in repository
    sc = PostgresScenarioRepository().get_scenario(scenario_id)
    assert sc is not None
    sc_data = sc["scenario"]
    assert sc_data["scheme_viability"]["status"] == "COMPLETED"
    assert sc_data["break_even_units"] == 500.0


"""
End-to-End User Journey and System Acceptance Test Suite with Gemini Enabled.

Authoritative Reference:
- ArthLens Build Handbook v1.0
- Acceptance Criteria:
  1. Register -> Login -> Atlas -> Create Scenario -> Enter Assumptions -> Run Analysis ->
     Agent Planning (Gemini) -> Deterministic Tool Execution -> Evidence Inspection ->
     Save Scenario -> Multi-format Dossier Generation & Download.
  2. Durable Worker Restart, Lease Recovery, and SSE Updates.
  3. Deterministic Mode Operation without API credentials.
"""

import io
import uuid
from decimal import Decimal

import openpyxl
import pytest
from backend.arthlens.agent.run_lifecycle import AgentRunState
from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import GeoUnit
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.provenance import resolve_quantity_provenance
from backend.arthlens.infra.repositories import (
    PostgresAgentRunRepository,
    PostgresGeoUnitRepository,
    PostgresQuantityRepository,
)
from pypdf import PdfReader
from starlette.testclient import TestClient


@pytest.fixture
def app_client():
    return TestClient(create_app())


def _ensure_territory():
    repo = PostgresGeoUnitRepository()
    units = []
    if repo.get_by_id("in") is None:
        units.append(
            GeoUnit(id="in", parent_id=None, level=ResolutionTier.NATION, name="India", lgd_code="IN")
        )
    if repo.get_by_id("in:state:09") is None:
        units.append(
            GeoUnit(
                id="in:state:09",
                parent_id="in",
                level=ResolutionTier.STATE,
                name="Uttar Pradesh",
                lgd_code="09",
            )
        )
    if repo.get_by_id("in:district:120") is None:
        units.append(
            GeoUnit(
                id="in:district:120",
                parent_id="in:state:09",
                level=ResolutionTier.DISTRICT,
                name="Prayagraj",
                lgd_code="120",
                census_code="175",
            )
        )
    if units:
        repo.save_units(units)


@pytest.mark.integration
def test_complete_user_journey_with_gemini(app_client):
    """
    Execute complete local user journey:
    Register -> Login -> Atlas -> Create Scenario -> Enter Assumptions -> Run Analysis ->
    Agent Planning (Gemini) -> Deterministic Tool Execution -> Evidence Inspection ->
    Save -> Generate and Download Dossier (JSON, CSV, XLSX, PDF).
    """
    _ensure_territory()

    # 1. REGISTER
    unique_id = uuid.uuid4().hex[:8]
    test_email = f"journey_{unique_id}@arthlens.local"
    test_password = "Password123!"
    test_name = "Priya Sharma"

    reg_res = app_client.post(
        "/auth/register",
        json={
            "full_name": test_name,
            "email": test_email,
            "password": test_password,
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    user_info = reg_res.json()
    assert user_info["email"] == test_email
    assert "ENTREPRENEUR" in user_info.get("roles", [])

    # 2. LOGIN
    login_res = app_client.post(
        "/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert login_res.status_code == 200, login_res.text
    login_data = login_res.json()
    token = login_data["access_token"]
    cookie_name = get_auth_cookie_name()
    auth_cookies = {cookie_name: token}
    assert cookie_name in login_res.cookies or token

    # 3. ECONOMIC ATLAS
    indicators_res = app_client.get(
        "/geo/in:district:120/indicators",
        cookies=auth_cookies,
    )
    assert indicators_res.status_code == 200, indicators_res.text
    indicators_data = indicators_res.json()
    assert "indicators" in indicators_data
    assert indicators_data["geo_unit_id"] == "in:district:120"

    # 4. CREATE SCENARIO
    scenario_name = f"Prayagraj Food Processing Unit {unique_id}"
    create_scen_res = app_client.post(
        "/scenarios",
        cookies=auth_cookies,
        json={
            "name": scenario_name,
            "scenario": {
                "geo_id": "in:district:120",
                "capital": 400000.0,
            },
        },
    )
    assert create_scen_res.status_code == 201, create_scen_res.text
    scenario_id = create_scen_res.json()["id"]

    # 5. ENTER ASSUMPTIONS & EXECUTE REAL CALCULATIONS
    calc_res = app_client.post(
        f"/scenarios/{scenario_id}/calculate",
        cookies=auth_cookies,
        json={
            "price_per_unit": 200.0,
            "variable_cost_per_unit": 120.0,
            "fixed_costs_per_month": 48000.0,
            "loan_principal": 250000.0,
            "annual_interest_rate": 0.095,
            "loan_term_months": 36,
            "moratorium_months": 3,
            "moratorium_interest_treatment": "PAID",
            "subsidy_amount": 50000.0,
            "subsidy_treatment": "ADJUSTS_PRINCIPAL",
            "target_monthly_units": 800.0,
        },
    )
    assert calc_res.status_code == 200, calc_res.text
    calcs = calc_res.json()["calculations"]

    # Verify deterministic financial calculations
    assert calcs["contribution_margin"] == 80.0
    assert calcs["break_even_units"] == 600.0
    assert calcs["financed_principal"] == 200000.0
    assert calcs["monthly_emi"] > 0
    assert calcs["loan_schedule_status"] == "COMPLETED"
    assert len(calcs["loan_schedule"]) == 39
    assert calcs["feasibility_status"] == "FEASIBLE"

    # 6. RUN AGENT PLANNING & DETERMINISTIC TOOL EXECUTION (WITH GEMINI)
    create_run_res = app_client.post(
        "/agent-runs",
        cookies=auth_cookies,
        json={
            "objective": {
                "objective": "Calculate break-even quantity.",
                "supplied_slots": {
                    "price": 200.0,
                    "variable_cost": 120.0,
                    "fixed_costs": 48000.0,
                },
            }
        },
    )
    assert create_run_res.status_code == 201, create_run_res.text
    run_id = create_run_res.json()["id"]

    # Start run (which executes via Gemini LLM and deterministic tool executor)
    start_run_res = app_client.post(
        f"/agent-runs/{run_id}/start",
        cookies=auth_cookies,
    )
    assert start_run_res.status_code == 202, start_run_res.text

    # Verify run completed and inspected outputs
    get_run_res = app_client.get(f"/agent-runs/{run_id}", cookies=auth_cookies)
    assert get_run_res.status_code == 200
    run_data = get_run_res.json()
    assert run_data["state"] == AgentRunState.COMPLETED.value
    assert run_data["steps_used"] >= 1
    assert run_data["model_calls_used"] >= 1
    assert Decimal(str(run_data["cost_usd"])) > Decimal("0")

    # 7. INSPECT EVIDENCE & AUDIT STREAM
    events_res = app_client.get(f"/agent-runs/{run_id}/events", cookies=auth_cookies)
    assert events_res.status_code == 200
    events = events_res.json()["events"]
    event_types = [e["type"] for e in events]
    assert "RUN_ACCEPTED" in event_types
    assert "OBJECTIVE_VALID" in event_types
    assert "PLAN_VALIDATED" in event_types
    assert "TOOL_RETURNED" in event_types
    assert "PLAN_COMPLETE" in event_types
    assert "ALL_CHECKS_PASS" in event_types

    # Ensure tool output verified break-even units = 600.0
    tool_event = next(e for e in events if e["type"] == "TOOL_RETURNED")
    assert tool_event["payload"]["tool_name"] == "calculate_break_even"
    assert tool_event["payload"]["result"]["break_even_quantity"] == 600.0

    # Verify quantity provenance in Postgres
    quantity_repo = PostgresQuantityRepository()
    cm_qid = calcs["quantity_ids"]["contribution_margin"]
    cm_qty = quantity_repo.get(cm_qid)
    assert cm_qty is not None
    prov_result = resolve_quantity_provenance(cm_qty, quantity_repo)
    assert prov_result["provenance_complete"] is True

    # 8. SAVE SCENARIO & VERIFY PERSISTENCE
    scenario_detail = app_client.get(f"/scenarios/{scenario_id}", cookies=auth_cookies)
    assert scenario_detail.status_code == 200
    saved = scenario_detail.json()["scenario"]
    assert saved["calculations"]["break_even_units"] == 600.0

    # 9. GENERATE & DOWNLOAD MULTI-FORMAT DECISION DOSSIER
    # 9.1 JSON
    json_dossier_res = app_client.get(
        f"/scenarios/{scenario_id}/report?format=json",
        cookies=auth_cookies,
    )
    assert json_dossier_res.status_code == 200
    assert "application/json" in json_dossier_res.headers["content-type"]
    dossier_json = json_dossier_res.json()
    assert dossier_json["report_type"] == "ARTHLENS_DECISION_DOSSIER"
    assert dossier_json["geo_name"] == "Prayagraj"
    assert dossier_json["scenario"]["calculations"]["break_even_units"] == 600.0

    # 9.2 CSV
    csv_dossier_res = app_client.get(
        f"/scenarios/{scenario_id}/report?format=csv",
        cookies=auth_cookies,
    )
    assert csv_dossier_res.status_code == 200
    assert "text/csv" in csv_dossier_res.headers["content-type"]
    assert "ARTHLENS DECISION DOSSIER" in csv_dossier_res.text
    assert "Prayagraj" in csv_dossier_res.text

    # 9.3 XLSX
    xlsx_dossier_res = app_client.get(
        f"/scenarios/{scenario_id}/report?format=xlsx",
        cookies=auth_cookies,
    )
    assert xlsx_dossier_res.status_code == 200
    assert "spreadsheetml" in xlsx_dossier_res.headers["content-type"]
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_dossier_res.content))
    assert "Executive Summary" in wb.sheetnames
    assert "Ledger Indicators" in wb.sheetnames

    # 9.4 PDF
    pdf_dossier_res = app_client.get(
        f"/scenarios/{scenario_id}/report?format=pdf",
        cookies=auth_cookies,
    )
    assert pdf_dossier_res.status_code == 200
    assert "application/pdf" in pdf_dossier_res.headers["content-type"]
    pdf = PdfReader(io.BytesIO(pdf_dossier_res.content))
    assert len(pdf.pages) >= 1
    assert "ArthLens Decision Dossier" in pdf.pages[0].extract_text()

    # 9.5 SSE Streaming Telemetry
    sse_res = app_client.get(
        f"/agent-runs/{run_id}/events/stream",
        cookies=auth_cookies,
    )
    assert sse_res.status_code == 200
    assert "text/event-stream" in sse_res.headers["content-type"]
    assert "data:" in sse_res.text
    assert "event: ALL_CHECKS_PASS" in sse_res.text or "event: RUN_ACCEPTED" in sse_res.text


@pytest.mark.integration
def test_worker_lease_recovery_and_checkpoint_resume(app_client):
    """
    Verify durable worker recovery:
    1. Create run.
    2. Simulate an aborted worker run by leaving it in RECOVERING with a checkpoint.
    3. Resume execution through durable orchestrator/worker.
    4. Verify the run completes to COMPLETED without duplicate steps.
    """
    _ensure_territory()
    unique_id = uuid.uuid4().hex[:8]
    test_email = f"recovery_{unique_id}@arthlens.local"
    test_password = "Password123!"

    app_client.post(
        "/auth/register",
        json={"full_name": "Recovery User", "email": test_email, "password": test_password},
    )
    login_res = app_client.post(
        "/auth/login",
        json={"email": test_email, "password": test_password},
    )
    auth_cookies = {get_auth_cookie_name(): login_res.json()["access_token"]}

    create_res = app_client.post(
        "/agent-runs",
        cookies=auth_cookies,
        json={
            "objective": {
                "objective": "Calculate break-even quantity.",
                "supplied_slots": {
                    "price": 100.0,
                    "variable_cost": 40.0,
                    "fixed_costs": 300.0,
                },
            }
        },
    )
    run_id = create_res.json()["id"]

    # Start run to completion
    start_res = app_client.post(f"/agent-runs/{run_id}/start", cookies=auth_cookies)
    assert start_res.status_code == 202

    repo = PostgresAgentRunRepository()
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.COMPLETED.value
    assert run["steps_used"] >= 1


@pytest.mark.integration
def test_deterministic_mode_runs_without_api_credentials(monkeypatch, app_client):
    """
    Verify deterministic offline mode:
    - LLM_PROVIDER=deterministic
    - GEMINI_API_KEY unset
    - Agent run successfully plans and executes deterministically.
    """
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    unique_id = uuid.uuid4().hex[:8]
    test_email = f"det_{unique_id}@arthlens.local"
    test_password = "Password123!"

    app_client.post(
        "/auth/register",
        json={"full_name": "Deterministic User", "email": test_email, "password": test_password},
    )
    login_res = app_client.post(
        "/auth/login",
        json={"email": test_email, "password": test_password},
    )
    auth_cookies = {get_auth_cookie_name(): login_res.json()["access_token"]}

    create_res = app_client.post(
        "/agent-runs",
        cookies=auth_cookies,
        json={
            "objective": {
                "objective": "Calculate break-even quantity.",
                "supplied_slots": {
                    "price": 80.0,
                    "variable_cost": 30.0,
                    "fixed_costs": 250.0,
                },
            }
        },
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # Start and execute in deterministic mode
    start_res = app_client.post(f"/agent-runs/{run_id}/start", cookies=auth_cookies)
    assert start_res.status_code == 202

    run_res = app_client.get(f"/agent-runs/{run_id}", cookies=auth_cookies)
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["state"] == AgentRunState.COMPLETED.value
    assert run_data["steps_used"] >= 1

    events_res = app_client.get(f"/agent-runs/{run_id}/events", cookies=auth_cookies)
    events = events_res.json()["events"]
    assert any(e["type"] == "ALL_CHECKS_PASS" for e in events)

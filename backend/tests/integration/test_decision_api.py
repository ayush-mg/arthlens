"""
Integration Tests for Decision Intelligence & Simulation REST APIs.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 4: Decision Intelligence Engine & Scenario Laboratory (Modules 8 & 9, UC-59 to UC-74).
"""

from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_user():
    """Create a verified test user and authorization header."""
    repo = PostgresUserRepository()
    email = f"decision_lead_{uuid.uuid4().hex[:8]}@arthlens.org"
    password_hash = hash_password("ValidPassword2026!")
    user_id = repo.save({
        "email": email,
        "password_hash": password_hash,
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(str(user_id), email, [Role.ENTREPRENEUR.value])
    return {
        "id": str(user_id),
        "email": email,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.integration
class TestDecisionIntelligenceAPI:
    """End-to-end integration tests of Decision Intelligence & Simulation endpoints."""

    def test_decision_version_graph_and_scenario_replay_endpoints(self, client, auth_user):
        """Saved decision versions and scenario simulations remain linked and reproducible over HTTP."""
        business_response = client.post(
            "/businesses",
            json={"name": f"Version Lab {uuid.uuid4().hex[:8]}", "industry": "Manufacturing"},
            headers=auth_user["headers"],
        )
        assert business_response.status_code == 201, business_response.text
        business_id = business_response.json()["id"]

        decision_inputs = {
            "cost_category": "packaging",
            "current_monthly_cost": 12000,
            "proposed_monthly_cost": 8500,
            "one_time_implementation_cost": 5000,
            "expected_quality_cost_monthly": 250,
            "evaluation_months": 12,
        }
        first_response = client.post(
            f"/businesses/{business_id}/decisions/evaluate",
            json={"model_id": "COST_REDUCTION", "inputs": decision_inputs},
            headers=auth_user["headers"],
        )
        assert first_response.status_code == 200, first_response.text
        first = first_response.json()
        assert first["version_number"] == 1
        assert first["graph"]["nodes"]

        second_response = client.post(
            f"/businesses/{business_id}/decisions/evaluate",
            json={
                "model_id": "COST_REDUCTION",
                "inputs": {**decision_inputs, "proposed_monthly_cost": 8000},
                "parent_decision_id": first["evaluation_id"],
            },
            headers=auth_user["headers"],
        )
        assert second_response.status_code == 200, second_response.text
        second = second_response.json()
        assert second["version_number"] == 2
        assert second["parent_decision_id"] == first["evaluation_id"]

        versions_response = client.get(
            f"/businesses/{business_id}/decisions/{first['evaluation_id']}/versions",
            headers=auth_user["headers"],
        )
        assert versions_response.status_code == 200, versions_response.text
        versions = versions_response.json()
        assert [version["version_number"] for version in versions] == [1, 2]
        assert versions[1]["parent_decision_id"] == first["evaluation_id"]
        assert versions[0]["causal_graph"]["nodes"]

        assumptions = {
            "horizon_months": 12,
            "initial_quantity": 100,
            "monthly_volume_growth_rate": 0.03,
            "selling_price": 120,
            "variable_cost_per_unit": 55,
            "fixed_monthly_operating_expenses": 2500,
            "opening_cash": 20000,
            "distributions": {
                "selling_price": {"distribution": "NORMAL", "mean": 120, "std_dev": 3},
            },
        }
        scenario_response = client.post(
            f"/businesses/{business_id}/scenarios",
            json={"name": "Baseline v1", "description": "Version and replay contract", "assumptions": assumptions},
            headers=auth_user["headers"],
        )
        assert scenario_response.status_code == 200, scenario_response.text
        scenario = scenario_response.json()
        scenario_id = scenario["id"]
        assert scenario["latest_version"]["version_number"] == 1

        updated_assumptions = {**assumptions, "selling_price": 125}
        version_response = client.post(
            f"/businesses/{business_id}/scenarios/{scenario_id}/versions",
            json={"assumptions": updated_assumptions},
            headers=auth_user["headers"],
        )
        assert version_response.status_code == 200, version_response.text
        assert version_response.json()["latest_version"]["version_number"] == 2
        scenario_versions_response = client.get(
            f"/businesses/{business_id}/scenarios/{scenario_id}/versions",
            headers=auth_user["headers"],
        )
        assert scenario_versions_response.status_code == 200, scenario_versions_response.text
        assert [item["version_number"] for item in scenario_versions_response.json()] == [2, 1]

        run_response = client.post(
            f"/businesses/{business_id}/scenarios/{scenario_id}/runs",
            json={"iterations": 40, "random_seed": 20261112},
            headers=auth_user["headers"],
        )
        assert run_response.status_code == 200, run_response.text
        run = run_response.json()
        assert run["random_seed"] == 20261112
        assert run["scenario_version_id"] == version_response.json()["latest_version"]["id"]

        replay_response = client.post(
            f"/businesses/{business_id}/scenarios/{scenario_id}/runs/{run['id']}/replay",
            headers=auth_user["headers"],
        )
        assert replay_response.status_code == 200, replay_response.text
        replay = replay_response.json()
        assert replay["replayed"] is True
        assert replay["random_seed"] == run["random_seed"]
        assert replay["result"] == run["result"]

        # Verify scenario version comparison
        version_1_id = scenario["latest_version"]["id"]
        version_2_id = version_response.json()["latest_version"]["id"]
        compare_response = client.post(
            f"/businesses/{business_id}/scenarios/compare",
            json={"version_ids": [version_1_id, version_2_id]},
            headers=auth_user["headers"],
        )
        assert compare_response.status_code == 200, compare_response.text
        comparison = compare_response.json()
        assert len(comparison["versions"]) == 2
        assert {item["version_number"] for item in comparison["versions"]} == {1, 2}
        assert "base" in comparison["versions"][0]["cases"]

        # Verify scenario deletion cascades
        delete_response = client.delete(
            f"/businesses/{business_id}/scenarios/{scenario_id}",
            headers=auth_user["headers"],
        )
        assert delete_response.status_code == 200, delete_response.text
        assert delete_response.json()["status"] == "deleted"

        # Verify scenario no longer exists
        not_found_response = client.get(
            f"/businesses/{business_id}/scenarios/{scenario_id}/versions",
            headers=auth_user["headers"],
        )
        assert not_found_response.status_code == 404

    def test_flagship_8_lakh_machinery_purchase_evaluation_and_simulation(self, client, auth_user):
        """
        Executes the flagship ₹8 Lakh machinery purchase journey:
        1. Creates business and seeds existing working capital and liquidity.
        2. Evaluates 3 financing alternatives, constraints, DSCR, and graph.
        3. Runs 1,000-iteration Monte Carlo PCG64 risk simulation (P10, P50, P90).
        4. Runs OAT sensitivity analysis (Tornado chart points).
        5. Verifies audit persistence in PostgreSQL history.
        """
        # 1. Create bakery business
        b_res = client.post(
            "/businesses",
            json={"name": "Avadh Artisan Bakes", "industry": "Food Processing"},
            headers=auth_user["headers"],
        )
        assert b_res.status_code == 201
        biz_id = b_res.json()["id"]

        # 2. Seed initial cash liquidity of ₹4,50,000 via customer payment
        seed_pay = client.post(
            f"/businesses/{biz_id}/income",
            json={
                "category": "Capital Infusion",
                "amount": 450000.0,
                "date": date.today().isoformat(),
                "payment_method": "BANK_TRANSFER",
            },
            headers=auth_user["headers"],
        )
        assert seed_pay.status_code == 201

        # 3. Evaluate Machine Purchase Decision: ₹8,00,000 Oven
        eval_payload = {
            "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
            "inputs": {
                "machine_name": "Commercial Rotary Convection Oven",
                "machine_cost": 800000.0,
                "down_payment": 160000.0,  # 20% down
                "loan_amount": 640000.0,
                "loan_interest_rate_pct": 10.5,
                "loan_tenure_months": 36,
                "monthly_maintenance": 6000.0,
                "current_monthly_volume": 8000.0,
                "capacity_monthly_volume": 12000.0,  # +4,000 loaves/month
                "unit_price": 40.0,
                "unit_variable_cost": 22.0,
            },
            "constraints_override": {
                "min_cash_reserve_floor": 200000.0,
                "min_dscr": 1.25,
            },
            "save_evaluation": True,
        }

        eval_res = client.post(
            f"/businesses/{biz_id}/decisions/evaluate",
            json=eval_payload,
            headers=auth_user["headers"],
        )
        assert eval_res.status_code == 200, eval_res.text
        eval_data = eval_res.json()

        assert eval_data["model_id"] == "MACHINE_OR_EQUIPMENT_PURCHASE"
        assert eval_data["outcome"] == "FEASIBLE"
        # Monthly incremental gross profit: 4,000 * 18 = 72,000
        assert eval_data["calculations"]["incremental_monthly_gross_profit"] == 72000.0
        # Post purchase cash: 450k - 160k = 290k (comfortably above 200k floor)
        assert eval_data["calculations"]["post_purchase_cash_liquidity"] == 290000.0
        # DSCR > 1.25
        assert eval_data["calculations"]["debt_service_coverage_ratio_dscr"] >= 1.25

        # Verify multi-alternative trade-offs
        assert len(eval_data["alternatives"]) == 3
        alt_names = [a["alternative_id"] for a in eval_data["alternatives"]]
        assert "ALT_LOAN_36M" in alt_names
        assert "ALT_LOAN_60M" in alt_names
        assert "ALT_SELF_FINANCED" in alt_names

        # Verify typed graph structure
        assert len(eval_data["graph"]["nodes"]) >= 7
        assert len(eval_data["graph"]["edges"]) >= 6

        # 4. Run Monte Carlo Risk Simulation (PCG64) with 1,000 iterations
        sim_payload = {
            "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
            "inputs": {
                **eval_payload["inputs"],
                # Request values and provenance must not override authenticated ledger records.
                "current_cash_liquidity": 1000000000.0,
                "current_monthly_ebitda": 1000000.0,
                "input_provenance": {"current_cash_liquidity": "VERIFIED_BUSINESS_RECORD"},
            },
            "uncertainty_params": {
                "unit_price": {"std_dev_pct": 0.05},
                "unit_variable_cost": {"std_dev_pct": 0.08},
                "capacity_monthly_volume": {"std_dev_pct": 0.10},
            },
            "iterations": 1000,
            "random_seed": 2026,
        }
        sim_res = client.post(
            f"/businesses/{biz_id}/decisions/simulate-risk",
            json=sim_payload,
            headers=auth_user["headers"],
        )
        assert sim_res.status_code == 200, sim_res.text
        sim_data = sim_res.json()
        assert sim_data["iterations"] == 1000
        assert sim_data["random_seed"] == 2026
        assert "stochastic_metrics" in sim_data
        assert sim_data["baseline_calculations"]["post_purchase_cash_liquidity"] == eval_data["calculations"]["post_purchase_cash_liquidity"]
        cf_metric = sim_data["stochastic_metrics"]["net_monthly_cash_flow_after_emi"]
        assert cf_metric["p10_downside"] <= cf_metric["p50_median"] <= cf_metric["p90_upside"]
        assert sim_data["shortfall_risk_probability_percent"] <= 5.0  # very safe decision

        # 5. Run OAT Sensitivity Analysis (Tornado Chart)
        sens_payload = {
            "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
            "inputs": eval_payload["inputs"],
            "target_output_metric": "net_monthly_cash_flow_after_emi",
            "variation_pct": 0.20,
        }
        sens_res = client.post(
            f"/businesses/{biz_id}/decisions/sensitivity",
            json=sens_payload,
            headers=auth_user["headers"],
        )
        assert sens_res.status_code == 200, sens_res.text
        tornado = sens_res.json()
        assert len(tornado) >= 3
        # Top parameter has largest swing
        assert tornado[0]["swing"] >= tornado[1]["swing"]

        # 6. Verify audit history in PostgreSQL
        hist_res = client.get(f"/businesses/{biz_id}/decisions/history", headers=auth_user["headers"])
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) >= 1
        assert history[0]["model_id"] == "MACHINE_OR_EQUIPMENT_PURCHASE"
        assert history[0]["outcome"] == "FEASIBLE"

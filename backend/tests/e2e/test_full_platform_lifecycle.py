"""End-to-end workspace journey across operations, analysis, planning, and reporting."""

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
    return TestClient(create_app())


@pytest.fixture
def auth_headers():
    email = f"lifecycle_{uuid.uuid4().hex[:10]}@arthlens.test"
    user_id = PostgresUserRepository().save({
        "email": email,
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(str(user_id), email, [Role.ENTREPRENEUR.value])
    return {"Authorization": f"Bearer {token}"}


def _assert_response(response, expected_status: int):
    assert response.status_code == expected_status, response.text
    return response.json()


@pytest.mark.integration
def test_workspace_operations_reconcile_costs_and_complete_analysis_lifecycle(client, auth_headers):
    today = date.today()
    business = _assert_response(
        client.post(
            "/businesses",
            json={
                "name": f"Lifecycle Workshop {uuid.uuid4().hex[:6]}",
                "industry": "Light Manufacturing",
                "address": "Pune, Maharashtra",
                "currency": "INR",
            },
            headers=auth_headers,
        ),
        201,
    )
    business_id = business["id"]

    _assert_response(
        client.post(
            f"/businesses/{business_id}/income",
            json={
                "category": "CAPITAL_INJECTION",
                "amount": 25000,
                "date": today.isoformat(),
                "description": "Lifecycle test opening cash",
                "payment_method": "BANK_TRANSFER",
            },
            headers=auth_headers,
        ),
        201,
    )
    customer = _assert_response(
        client.post(
            f"/businesses/{business_id}/customers",
            json={"name": "Lifecycle Customer", "credit_limit": 5000},
            headers=auth_headers,
        ),
        201,
    )
    supplier = _assert_response(
        client.post(
            f"/businesses/{business_id}/suppliers",
            json={"name": "Lifecycle Supplier"},
            headers=auth_headers,
        ),
        201,
    )
    product = _assert_response(
        client.post(
            f"/businesses/{business_id}/products",
            json={
                "sku": f"LIFE-{uuid.uuid4().hex[:8]}",
                "name": "Lifecycle Component",
                "category": "COMPONENT",
                "unit": "pcs",
                "purchase_price": 0,
                "selling_price": 100,
                "initial_stock": 0,
            },
            headers=auth_headers,
        ),
        201,
    )

    # An explicitly unpriced opening count exercises the documented attestation workflow.
    _assert_response(
        client.post(
            f"/businesses/{business_id}/inventory/adjust",
            json={
                "product_id": product["id"],
                "movement_type": "OPENING",
                "quantity": 2,
                "unit_price": 0,
                "reason": "Opening count awaiting source cost",
                "reference_id": "LIFECYCLE-OPENING",
            },
            headers=auth_headers,
        ),
        200,
    )
    purchase = _assert_response(
        client.post(
            f"/businesses/{business_id}/purchases",
            json={
                "supplier_id": supplier["id"],
                "bill_number": f"BILL-{uuid.uuid4().hex[:8]}",
                "purchase_date": today.isoformat(),
                "due_date": (today + timedelta(days=30)).isoformat(),
                "items": [{
                    "product_id": product["id"],
                    "description": "Component procurement",
                    "quantity": 10,
                    "unit": "pcs",
                    "unit_price": 40,
                }],
                "tax_amount": 0,
            },
            headers=auth_headers,
        ),
        201,
    )
    purchase_item_id = purchase["items"][0]["id"]

    invoice = _assert_response(
        client.post(
            f"/businesses/{business_id}/invoices",
            json={
                "customer_id": customer["id"],
                "invoice_number": f"SALE-{uuid.uuid4().hex[:8]}",
                "invoice_date": today.isoformat(),
                "due_date": (today + timedelta(days=30)).isoformat(),
                "items": [{
                    "product_id": product["id"],
                    "description": "Component sale",
                    "quantity": 4,
                    "unit": "pcs",
                    "unit_price": 100,
                }],
                "tax_amount": 0,
            },
            headers=auth_headers,
        ),
        201,
    )
    sales_return = _assert_response(
        client.post(
            f"/businesses/{business_id}/returns/sales",
            json={
                "invoice_id": invoice["id"],
                "return_date": today.isoformat(),
                "reason": "One item returned for inspection",
                "items": [{
                    "product_id": product["id"],
                    "quantity": 1,
                    "unit_price": 100,
                }],
            },
            headers=auth_headers,
        ),
        200,
    )
    assert sales_return["status"] == "PROCESSED"

    purchase_return = _assert_response(
        client.post(
            f"/businesses/{business_id}/returns/purchases",
            json={
                "purchase_id": purchase["id"],
                "return_date": today.isoformat(),
                "reason": "One damaged component returned",
                "idempotency_key": f"life-{uuid.uuid4().hex}",
                "items": [{"purchase_item_id": purchase_item_id, "quantity": 1}],
            },
            headers=auth_headers,
        ),
        200,
    )
    assert purchase_return["status"] == "PROCESSED"

    unreconciled = _assert_response(
        client.get(f"/businesses/{business_id}/inventory/unreconciled-costs", headers=auth_headers),
        200,
    )
    assert unreconciled["unreconciled_movement_count"] >= 1
    opening_movement = next(
        movement for movement in unreconciled["movements"]
        if movement["reference_id"] == "LIFECYCLE-OPENING"
    )
    reconciliation = _assert_response(
        client.post(
            f"/businesses/{business_id}/inventory/reconcile-costs",
            json={
                "mode": "MANUAL_ATTESTATION",
                "overrides": [{
                    "movement_id": opening_movement["movement_id"],
                    "unit_cost": 30,
                    "note": "Owner confirmed the documented opening count cost.",
                }],
            },
            headers=auth_headers,
        ),
        200,
    )
    assert reconciliation["status"] == "COMPLETED"
    after_reconciliation = _assert_response(
        client.get(f"/businesses/{business_id}/inventory/unreconciled-costs", headers=auth_headers),
        200,
    )
    assert after_reconciliation["unreconciled_movement_count"] == 0

    health = _assert_response(
        client.get(f"/businesses/{business_id}/analytics/health-score", headers=auth_headers),
        200,
    )
    assert 0 <= health["overall_score"] <= 100
    assert health["grade"] in {"EXCELLENT", "HEALTHY", "NEEDS_ATTENTION", "CRITICAL"}

    decision_inputs = {
        "cost_category": "component handling",
        "current_monthly_cost": 5000,
        "proposed_monthly_cost": 3500,
        "one_time_implementation_cost": 2500,
        "expected_quality_cost_monthly": 100,
        "evaluation_months": 12,
    }
    decision_v1 = _assert_response(
        client.post(
            f"/businesses/{business_id}/decisions/evaluate",
            json={"model_id": "COST_REDUCTION", "inputs": decision_inputs},
            headers=auth_headers,
        ),
        200,
    )
    decision_v2_inputs = {**decision_inputs, "proposed_monthly_cost": 3200}
    decision_v2 = _assert_response(
        client.post(
            f"/businesses/{business_id}/decisions/evaluate",
            json={
                "model_id": "COST_REDUCTION",
                "inputs": decision_v2_inputs,
                "parent_decision_id": decision_v1["evaluation_id"],
            },
            headers=auth_headers,
        ),
        200,
    )
    versions = _assert_response(
        client.get(
            f"/businesses/{business_id}/decisions/{decision_v1['evaluation_id']}/versions",
            headers=auth_headers,
        ),
        200,
    )
    assert len(versions) == 2
    assert {version["version_number"] for version in versions} == {1, 2}
    assert decision_v2["parent_decision_id"] == decision_v1["evaluation_id"]

    assumptions = {
        "horizon_months": 12,
        "initial_quantity": 100,
        "monthly_volume_growth_rate": 0.05,
        "selling_price": 100,
        "variable_cost_per_unit": 40,
        "fixed_monthly_operating_expenses": 1000,
        "opening_cash": 5000,
        "distributions": {
            "selling_price": {"distribution": "NORMAL", "mean": 100, "std_dev": 2},
        },
    }
    scenario = _assert_response(
        client.post(
            f"/businesses/{business_id}/scenarios",
            json={"name": "Lifecycle baseline", "description": "Replay verification", "assumptions": assumptions},
            headers=auth_headers,
        ),
        200,
    )
    scenario_id = scenario["id"]
    simulation = _assert_response(
        client.post(
            f"/businesses/{business_id}/scenarios/{scenario_id}/runs",
            json={"iterations": 40, "random_seed": 20261112},
            headers=auth_headers,
        ),
        200,
    )
    replay = _assert_response(
        client.post(
            f"/businesses/{business_id}/scenarios/{scenario_id}/runs/{simulation['id']}/replay",
            headers=auth_headers,
        ),
        200,
    )
    assert replay["replayed"] is True
    assert replay["random_seed"] == 20261112

    goal = _assert_response(
        client.post(
            f"/businesses/{business_id}/goals",
            json={
                "goal_type": "REVENUE",
                "title": "Lifecycle revenue target",
                "target_value": 1000,
                "start_date": today.isoformat(),
                "target_date": (today + timedelta(days=30)).isoformat(),
            },
            headers=auth_headers,
        ),
        201,
    )
    deviation = _assert_response(
        client.post(
            f"/businesses/{business_id}/goals/{goal['id']}/evaluate?as_of_date={today.isoformat()}",
            headers=auth_headers,
        ),
        200,
    )
    assert deviation["goal_id"] == goal["id"]
    assert {"actual_value", "planned_value", "deviation_value"} <= deviation.keys()
    assert deviation["evidence_items"]

    dossier = client.get(f"/businesses/{business_id}/reports/dossier.pdf", headers=auth_headers)
    assert dossier.status_code == 200, dossier.text
    assert dossier.headers["content-type"] == "application/pdf"
    assert dossier.content.startswith(b"%PDF-")
    assert len(dossier.content) > 1000

    transaction_export = client.get(
        f"/businesses/{business_id}/transactions/export.csv",
        headers=auth_headers,
    )
    assert transaction_export.status_code == 200, transaction_export.text
    assert "text/csv" in transaction_export.headers["content-type"]
    assert "Reference type" in transaction_export.text

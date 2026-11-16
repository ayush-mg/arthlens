"""
End-to-End Flagship Continuous Demonstration Journey Test.
Executes the flagship micro-enterprise journey:
- Multi-business workspace: "Annapurna Bakeries & Sweets"
- Khata & credit ledgers (Customers & Suppliers)
- Perpetual inventory with Weighted Average Cost (WAC)
- Sales invoicing with automatic stock decrement
- Deterministic Financial Intelligence (P&L, Cash Flow, Solvency, Ageing, Break-even, Health)
- Flagship Decision Laboratory: Commercial 32-Tray Rotary Rack Oven (Rs 8,00,000)
- 1,000-iteration NumPy PCG64 Monte Carlo simulation
- OAT Tornado sensitivity analysis
- Agentic Gemini Copilot DAG investigation
- ReportLab 2-Page Decision Brief PDF & Full Dossier PDF generation
- CSV Ledger exports
"""

from datetime import date
from decimal import Decimal
import io
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.arthlens.api.app import create_app
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token


@pytest.fixture
def auth_headers():
    repo = PostgresUserRepository()
    email = f"owner_{uuid.uuid4().hex[:8]}@annapurna.test"
    password_hash = hash_password("ValidPassword2026!")
    user_id = repo.save({
        "email": email,
        "password_hash": password_hash,
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(str(user_id), email, [Role.ENTREPRENEUR.value])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    return TestClient(create_app())


def test_flagship_8_lakh_rotary_oven_journey(client, auth_headers):
    # -------------------------------------------------------------
    # Step 1: Create Business Workspace
    # -------------------------------------------------------------
    ws_payload = {
        "name": "Annapurna Bakeries & Sweets",
        "industry": "Food Processing & Retail",
        "address": "Varanasi, Uttar Pradesh, 221002",
    }
    r = client.post("/businesses", json=ws_payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    business = r.json()
    b_id = business["id"]
    assert business["name"] == "Annapurna Bakeries & Sweets"

    # Seed initial bank cash reserve for business (Rs 3.5 Lakhs)
    r = client.post(
        f"/businesses/{b_id}/income",
        json={
            "category": "CAPITAL_INJECTION",
            "amount": 350000.0,
            "date": "2026-11-01",
            "description": "Founder seed working capital",
            "payment_method": "BANK_TRANSFER",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201

    # -------------------------------------------------------------
    # Step 2: Register Khata Parties (Customer & Supplier)
    # -------------------------------------------------------------
    # Customer: Royal Sweets & Retailers
    r = client.post(
        f"/businesses/{b_id}/customers",
        json={
            "name": "Royal Sweets & Retailers",
            "phone": "+91 98765 11223",
            "credit_limit": 100000.0,
            "opening_balance": 0.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    customer = r.json()
    c_id = customer["id"]

    # Supplier: Apex Flour Mills Ltd
    r = client.post(
        f"/businesses/{b_id}/suppliers",
        json={
            "name": "Apex Flour Mills Ltd",
            "phone": "+91 91234 55667",
            "opening_balance": 0.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    supplier = r.json()
    s_id = supplier["id"]

    # -------------------------------------------------------------
    # Step 3: Product Catalog & Perpetual Inventory
    # -------------------------------------------------------------
    # Product: Artisan Multigrain Loaf
    r = client.post(
        f"/businesses/{b_id}/products",
        json={
            "name": "Artisan Multigrain Bread (400g)",
            "sku": "BAKE-BREAD-01",
            "category": "FINISHED_GOODS",
            "unit": "pcs",
            "selling_price": 60.0,
            "purchase_price": 28.0,
            "min_stock_alert": 50.0,
            "initial_stock": 0.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    product = r.json()
    p_id = product["id"]

    # -------------------------------------------------------------
    # Step 4: Purchase Procurement (Stock In & WAC Update)
    # -------------------------------------------------------------
    purchase_payload = {
        "supplier_id": s_id,
        "bill_number": "PO-2026-001",
        "purchase_date": "2026-11-01",
        "due_date": "2026-11-15",
        "items": [
            {
                "product_id": p_id,
                "description": "Initial Batch Artisan Loaf Production Ingredients",
                "quantity": 500.0,
                "unit": "pcs",
                "unit_price": 28.0,
            }
        ],
        "tax_amount": 700.0,
    }
    r = client.post(f"/businesses/{b_id}/purchases", json=purchase_payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    purchase = r.json()
    assert purchase["total_amount"] == 14700.0

    # Verify inventory balance updated to 500
    r = client.get(f"/businesses/{b_id}/inventory/balances", headers=auth_headers)
    assert r.status_code == 200
    balances = r.json()
    p_balance = next(b for b in balances if b["product_id"] == p_id)
    assert p_balance["quantity_on_hand"] == 500.0
    assert p_balance["unit_cost"] == 28.0

    # -------------------------------------------------------------
    # Step 5: Sales Invoicing (Stock Decrement & Receivable Posting)
    # -------------------------------------------------------------
    invoice_payload = {
        "customer_id": c_id,
        "invoice_number": "INV-2026-001",
        "invoice_date": "2026-11-05",
        "due_date": "2026-11-20",
        "items": [
            {
                "product_id": p_id,
                "description": "Artisan Multigrain Bread - Weekly Supply",
                "quantity": 200.0,
                "unit": "pcs",
                "unit_price": 60.0,
                "discount_percent": 0.0,
            }
        ],
        "tax_amount": 600.0,
    }
    r = client.post(f"/businesses/{b_id}/invoices", json=invoice_payload, headers=auth_headers)
    assert r.status_code == 201, r.text
    invoice = r.json()
    assert invoice["total_amount"] == 12600.0
    assert invoice["outstanding_balance"] == 12600.0

    # Verify stock decremented: 500 - 200 = 300
    r = client.get(f"/businesses/{b_id}/inventory/balances", headers=auth_headers)
    balances = r.json()
    p_balance = next(b for b in balances if b["product_id"] == p_id)
    assert p_balance["quantity_on_hand"] == 300.0

    # Customer pays 50% partial payment
    r = client.post(
        f"/businesses/{b_id}/invoices/{invoice['id']}/payments",
        json={"amount": 6300.0, "payment_date": "2026-11-06", "payment_method": "BANK_TRANSFER"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    updated_inv = r.json()
    assert updated_inv["paid_amount"] == 6300.0
    assert updated_inv["outstanding_balance"] == 6300.0
    assert updated_inv["status"] == "PARTIALLY_PAID"

    # -------------------------------------------------------------
    # Step 6: Cash Position & Operational Goals
    # -------------------------------------------------------------
    r = client.get(f"/businesses/{b_id}/cash-position", headers=auth_headers)
    assert r.status_code == 200
    cash = r.json()
    assert cash["bank_balance"] >= 6300.0

    # Create Goal
    r = client.post(
        f"/businesses/{b_id}/goals",
        json={
            "title": "Monthly Revenue Target",
            "goal_type": "REVENUE",
            "target_value": 50000.0,
            "start_date": "2026-11-01",
            "target_date": "2026-11-30",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    goal = r.json()
    assert goal["target_value"] == 50000.0

    # -------------------------------------------------------------
    # Step 7: Deterministic Financial Intelligence Suite
    # -------------------------------------------------------------
    # P&L
    r = client.get(f"/businesses/{b_id}/analytics/pnl", headers=auth_headers)
    assert r.status_code == 200
    pnl = r.json()
    assert pnl["gross_sales"] == 12000.0
    assert pnl["total_revenue"] >= 12000.0
    assert pnl["cost_of_goods_sold"] == 5600.0  # 200 * 28.0 WAC cost
    assert pnl["gross_profit"] > 0
    assert pnl["net_profit"] > 0

    # Cash Flow
    r = client.get(f"/businesses/{b_id}/analytics/cash-flow", headers=auth_headers)
    assert r.status_code == 200
    cf = r.json()
    assert cf["operating_cash_inflows"] == 356300.0  # 350k seed + 6.3k collection

    # Working Capital
    r = client.get(f"/businesses/{b_id}/analytics/working-capital", headers=auth_headers)
    assert r.status_code == 200
    wc = r.json()
    assert wc["accounts_receivable"] == 6300.0
    assert wc["inventory_valuation"] == 8400.0  # 300 * 28.0
    assert wc["net_working_capital"] > 0

    # Ageing
    r = client.get(f"/businesses/{b_id}/analytics/ageing", headers=auth_headers)
    assert r.status_code == 200
    ageing = r.json()
    assert ageing["receivables"]["total_outstanding"] == 6300.0
    assert ageing["receivables"]["0_30_days"] == 6300.0

    # Break-Even
    r = client.get(f"/businesses/{b_id}/analytics/break-even", headers=auth_headers)
    assert r.status_code == 200
    be = r.json()
    assert be["total_revenue"] >= 12600.0

    # Health Score
    r = client.get(f"/businesses/{b_id}/analytics/health-score", headers=auth_headers)
    assert r.status_code == 200
    health = r.json()
    assert 0 <= health["overall_score"] <= 100
    assert health["grade"] in ("EXCELLENT", "HEALTHY", "NEEDS_ATTENTION", "CRITICAL")
    assert len(health["key_strengths"]) > 0

    # -------------------------------------------------------------
    # Step 8: Flagship Decision Laboratory (Rs 8L Rotary Oven)
    # -------------------------------------------------------------
    eval_payload = {
        "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
        "inputs": {
            "machine_name": "Commercial 32-Tray Rotary Convection Oven",
            "machine_cost": 800000.0,
            "down_payment": 160000.0,
            "loan_amount": 640000.0,
            "loan_interest_rate_pct": 10.5,
            "loan_tenure_months": 36,
            "monthly_maintenance": 6000.0,
            "current_monthly_volume": 8000.0,
            "capacity_monthly_volume": 12000.0,
            "unit_price": 40.0,
            "unit_variable_cost": 22.0,
        },
        "constraints_override": {
            "min_cash_reserve_floor": 100000.0,
            "min_dscr": 1.25,
        },
        "save_evaluation": True,
    }
    r = client.post(f"/businesses/{b_id}/decisions/evaluate", json=eval_payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    decision = r.json()
    assert decision["model_id"] == "MACHINE_OR_EQUIPMENT_PURCHASE"
    assert decision["outcome"] in ("FEASIBLE", "HIGHLY_RECOMMENDED")
    assert len(decision["alternatives"]) == 3

    # Monte Carlo Risk Simulation (1,000 iterations)
    mc_payload = {
        "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
        "inputs": eval_payload["inputs"],
        "iterations": 1000,
        "random_seed": 2026,
    }
    r = client.post(f"/businesses/{b_id}/decisions/simulate-risk", json=mc_payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    mc = r.json()
    assert mc["iterations"] == 1000
    assert "stochastic_metrics" in mc

    # Sensitivity Tornado Analysis
    sens_payload = {
        "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
        "inputs": eval_payload["inputs"],
        "target_output_metric": "net_monthly_cash_flow_after_emi",
        "variation_pct": 0.20,
    }
    r = client.post(f"/businesses/{b_id}/decisions/sensitivity", json=sens_payload, headers=auth_headers)
    assert r.status_code == 200, r.text
    sens = r.json()
    assert len(sens) >= 3
    assert sens[0]["swing"] >= sens[1]["swing"]

    # -------------------------------------------------------------
    # Step 9: Agentic Copilot Investigation DAG
    # -------------------------------------------------------------
    r = client.post(
        f"/businesses/{b_id}/agent/investigate",
        json={"query": "Should we buy the 8 lakh rotary rack oven for the bakery?"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    agent_res = r.json()
    assert agent_res["intent"] == "EQUIPMENT_PURCHASE_EVALUATION"
    assert len(agent_res["plan"]) >= 3
    assert agent_res["decision_outcome"] == "INSUFFICIENT_INFORMATION"
    assert "INSUFFICIENT INFORMATION" in agent_res["synthesis"]
    assert "down_payment" in agent_res["data_gaps"]
    assert "unit_price" in agent_res["data_gaps"]

    # -------------------------------------------------------------
    # Step 10: Reports & Governance Deliverables
    # -------------------------------------------------------------
    # 1. Decision History & 2-Page Executive Decision Brief PDF
    r = client.get(f"/businesses/{b_id}/decisions/history", headers=auth_headers)
    assert r.status_code == 200
    hist = r.json()
    eval_id = hist[0]["id"]

    r = client.get(f"/businesses/{b_id}/reports/decisions/{eval_id}/brief.pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF-")
    assert len(r.content) > 1000

    # 2. Complete Business Dossier PDF
    r = client.get(f"/businesses/{b_id}/reports/dossier.pdf", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF-")
    assert len(r.content) > 2000

    # 3. CSV Customer Ledger
    r = client.get(f"/businesses/{b_id}/reports/customers/{c_id}/ledger.csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "date,type,reference,debit,credit,running_balance,notes" in r.text

    # 4. CSV Supplier Ledger
    r = client.get(f"/businesses/{b_id}/reports/suppliers/{s_id}/ledger.csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "date,type,reference,debit,credit,running_balance,notes" in r.text

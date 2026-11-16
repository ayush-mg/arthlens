"""
Integration Tests for Financial Intelligence Engine REST APIs.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 3: Financial Understanding & Analytics (P&L, Cash Flow, Working Capital, Ageing, Break-even, Health Score).
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
    email = f"cfo_{uuid.uuid4().hex[:8]}@arthlens.org"
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
class TestFinancialIntelligenceAPI:
    """End-to-end integration tests of Financial Analytics endpoints."""

    def test_inventory_cost_reconciliation_and_history_endpoints(self, client, auth_user):
        """An unpriced opening movement can be attested and audited through the API."""
        business_response = client.post(
            "/businesses",
            json={"name": f"Cost Audit {uuid.uuid4().hex[:8]}", "industry": "Retail"},
            headers=auth_user["headers"],
        )
        assert business_response.status_code == 201, business_response.text
        business_id = business_response.json()["id"]

        product_response = client.post(
            f"/businesses/{business_id}/products",
            json={
                "sku": f"COST-{uuid.uuid4().hex[:8]}",
                "name": "Unpriced Opening Stock",
                "category": "Inventory",
                "unit": "pcs",
                "purchase_price": 120,
                "selling_price": 200,
                "initial_stock": 0,
            },
            headers=auth_user["headers"],
        )
        assert product_response.status_code == 201, product_response.text
        product_id = product_response.json()["id"]

        movement_response = client.post(
            f"/businesses/{business_id}/inventory/adjust",
            json={
                "product_id": product_id,
                "movement_type": "OPENING",
                "quantity": 4,
                "unit_price": 0,
                "reason": "Opening count awaiting a documented cost",
                "reference_id": f"COST-AUDIT-{uuid.uuid4().hex[:8]}",
            },
            headers=auth_user["headers"],
        )
        assert movement_response.status_code == 200, movement_response.text

        outstanding_response = client.get(
            f"/businesses/{business_id}/inventory/unreconciled-costs",
            headers=auth_user["headers"],
        )
        assert outstanding_response.status_code == 200, outstanding_response.text
        outstanding = outstanding_response.json()
        assert outstanding["unreconciled_movement_count"] == 1
        assert outstanding["unreconciled_product_count"] == 1
        movement = outstanding["movements"][0]
        assert movement["movement_type"] == "OPENING"
        assert movement["cost_reconciliation_status"] != "VERIFIED"

        reconciliation_response = client.post(
            f"/businesses/{business_id}/inventory/reconcile-costs",
            json={
                "mode": "MANUAL_ATTESTATION",
                "overrides": [{
                    "movement_id": movement["movement_id"],
                    "unit_cost": 115.25,
                    "note": "Owner verified the supplier receipt for this opening count.",
                }],
            },
            headers=auth_user["headers"],
        )
        assert reconciliation_response.status_code == 200, reconciliation_response.text
        reconciliation = reconciliation_response.json()
        assert reconciliation["status"] == "COMPLETED"
        assert reconciliation["resolved_movement_count"] == 1
        assert reconciliation["unresolved_movement_count"] == 0

        cleared_response = client.get(
            f"/businesses/{business_id}/inventory/unreconciled-costs",
            headers=auth_user["headers"],
        )
        assert cleared_response.status_code == 200, cleared_response.text
        assert cleared_response.json()["unreconciled_movement_count"] == 0

        history_response = client.get(
            f"/businesses/{business_id}/inventory/cost-reconciliation-history",
            headers=auth_user["headers"],
        )
        assert history_response.status_code == 200, history_response.text
        history = history_response.json()
        assert history[0]["reconciliation_id"] == reconciliation["reconciliation_id"]
        assert history[0]["status"] == "COMPLETED"
        assert history[0]["summary"]["resolved_movement_count"] == 1

    def test_full_financial_analytics_lifecycle(self, client, auth_user):
        """Creates complete business operations data and verifies all 6 financial intelligence endpoints."""
        # 1. Create business
        b_res = client.post(
            "/businesses",
            json={"name": "Varanasi Precision Brass", "industry": "Light Engineering"},
            headers=auth_user["headers"],
        )
        assert b_res.status_code == 201
        biz_id = b_res.json()["id"]

        # 2. Add product: Brass Valves @ cost ₹120, sell ₹250, initial stock 100 units
        p_res = client.post(
            f"/businesses/{biz_id}/products",
            json={
                "sku": "VALVE-BRASS-50",
                "name": "Heavy Duty Brass Gate Valve 50mm",
                "category": "Fittings",
                "unit": "pcs",
                "purchase_price": 120.0,
                "selling_price": 250.0,
                "initial_stock": 100.0,
            },
            headers=auth_user["headers"],
        )
        assert p_res.status_code == 201
        prod_id = p_res.json()["id"]

        # 3. Add customer
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={"name": "Kanpur Plumbing Corp", "credit_limit": 50000.0},
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # 4. Create sales invoice: 40 valves @ ₹250 = ₹10,000 + ₹1,800 tax = ₹11,800
        inv_res = client.post(
            f"/businesses/{biz_id}/invoices",
            json={
                "customer_id": cust_id,
                "invoice_number": "INV-VPB-001",
                "invoice_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=15)).isoformat(),
                "items": [
                    {
                        "product_id": prod_id,
                        "description": "Heavy Duty Brass Gate Valve 50mm",
                        "quantity": 40.0,
                        "unit": "pcs",
                        "unit_price": 250.0,
                    }
                ],
                "tax_amount": 1800.0,
            },
            headers=auth_user["headers"],
        )
        assert inv_res.status_code == 201
        inv_id = inv_res.json()["id"]

        # 5. Customer makes partial payment of ₹5,000
        pay_res = client.post(
            f"/businesses/{biz_id}/invoices/{inv_id}/payments",
            json={
                "amount": 5000.0,
                "payment_date": date.today().isoformat(),
                "payment_method": "BANK_TRANSFER",
                "notes": "NEFT Advance",
            },
            headers=auth_user["headers"],
        )
        assert pay_res.status_code == 200

        # 6. Record direct income of ₹2,000
        inc_res = client.post(
            f"/businesses/{biz_id}/income",
            json={
                "category": "Brass Borings Scrap",
                "amount": 2000.0,
                "date": date.today().isoformat(),
                "payment_method": "CASH",
            },
            headers=auth_user["headers"],
        )
        assert inc_res.status_code == 201

        # 7. Record operational expenses of ₹1,500
        exp_res = client.post(
            f"/businesses/{biz_id}/expenses",
            json={
                "category": "OPERATING",
                "amount": 1500.0,
                "date": date.today().isoformat(),
                "description": "Foundry furnace power tariff",
                "payment_method": "BANK_TRANSFER",
            },
            headers=auth_user["headers"],
        )
        assert exp_res.status_code == 201

        # ======================================================================
        # Test Endpoint 1: P&L Statement
        # ======================================================================
        pnl_res = client.get(f"/businesses/{biz_id}/analytics/pnl", headers=auth_user["headers"])
        assert pnl_res.status_code == 200
        pnl = pnl_res.json()
        # Sales revenue excludes the output tax liability.
        assert pnl["gross_sales"] == 10000.0
        assert pnl["direct_income"] == 2000.0
        assert pnl["total_revenue"] == 12000.0
        assert pnl["total_operating_expenses"] == 1500.0
        assert pnl["net_profit"] > 0
        assert "formatted_total_revenue" in pnl

        # ======================================================================
        # Test Endpoint 2: Cash Flow Statement
        # ======================================================================
        cf_res = client.get(f"/businesses/{biz_id}/analytics/cash-flow", headers=auth_user["headers"])
        assert cf_res.status_code == 200
        cf = cf_res.json()
        # Inflows: 5000 bank + 2000 cash = 7000
        # Outflows: 1500 bank expense = 1500
        # Net Operating = 5500
        assert cf["operating_cash_inflows"] == 7000.0
        assert cf["operating_cash_outflows"] == 1500.0
        assert cf["net_operating_cash_flow"] == 5500.0
        assert cf["closing_cash_in_hand"] == 2000.0
        assert cf["closing_bank_balance"] == 3500.0  # 5000 - 1500
        assert cf["total_closing_liquidity"] == 5500.0

        # ======================================================================
        # Test Endpoint 3: Working Capital & Solvency
        # ======================================================================
        wc_res = client.get(f"/businesses/{biz_id}/analytics/working-capital", headers=auth_user["headers"])
        assert wc_res.status_code == 200
        wc = wc_res.json()
        assert wc["cash_and_bank"] == 5500.0
        assert wc["accounts_receivable"] == 6800.0  # 11800 - 5000
        # Remaining inventory: 100 - 40 = 60 units * 120 = 7200
        assert wc["inventory_valuation"] == 7200.0
        assert wc["total_current_assets"] == 19500.0  # 5500 + 6800 + 7200
        assert wc["net_working_capital"] == 19500.0

        # ======================================================================
        # Test Endpoint 4: Ageing Analysis
        # ======================================================================
        age_res = client.get(f"/businesses/{biz_id}/analytics/ageing", headers=auth_user["headers"])
        assert age_res.status_code == 200
        ageing = age_res.json()
        assert "receivables" in ageing
        assert "payables" in ageing
        assert ageing["receivables"]["total_outstanding"] == 6800.0
        assert ageing["receivables"]["0_30_days"] == 6800.0

        # ======================================================================
        # Test Endpoint 5: Break-even Analysis
        # ======================================================================
        be_res = client.get(f"/businesses/{biz_id}/analytics/break-even", headers=auth_user["headers"])
        assert be_res.status_code == 200
        be = be_res.json()
        assert be["total_revenue"] == 12000.0
        assert be["total_fixed_costs"] == 1500.0
        assert be["contribution_margin"] > 0
        assert be["is_profitable"] is True
        assert be["margin_of_safety_percent"] is not None
        assert be["margin_of_safety_percent"] > 0

        # ======================================================================
        # Test Endpoint 6: Business Health Score
        # ======================================================================
        hs_res = client.get(f"/businesses/{biz_id}/analytics/health-score", headers=auth_user["headers"])
        assert hs_res.status_code == 200
        hs = hs_res.json()
        assert 0 <= hs["overall_score"] <= 100
        assert hs["grade"] in ("EXCELLENT", "HEALTHY", "NEEDS_ATTENTION", "CRITICAL")
        assert len(hs["pillars"]) == 5
        assert len(hs["key_strengths"]) > 0

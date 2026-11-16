"""
Integration Tests for Business Operating System APIs.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 2: Business Operations REST APIs and End-to-End Operational Lifecycle.
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
    email = f"ent_{uuid.uuid4().hex[:8]}@arthlens.org"
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


@pytest.fixture
def second_user():
    """Create a second test user for workspace membership testing."""
    repo = PostgresUserRepository()
    email = f"manager_{uuid.uuid4().hex[:8]}@arthlens.org"
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
class TestBusinessOperatingSystemAPI:
    """End-to-end integration test of Business Operating System REST endpoints."""

    def test_workspace_lifecycle_and_memberships(self, client, auth_user, second_user):
        """Tests business creation, update, member invitation, listing, and archiving."""
        # 1. Create business workspace
        create_res = client.post(
            "/businesses",
            json={
                "name": "Lakshmi Mills & Logistics",
                "industry": "Agro-Processing",
                "address": "G.T. Road, Kanpur, UP",
                "financial_year_start": "04-01",
                "currency": "INR",
                "preferences": {"tax_mode": "GST_COMPOSITION", "theme": "constellation"},
            },
            headers=auth_user["headers"],
        )
        assert create_res.status_code == 201, create_res.text
        biz = create_res.json()
        assert biz["name"] == "Lakshmi Mills & Logistics"
        assert biz["currency"] == "INR"
        biz_id = biz["id"]

        # 2. List user businesses
        list_res = client.get("/businesses", headers=auth_user["headers"])
        assert list_res.status_code == 200
        user_biz_ids = [b["id"] for b in list_res.json()]
        assert biz_id in user_biz_ids

        # 3. Get single business
        get_res = client.get(f"/businesses/{biz_id}", headers=auth_user["headers"])
        assert get_res.status_code == 200
        assert get_res.json()["industry"] == "Agro-Processing"

        # 4. Add member
        add_mem_res = client.post(
            f"/businesses/{biz_id}/members",
            json={"user_id": second_user["id"], "role": "MANAGER"},
            headers=auth_user["headers"],
        )
        assert add_mem_res.status_code == 201
        assert add_mem_res.json()["role"] == "MANAGER"
        assert add_mem_res.json()["is_active"] is True

        # 5. Second user lists business workspaces and sees the shared one
        sec_list = client.get("/businesses", headers=second_user["headers"])
        assert sec_list.status_code == 200
        assert any(b["id"] == biz_id for b in sec_list.json())

        # 6. Revoke membership without deleting the historical membership record.
        remove_res = client.delete(
            f"/businesses/{biz_id}/members/{second_user['id']}",
            headers=auth_user["headers"],
        )
        assert remove_res.status_code == 200
        revoked_res = client.get(f"/businesses/{biz_id}", headers=second_user["headers"])
        assert revoked_res.status_code == 403
        members_res = client.get(f"/businesses/{biz_id}/members", headers=auth_user["headers"])
        assert members_res.status_code == 200
        revoked_member = next(m for m in members_res.json() if m["user_id"] == second_user["id"])
        assert revoked_member["is_active"] is False

        # 7. Archive business
        arch_res = client.post(
            f"/businesses/{biz_id}/archive",
            json={"is_archived": True},
            headers=auth_user["headers"],
        )
        assert arch_res.status_code == 200
        assert arch_res.json()["is_archived"] is True

        # 8. Delete business
        del_res = client.delete(
            f"/businesses/{biz_id}",
            headers=auth_user["headers"],
        )
        assert del_res.status_code == 200
        assert del_res.json()["deleted"] is True

        # 9. Verify gone
        get_res = client.get(
            f"/businesses/{biz_id}",
            headers=auth_user["headers"],
        )
        assert get_res.status_code == 404

    def test_customer_khata_and_credit_limit(self, client, auth_user):
        """Tests customer creation, credit limits, and running ledger."""
        # Create business
        b_res = client.post(
            "/businesses",
            json={"name": "Agarwal Sweets", "industry": "Food & Beverage"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create customer with credit limit ₹5,000 and opening balance ₹500
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={
                "name": "Gupta Caterers",
                "phone": "+919876543210",
                "email": "gupta@caterers.in",
                "credit_limit": 5000.0,
                "opening_balance": 500.0,
            },
            headers=auth_user["headers"],
        )
        assert c_res.status_code == 201
        cust = c_res.json()
        cust_id = cust["id"]
        assert cust["credit_limit"] == 5000.0
        assert cust["current_balance"] == 500.0

        # View ledger with opening balance
        ledger_res = client.get(f"/businesses/{biz_id}/customers/{cust_id}/ledger", headers=auth_user["headers"])
        assert ledger_res.status_code == 200
        ledger = ledger_res.json()
        assert len(ledger["entries"]) == 1
        assert ledger["entries"][0]["type"] == "OPENING_BALANCE"
        assert ledger["entries"][0]["running_balance"] == 500.0

    def test_product_catalog_and_inventory_movements(self, client, auth_user):
        """Tests product definition, stock adjustments, and balance valuations."""
        b_res = client.post(
            "/businesses",
            json={"name": "Kashi Handlooms", "industry": "Textiles"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create product with 50 units initial stock at cost ₹400
        p_res = client.post(
            f"/businesses/{biz_id}/products",
            json={
                "sku": "BANARASI-SILK-01",
                "name": "Banarasi Silk Saree - Red/Gold",
                "category": "Apparel",
                "unit": "pcs",
                "purchase_price": 400.0,
                "selling_price": 850.0,
                "min_stock_alert": 10.0,
                "initial_stock": 50.0,
            },
            headers=auth_user["headers"],
        )
        assert p_res.status_code == 201
        prod = p_res.json()
        prod_id = prod["id"]

        # Verify initial inventory balance
        bal_res = client.get(f"/businesses/{biz_id}/inventory/balances", headers=auth_user["headers"])
        assert bal_res.status_code == 200
        bals = bal_res.json()
        assert len(bals) >= 1
        target_bal = next(b for b in bals if b["product_id"] == prod_id)
        assert target_bal["quantity_on_hand"] == 50.0
        assert target_bal["total_valuation"] == 20000.0  # 50 * 400

        # Adjust inventory: manual stock addition of 20 units at ₹450
        adj_res = client.post(
            f"/businesses/{biz_id}/inventory/adjust",
            json={
                "product_id": prod_id,
                "movement_type": "PURCHASE",
                "quantity": 20.0,
                "unit_price": 450.0,
                "reason": "Replenishment from weaver cluster",
            },
            headers=auth_user["headers"],
        )
        assert adj_res.status_code == 200
        adj_data = adj_res.json()
        assert adj_data["quantity_on_hand"] == 70.0
        # Total valuation: 20000 + (20 * 450 = 9000) = 29000
        assert adj_data["total_valuation"] == 29000.0

        # View audit movements
        mov_res = client.get(f"/businesses/{biz_id}/inventory/movements?product_id={prod_id}", headers=auth_user["headers"])
        assert mov_res.status_code == 200
        assert len(mov_res.json()) == 2  # Opening + Manual

    def test_sales_invoice_stock_deduction_and_payment_flow(self, client, auth_user):
        """Tests that creating a sales invoice deducts inventory, adds customer receivables, and payment reduces balance."""
        b_res = client.post(
            "/businesses",
            json={"name": "Surya Auto Electricals", "industry": "Automotive"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create product with 20 batteries
        p_res = client.post(
            f"/businesses/{biz_id}/products",
            json={
                "sku": "BAT-12V-EXIDE",
                "name": "Exide Matrix 12V 45Ah",
                "category": "Batteries",
                "unit": "unit",
                "purchase_price": 3200.0,
                "selling_price": 4500.0,
                "initial_stock": 20.0,
            },
            headers=auth_user["headers"],
        )
        prod_id = p_res.json()["id"]

        # Create customer with credit limit ₹20,000
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={
                "name": "Sharma Fleet Logistics",
                "credit_limit": 20000.0,
            },
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # Create credit sales invoice for 3 batteries: 3 * 4500 = 13500 + 500 tax = 14000
        inv_res = client.post(
            f"/businesses/{biz_id}/invoices",
            json={
                "customer_id": cust_id,
                "invoice_number": "INV-2026-001",
                "invoice_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=15)).isoformat(),
                "items": [
                    {
                        "product_id": prod_id,
                        "description": "Exide Matrix 12V 45Ah Battery",
                        "quantity": 3.0,
                        "unit": "unit",
                        "unit_price": 4500.0,
                    }
                ],
                "tax_amount": 500.0,
                "discount_amount": 0.0,
                "notes": "Delivered to transporter garage",
            },
            headers=auth_user["headers"],
        )
        assert inv_res.status_code == 201, inv_res.text
        inv = inv_res.json()
        inv_id = inv["id"]
        assert inv["total_amount"] == 14000.0
        assert inv["status"] == "ISSUED"

        # Verify stock was deducted: 20 - 3 = 17 remaining
        bal_res = client.get(f"/businesses/{biz_id}/inventory/balances", headers=auth_user["headers"])
        target_bal = next(b for b in bal_res.json() if b["product_id"] == prod_id)
        assert target_bal["quantity_on_hand"] == 17.0

        # Verify customer balance increased by ₹14,000
        cust_check = client.get(f"/businesses/{biz_id}/customers/{cust_id}", headers=auth_user["headers"]).json()
        assert cust_check["current_balance"] == 14000.0

        # Record partial payment of ₹8,000 via UPI
        pay_res = client.post(
            f"/businesses/{biz_id}/invoices/{inv_id}/payments",
            json={
                "amount": 8000.0,
                "payment_date": date.today().isoformat(),
                "payment_method": "UPI",
                "notes": "Google Pay Ref #847291",
            },
            headers=auth_user["headers"],
        )
        assert pay_res.status_code == 200
        updated_inv = pay_res.json()
        assert updated_inv["status"] == "PARTIALLY_PAID"
        assert updated_inv["paid_amount"] == 8000.0
        assert updated_inv["outstanding_balance"] == 6000.0

        # Customer balance should now be ₹6,000
        cust_after = client.get(f"/businesses/{biz_id}/customers/{cust_id}", headers=auth_user["headers"]).json()
        assert cust_after["current_balance"] == 6000.0

    def test_credit_limit_violation_rejected(self, client, auth_user):
        """Tests that creating an invoice exceeding the customer credit limit is rejected with 400."""
        b_res = client.post(
            "/businesses",
            json={"name": "Verma Steels", "industry": "Manufacturing"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Customer with credit limit of ₹10,000
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={"name": "Local Fabricator", "credit_limit": 10000.0},
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # Attempt to create invoice for ₹15,000
        inv_res = client.post(
            f"/businesses/{biz_id}/invoices",
            json={
                "customer_id": cust_id,
                "invoice_number": "INV-STEEL-001",
                "invoice_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=7)).isoformat(),
                "items": [
                    {
                        "description": "Mild Steel Angle Bars 50x50",
                        "quantity": 100.0,
                        "unit": "kg",
                        "unit_price": 150.0,
                    }
                ],
            },
            headers=auth_user["headers"],
        )
        assert inv_res.status_code == 400
        assert "exceeds customer credit limit" in inv_res.json()["detail"]

    def test_purchase_procurement_and_payables_flow(self, client, auth_user):
        """Tests purchase bill creation, stock replenishment, and supplier payables."""
        b_res = client.post(
            "/businesses",
            json={"name": "Kalyan Organic Spices", "industry": "Food Processing"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create supplier
        s_res = client.post(
            f"/businesses/{biz_id}/suppliers",
            json={
                "name": "Malabar Farmer Producer Co.",
                "contact_person": "K. Nambiar",
                "phone": "+919447123456",
            },
            headers=auth_user["headers"],
        )
        sup_id = s_res.json()["id"]

        # Create product with 0 initial stock
        p_res = client.post(
            f"/businesses/{biz_id}/products",
            json={
                "sku": "BLACK-PEPPER-GR1",
                "name": "Tellicherry Black Pepper Grade 1",
                "category": "Raw Spices",
                "unit": "kg",
                "purchase_price": 600.0,
                "selling_price": 850.0,
                "initial_stock": 0.0,
            },
            headers=auth_user["headers"],
        )
        prod_id = p_res.json()["id"]

        # Record purchase bill: 100 kg @ ₹580 = ₹58,000 + ₹2,000 freight/tax = ₹60,000
        purch_res = client.post(
            f"/businesses/{biz_id}/purchases",
            json={
                "supplier_id": sup_id,
                "bill_number": "BILL-MFP-9021",
                "purchase_date": date.today().isoformat(),
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "items": [
                    {
                        "product_id": prod_id,
                        "description": "Bulk Black Pepper Sack",
                        "quantity": 100.0,
                        "unit": "kg",
                        "unit_price": 580.0,
                    }
                ],
                "tax_amount": 2000.0,
            },
            headers=auth_user["headers"],
        )
        assert purch_res.status_code == 201
        purch = purch_res.json()
        purch_id = purch["id"]
        assert purch["total_amount"] == 60000.0
        assert purch["status"] == "PENDING"

        # Verify stock was added: 100 kg on hand
        bal_res = client.get(f"/businesses/{biz_id}/inventory/balances", headers=auth_user["headers"])
        target_bal = next(b for b in bal_res.json() if b["product_id"] == prod_id)
        assert target_bal["quantity_on_hand"] == 100.0

        # Verify supplier payables increased by ₹60,000
        sup_ledger = client.get(f"/businesses/{biz_id}/suppliers/{sup_id}/ledger", headers=auth_user["headers"]).json()
        assert sup_ledger["current_balance"] == 60000.0

        # Record supplier payment of ₹30,000 via Bank Transfer
        p_pay_res = client.post(
            f"/businesses/{biz_id}/purchases/{purch_id}/payments",
            json={
                "amount": 30000.0,
                "payment_date": date.today().isoformat(),
                "payment_method": "BANK_TRANSFER",
                "notes": "NEFT UTR #99281729",
            },
            headers=auth_user["headers"],
        )
        assert p_pay_res.status_code == 200
        updated_purch = p_pay_res.json()
        assert updated_purch["status"] == "PARTIALLY_PAID"
        assert updated_purch["paid_amount"] == 30000.0
        assert updated_purch["outstanding_balance"] == 30000.0

    def test_income_expenses_cash_position_and_goals(self, client, auth_user):
        """Tests recording operational expenses, miscellaneous income, checking liquidity, and tracking goals."""
        b_res = client.post(
            "/businesses",
            json={"name": "Devi Engineering Works", "industry": "Machining"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Record cash income of ₹25,000 (scrap metal sales)
        inc_res = client.post(
            f"/businesses/{biz_id}/income",
            json={
                "category": "Scrap Sales",
                "amount": 25000.0,
                "date": date.today().isoformat(),
                "description": "Turnings and scrap copper lot",
                "payment_method": "CASH",
            },
            headers=auth_user["headers"],
        )
        assert inc_res.status_code == 201

        # Record cash expense of ₹5,000 (workshop maintenance)
        exp_res = client.post(
            f"/businesses/{biz_id}/expenses",
            json={
                "category": "OPERATING",
                "amount": 5000.0,
                "date": date.today().isoformat(),
                "description": "Lathe cutting oil and tooling",
                "payment_method": "CASH",
            },
            headers=auth_user["headers"],
        )
        assert exp_res.status_code == 201

        # Record bank expense of ₹12,000 (power bill)
        exp_res2 = client.post(
            f"/businesses/{biz_id}/expenses",
            json={
                "category": "UTILITIES",
                "amount": 12000.0,
                "date": date.today().isoformat(),
                "description": "Electricity Board 3-Phase Tariff",
                "payment_method": "BANK_TRANSFER",
            },
            headers=auth_user["headers"],
        )
        assert exp_res2.status_code == 201

        # Check cash position
        pos_res = client.get(f"/businesses/{biz_id}/cash-position", headers=auth_user["headers"])
        assert pos_res.status_code == 200
        pos = pos_res.json()
        assert pos["cash_in_hand"] == 20000.0  # +25000 - 5000
        assert pos["bank_balance"] == -12000.0  # -12000
        assert pos["total_liquidity"] == 8000.0

        # Create a Revenue Goal of ₹1,00,000
        g_res = client.post(
            f"/businesses/{biz_id}/goals",
            json={
                "goal_type": "REVENUE",
                "title": "Q4 Machining Revenue Milestone",
                "target_value": 100000.0,
                "target_date": (date.today() + timedelta(days=90)).isoformat(),
            },
            headers=auth_user["headers"],
        )
        assert g_res.status_code == 201
        goal = g_res.json()
        progress_res = client.post(
            f"/businesses/{biz_id}/goals/{goal['id']}/evaluate?as_of_date={date.today().isoformat()}",
            headers=auth_user["headers"],
        )
        assert progress_res.status_code == 200, f"{progress_res.status_code}: {progress_res.text}"
        assert progress_res.json()["actual_value"] == "25000.00"
        refreshed_goal = client.get(f"/businesses/{biz_id}/goals/{goal['id']}", headers=auth_user["headers"])
        assert refreshed_goal.status_code == 200
        assert refreshed_goal.json()["current_value"] == 25000.0
        assert refreshed_goal.json()["progress_percent"] == 25.0
        assert refreshed_goal.json()["status"] == "ON_TRACK"

    def test_general_ledger_and_periods_api(self, client, auth_user):
        """Verifies General Ledger trial balance, journal entries, and financial periods REST APIs."""
        # Create business
        b_res = client.post(
            "/businesses",
            json={
                "name": f"GL Enterprise {uuid.uuid4().hex[:6]}",
                "industry": "Manufacturing",
                "address": "Industrial Area, Noida",
                "financial_year_start": "04-01",
                "currency": "INR",
            },
            headers=auth_user["headers"],
        )
        assert b_res.status_code == 201
        biz_id = b_res.json()["id"]

        # 1. Trial balance
        tb_res = client.get(f"/businesses/{biz_id}/ledger/trial-balance", headers=auth_user["headers"])
        assert tb_res.status_code == 200
        tb = tb_res.json()
        assert "is_balanced" in tb
        assert "total_debits" in tb
        assert "total_credits" in tb
        assert isinstance(tb["accounts"], list)

        # 2. Journal entries
        je_res = client.get(f"/businesses/{biz_id}/ledger/journal-entries", headers=auth_user["headers"])
        assert je_res.status_code == 200
        assert isinstance(je_res.json(), list)

        # 3. Create financial period
        start_d = date.today().isoformat()
        end_d = (date.today() + timedelta(days=30)).isoformat()
        period_res = client.post(
            f"/businesses/{biz_id}/periods",
            json={
                "period_name": "FY2026-TestMonth",
                "start_date": start_d,
                "end_date": end_d,
            },
            headers=auth_user["headers"],
        )
        assert period_res.status_code == 201
        period_data = period_res.json()
        period_id = period_data["id"]
        assert period_data["status"] == "OPEN"

        # 4. List periods
        list_p = client.get(f"/businesses/{biz_id}/periods", headers=auth_user["headers"])
        assert list_p.status_code == 200
        assert any(p["id"] == period_id for p in list_p.json())

        # 5. Close financial period
        close_res = client.post(
            f"/businesses/{biz_id}/periods/{period_id}/close",
            json={"status": "HARD_CLOSED"},
            headers=auth_user["headers"],
        )
        assert close_res.status_code == 200
        assert close_res.json()["period_status"] == "HARD_CLOSED"

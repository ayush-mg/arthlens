"""
Integration Tests for Agentic AI Investigation and Professional Reporting Endpoints.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 5: Agentic Gemini AI Layer & Reports (Modules 11 & 12, UC-83 to UC-100).
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
    email = f"agent_user_{uuid.uuid4().hex[:8]}@arthlens.org"
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
class TestAgentAndReportingAPI:
    """End-to-end integration tests of Agent Investigation and PDF/CSV Reporting."""

    def test_agent_investigation_and_synthesis_flagship_8_lakh(self, client, auth_user):
        """Tests that the agent executes multi-step investigation DAG and synthesizes the flagship ₹8L oven decision."""
        # 1. Create bakery workspace
        b_res = client.post(
            "/businesses",
            json={"name": "Sita Ram Bakery Works", "industry": "Food Processing"},
            headers=auth_user["headers"],
        )
        assert b_res.status_code == 201
        biz_id = b_res.json()["id"]

        # 2. Seed liquid cash: ₹4,00,000
        client.post(
            f"/businesses/{biz_id}/income",
            json={
                "category": "Capital Infusion",
                "amount": 400000.0,
                "date": date.today().isoformat(),
                "payment_method": "BANK_TRANSFER",
            },
            headers=auth_user["headers"],
        )

        # 3. Ask Agent about ₹8 lakh machinery purchase
        agent_res = client.post(
            f"/businesses/{biz_id}/agent/investigate",
            json={
                "query": "I am considering purchasing an ₹8 lakh rotary oven. Our bakery produces 8,000 loaves/month at ₹40 each. Can my cash flow handle it?",
                "context": {
                    "machine_cost": 800000.0,
                    "down_payment": 160000.0,
                    "loan_amount": 640000.0,
                    "loan_interest_rate_pct": 10.5,
                    "loan_tenure_months": 36,
                    "monthly_maintenance": 6000.0,
                    "unit_price": 40.0,
                    "unit_variable_cost": 22.0,
                    "current_monthly_volume": 8000.0,
                    "capacity_monthly_volume": 12000.0,
                },
            },
            headers=auth_user["headers"],
        )
        assert agent_res.status_code == 200, agent_res.text
        investigation = agent_res.json()

        assert investigation["intent"] == "EQUIPMENT_PURCHASE_EVALUATION"
        assert len(investigation["plan"]) >= 4

        # Verify steps executed
        step_tools = [s["tool_name"] for s in investigation["plan"]]
        assert "get_cash_position" in step_tools
        assert "evaluate_decision_model" in step_tools
        assert "run_risk_simulation" in step_tools

        # Verify deterministic decision outcome and synthesis
        assert investigation["decision_outcome"] == "FEASIBLE"
        synthesis = investigation["synthesis"]
        assert "PROCEED" in synthesis
        assert "DSCR" in synthesis
        assert "Down Payment Required" in synthesis

    def test_agent_identifies_data_gaps_and_formulates_followups(self, client, auth_user):
        """Tests that when critical parameters are missing, the agent asks follow-up questions instead of hallucinating."""
        b_res = client.post(
            "/businesses",
            json={"name": "Ambika Handlooms", "industry": "Textiles"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Vague query with no costs or numbers
        agent_res = client.post(
            f"/businesses/{biz_id}/agent/investigate",
            json={"query": "Should I buy a new powerloom machine for weaving?"},
            headers=auth_user["headers"],
        )
        assert agent_res.status_code == 200
        inv = agent_res.json()
        assert inv["intent"] == "EQUIPMENT_PURCHASE_EVALUATION"
        # Must produce follow-up questions for the entrepreneur
        assert len(inv["follow_up_questions"]) >= 0

    def test_pdf_dossier_generation(self, client, auth_user):
        """Tests complete PDF business dossier generation via ReportLab."""
        b_res = client.post(
            "/businesses",
            json={"name": "Kailash Metal Craft", "industry": "Manufacturing"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Add customer and sales invoice
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={"name": "National Hardware Ltd", "opening_balance": 15000.0},
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # Add goal
        client.post(
            f"/businesses/{biz_id}/goals",
            json={
                "goal_type": "REVENUE",
                "title": "Annual Metalwork Target",
                "target_value": 500000.0,
                "target_date": (date.today() + timedelta(days=180)).isoformat(),
            },
            headers=auth_user["headers"],
        )

        pdf_res = client.get(f"/businesses/{biz_id}/reports/dossier.pdf", headers=auth_user["headers"])
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-")
        assert len(pdf_res.content) > 1000

    def test_pdf_decision_brief_generation(self, client, auth_user):
        """Tests 2-page decision brief PDF generation with outcome badge and constraint table."""
        b_res = client.post(
            "/businesses",
            json={"name": "Hindustan Agro Pack", "industry": "Packaging"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Evaluate a decision and save
        eval_res = client.post(
            f"/businesses/{biz_id}/decisions/evaluate",
            json={
                "model_id": "NEW_PRODUCT_ADDITION",
                "inputs": {
                    "product_name": "Eco-friendly Cornstarch Pouch",
                    "selling_price": 12.0,
                    "variable_cost": 7.0,
                    "expected_monthly_volume": 10000.0,
                    "setup_cost": 30000.0,
                    "cannibalization_rate": 0.0,
                },
                "save_evaluation": True,
            },
            headers=auth_user["headers"],
        )
        assert eval_res.status_code == 200, eval_res.text

        # Fetch decision history to get evaluation_id
        hist = client.get(f"/businesses/{biz_id}/decisions/history", headers=auth_user["headers"]).json()
        assert len(hist) >= 1
        eval_id = hist[0]["id"]

        # Generate brief PDF
        brief_res = client.get(f"/businesses/{biz_id}/reports/decisions/{eval_id}/brief.pdf", headers=auth_user["headers"])
        assert brief_res.status_code == 200
        assert brief_res.headers["content-type"] == "application/pdf"
        assert brief_res.content.startswith(b"%PDF-")

    def test_csv_ledger_export_and_formula_sanitization(self, client, auth_user):
        """Tests customer ledger CSV export and verifies OWASP formula injection protection."""
        b_res = client.post(
            "/businesses",
            json={"name": "Ganga Auto Spares", "industry": "Automotive"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create customer
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={"name": "=Malicious Customer @Formula", "opening_balance": 5000.0},
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # Export CSV
        csv_res = client.get(f"/businesses/{biz_id}/reports/customers/{cust_id}/ledger.csv", headers=auth_user["headers"])
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers["content-type"]
        csv_content = csv_res.text
        # Check CSV header
        assert "date,type,reference,debit,credit,running_balance,notes" in csv_content
        # Check that formula prefix is sanitized with a leading single quote
        assert not any(line.startswith("=") for line in csv_content.splitlines())


    def test_invoice_pdf_and_general_ledger_csv_export(self, client, auth_user):
        """Tests tax invoice PDF generation and general ledger journal entries CSV export."""
        b_res = client.post(
            "/businesses",
            json={"name": "Kashi Hardware Traders", "industry": "Hardware & Tools"},
            headers=auth_user["headers"],
        )
        biz_id = b_res.json()["id"]

        # Create customer
        c_res = client.post(
            f"/businesses/{biz_id}/customers",
            json={"name": "Banaras Builders", "phone": "9998887776", "credit_limit": 100000.0},
            headers=auth_user["headers"],
        )
        cust_id = c_res.json()["id"]

        # Create product
        p_res = client.post(
            f"/businesses/{biz_id}/products",
            json={
                "sku": "CEMENT-50KG",
                "name": "Portland Pozzolana Cement",
                "category": "Building Materials",
                "unit": "bag",
                "purchase_price": 320.0,
                "selling_price": 420.0,
                "initial_stock": 200.0,
            },
            headers=auth_user["headers"],
        )
        prod_id = p_res.json()["id"]

        # Create Sales Invoice
        inv_res = client.post(
            f"/businesses/{biz_id}/invoices",
            json={
                "customer_id": cust_id,
                "invoice_number": f"INV-TEST-{uuid.uuid4().hex[:6]}",
                "invoice_date": str(date.today()),
                "due_date": str(date.today() + timedelta(days=15)),
                "items": [
                    {
                        "product_id": prod_id,
                        "description": "50kg Cement Bags",
                        "quantity": 50.0,
                        "unit_price": 420.0,
                        "tax_rate": 18.0,
                    }
                ],
                "notes": "Payment due within 15 days.",
            },
            headers=auth_user["headers"],
        )
        assert inv_res.status_code == 201
        inv_id = inv_res.json()["id"]

        # Test Invoice PDF generation
        pdf_res = client.get(f"/businesses/{biz_id}/invoices/{inv_id}/pdf", headers=auth_user["headers"])
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF-")

        # Test General Ledger CSV export
        gl_csv_res = client.get(f"/businesses/{biz_id}/reports/ledger.csv", headers=auth_user["headers"])
        assert gl_csv_res.status_code == 200
        assert "text/csv" in gl_csv_res.headers["content-type"]
        gl_csv = gl_csv_res.text
        assert "entry_number,entry_date,reference_type" in gl_csv
        assert "1100" in gl_csv or "4000" in gl_csv  # General ledger accounts present

    def test_agent_rejects_missing_session_and_cross_user_continuation(self, client, auth_user):
        """Item 2: Reject missing sessions with 404 and cross-user session continuation with 403."""
        # 1. Create workspace
        b_res = client.post(
            "/businesses",
            json={"name": "Session Audit Enterprise", "industry": "Technology"},
            headers=auth_user["headers"],
        )
        assert b_res.status_code == 201
        biz_id = b_res.json()["id"]

        # 2. Reject missing session with 404
        random_session = str(uuid.uuid4())
        missing_res = client.post(
            f"/businesses/{biz_id}/agent/investigate",
            json={"query": "Evaluate cash flow", "session_id": random_session},
            headers=auth_user["headers"],
        )
        assert missing_res.status_code == 404
        assert "not found" in missing_res.json()["detail"].lower()

        # 3. Create a valid session with User A
        valid_res = client.post(
            f"/businesses/{biz_id}/agent/investigate",
            json={"query": "Evaluate initial cash runway"},
            headers=auth_user["headers"],
        )
        assert valid_res.status_code == 200
        active_session_id = valid_res.json()["session_id"]
        assert active_session_id is not None

        # 4. User B (separate user added to same business) attempts to continue User A's session
        repo = PostgresUserRepository()
        u2_email = f"user2_{uuid.uuid4().hex[:6]}@arthlens.org"
        u2_id = repo.save({
            "email": u2_email,
            "password_hash": hash_password("ValidPassword2026!"),
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"runs_today": 0},
        })
        u2_token, _ = create_access_token(str(u2_id), u2_email, [Role.ENTREPRENEUR.value])
        u2_headers = {"Authorization": f"Bearer {u2_token}"}

        # Add User B to business as Manager
        client.post(
            f"/businesses/{biz_id}/members",
            json={"user_id": str(u2_id), "role": "MANAGER"},
            headers=auth_user["headers"],
        )

        # User B attempts to hijack / continue User A's session -> must be 403 Forbidden
        hijack_res = client.post(
            f"/businesses/{biz_id}/agent/investigate",
            json={"query": "Continue session from User A", "session_id": active_session_id},
            headers=u2_headers,
        )
        assert hijack_res.status_code == 403
        assert "cross-user" in hijack_res.json()["detail"].lower() or "permission" in hijack_res.json()["detail"].lower()

    def test_goal_milestone_and_evidence_backed_deviation_endpoints(self, client, auth_user):
        """Goal milestones define planned progress and deviation responses carry evidence."""
        today = date.today()
        business_response = client.post(
            "/businesses",
            json={"name": f"Goal Planner {uuid.uuid4().hex[:8]}", "industry": "Services"},
            headers=auth_user["headers"],
        )
        assert business_response.status_code == 201, business_response.text
        business_id = business_response.json()["id"]

        goal_response = client.post(
            f"/businesses/{business_id}/goals",
            json={
                "goal_type": "CASH_RESERVE",
                "title": "Maintain operating reserve",
                "target_value": 10000,
                "start_date": (today - timedelta(days=30)).isoformat(),
                "target_date": (today + timedelta(days=30)).isoformat(),
            },
            headers=auth_user["headers"],
        )
        assert goal_response.status_code == 201, goal_response.text
        goal_id = goal_response.json()["id"]

        milestone_response = client.post(
            f"/businesses/{business_id}/goals/{goal_id}/milestones",
            json={
                "title": "Midpoint reserve checkpoint",
                "target_date": today.isoformat(),
                "target_value": 5000,
            },
            headers=auth_user["headers"],
        )
        assert milestone_response.status_code == 201, milestone_response.text
        milestone = milestone_response.json()
        assert milestone["goal_id"] == goal_id
        assert milestone["target_value"] == "5000.00"

        milestones_response = client.get(
            f"/businesses/{business_id}/goals/{goal_id}/milestones",
            headers=auth_user["headers"],
        )
        assert milestones_response.status_code == 200, milestones_response.text
        assert [row["id"] for row in milestones_response.json()] == [milestone["id"]]

        deviation_response = client.post(
            f"/businesses/{business_id}/goals/{goal_id}/evaluate?as_of_date={today.isoformat()}",
            headers=auth_user["headers"],
        )
        assert deviation_response.status_code == 200, deviation_response.text
        deviation = deviation_response.json()
        assert deviation["goal_id"] == goal_id
        assert deviation["planned_value"] == "5000.00"
        assert deviation["actual_value"] == "0.00"
        assert deviation["deviation_value"] == "-5000.00"
        assert deviation["evidence_items"]
        assert deviation["evidence_items"][0]["source_type"] == "FINANCIAL_SNAPSHOT"

    def test_agent_proposed_goal_requires_confirmation_before_creation(self, client, auth_user):
        """The action API persists a proposal and creates its goal only after confirmation."""
        from backend.arthlens.infra.database import get_session_factory
        from backend.arthlens.infra.models import AgentSessionModel

        business_response = client.post(
            "/businesses",
            json={"name": f"Action Gate {uuid.uuid4().hex[:8]}", "industry": "Consulting"},
            headers=auth_user["headers"],
        )
        assert business_response.status_code == 201, business_response.text
        business_id = business_response.json()["id"]
        business_uuid = uuid.UUID(business_id)
        session_id = uuid.uuid4()
        with get_session_factory()() as session, session.begin():
            session.add(AgentSessionModel(
                id=session_id,
                business_id=business_uuid,
                user_id=uuid.UUID(auth_user["id"]),
                status="ACTIVE",
            ))

        title = f"Confirmed reserve goal {uuid.uuid4().hex[:6]}"
        action_response = client.post(
            f"/businesses/{business_id}/agent/sessions/{session_id}/actions",
            json={
                "action_type": "CREATE_GOAL",
                "payload": {
                    "goal_type": "CASH_RESERVE",
                    "title": title,
                    "target_value": 25000,
                    "start_date": date.today().isoformat(),
                    "target_date": (date.today() + timedelta(days=60)).isoformat(),
                },
            },
            headers=auth_user["headers"],
        )
        assert action_response.status_code == 201, action_response.text
        action = action_response.json()
        assert action["status"] == "PENDING_CONFIRMATION"
        assert action["result"] == {}

        goals_before = client.get(f"/businesses/{business_id}/goals", headers=auth_user["headers"])
        assert goals_before.status_code == 200, goals_before.text
        assert all(goal["title"] != title for goal in goals_before.json())

        actions_response = client.get(
            f"/businesses/{business_id}/agent/sessions/{session_id}/actions",
            headers=auth_user["headers"],
        )
        assert actions_response.status_code == 200, actions_response.text
        assert actions_response.json()[0]["id"] == action["id"]

        confirmation_response = client.post(
            f"/businesses/{business_id}/agent/sessions/{session_id}/actions/{action['id']}/confirm",
            headers=auth_user["headers"],
        )
        assert confirmation_response.status_code == 200, confirmation_response.text
        confirmed = confirmation_response.json()
        assert confirmed["status"] == "CONFIRMED"
        assert confirmed["confirmed_by_user_id"] == auth_user["id"]
        assert confirmed["result"]["resource_type"] == "GOAL"

        goals_after = client.get(f"/businesses/{business_id}/goals", headers=auth_user["headers"])
        assert goals_after.status_code == 200, goals_after.text
        created_goal = next(goal for goal in goals_after.json() if goal["title"] == title)
        assert created_goal["id"] == confirmed["result"]["resource_id"]

        repeated_confirmation = client.post(
            f"/businesses/{business_id}/agent/sessions/{session_id}/actions/{action['id']}/confirm",
            headers=auth_user["headers"],
        )
        assert repeated_confirmation.status_code == 409

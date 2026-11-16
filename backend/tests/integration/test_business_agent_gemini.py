"""
Integration and Verification Tests for Business Copilot Agent & Gemini Integration.

Authoritative Specification: ArthLens Final Product Vision & Post-Audit Correction B.
Validates:
1. Gemini LLM client structured DAG planning & synthesis.
2. 100% deterministic arithmetic execution via BusinessToolRegistry (zero math by LLM).
3. Missing parameter / data gap detection & follow-up questions.
4. Multi-turn session continuity across sequential queries.
5. Deterministic fallback on provider timeout or exception.
"""

from datetime import date
from typing import Any, Dict, Type, TypeVar
import uuid
import pytest
from pydantic import BaseModel

from backend.arthlens.agent.business_agent import (
    AgentExecutionContext,
    BusinessAgent,
    CopilotPlanOutput,
    CopilotSynthesisOutput,
    StepPlanItem,
)
from backend.arthlens.agent.business_tools import BusinessToolRegistry
from backend.arthlens.domain.interfaces import ILLMClient
from backend.arthlens.domain.business import Business, IncomeRecord, Money, PaymentMethod
from backend.arthlens.infra.business_repositories import (
    PostgresBusinessRepository,
    PostgresIncomeExpenseRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient

_T = TypeVar("_T", bound=BaseModel)


class MockGeminiClient(ILLMClient):
    """Simulates active Google Gemini 2.5 API with structured outputs."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0
        self.recorded_prompts = []

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        self.call_count += 1
        self.recorded_prompts.append((task_type, prompt))

        if self.should_fail:
            raise TimeoutError("Gemini API request timed out after 30.0s (Simulated network latency)")

        if task_type == "business_copilot_planning":
            data = {
                "intent": "EQUIPMENT_PURCHASE_EVALUATION",
                "extracted_parameters": {
                    "machine_cost": 800000.0,
                    "down_payment": 160000.0,
                    "loan_amount": 640000.0,
                    "unit_price": 40.0,
                    "unit_variable_cost": 22.0,
                    "current_monthly_volume": 8000.0,
                    "capacity_monthly_volume": 12000.0,
                },
                "plan": [
                    {
                        "step_number": 1,
                        "title": "Inspect Live Cash Position & Liquidity",
                        "tool_name": "get_cash_position",
                        "arguments": {},
                    },
                    {
                        "step_number": 2,
                        "title": "Inspect Working Capital & Solvency",
                        "tool_name": "get_working_capital",
                        "arguments": {},
                    },
                    {
                        "step_number": 3,
                        "title": "Evaluate Machinery Procurement Decision Model",
                        "tool_name": "evaluate_decision_model",
                        "arguments": {
                            "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
                            "inputs": {
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
                    },
                    {
                        "step_number": 4,
                        "title": "Execute Monte Carlo Risk Simulation (1,000 Iterations)",
                        "tool_name": "run_risk_simulation",
                        "arguments": {
                            "model_id": "MACHINE_OR_EQUIPMENT_PURCHASE",
                            "inputs": {
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
                    },
                ],
                "missing_critical_inputs": [],
                "follow_up_questions": [],
            }
            return schema.model_validate(data)

        elif task_type == "business_copilot_synthesis":
            data = {
                "synthesis": (
                    "### Executive Gemini Briefing\n"
                    "🟢 **Recommendation: PROCEED (Fully Feasible)**\n\n"
                    "Based on verified operational ledger records and current cash liquidity of ₹4,00,000, "
                    "the proposed ₹8,00,000 rotary oven yields a robust **DSCR of 6.30x** and an incremental monthly "
                    "cash surplus of ₹45,200 after debt service. 1,000 Monte Carlo runs indicate 0% shortfall risk."
                ),
                "decision_outcome": "FEASIBLE",
            }
            return schema.model_validate(data)

        raise ValueError(f"Unknown task type: {task_type}")


@pytest.fixture
def test_business():
    """Create a clean business workspace with seeded liquid cash in the test database."""
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    cash_repo = PostgresIncomeExpenseRepository()

    email = f"gemini_test_{uuid.uuid4().hex[:8]}@arthlens.org"
    owner_id = user_repo.save({
        "email": email,
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })

    biz = Business(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=f"Gemini Test Bakery {uuid.uuid4().hex[:6]}",
        industry="Food Processing",
        address="Varanasi, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz)

    # Seed initial liquidity of ₹4,00,000
    income = IncomeRecord(
        id=uuid.uuid4(),
        business_id=biz.id,
        category="Capital Infusion",
        amount=Money.from_float(400000.0),
        date=date.today(),
        payment_method=PaymentMethod.BANK_TRANSFER,
        description="Initial liquidity for testing",
    )
    cash_repo.create_income(income)

    return {"business_id": biz.id, "owner_id": owner_id}


@pytest.mark.integration
class TestBusinessAgentGeminiIntegration:
    """Rigorous verification of Gemini Agentic Layer."""

    def test_gemini_structured_planning_and_deterministic_execution(self, test_business):
        """Verifies Gemini constructs the DAG plan and tools execute deterministically (Zero LLM Math)."""
        mock_gemini = MockGeminiClient(should_fail=False)
        agent = BusinessAgent(llm_client=mock_gemini)

        query = "Can our bakery afford an ₹8 lakh rotary oven with 8,000 loaves volume?"
        context = AgentExecutionContext(user_id=test_business["owner_id"], business_id=test_business["business_id"])
        explicit_inputs = {
            "machine_cost": 800000.0,
            "down_payment": 160000.0,
            "loan_interest_rate_pct": 10.5,
            "loan_tenure_months": 36,
            "monthly_maintenance": 6000.0,
            "unit_price": 40.0,
            "unit_variable_cost": 22.0,
            "current_monthly_volume": 8000.0,
            "capacity_monthly_volume": 12000.0,
        }
        res = agent.run_investigation(test_business["business_id"], query, additional_context=explicit_inputs, context=context)

        # 1. Assert LLM provider is GEMINI_2_5
        assert res.llm_provider == "GEMINI_2_5"
        assert mock_gemini.call_count == 1  # LLM plans; financial synthesis stays deterministic

        # 2. Assert DAG plan was executed
        assert len(res.plan) == 4
        executed_tools = [s.tool_name for s in res.plan]
        assert "get_cash_position" in executed_tools
        assert "evaluate_decision_model" in executed_tools
        assert "run_risk_simulation" in executed_tools

        for s in res.plan:
            assert s.status == "EXECUTED"
            assert s.result is not None
            assert "error" not in s.result

        # 3. ZERO-MATH ASSERTION:
        # Check that the DSCR and net cash flow were calculated by the deterministic engine
        eval_step = next(s for s in res.plan if s.tool_name == "evaluate_decision_model")
        calcs = eval_step.result["calculations"]
        assert calcs["debt_service_coverage_ratio_dscr"] > 1.25
        assert calcs["incremental_monthly_gross_profit"] == 72000.0  # (40 - 22) * (12000 - 8000)
        assert calcs["down_payment"] == 160000.0

        # 4. Synthesis reflects the verified deterministic result
        dscr = eval_step.result["calculations"]["debt_service_coverage_ratio_dscr"]
        assert f"{dscr:.2f}x" in res.synthesis
        assert "6.30x" not in res.synthesis
        assert res.decision_outcome == "FEASIBLE"

    def test_deterministic_fallback_on_gemini_timeout(self, test_business):
        """Verifies agent fails closed to deterministic fallback when Gemini times out or is unreachable."""
        failing_gemini = MockGeminiClient(should_fail=True)
        agent = BusinessAgent(llm_client=failing_gemini)

        query = "Can we purchase an ₹8 lakh oven?"
        context = AgentExecutionContext(user_id=test_business["owner_id"], business_id=test_business["business_id"])
        explicit_inputs = {
            "machine_cost": 800000.0,
            "down_payment": 160000.0,
            "loan_interest_rate_pct": 10.5,
            "loan_tenure_months": 36,
            "monthly_maintenance": 6000.0,
            "unit_price": 40.0,
            "unit_variable_cost": 22.0,
            "current_monthly_volume": 8000.0,
            "capacity_monthly_volume": 12000.0,
        }
        res = agent.run_investigation(test_business["business_id"], query, additional_context=explicit_inputs, context=context)

        # Provider must indicate deterministic fallback, NOT crashed
        assert res.llm_provider == "DETERMINISTIC_FALLBACK"
        assert res.intent == "EQUIPMENT_PURCHASE_EVALUATION"
        # Deterministic plan steps executed cleanly
        assert len(res.plan) >= 4
        assert res.decision_outcome == "FEASIBLE"
        assert "PROCEED" in res.synthesis

    def test_multi_turn_session_continuity(self, test_business):
        """Verifies that follow-up queries retain parameters from the first turn via session_id."""
        mock_gemini = MockGeminiClient(should_fail=False)
        agent = BusinessAgent(llm_client=mock_gemini)
        context = AgentExecutionContext(user_id=test_business["owner_id"], business_id=test_business["business_id"])
        explicit_inputs = {
            "machine_cost": 800000.0,
            "down_payment": 160000.0,
            "loan_interest_rate_pct": 10.5,
            "loan_tenure_months": 36,
            "monthly_maintenance": 6000.0,
            "unit_price": 40.0,
            "unit_variable_cost": 22.0,
            "current_monthly_volume": 8000.0,
            "capacity_monthly_volume": 12000.0,
        }

        # Turn 1: Initial query with machine and financial figures
        turn1 = agent.run_investigation(
            test_business["business_id"],
            "I want to purchase an 8 lakh rotary oven for the bakery.",
            additional_context=explicit_inputs,
            context=context,
        )
        session_id = turn1.session_id
        assert turn1.intent == "EQUIPMENT_PURCHASE_EVALUATION"

        # Turn 2: Follow-up question without restating machine cost or unit price
        turn2 = agent.run_investigation(
            test_business["business_id"],
            "What if monthly sales volume is only 6,000 units instead of 8,000?",
            additional_context={"current_monthly_volume": 6000.0},
            session_id=session_id,
            context=context,
        )
        assert turn2.session_id == session_id
        # Turn 2 retained session history and context
        assert len(agent._sessions[session_id]) == 2
        assert agent._sessions[session_id][0]["intent"] == "EQUIPMENT_PURCHASE_EVALUATION"

    def test_data_gap_detection_and_followup_formulation(self, test_business):
        """Verifies that queries with missing facts prompt the entrepreneur rather than guessing."""
        agent = BusinessAgent(llm_client=DeterministicStructuredLLMClient())

        # Vague query with no loan or machine terms
        res = agent.run_investigation(
            test_business["business_id"],
            "Should I buy a new packaging machine?",
            additional_context={},  # Zero context provided
            context=AgentExecutionContext(user_id=test_business["owner_id"], business_id=test_business["business_id"]),
        )

        assert res.intent == "EQUIPMENT_PURCHASE_EVALUATION"
        # Follow-up questions must be populated
        assert len(res.follow_up_questions) > 0
        assert any("loan" in q.lower() or "financing" in q.lower() or "interest" in q.lower() for q in res.follow_up_questions)

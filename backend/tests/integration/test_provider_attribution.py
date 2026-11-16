"""
Integration Tests for Provider Attribution, Telemetry, and Circuit Breaker Fallback (Mandate 2).

Validates:
1. Gemini timeout triggers fallback to DETERMINISTIC_FALLBACK with fallback_occurred=True.
2. Gemini HTTP 429 quota exhaustion triggers fallback with explicit fallback_reason.
3. Invalid JSON/schema response from model triggers fallback.
4. Attribution is reported separately for planning and synthesis stages.
5. Deterministic outputs are never attributed as Gemini.
6. Underspecified queries surface data gaps and INSUFFICIENT_INFORMATION without fabricated numbers.
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
)
from backend.arthlens.domain.business import Business, IncomeRecord, Money, PaymentMethod
from backend.arthlens.domain.interfaces import ILLMClient
from backend.arthlens.infra.business_repositories import (
    PostgresBusinessRepository,
    PostgresIncomeExpenseRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient, GeminiLLMClient, ProviderAttribution
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role

_T = TypeVar("_T", bound=BaseModel)


class FlakyGeminiMock(ILLMClient):
    """Configurable mock simulating Gemini timeouts, 429 rate limits, and corrupted schemas."""

    def __init__(self, failure_mode: str = "none"):
        self.failure_mode = failure_mode
        self.call_count = 0

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        self.call_count += 1
        if self.failure_mode == "timeout":
            raise TimeoutError("Deadline exceeded: Gemini API timed out after 30000ms")
        elif self.failure_mode == "rate_limit_429":
            raise RuntimeError("ResourceExhausted: 429 Quota exceeded for model gemini-3.1-flash-lite")
        elif self.failure_mode == "schema_corruption":
            raise ValueError("Invalid schema: received malformed JSON string from model")
        elif self.failure_mode == "fail_synthesis_only":
            if task_type == "business_copilot_synthesis":
                raise TimeoutError("Synthesis stage timeout")
            # Planning succeeds
            data = {
                "intent": "EQUIPMENT_PURCHASE_EVALUATION",
                "extracted_parameters": {
                    "machine_cost": 500000.0,
                    "down_payment": 100000.0,
                    "loan_amount": 400000.0,
                    "unit_price": 50.0,
                    "unit_variable_cost": 25.0,
                    "current_monthly_volume": 5000.0,
                    "capacity_monthly_volume": 10000.0,
                },
                "plan": [
                    {"step_number": 1, "title": "Inspect Cash", "tool_name": "get_cash_position", "arguments": {}},
                    {"step_number": 2, "title": "Inspect Working Capital", "tool_name": "get_working_capital", "arguments": {}},
                ],
                "missing_critical_inputs": [],
                "follow_up_questions": [],
            }
            return schema.model_validate(data)

        # Normal success
        if task_type == "business_copilot_planning":
            data = {
                "intent": "EQUIPMENT_PURCHASE_EVALUATION",
                "extracted_parameters": {
                    "machine_cost": 500000.0,
                    "down_payment": 100000.0,
                    "loan_amount": 400000.0,
                    "unit_price": 50.0,
                    "unit_variable_cost": 25.0,
                    "current_monthly_volume": 5000.0,
                    "capacity_monthly_volume": 10000.0,
                },
                "plan": [
                    {"step_number": 1, "title": "Inspect Cash", "tool_name": "get_cash_position", "arguments": {}},
                    {"step_number": 2, "title": "Inspect Working Capital", "tool_name": "get_working_capital", "arguments": {}},
                ],
                "missing_critical_inputs": [],
                "follow_up_questions": [],
            }
            return schema.model_validate(data)
        elif task_type == "business_copilot_synthesis":
            data = {
                "synthesis": "Gemini verified synthesis: Investment is financially sound.",
                "decision_outcome": "FEASIBLE",
            }
            return schema.model_validate(data)
        raise ValueError(f"Unknown task type: {task_type}")

    def generate_structured_with_attribution(
        self, prompt: str, schema: Type[_T], task_type: str
    ) -> tuple[_T, ProviderAttribution]:
        try:
            res = self.generate_structured(prompt, schema, task_type)
            attr = ProviderAttribution(
                configured_provider="GEMINI",
                actual_provider="GEMINI",
                model="gemini-3.1-flash-lite",
                fallback_occurred=False,
                fallback_reason=None,
                task_type=task_type,
            )
            return res, attr
        except Exception as exc:
            # Fall back to deterministic fallback
            det = DeterministicStructuredLLMClient()
            res = det.generate_structured(prompt, schema, task_type)
            attr = ProviderAttribution(
                configured_provider="GEMINI",
                actual_provider="DETERMINISTIC_FALLBACK",
                model="gemini-3.1-flash-lite",
                fallback_occurred=True,
                fallback_reason=str(exc),
                task_type=task_type,
            )
            return res, attr


@pytest.fixture
def test_business():
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    cash_repo = PostgresIncomeExpenseRepository()

    owner = user_repo.save({
        "email": f"attribution_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    biz = Business(
        id=uuid.uuid4(),
        owner_id=owner,
        name=f"Attribution Enterprise {uuid.uuid4().hex[:4]}",
        industry="Retail",
        address="Kanpur, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz)

    cash_repo.create_income(IncomeRecord(
        id=uuid.uuid4(),
        business_id=biz.id,
        category="Capital",
        amount=Money.from_float(500000.0),
        date=date.today(),
        payment_method=PaymentMethod.BANK_TRANSFER,
        description="Initial seed cash",
    ))
    return {"owner": owner, "biz": biz}


def test_gemini_timeout_fallback_telemetry(test_business):
    """Verifies that on Gemini timeout, telemetry reports fallback_occurred=True and actual_provider=DETERMINISTIC_FALLBACK."""
    flaky = FlakyGeminiMock(failure_mode="timeout")
    agent = BusinessAgent(llm_client=flaky)
    context = AgentExecutionContext(user_id=test_business["owner"], business_id=test_business["biz"].id)

    res = agent.run_investigation(
        test_business["biz"].id,
        "Can we purchase a 5 lakh packaging unit?",
        context=context,
    )

    # Telemetry assertions
    assert res.planning_attribution.configured_provider == "GEMINI"
    assert res.planning_attribution.actual_provider == "DETERMINISTIC_FALLBACK"
    assert res.planning_attribution.fallback_occurred is True
    assert "Deadline exceeded" in (res.planning_attribution.fallback_reason or "")

    assert res.synthesis_attribution.actual_provider == "DETERMINISTIC_RULES"
    assert res.llm_provider == "DETERMINISTIC_FALLBACK"


def test_gemini_429_quota_exhaustion_telemetry(test_business):
    """Verifies that 429 quota exhaustion is accurately captured in telemetry."""
    flaky = FlakyGeminiMock(failure_mode="rate_limit_429")
    agent = BusinessAgent(llm_client=flaky)
    context = AgentExecutionContext(user_id=test_business["owner"], business_id=test_business["biz"].id)

    res = agent.run_investigation(
        test_business["biz"].id,
        "Can we buy an equipment for 3 lakhs?",
        context=context,
    )

    assert res.planning_attribution.fallback_occurred is True
    assert res.planning_attribution.actual_provider == "DETERMINISTIC_FALLBACK"
    assert "429 Quota exceeded" in (res.planning_attribution.fallback_reason or "")


def test_gemini_schema_corruption_fallback_telemetry(test_business):
    """Verifies that malformed model outputs trigger deterministic fallback."""
    flaky = FlakyGeminiMock(failure_mode="schema_corruption")
    agent = BusinessAgent(llm_client=flaky)
    context = AgentExecutionContext(user_id=test_business["owner"], business_id=test_business["biz"].id)

    res = agent.run_investigation(
        test_business["biz"].id,
        "Evaluate purchase of a delivery vehicle for 4 lakhs",
        context=context,
    )

    assert res.planning_attribution.fallback_occurred is True
    assert res.planning_attribution.actual_provider == "DETERMINISTIC_FALLBACK"
    assert "Invalid schema" in (res.planning_attribution.fallback_reason or "")


def test_financial_synthesis_uses_deterministic_rules(test_business):
    """Verifies financial facts are presented by deterministic rules after LLM planning."""
    flaky = FlakyGeminiMock(failure_mode="fail_synthesis_only")
    agent = BusinessAgent(llm_client=flaky)
    context = AgentExecutionContext(user_id=test_business["owner"], business_id=test_business["biz"].id)

    res = agent.run_investigation(
        test_business["biz"].id,
        "Evaluate rotary oven for 500000",
        context=context,
    )

    # Planning was Gemini
    assert res.planning_attribution.configured_provider == "GEMINI"
    assert res.planning_attribution.actual_provider == "GEMINI"
    assert res.planning_attribution.fallback_occurred is False

    # The model's synthesis output is not used for finance-bearing responses.
    assert res.synthesis_attribution.actual_provider == "DETERMINISTIC_RULES"
    assert res.synthesis_attribution.fallback_occurred is False
    assert flaky.call_count == 1
    assert res.llm_provider == "GEMINI"


def test_underspecified_query_reports_insufficient_information_without_hallucinating(test_business):
    """Verifies that underspecified queries yield INSUFFICIENT_INFORMATION and data gaps without fabricated figures."""
    det_client = DeterministicStructuredLLMClient()
    agent = BusinessAgent(llm_client=det_client)
    context = AgentExecutionContext(user_id=test_business["owner"], business_id=test_business["biz"].id)

    # Vague query without machine cost or financial figures
    res = agent.run_investigation(
        test_business["biz"].id,
        "Should we expand our factory operations?",
        context=context,
    )

    assert res.decision_outcome == "INSUFFICIENT_INFORMATION"
    assert len(res.data_gaps) > 0
    assert len(res.follow_up_questions) > 0
    assert "INSUFFICIENT INFORMATION" in res.synthesis

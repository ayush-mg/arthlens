"""Pure tests for decision input extraction and provenance safeguards."""

import uuid
from decimal import Decimal

from backend.arthlens.domain.business import Money

import pytest

from backend.arthlens.agent.business_agent import (
    AgentExecutionContext,
    BusinessAgent,
    CopilotPlanOutput,
    StepPlanItem,
)
from backend.arthlens.agent.business_tools import BusinessToolRegistry
from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.decision.models import DecisionOutcome
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient, ProviderAttribution
from backend.arthlens.services.business_service import UnauthorizedBusinessAccessError
from backend.arthlens.domain.business import BusinessRole


def test_equipment_query_does_not_fill_missing_financial_inputs():
    agent = BusinessAgent()

    intent, params, missing, questions = agent._parse_intent_and_extract_parameters(
        "I am considering buying an oven for ₹8 lakh", {}
    )

    assert intent == "EQUIPMENT_PURCHASE_EVALUATION"
    assert params["machine_cost"] == 800000.0
    assert "down_payment" in missing
    assert "unit_price" in missing
    assert "loan_interest_rate_pct" in missing
    assert len(questions) == len(missing)
    assert "loan_amount" not in params


def test_agent_execution_never_infers_the_business_owner_as_user():
    agent = BusinessAgent()

    with pytest.raises(UnauthorizedBusinessAccessError, match="Authenticated AgentExecutionContext"):
        agent.run_investigation(uuid.uuid4(), "Show my financial position")


def test_planner_reports_missing_terms_instead_of_inventing_them():
    client = DeterministicStructuredLLMClient()
    output = client._handle_business_copilot_planning(
        "OBJECTIVE_QUERY:\nI am buying equipment for ₹8 lakh\n"
        "BUSINESS_ID:\n00000000-0000-0000-0000-000000000001\n"
        "CONTEXT_JSON:\n{}\nPRIOR_TURNS_JSON:\n[]\n",
        __import__("backend.arthlens.agent.business_agent", fromlist=["CopilotPlanOutput"]).CopilotPlanOutput,
    )

    assert output.extracted_parameters["machine_cost"] == 800000.0
    assert "down_payment" in output.missing_critical_inputs
    assert "unit_price" in output.missing_critical_inputs
    assert all("evaluate_decision_model" != step.tool_name for step in output.plan)


class _FinanceStub:
    class _WorkingCapital:
        cash_and_bank = Money(Decimal("123456.78"))

    class _Pnl:
        operating_profit_ebitda = Money(Decimal("-9000.00"))

    def calculate_working_capital(self, _business_id):
        return self._WorkingCapital()

    def calculate_pnl(self, _business_id, _start_date, _end_date):
        return self._Pnl()


def test_decision_uses_recorded_cash_and_signed_ebitda_with_provenance():
    engine = DecisionIntelligenceEngine(
        decision_repo=type("RepoStub", (), {})(),
        finance_engine=_FinanceStub(),
    )
    supplied = {
        "machine_cost": 800000.0,
        "down_payment": 160000.0,
        "loan_interest_rate_pct": 10.5,
        "loan_tenure_months": 36,
        "monthly_maintenance": 6000.0,
        "current_monthly_volume": 8000.0,
        "capacity_monthly_volume": 12000.0,
        "unit_price": 40.0,
        "unit_variable_cost": 22.0,
        # These request values must never override the ledger.
        "current_cash_liquidity": 999999.0,
        "current_monthly_ebitda": 50000.0,
        "input_provenance": {"current_cash_liquidity": "USER_ASSUMPTION"},
    }

    result = engine.evaluate_decision(
        business_id=uuid.uuid4(),
        model_id="MACHINE_OR_EQUIPMENT_PURCHASE",
        user_inputs=supplied,
        save_evaluation=False,
    )

    assert result.outcome != DecisionOutcome.INSUFFICIENT_INFORMATION
    assert result.inputs["current_cash_liquidity"] == 123456.78
    assert result.inputs["current_monthly_ebitda"] == -3000.0
    assert result.inputs["input_provenance"]["current_cash_liquidity"] == "LEDGER_ACTUAL"
    assert result.inputs["input_provenance"]["loan_amount"] == "USER_ASSUMPTION"


def test_gemini_registry_exposes_new_evaluator_and_service_tools():
    registry = BusinessToolRegistry(
        business_service=object(),
        finance_engine=object(),
        decision_engine=object(),
    )
    schemas = {schema["name"]: schema for schema in registry.get_tool_schemas()}

    assert {
        "evaluate_cash_flow_pressure",
        "evaluate_business_viability",
        "check_unreconciled_inventory_costs",
        "run_scenario_simulation",
        "replay_scenario_simulation",
        "analyze_goal_deviation",
        "propose_agent_action",
    } <= schemas.keys()
    assert "random_seed" in schemas["run_scenario_simulation"]["parameters"]["required"]
    assert "session_id" not in schemas["propose_agent_action"]["parameters"]["properties"]


def test_gemini_planning_prompt_receives_the_registered_tool_contracts():
    class PlanCapture:
        prompt = ""

        def generate_structured_with_attribution(self, prompt, schema, task_type):
            self.prompt = prompt
            plan = CopilotPlanOutput(
                intent="GENERAL_FINANCIAL_INQUIRY",
                plan=[
                    StepPlanItem(step_number=1, title="Cash", tool_name="get_cash_position"),
                    StepPlanItem(step_number=2, title="P&L", tool_name="get_profit_and_loss"),
                ],
            )
            assert schema is CopilotPlanOutput
            return plan, ProviderAttribution(
                configured_provider="CUSTOM",
                actual_provider="CUSTOM",
                model="test",
                fallback_occurred=False,
                task_type=task_type,
            )

    client = PlanCapture()
    agent = BusinessAgent(llm_client=client, session_repo=object())
    agent._plan_investigation(
        AgentExecutionContext(user_id=uuid.uuid4(), business_id=uuid.uuid4()),
        "Review my business.",
        {},
        [],
    )

    assert "TOOL_CONTRACTS_JSON" in client.prompt
    for name in (
        "evaluate_cash_flow_pressure",
        "evaluate_business_viability",
        "check_unreconciled_inventory_costs",
        "run_scenario_simulation",
        "replay_scenario_simulation",
        "analyze_goal_deviation",
        "propose_agent_action",
    ):
        assert name in client.prompt


def test_new_financial_evaluator_requires_finance_edit_role_before_execution():
    class AccessRecorder:
        required_roles = None

        def verify_access(self, _business_id, _user_id, required_roles=None):
            self.required_roles = required_roles
            if BusinessRole.VIEWER not in (required_roles or []):
                raise UnauthorizedBusinessAccessError("role rejected")

    class DecisionRecorder:
        called = False

        def evaluate_decision(self, *_args, **_kwargs):
            self.called = True
            return type("Result", (), {"to_dict": lambda _self: {"model_id": "CASH_FLOW_PRESSURE"}})()

    access = AccessRecorder()
    decision = DecisionRecorder()
    registry = BusinessToolRegistry(
        business_service=access,
        finance_engine=object(),
        decision_engine=decision,
    )
    result = registry.execute_tool(
        "evaluate_cash_flow_pressure",
        {
            "business_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "inputs": {},
        },
    )

    assert result["status"] == "ERROR"
    assert not decision.called
    assert access.required_roles == [
        BusinessRole.OWNER,
        BusinessRole.ADMIN,
        BusinessRole.MANAGER,
        BusinessRole.ACCOUNTANT,
    ]


def test_action_tool_only_stores_pending_proposals_for_trusted_agent_session():
    class AccessRecorder:
        def verify_access(self, *_args, **_kwargs):
            return None

    class ActionRecorder:
        call = None

        def create(self, *args):
            self.call = args
            return {"status": "PENDING_CONFIRMATION", "action_type": args[3]}

    action_service = ActionRecorder()
    registry = BusinessToolRegistry(
        business_service=AccessRecorder(),
        finance_engine=object(),
        decision_engine=object(),
        agent_action_service=action_service,
    )
    arguments = {
        "business_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "action_type": "GENERATE_REPORT",
        "payload": {"report_type": "EXECUTIVE_DOSSIER"},
    }

    denied = registry.execute_tool("propose_agent_action", arguments)
    assert denied["status"] == "FAILED"
    assert action_service.call is None

    trusted_session_id = uuid.uuid4()
    proposal = registry.execute_tool(
        "propose_agent_action",
        arguments,
        trusted_session_id=trusted_session_id,
    )
    assert proposal["status"] == "PENDING_CONFIRMATION"
    assert action_service.call[1] == trusted_session_id

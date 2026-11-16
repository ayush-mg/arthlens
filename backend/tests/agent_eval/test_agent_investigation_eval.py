"""Deterministic agent investigation evaluations without live LLM or database calls."""

from __future__ import annotations

import uuid

from backend.arthlens.agent.business_agent import (
    AgentExecutionContext,
    BusinessAgent,
    CopilotPlanOutput,
    StepPlanItem,
)
from backend.arthlens.domain.business import DecisionOutcome
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient, ProviderAttribution


def _plan(intent: str, *steps: tuple[str, dict]) -> CopilotPlanOutput:
    return CopilotPlanOutput(
        intent=intent,
        plan=[
            StepPlanItem(
                step_number=index,
                title=tool_name.replace("_", " ").title(),
                tool_name=tool_name,
                arguments=arguments,
            )
            for index, (tool_name, arguments) in enumerate(steps, start=1)
        ],
    )


class _PlannedLLM:
    def __init__(self, plans: list[CopilotPlanOutput]):
        self.plans = list(plans)
        self.prompts: list[str] = []

    def generate_structured_with_attribution(self, prompt, schema, task_type):
        self.prompts.append(prompt)
        if task_type == "business_copilot_planning":
            result = self.plans.pop(0)
        else:
            raise AssertionError(f"Unexpected LLM task: {task_type}")
        assert schema is CopilotPlanOutput
        return result, ProviderAttribution(
            configured_provider="CUSTOM",
            actual_provider="CUSTOM",
            model="agent-eval",
            fallback_occurred=False,
            task_type=task_type,
        )


class _SessionRepository:
    def __init__(self):
        self.saved_turns = []

    def verify_session_ownership(self, *_args, **_kwargs):
        return True

    def get_turns(self, *_args, **_kwargs):
        return []

    def save_turn(self, **kwargs):
        self.saved_turns.append(kwargs)


class _ToolRegistry:
    def __init__(self, tools):
        self._tools = {name: object() for name in tools}
        self.calls = []
        self.confirm_calls = 0

    def get_tool_schemas(self):
        return [{"name": name, "parameters": {"type": "object", "properties": {}}} for name in self._tools]

    def execute_tool(self, tool_name, arguments, *, trusted_session_id=None):
        self.calls.append((tool_name, dict(arguments), trusted_session_id))
        if tool_name == "get_cash_position":
            return {"cash_balance": 8200, "total_liquidity": 8200}
        if tool_name == "evaluate_business_viability":
            return {
                "model_id": "BUSINESS_VIABILITY",
                "outcome": "FEASIBLE",
                "calculations": {},
                "inputs_used": dict(arguments["inputs"]),
            }
        if tool_name == "get_working_capital":
            return {"error": "temporary working capital service failure", "status": "ERROR"}
        if tool_name == "get_business_health":
            return {"overall_score": 76, "grade": "HEALTHY"}
        if tool_name == "identify_data_gaps":
            supplied = arguments.get("supplied_inputs", {})
            missing = [name for name in ("machine_cost", "down_payment", "loan_interest_rate_pct") if name not in supplied]
            return {
                "has_data_gaps": bool(missing),
                "missing_inputs": missing,
                "follow_up_questions": [f"Please provide {name}." for name in missing],
            }
        if tool_name == "propose_agent_action":
            return {
                "id": str(uuid.uuid4()),
                "action_type": arguments["action_type"],
                "status": "PENDING_CONFIRMATION",
                "payload": dict(arguments["payload"]),
            }
        return {"observed": tool_name}


def _agent(registry, llm, session_repo=None):
    return BusinessAgent(
        tool_registry=registry,
        llm_client=llm,
        session_repo=session_repo or _SessionRepository(),
    )


def test_investigation_chains_verified_read_output_into_evaluator():
    registry = _ToolRegistry(["get_cash_position", "evaluate_business_viability"])
    llm = _PlannedLLM([
        _plan(
            "BUSINESS_VIABILITY_INVESTIGATION",
            ("get_cash_position", {}),
            (
                "evaluate_business_viability",
                {
                    "inputs": {
                        "current_monthly_revenue": 10000,
                        "variable_cost_pct": 40,
                        "monthly_fixed_costs": 3000,
                        "cash_balance": {"$ref": {"step_id": 1, "path": "result.cash_balance"}},
                        "monthly_debt_service": 500,
                        "current_working_capital": 1000,
                        "monthly_revenue_growth_pct": 2,
                        "annual_interest_rate_pct": 10,
                        "monthly_capex": 200,
                        "current_debt": 4000,
                    }
                },
            ),
        )
    ])
    agent = _agent(registry, llm)
    business_id, user_id = uuid.uuid4(), uuid.uuid4()
    query = (
        "Evaluate viability with monthly revenue 10000, variable cost 40%, fixed costs 3000, "
        "debt service 500, working capital 1000, revenue growth 2%, interest 10%, "
        "monthly capex 200, and current debt 4000."
    )

    result = agent.run_investigation(
        business_id,
        query,
        context=AgentExecutionContext(user_id=user_id, business_id=business_id),
    )

    evaluation = next(step for step in result.plan if step.tool_name == "evaluate_business_viability")
    assert [step.status for step in result.plan] == ["EXECUTED", "EXECUTED"]
    assert evaluation.result["inputs_used"]["cash_balance"] == 8200
    assert result.decision_outcome == "FEASIBLE"
    assert registry.calls[1][1]["inputs"]["cash_balance"] == 8200


def test_missing_purchase_terms_return_clarification_without_evaluation():
    registry = _ToolRegistry([
        "get_cash_position",
        "get_working_capital",
        "get_profit_and_loss",
        "identify_data_gaps",
        "evaluate_decision_model",
    ])
    agent = _agent(registry, DeterministicStructuredLLMClient())
    business_id, user_id = uuid.uuid4(), uuid.uuid4()

    result = agent.run_investigation(
        business_id,
        "Should I buy an oven for my bakery?",
        context=AgentExecutionContext(user_id=user_id, business_id=business_id),
    )

    assert result.decision_outcome == DecisionOutcome.INSUFFICIENT_INFORMATION.value
    assert "machine_cost" in result.data_gaps
    assert "down_payment" in result.data_gaps
    assert result.follow_up_questions
    assert all(call[0] != "evaluate_decision_model" for call in registry.calls)


def test_read_tool_error_triggers_one_shot_replan_and_recovery():
    registry = _ToolRegistry([
        "get_cash_position",
        "get_working_capital",
        "get_business_health",
    ])
    llm = _PlannedLLM([
        _plan(
            "BUSINESS_HEALTH_INVESTIGATION",
            ("get_cash_position", {}),
            ("get_working_capital", {}),
        ),
        _plan(
            "BUSINESS_HEALTH_INVESTIGATION",
            ("get_cash_position", {}),
            ("get_business_health", {}),
        ),
    ])
    agent = _agent(registry, llm)
    business_id, user_id = uuid.uuid4(), uuid.uuid4()

    result = agent.run_investigation(
        business_id,
        "Check my cash position and business health.",
        context=AgentExecutionContext(user_id=user_id, business_id=business_id),
    )

    assert len(llm.prompts) == 2
    assert "_agent_replan" in llm.prompts[1]
    assert [step.tool_name for step in result.plan] == [
        "get_cash_position",
        "get_working_capital",
        "get_business_health",
    ]
    assert result.plan[1].status == "FAILED"
    assert result.plan[2].status == "EXECUTED"
    assert registry.calls.count(("get_cash_position", registry.calls[0][1], None)) == 1


def test_action_proposal_is_returned_pending_user_confirmation():
    registry = _ToolRegistry(["get_cash_position", "propose_agent_action"])
    llm = _PlannedLLM([
        _plan(
            "GENERAL_FINANCIAL_INQUIRY",
            ("get_cash_position", {}),
            (
                "propose_agent_action",
                {
                    "action_type": "GENERATE_REPORT",
                    "payload": {"report_type": "EXECUTIVE_DOSSIER"},
                },
            ),
        )
    ])
    agent = _agent(registry, llm)
    business_id, user_id = uuid.uuid4(), uuid.uuid4()

    result = agent.run_investigation(
        business_id,
        "Prepare an executive report for me.",
        context=AgentExecutionContext(user_id=user_id, business_id=business_id),
    )

    assert len(result.proposed_actions) == 1
    assert result.proposed_actions[0]["status"] == "PENDING_CONFIRMATION"
    action_call = next(call for call in registry.calls if call[0] == "propose_agent_action")
    assert action_call[2] == uuid.UUID(result.session_id)
    assert registry.confirm_calls == 0

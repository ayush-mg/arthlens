from decimal import Decimal

import pytest
from backend.arthlens.agent.budgets import RunBudgetDecision, RunBudgetLimits
from backend.arthlens.agent.planning import (
    AgentPlan,
    GoalInterpretation,
    GoalInterpreter,
    MissingGoalSlots,
    Planner,
    PlanValidationError,
    PlanValidator,
    RecoveryAction,
    RecoveryReason,
    ReplanLimitReached,
    choose_recovery_action,
)
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient
from backend.arthlens.llm.testing import FakeLLMClient
from pydantic import ValidationError


def _goal(**overrides):
    return GoalInterpretation(
        objective="Calculate break-even quantity.",
        intent="calculate break-even",
        required_slots=["price", "variable_cost", "fixed_costs"],
        supplied_slots={
            "price": 10,
            "variable_cost": 4,
            "fixed_costs": 120,
        },
        **overrides,
    )


def _budget(*, allowed=True, exhausted_budget=None, replans_used=0):
    return RunBudgetDecision(
        allowed=allowed,
        exhausted_budget=exhausted_budget,
        steps_used=0,
        replans_used=replans_used,
        model_calls_used=0,
        cost_usd=Decimal("0"),
    )


def _break_even_plan():
    return {
        "steps": [
            {
                "step_id": "break_even",
                "tool_name": "calculate_break_even",
                "tool_input": {
                    "price": 10.0,
                    "variable_cost": 4.0,
                    "fixed_costs": 120.0,
                },
                "depends_on": [],
            }
        ]
    }


@pytest.mark.unit
def test_goal_interpreter_uses_typed_output_and_marks_missing_facts():
    llm = FakeLLMClient(
        {
            "goal_interpretation": [
                {
                    "objective": "Calculate break-even quantity.",
                    "intent": "calculate break-even",
                    "required_slots": ["price", "fixed_costs"],
                }
            ]
        }
    )

    goal = GoalInterpreter(llm).interpret(
        "Calculate break-even quantity.",
        supplied_slots={"price": 10},
    )

    assert goal.missing_slots == ("fixed_costs",)


@pytest.mark.unit
def test_goal_schema_rejects_duplicate_or_untrimmed_slots():
    with pytest.raises(ValidationError):
        GoalInterpretation(
            objective="Goal",
            intent="Intent",
            required_slots=["price", "price"],
            supplied_slots={},
        )


@pytest.mark.unit
def test_goal_interpreter_uses_only_caller_supplied_facts():
    llm = FakeLLMClient(
        {
            "goal_interpretation": [
                {
                    "objective": "Calculate break-even quantity.",
                    "intent": "calculate break-even",
                    "required_slots": ["price"],
                    "supplied_slots": {"price": 10},
                }
            ]
        }
    )

    with pytest.raises(ValidationError):
        GoalInterpreter(llm).interpret("Calculate break-even quantity.")


@pytest.mark.unit
def test_goal_interpreter_rejects_non_json_supplied_fact_values():
    llm = FakeLLMClient({"goal_interpretation": []})

    with pytest.raises(ValueError, match="finite JSON"):
        GoalInterpreter(llm).interpret(
            "Calculate break-even quantity.",
            supplied_slots={"price": float("nan")},
        )


@pytest.mark.unit
def test_plan_validator_checks_inputs_dependencies_and_approval_metadata():
    validator = PlanValidator(build_default_tool_registry())
    plan = AgentPlan.model_validate(
        {
            "steps": [
                {
                    "step_id": "first",
                    "tool_name": "calculate_break_even",
                    "tool_input": {
                        "price": 10,
                        "variable_cost": 4,
                        "fixed_costs": 120,
                    },
                },
                {
                    "step_id": "publish",
                    "tool_name": "publish_to_shared_view",
                    "tool_input": {"run_id": "run-1"},
                    "depends_on": ["first"],
                },
            ]
        }
    )

    validated = validator.validate(plan)

    assert validated.steps[0].tool_input["price"] == 10.0
    assert validated.steps[1].depends_on == ("first",)
    assert validated.steps[1].approval_required is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "tool_input",
    [
        {"price": float("nan"), "variable_cost": 4, "fixed_costs": 120},
        {"price": 10, "variable_cost": 4, "fixed_costs": float("inf")},
    ],
)
def test_plan_schema_rejects_non_finite_tool_input_numbers(tool_input):
    with pytest.raises(ValidationError, match="finite JSON"):
        AgentPlan.model_validate(
            {
                "steps": [
                    {
                        "step_id": "break_even",
                        "tool_name": "calculate_break_even",
                        "tool_input": tool_input,
                    }
                ]
            }
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "steps, message",
    [
        (
            [
                {
                    "step_id": "bad",
                    "tool_name": "unknown_tool",
                    "tool_input": {},
                }
            ],
            "unknown tool or invalid input",
        ),
        (
            [
                {
                    "step_id": "first",
                    "tool_name": "calculate_break_even",
                    "tool_input": {
                        "price": 10,
                        "variable_cost": 4,
                        "fixed_costs": 120,
                        "unregistered": True,
                    },
                }
            ],
            "unknown tool or invalid input",
        ),
        (
            [
                {
                    "step_id": "first",
                    "tool_name": "calculate_break_even",
                    "tool_input": {
                        "price": 10,
                        "variable_cost": 4,
                        "fixed_costs": 120,
                    },
                    "depends_on": ["later"],
                }
            ],
            "unknown or later",
        ),
    ],
)
def test_plan_validator_rejects_unexecutable_steps(steps, message):
    validator = PlanValidator(build_default_tool_registry())
    plan = AgentPlan.model_validate({"steps": steps})

    with pytest.raises(PlanValidationError, match=message):
        validator.validate(plan)


@pytest.mark.unit
def test_planner_refuses_to_plan_without_required_user_facts():
    llm = FakeLLMClient({"planning": [_break_even_plan()]})
    planner = Planner(llm, PlanValidator(build_default_tool_registry()))
    goal = GoalInterpretation(
        objective="Calculate break-even quantity.",
        intent="calculate break-even",
        required_slots=["price"],
        supplied_slots={},
    )

    with pytest.raises(MissingGoalSlots) as exc_info:
        planner.plan(goal)

    assert exc_info.value.slots == ("price",)


@pytest.mark.unit
def test_planner_sends_tool_contracts_and_limits_plan_length():
    validator = PlanValidator(build_default_tool_registry())
    contracts = {
        contract["name"]: contract
        for contract in validator.tool_contracts()
    }
    llm = FakeLLMClient({"planning": [_break_even_plan()]})
    planner = Planner(
        llm,
        validator,
        max_steps=1,
    )

    result = planner.plan(_goal())

    assert len(result.steps) == 1
    assert result.steps[0].approval_required is False
    assert contracts["calculate_break_even"]["output_schema"] is not None
    assert contracts["fetch_economic_indicator"]["output_schema"] is None


@pytest.mark.unit
def test_deterministic_offline_planner_uses_only_explicit_caller_financial_facts():
    client = DeterministicStructuredLLMClient()
    goal = GoalInterpreter(client).interpret(
        "Calculate break-even quantity.",
        supplied_slots={"price": 275, "variable_cost": 192, "fixed_costs": 8400},
    )

    plan = Planner(client, PlanValidator(build_default_tool_registry())).plan(goal)

    assert plan.steps[0].tool_input == {
        "price": 275.0,
        "variable_cost": 192.0,
        "fixed_costs": 8400.0,
    }


@pytest.mark.unit
def test_deterministic_offline_planner_does_not_fill_missing_financial_facts():
    client = DeterministicStructuredLLMClient()
    goal = GoalInterpreter(client).interpret(
        "Calculate break-even quantity.",
        supplied_slots={"price": 275, "variable_cost": 192},
    )

    assert goal.missing_slots == ("fixed_costs",)
    with pytest.raises(MissingGoalSlots, match="fixed_costs"):
        Planner(client, PlanValidator(build_default_tool_registry())).plan(goal)


@pytest.mark.unit
def test_plan_validator_rejects_llm_financial_input_not_supported_by_user_facts():
    validator = PlanValidator(build_default_tool_registry())
    plan = AgentPlan.model_validate(_break_even_plan())

    with pytest.raises(PlanValidationError, match="does not match its caller supplied fact"):
        validator.validate(
            plan,
            supplied_slots={"price": 12, "variable_cost": 4, "fixed_costs": 120},
        )


@pytest.mark.unit
def test_planner_requires_persisted_replan_capacity_before_replanning():
    llm = FakeLLMClient({"planning": [_break_even_plan()]})
    planner = Planner(
        llm,
        PlanValidator(build_default_tool_registry()),
        budget_limits=RunBudgetLimits(max_replans=1),
    )

    with pytest.raises(ReplanLimitReached):
        planner.plan(_goal(), replan=True, budget=_budget(replans_used=2))

    planned = planner.plan(_goal(), replan=True, budget=_budget(replans_used=1))
    assert len(planned.steps) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    "reason, retries, expected",
    [
        (
            RecoveryReason.TRANSIENT_TOOL_ERROR,
            0,
            RecoveryAction.RETRY_OR_ALTERNATE_TOOL,
        ),
        (RecoveryReason.TRANSIENT_TOOL_ERROR, 1, RecoveryAction.NEEDS_REPLAN),
        (RecoveryReason.INVALID_PLAN, 0, RecoveryAction.NEEDS_REPLAN),
        (RecoveryReason.VERIFICATION_FAILED, 0, RecoveryAction.NEEDS_REPLAN),
        (RecoveryReason.MISSING_USER_FACT, 0, RecoveryAction.NEEDS_USER_FACT),
        (RecoveryReason.CONTRADICTION, 0, RecoveryAction.NEEDS_REPLAN),
        (RecoveryReason.APPROVAL_REQUIRED, 0, RecoveryAction.AWAIT_APPROVAL),
        (RecoveryReason.UNRECOVERABLE, 0, RecoveryAction.FAIL),
        (RecoveryReason.BUDGET_EXHAUSTED, 0, RecoveryAction.FAIL),
    ],
)
def test_recovery_decision_table(reason, retries, expected):
    assert (
        choose_recovery_action(reason, retries_used=retries, budget=_budget())
        is expected
    )


@pytest.mark.unit
def test_recovery_decision_table_fails_closed_when_budget_is_exhausted():
    action = choose_recovery_action(
        RecoveryReason.INVALID_PLAN,
        retries_used=0,
        budget=_budget(allowed=False, exhausted_budget="steps"),
    )

    assert action is RecoveryAction.FAIL


@pytest.mark.unit
def test_recovery_replan_limit_respects_custom_run_limits():
    action = choose_recovery_action(
        RecoveryReason.INVALID_PLAN,
        retries_used=1,
        budget=_budget(replans_used=1),
        limits=RunBudgetLimits(max_replans=1),
    )

    assert action is RecoveryAction.FAIL

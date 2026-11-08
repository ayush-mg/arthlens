"""Tests for golden replay traces across Loop A, Loop B, and Loop C."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
from backend.arthlens.agent.followups import (
    UnresolvedGap,
    tasks_from_unresolved_gaps,
)
from backend.arthlens.agent.planning import GoalInterpreter, Planner, PlanValidator
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from backend.arthlens.llm.testing import (
    LLMFixtureError,
    ReplayLLMClient,
    ReplayTrace,
)


@pytest.fixture
def golden_traces():
    fixture_path = (
        Path(__file__).parents[2] / "fixtures" / "replay" / "golden_replay_traces.json"
    )
    with open(fixture_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def tool_registry():
    return build_default_tool_registry()


def _make_trace(trace_dict: dict) -> ReplayTrace:
    return ReplayTrace(
        task_type=trace_dict["task_type"],
        prompt_sha256=trace_dict["prompt_sha256"],
        schema_sha256=trace_dict["schema_sha256"],
        response_json=trace_dict["response_json"],
    )


def test_golden_replay_loop_a_break_even(golden_traces, tool_registry):
    loop_data = golden_traces["loops"]["loop_a_break_even"]
    t_interp = _make_trace(loop_data["interpretation_trace"])
    t_plan = _make_trace(loop_data["planning_trace"])

    client = ReplayLLMClient([t_interp, t_plan])
    interpreter = GoalInterpreter(client)
    planner = Planner(client, PlanValidator(tool_registry))

    goal = interpreter.interpret(
        loop_data["objective"], supplied_slots=loop_data["supplied_slots"]
    )
    assert goal.intent == "calculate break-even"
    assert goal.missing_slots == ()

    plan = planner.plan(goal)
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "calculate_break_even"
    assert plan.steps[0].tool_input["price"] == 100.0
    assert plan.steps[0].tool_input["variable_cost"] == 40.0
    assert plan.steps[0].tool_input["fixed_costs"] == 150000.0


def test_golden_replay_loop_b_catchment(golden_traces, tool_registry):
    loop_data = golden_traces["loops"]["loop_b_catchment"]
    t_interp = _make_trace(loop_data["interpretation_trace"])
    t_plan = _make_trace(loop_data["planning_trace"])

    client = ReplayLLMClient([t_interp, t_plan])
    interpreter = GoalInterpreter(client)
    planner = Planner(client, PlanValidator(tool_registry))

    goal = interpreter.interpret(
        loop_data["objective"], supplied_slots=loop_data["supplied_slots"]
    )
    assert goal.intent == "compute catchment"
    assert goal.missing_slots == ()

    plan = planner.plan(goal)
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "compute_catchment"
    assert plan.steps[0].tool_input["minutes"] == 45.0
    assert plan.steps[0].tool_input["mode"] == "driving"


def test_golden_replay_loop_c_scheme_eligibility(golden_traces, tool_registry):
    loop_data = golden_traces["loops"]["loop_c_scheme_eligibility"]
    t_interp = _make_trace(loop_data["interpretation_trace"])
    t_plan = _make_trace(loop_data["planning_trace"])

    client = ReplayLLMClient([t_interp, t_plan])
    interpreter = GoalInterpreter(client)
    planner = Planner(client, PlanValidator(tool_registry))

    goal = interpreter.interpret(
        loop_data["objective"], supplied_slots=loop_data["supplied_slots"]
    )
    assert goal.intent == "evaluate scheme eligibility"
    assert goal.missing_slots == ()

    plan = planner.plan(goal)
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "evaluate_scheme_eligibility"
    assert plan.steps[0].tool_input["scheme"] == "PMFME"
    assert plan.steps[0].tool_input["facts"]["enterprise_type"] == "micro"


def test_replay_client_fail_closed_on_tampered_prompt(golden_traces):
    loop_data = golden_traces["loops"]["loop_a_break_even"]
    t_interp = _make_trace(loop_data["interpretation_trace"])

    client = ReplayLLMClient([t_interp])
    interpreter = GoalInterpreter(client)

    with pytest.raises(LLMFixtureError, match="Replay trace does not match"):
        interpreter.interpret(
            "Tampered prompt that does not match the recorded golden prompt",
            supplied_slots=loop_data["supplied_slots"],
        )


def test_replay_client_exhaustion_detection(golden_traces):
    loop_data = golden_traces["loops"]["loop_a_break_even"]
    t_interp = _make_trace(loop_data["interpretation_trace"])

    client = ReplayLLMClient([t_interp])
    interpreter = GoalInterpreter(client)

    interpreter.interpret(
        loop_data["objective"], supplied_slots=loop_data["supplied_slots"]
    )

    with pytest.raises(LLMFixtureError, match="Replay trace is exhausted"):
        interpreter.interpret(
            loop_data["objective"], supplied_slots=loop_data["supplied_slots"]
        )


def test_deterministic_followup_task_creation():
    gap_id = uuid4()
    gaps = [
        UnresolvedGap(
            description="Verified power supply tariff is unconfirmed.",
            linked_gap_quantity_id=gap_id,
        )
    ]
    tasks = tasks_from_unresolved_gaps(gaps)
    assert len(tasks) == 1
    assert (
        tasks[0]["text"]
        == "Resolve this evidence gap: Verified power supply tariff is unconfirmed."
    )
    assert tasks[0]["linked_gap_quantity_id"] == gap_id

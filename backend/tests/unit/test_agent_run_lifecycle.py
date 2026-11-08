import pytest
from backend.arthlens.agent.run_lifecycle import (
    TERMINAL_RUN_STATES,
    AgentRunEvent,
    AgentRunState,
    IllegalRunTransition,
    transition_run_state,
)


@pytest.mark.parametrize(
    ("state", "event", "expected"),
    [
        ("CREATED", "RUN_ACCEPTED", "INTERPRETING"),
        ("INTERPRETING", "OBJECTIVE_VALID", "PLANNING"),
        ("INTERPRETING", "REQUIRED_SLOTS_MISSING", "AWAITING_USER"),
        ("PLANNING", "PLAN_VALIDATED", "EXECUTING"),
        ("EXECUTING", "TOOL_RETURNED", "OBSERVING"),
        ("OBSERVING", "NEXT_STEP_READY", "EXECUTING"),
        ("OBSERVING", "ERROR_GAP_OR_CONTRADICTION", "RECOVERING"),
        ("OBSERVING", "GATED_ACTION_REACHED", "AWAITING_APPROVAL"),
        ("OBSERVING", "PLAN_COMPLETE", "VERIFYING"),
        ("RECOVERING", "RETRY_OR_ALTERNATE_TOOL", "EXECUTING"),
        ("RECOVERING", "NEEDS_REPLAN", "PLANNING"),
        ("RECOVERING", "NEEDS_USER_FACT", "AWAITING_USER"),
        ("RECOVERING", "UNRECOVERABLE", "FAILED"),
        ("AWAITING_USER", "ANSWER_RECEIVED", "PLANNING"),
        ("AWAITING_APPROVAL", "APPROVED", "EXECUTING"),
        ("AWAITING_APPROVAL", "REJECTED", "CANCELLED"),
        ("VERIFYING", "ALL_CHECKS_PASS", "COMPLETED"),
        ("VERIFYING", "CHECK_FAILS", "RECOVERING"),
    ],
)
def test_handbook_transition_table(state, event, expected):
    assert transition_run_state(state, event).value == expected


def test_invalid_plan_enters_recovery_before_persisted_replan_budget_is_reserved():
    assert transition_run_state(
        AgentRunState.PLANNING,
        AgentRunEvent.PLAN_INVALID,
        plan_retry_available=True,
    ) == AgentRunState.RECOVERING
    assert transition_run_state(
        AgentRunState.PLANNING,
        AgentRunEvent.PLAN_INVALID,
        plan_retry_available=False,
    ) == AgentRunState.RECOVERING


@pytest.mark.parametrize("state", list(AgentRunState))
def test_budget_limit_exhausts_any_nonterminal_state(state):
    if state in TERMINAL_RUN_STATES:
        with pytest.raises(IllegalRunTransition, match="Terminal state"):
            transition_run_state(state, AgentRunEvent.BUDGET_LIMIT_HIT)
    else:
        assert transition_run_state(
            state,
            AgentRunEvent.BUDGET_LIMIT_HIT,
        ) == AgentRunState.BUDGET_EXHAUSTED


@pytest.mark.parametrize(
    ("state", "event"),
    [
        ("CREATED", "PLAN_VALIDATED"),
        ("COMPLETED", "BUDGET_LIMIT_HIT"),
        ("AWAITING_APPROVAL", "ALL_CHECKS_PASS"),
        ("VERIFYING", "APPROVED"),
    ],
)
def test_illegal_transitions_raise_domain_error(state, event):
    with pytest.raises(IllegalRunTransition):
        transition_run_state(state, event)

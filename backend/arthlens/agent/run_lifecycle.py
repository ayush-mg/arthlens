"""Deterministic agent-run lifecycle transitions from Handbook Section 8.2."""

from enum import Enum


class AgentRunState(str, Enum):
    CREATED = "CREATED"
    INTERPRETING = "INTERPRETING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    RECOVERING = "RECOVERING"
    AWAITING_USER = "AWAITING_USER"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    CANCELLED = "CANCELLED"


class AgentRunEvent(str, Enum):
    RUN_ACCEPTED = "RUN_ACCEPTED"
    OBJECTIVE_VALID = "OBJECTIVE_VALID"
    REQUIRED_SLOTS_MISSING = "REQUIRED_SLOTS_MISSING"
    PLAN_VALIDATED = "PLAN_VALIDATED"
    PLAN_INVALID = "PLAN_INVALID"
    TOOL_RETURNED = "TOOL_RETURNED"
    NEXT_STEP_READY = "NEXT_STEP_READY"
    ERROR_GAP_OR_CONTRADICTION = "ERROR_GAP_OR_CONTRADICTION"
    GATED_ACTION_REACHED = "GATED_ACTION_REACHED"
    PLAN_COMPLETE = "PLAN_COMPLETE"
    RETRY_OR_ALTERNATE_TOOL = "RETRY_OR_ALTERNATE_TOOL"
    NEEDS_REPLAN = "NEEDS_REPLAN"
    NEEDS_USER_FACT = "NEEDS_USER_FACT"
    UNRECOVERABLE = "UNRECOVERABLE"
    ANSWER_RECEIVED = "ANSWER_RECEIVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ALL_CHECKS_PASS = "ALL_CHECKS_PASS"
    CHECK_FAILS = "CHECK_FAILS"
    BUDGET_LIMIT_HIT = "BUDGET_LIMIT_HIT"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"


TERMINAL_RUN_STATES = frozenset({
    AgentRunState.COMPLETED,
    AgentRunState.FAILED,
    AgentRunState.BUDGET_EXHAUSTED,
    AgentRunState.CANCELLED,
})


class IllegalRunTransition(ValueError):
    """Raised when an event is not valid for the current run state."""


def transition_run_state(
    state: AgentRunState | str,
    event: AgentRunEvent | str,
    *,
    plan_retry_available: bool = False,
) -> AgentRunState:
    """Return the next state or raise when the transition is not in the handbook."""
    try:
        current_state = AgentRunState(state)
        current_event = AgentRunEvent(event)
    except ValueError as exc:
        raise IllegalRunTransition(str(exc)) from exc

    if current_state in TERMINAL_RUN_STATES:
        raise IllegalRunTransition(f"Terminal state {current_state.value} cannot transition.")

    if current_event == AgentRunEvent.BUDGET_LIMIT_HIT:
        return AgentRunState.BUDGET_EXHAUSTED

    transitions = {
        (AgentRunState.CREATED, AgentRunEvent.UNRECOVERABLE): AgentRunState.FAILED,
        (AgentRunState.CREATED, AgentRunEvent.RUN_ACCEPTED): AgentRunState.INTERPRETING,
        (AgentRunState.INTERPRETING, AgentRunEvent.UNRECOVERABLE): AgentRunState.FAILED,
        (AgentRunState.INTERPRETING, AgentRunEvent.OBJECTIVE_VALID): AgentRunState.PLANNING,
        (AgentRunState.INTERPRETING, AgentRunEvent.REQUIRED_SLOTS_MISSING): AgentRunState.AWAITING_USER,
        (AgentRunState.PLANNING, AgentRunEvent.UNRECOVERABLE): AgentRunState.FAILED,
        (AgentRunState.PLANNING, AgentRunEvent.PLAN_INVALID): AgentRunState.RECOVERING,
        (AgentRunState.PLANNING, AgentRunEvent.PLAN_VALIDATED): AgentRunState.EXECUTING,
        (AgentRunState.EXECUTING, AgentRunEvent.GATED_ACTION_REACHED): AgentRunState.AWAITING_APPROVAL,
        (AgentRunState.EXECUTING, AgentRunEvent.TOOL_RETURNED): AgentRunState.OBSERVING,
        (AgentRunState.EXECUTING, AgentRunEvent.ERROR_GAP_OR_CONTRADICTION): AgentRunState.RECOVERING,
        (AgentRunState.OBSERVING, AgentRunEvent.NEXT_STEP_READY): AgentRunState.EXECUTING,
        (AgentRunState.OBSERVING, AgentRunEvent.ERROR_GAP_OR_CONTRADICTION): AgentRunState.RECOVERING,
        (AgentRunState.OBSERVING, AgentRunEvent.GATED_ACTION_REACHED): AgentRunState.AWAITING_APPROVAL,
        (AgentRunState.OBSERVING, AgentRunEvent.PLAN_COMPLETE): AgentRunState.VERIFYING,
        (AgentRunState.RECOVERING, AgentRunEvent.RETRY_OR_ALTERNATE_TOOL): AgentRunState.EXECUTING,
        (AgentRunState.RECOVERING, AgentRunEvent.NEEDS_REPLAN): AgentRunState.PLANNING,
        (AgentRunState.RECOVERING, AgentRunEvent.NEEDS_USER_FACT): AgentRunState.AWAITING_USER,
        (AgentRunState.RECOVERING, AgentRunEvent.UNRECOVERABLE): AgentRunState.FAILED,
        (AgentRunState.AWAITING_USER, AgentRunEvent.ANSWER_RECEIVED): AgentRunState.PLANNING,
        (AgentRunState.AWAITING_APPROVAL, AgentRunEvent.APPROVED): AgentRunState.EXECUTING,
        (AgentRunState.AWAITING_APPROVAL, AgentRunEvent.REJECTED): AgentRunState.CANCELLED,
        (AgentRunState.VERIFYING, AgentRunEvent.ALL_CHECKS_PASS): AgentRunState.COMPLETED,
        (AgentRunState.VERIFYING, AgentRunEvent.CHECK_FAILS): AgentRunState.RECOVERING,
    }

    next_state = transitions.get((current_state, current_event))
    if next_state is None:
        raise IllegalRunTransition(
            f"Event {current_event.value} is not valid from state {current_state.value}."
        )
    return next_state

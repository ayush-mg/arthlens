from decimal import Decimal

import pytest
from backend.arthlens.agent.budgets import (
    RunBudgetDecision,
    RunBudgetLimits,
)
from backend.arthlens.agent.execution import build_default_tool_executor
from backend.arthlens.agent.orchestration import AgentRunOrchestrator
from backend.arthlens.agent.planning import GoalInterpreter, Planner, PlanValidator
from backend.arthlens.agent.run_lifecycle import (
    AgentRunEvent,
    AgentRunState,
    transition_run_state,
)
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from backend.arthlens.llm.testing import FakeLLMClient

_GOAL_RESPONSE = {
    "objective": "Calculate break-even quantity.",
    "intent": "calculate break-even",
    "required_slots": ["price", "variable_cost", "fixed_costs"],
}
_PLAN_RESPONSE = {
    "steps": [
        {
            "step_id": "break_even",
            "tool_name": "calculate_break_even",
            "tool_input": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        }
    ]
}


def _test_model_call_cost(task_type):
    if task_type not in {"goal_interpretation", "planning"}:
        raise ValueError("Unexpected model task type.")
    return Decimal("0.001")


def _test_verifier(objective, outputs):
    return isinstance(objective, dict) and isinstance(outputs, tuple)


class MemoryAgentRunRepository:
    def __init__(
        self,
        objective,
        *,
        limits=RunBudgetLimits(),
    ):
        self.run = {
            "id": "run-1",
            "objective": objective,
            "state": AgentRunState.CREATED.value,
            "steps_used": 0,
            "replans_used": 0,
            "model_calls_used": 0,
            "cost_usd": 0.0,
        }
        self.limits = limits
        self.events = []
        self.checkpoints = []

    def record_event(self, run_id, event_type, payload=None):
        event = {
            "seq": len(self.events) + 1,
            "type": event_type,
            "payload": payload or {},
        }
        self.events.append(event)
        return event

    def get_run(self, run_id, _owner_id=None):
        if _owner_id is not None:
            return None
        return dict(self.run) if run_id == self.run["id"] else None

    def transition(
        self,
        run_id,
        event,
        payload=None,
        *,
        expected_state=None,
        plan_retry_available=False,
    ):
        assert run_id == self.run["id"]
        previous = AgentRunState(self.run["state"])
        if expected_state is not None:
            assert previous is expected_state
        persisted_event = event
        event_payload = payload or {}
        if (
            event is AgentRunEvent.NEEDS_REPLAN
            and self.run["replans_used"] >= self.limits.max_replans
        ):
            persisted_event = AgentRunEvent.BUDGET_LIMIT_HIT
            event_payload = {**event_payload, "budget": "replans"}
        next_state = transition_run_state(
            previous,
            persisted_event,
            plan_retry_available=plan_retry_available,
        )
        self.run["state"] = next_state.value
        if event is AgentRunEvent.NEEDS_REPLAN and persisted_event is event:
            self.run["replans_used"] += 1
        record = {"event": persisted_event.value, "payload": event_payload}
        self.events.append(record)
        return record

    def reserve_budget(self, run_id, reservation, *, checkpoint=None):
        assert run_id == self.run["id"]
        exhausted = None
        if self.run["steps_used"] + reservation.steps > self.limits.max_steps:
            exhausted = "steps"
        elif (
            self.run["model_calls_used"] + reservation.model_calls
            > self.limits.max_model_calls
        ):
            exhausted = "model_calls"
        elif (
            Decimal(str(self.run["cost_usd"])) + reservation.cost_usd
            > self.limits.max_cost_usd
        ):
            exhausted = "cost_usd"
        if exhausted:
            self.run["state"] = AgentRunState.BUDGET_EXHAUSTED.value
            self.events.append(
                {
                    "event": AgentRunEvent.BUDGET_LIMIT_HIT.value,
                    "payload": {"budget": exhausted},
                }
            )
            return self._decision(False, exhausted)
        self.run["steps_used"] += reservation.steps
        self.run["model_calls_used"] += reservation.model_calls
        self.run["cost_usd"] = float(
            Decimal(str(self.run["cost_usd"])) + reservation.cost_usd
        )
        if checkpoint is not None:
            self.checkpoints.append(checkpoint)
            self.events.append(
                {
                    "event": AgentRunEvent.CHECKPOINT_SAVED.value,
                    "payload": {"tool": checkpoint.tool},
                }
            )
        return self._decision(True, None)

    def _decision(self, allowed, exhausted):
        return RunBudgetDecision(
            allowed=allowed,
            exhausted_budget=exhausted,
            steps_used=self.run["steps_used"],
            replans_used=self.run["replans_used"],
            model_calls_used=self.run["model_calls_used"],
            cost_usd=Decimal(str(self.run["cost_usd"])),
        )


def _orchestrator(repository, *, verifier=_test_verifier, llm=None):
    client = llm or FakeLLMClient(
        {
            "goal_interpretation": [_GOAL_RESPONSE],
            "planning": [_PLAN_RESPONSE],
        }
    )
    registry = build_default_tool_registry()
    return AgentRunOrchestrator(
        repository,
        GoalInterpreter(client),
        Planner(client, PlanValidator(registry)),
        build_default_tool_executor(),
        model_call_cost=_test_model_call_cost,
        verifier=verifier,
    )


@pytest.mark.unit
def test_orchestrator_executes_validated_tool_plan_and_verifies_before_completion():
    repository = MemoryAgentRunRepository(
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        }
    )
    verified = []
    orchestrator = _orchestrator(
        repository,
        verifier=lambda objective, outputs: (
            verified.append((objective, outputs)) is None
            and outputs[0]["result"]["break_even_quantity"] == 5
        ),
    )

    result = orchestrator.run("run-1")

    assert result.state is AgentRunState.COMPLETED
    assert result.outputs[0]["result"]["break_even_quantity"] == 5.0
    assert len(verified) == 1
    assert repository.run["model_calls_used"] == 2
    assert repository.run["steps_used"] == 1
    assert len(repository.checkpoints) == 1
    assert [event["event"] for event in repository.events] == [
        "RUN_ACCEPTED",
        "OBJECTIVE_VALID",
        "PLAN_VALIDATED",
        "CHECKPOINT_SAVED",
        "TOOL_RETURNED",
        "PLAN_COMPLETE",
        "ALL_CHECKS_PASS",
    ]


@pytest.mark.unit
def test_orchestrator_pauses_for_required_user_slots_without_planning():
    repository = MemoryAgentRunRepository(
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {"price": 100},
        }
    )
    llm = FakeLLMClient(
        {
            "goal_interpretation": [
                {
                    "objective": _GOAL_RESPONSE["objective"],
                    "intent": _GOAL_RESPONSE["intent"],
                    "required_slots": ["price", "fixed_costs"],
                }
            ]
        }
    )

    result = _orchestrator(repository, llm=llm).run("run-1")

    assert result.state is AgentRunState.AWAITING_USER
    assert result.missing_slots == ("fixed_costs",)
    assert repository.run["model_calls_used"] == 1


@pytest.mark.unit
def test_orchestrator_fails_closed_when_verification_is_unavailable_or_fails():
    for verifier, reason in ((None, "verification_unavailable"), (lambda *_: False, "verification_failed")):
        repository = MemoryAgentRunRepository(
            {
                "objective": "Calculate break-even quantity.",
                "supplied_slots": {
                    "price": 100,
                    "variable_cost": 40,
                    "fixed_costs": 300,
                },
            }
        )

        result = _orchestrator(repository, verifier=verifier).run("run-1")

        assert result.state is AgentRunState.FAILED
        assert result.reason == reason


@pytest.mark.unit
def test_orchestrator_does_not_execute_approval_gated_tool():
    repository = MemoryAgentRunRepository(
        {
            "objective": "Publish a run.",
            "supplied_slots": {},
        }
    )
    plan = {
        "steps": [
            {
                "step_id": "publish",
                "tool_name": "publish_to_shared_view",
                "tool_input": {"run_id": "run-1"},
            }
        ]
    }
    llm = FakeLLMClient(
        {
            "goal_interpretation": [
                {
                    "objective": "Publish a run.",
                    "intent": "publish",
                    "required_slots": [],
                }
            ],
            "planning": [plan],
        }
    )

    result = _orchestrator(repository, llm=llm).run("run-1")

    assert result.state is AgentRunState.AWAITING_APPROVAL
    assert repository.run["steps_used"] == 0
    assert repository.events[-1]["event"] == "GATED_ACTION_REACHED"


@pytest.mark.unit
def test_orchestrator_persists_budget_exhaustion_before_model_call():
    repository = MemoryAgentRunRepository(
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        },
        limits=RunBudgetLimits(max_model_calls=0),
    )

    result = _orchestrator(repository).run("run-1")

    assert result.state is AgentRunState.BUDGET_EXHAUSTED
    assert repository.run["model_calls_used"] == 0
    assert len(repository.events) == 2
    assert repository.events[-1]["event"] == "BUDGET_LIMIT_HIT"


@pytest.mark.unit
def test_orchestrator_fails_invalid_persisted_objective_without_calling_model():
    repository = MemoryAgentRunRepository({"goal": "missing objective"})
    llm = FakeLLMClient({})

    result = _orchestrator(repository, llm=llm).run("run-1")

    assert result.state is AgentRunState.FAILED
    assert result.reason == "objective_missing"
    assert repository.events[-1]["event"] == "UNRECOVERABLE"


@pytest.mark.unit
def test_orchestrator_marks_tool_failures_as_generic_and_terminal():
    repository = MemoryAgentRunRepository(
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        }
    )
    orchestrator = _orchestrator(repository)

    class BrokenExecutor:
        def execute(self, tool_name, payload):
            assert tool_name == "calculate_break_even"
            assert payload
            raise RuntimeError("private secret")

    orchestrator._executor = BrokenExecutor()

    result = orchestrator.run("run-1")

    assert result.state is AgentRunState.FAILED
    assert result.reason == "tool_execution_failed"
    assert "private secret" not in repr(repository.events)


@pytest.mark.unit
def test_orchestrator_records_fallback_event_when_llm_client_falls_back(monkeypatch):
    monkeypatch.setenv("DUMMY_PROVIDER_API_KEY", "sensitive-secret-token-xyz")

    class FallbackLLMClient:
        def __init__(self):
            self._events = [
                {
                    "provider": "gemini",
                    "model": "gemini-3.1-flash-lite",
                    "task_type": "goal_interpretation",
                    "reason": "Connection failed with sensitive-secret-token-xyz",
                }
            ]
            self._deterministic = FakeLLMClient(
                {
                    "goal_interpretation": [_GOAL_RESPONSE],
                    "planning": [_PLAN_RESPONSE],
                }
            )

        def generate_structured(self, prompt, schema, task_type):
            return self._deterministic.generate_structured(prompt, schema, task_type)

        def consume_fallback_events(self):
            ev = list(self._events)
            self._events.clear()
            return ev

    repository = MemoryAgentRunRepository(
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        }
    )
    fallback_client = FallbackLLMClient()
    orchestrator = _orchestrator(repository, llm=fallback_client)

    result = orchestrator.run("run-1")

    assert result.state is AgentRunState.COMPLETED
    fallback_events = [
        e for e in repository.events if e.get("type") == "LLM_FALLBACK_ACTIVATED"
    ]
    assert len(fallback_events) == 1
    assert fallback_events[0]["payload"]["provider"] == "gemini"
    assert fallback_events[0]["payload"]["task_type"] == "goal_interpretation"
    assert "sensitive-secret-token-xyz" not in fallback_events[0]["payload"]["reason"]
    assert "[REDACTED_SECRET]" in fallback_events[0]["payload"]["reason"]


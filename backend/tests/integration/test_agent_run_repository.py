import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from backend.arthlens.agent.budgets import RunBudgetLimits, RunBudgetReservation
from backend.arthlens.agent.checkpoints import RunStepCheckpoint
from backend.arthlens.agent.execution import build_default_tool_executor
from backend.arthlens.agent.orchestration import AgentRunOrchestrator
from backend.arthlens.agent.planning import GoalInterpreter, Planner, PlanValidator
from backend.arthlens.agent.run_lifecycle import (
    AgentRunEvent,
    AgentRunState,
    IllegalRunTransition,
)
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from backend.arthlens.infra.repositories import (
    ConcurrentRunTransition,
    PostgresAgentRunRepository,
    PostgresUserRepository,
)
from backend.arthlens.llm.testing import FakeLLMClient


@pytest.mark.integration
def test_agent_run_transitions_and_events_are_persisted_atomically():
    owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-run-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    repository = PostgresAgentRunRepository()
    run_id = repository.create_run(owner_id, {"goal": "test lifecycle"})

    created = repository.get_run(run_id, owner_id)
    assert created is not None
    assert created["state"] == AgentRunState.CREATED.value
    assert repository.get_run(run_id, str(uuid.uuid4())) is None

    transition = repository.transition(
        run_id,
        AgentRunEvent.RUN_ACCEPTED,
        {"source": "test"},
        expected_state=AgentRunState.CREATED,
    )
    assert transition["from_state"] == AgentRunState.CREATED.value
    assert transition["state"] == AgentRunState.INTERPRETING.value
    assert transition["seq"] == 1
    assert not transition["terminal"]

    events = repository.list_events(run_id)
    assert len(events) == 1
    assert events[0]["seq"] == 1
    assert events[0]["type"] == AgentRunEvent.RUN_ACCEPTED.value
    assert events[0]["payload"] == {
        "source": "test",
        "from_state": AgentRunState.CREATED.value,
        "to_state": AgentRunState.INTERPRETING.value,
    }

    with pytest.raises(ConcurrentRunTransition, match="not expected"):
        repository.transition(
            run_id,
            AgentRunEvent.OBJECTIVE_VALID,
            expected_state=AgentRunState.CREATED,
        )

    with pytest.raises(IllegalRunTransition, match="not valid"):
        repository.transition(run_id, AgentRunEvent.TOOL_RETURNED)

    assert repository.get_run(run_id)["state"] == AgentRunState.INTERPRETING.value
    assert len(repository.list_events(run_id)) == 1


@pytest.mark.integration
def test_agent_run_budget_reservations_enforce_limits_atomically():
    owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-budget-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    limits = RunBudgetLimits(
        max_steps=2,
        max_replans=1,
        max_model_calls=2,
        max_cost_usd=Decimal("0.25"),
    )
    repository = PostgresAgentRunRepository(budget_limits=limits)

    step_run = repository.create_run(owner_id, {"budget": "steps"})
    assert repository.reserve_budget(
        step_run,
        RunBudgetReservation(steps=2),
    ).allowed
    step_decision = repository.reserve_budget(
        step_run,
        RunBudgetReservation(steps=1),
    )
    assert not step_decision.allowed
    assert step_decision.exhausted_budget == "steps"
    assert repository.get_run(step_run)["steps_used"] == 2
    assert repository.get_run(step_run)["state"] == AgentRunState.BUDGET_EXHAUSTED.value
    step_event = repository.list_events(step_run)[0]
    assert step_event["type"] == AgentRunEvent.BUDGET_LIMIT_HIT.value
    assert step_event["payload"]["budget"] == "steps"

    model_run = repository.create_run(owner_id, {"budget": "model_calls"})
    assert repository.reserve_budget(
        model_run,
        RunBudgetReservation(model_calls=2),
    ).allowed
    model_decision = repository.reserve_budget(
        model_run,
        RunBudgetReservation(model_calls=1),
    )
    assert not model_decision.allowed
    assert model_decision.exhausted_budget == "model_calls"
    assert repository.get_run(model_run)["model_calls_used"] == 2

    cost_run = repository.create_run(owner_id, {"budget": "cost"})
    assert repository.reserve_budget(
        cost_run,
        RunBudgetReservation(cost_usd=Decimal("0.2500")),
    ).allowed
    cost_decision = repository.reserve_budget(
        cost_run,
        RunBudgetReservation(cost_usd=Decimal("0.0001")),
    )
    assert not cost_decision.allowed
    assert cost_decision.exhausted_budget == "cost_usd"
    assert repository.get_run(cost_run)["cost_usd"] == 0.25
    assert repository.get_run(cost_run)["state"] == AgentRunState.BUDGET_EXHAUSTED.value


@pytest.mark.integration
def test_replan_budget_exhaustion_is_persisted_as_terminal_event():
    owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-replan-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    repository = PostgresAgentRunRepository(
        budget_limits=RunBudgetLimits(max_replans=1)
    )
    run_id = repository.create_run(owner_id, {"budget": "replans"})
    events_to_recover = (
        AgentRunEvent.RUN_ACCEPTED,
        AgentRunEvent.OBJECTIVE_VALID,
        AgentRunEvent.PLAN_VALIDATED,
        AgentRunEvent.TOOL_RETURNED,
        AgentRunEvent.ERROR_GAP_OR_CONTRADICTION,
        AgentRunEvent.NEEDS_REPLAN,
        AgentRunEvent.PLAN_VALIDATED,
        AgentRunEvent.TOOL_RETURNED,
        AgentRunEvent.ERROR_GAP_OR_CONTRADICTION,
    )
    for event in events_to_recover:
        repository.transition(run_id, event)

    exhausted = repository.transition(run_id, AgentRunEvent.NEEDS_REPLAN)

    assert exhausted["state"] == AgentRunState.BUDGET_EXHAUSTED.value
    assert exhausted["event"] == AgentRunEvent.BUDGET_LIMIT_HIT.value
    assert exhausted["payload"]["budget"] == "replans"
    assert repository.get_run(run_id)["replans_used"] == 1


@pytest.mark.integration
def test_concurrent_budget_reservations_cannot_exceed_run_cap():
    owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-concurrent-budget-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    repository = PostgresAgentRunRepository(
        budget_limits=RunBudgetLimits(max_steps=1)
    )
    run_id = repository.create_run(owner_id, {"budget": "concurrent"})

    def reserve_one_step():
        return repository.reserve_budget(
            run_id,
            RunBudgetReservation(steps=1),
        ).allowed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: reserve_one_step(), range(2)))

    assert sorted(results) == [False, True]
    run = repository.get_run(run_id)
    assert run["steps_used"] == 1
    assert run["state"] == AgentRunState.BUDGET_EXHAUSTED.value
    events = repository.list_events(run_id)
    assert len(events) == 1
    assert events[0]["type"] == AgentRunEvent.BUDGET_LIMIT_HIT.value


@pytest.mark.integration
def test_checkpoint_and_step_budget_commit_atomically_and_can_be_loaded():
    owner_id = str(uuid.uuid4())
    other_owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-checkpoint-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    repository = PostgresAgentRunRepository(
        budget_limits=RunBudgetLimits(max_steps=2)
    )
    run_id = repository.create_run(owner_id, {"goal": "recover after restart"})
    checkpoint = RunStepCheckpoint(
        tool="fetch_economic_indicator",
        input={"series": "population.total"},
        memento={"plan": [{"tool": "verify_claim"}], "next_step": 0},
        status="WAITING",
    )

    stored = repository.reserve_budget(
        run_id,
        RunBudgetReservation(steps=1, model_calls=1, cost_usd=Decimal("0.01")),
        checkpoint=checkpoint,
    )

    assert stored.allowed
    assert stored.checkpoint_seq == 1
    assert repository.get_run(run_id)["steps_used"] == 1
    assert repository.get_run(run_id)["model_calls_used"] == 1
    assert repository.get_latest_checkpoint(run_id, owner_id) == {
        "run_id": run_id,
        "seq": 1,
        "tool": "fetch_economic_indicator",
        "input": {"series": "population.total"},
        "output": None,
        "memento": {"plan": [{"tool": "verify_claim"}], "next_step": 0},
        "status": "WAITING",
        "started_at": None,
        "ended_at": None,
    }
    assert repository.get_latest_checkpoint(run_id, other_owner_id) is None

    events = repository.list_events(run_id)
    assert len(events) == 1
    assert events[0]["type"] == AgentRunEvent.CHECKPOINT_SAVED.value
    assert events[0]["payload"]["step_seq"] == 1
    assert "memento" not in events[0]["payload"]

    second_checkpoint = repository.reserve_budget(
        run_id,
        RunBudgetReservation(steps=1),
        checkpoint=RunStepCheckpoint(
            memento={"plan": [{"tool": "verify_claim"}], "next_step": 1},
            status="RUNNING",
        ),
    )
    assert second_checkpoint.allowed
    assert second_checkpoint.checkpoint_seq == 2
    assert repository.get_latest_checkpoint(run_id, owner_id)["seq"] == 2

    denied = repository.reserve_budget(
        run_id,
        RunBudgetReservation(steps=1),
        checkpoint=RunStepCheckpoint(
            memento={"next_step": 2},
            status="RUNNING",
        ),
    )
    assert not denied.allowed
    assert denied.exhausted_budget == "steps"
    assert repository.get_run(run_id)["steps_used"] == 2
    assert repository.get_latest_checkpoint(run_id, owner_id)["seq"] == 2
    events = repository.list_events(run_id)
    assert [event["type"] for event in events] == [
        AgentRunEvent.CHECKPOINT_SAVED.value,
        AgentRunEvent.CHECKPOINT_SAVED.value,
        AgentRunEvent.BUDGET_LIMIT_HIT.value,
    ]

@pytest.mark.integration
def test_agent_orchestrator_persists_verified_tool_run_to_postgres():
    owner_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"agent-orchestrator-{owner_id}@arthlens.test",
        "password_hash": "integration-test-only",
    })
    repository = PostgresAgentRunRepository()
    run_id = repository.create_run(
        owner_id,
        {
            "objective": "Calculate break-even quantity.",
            "supplied_slots": {
                "price": 100,
                "variable_cost": 40,
                "fixed_costs": 300,
            },
        },
    )
    llm_client = FakeLLMClient(
        {
            "goal_interpretation": [
                {
                    "objective": "Calculate break-even quantity.",
                    "intent": "calculate break-even",
                    "required_slots": ["price", "variable_cost", "fixed_costs"],
                }
            ],
            "planning": [
                {
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
            ],
        }
    )
    tools = build_default_tool_registry()
    service = AgentRunOrchestrator(
        repository,
        GoalInterpreter(llm_client),
        Planner(llm_client, PlanValidator(tools)),
        build_default_tool_executor(),
        model_call_cost=lambda _: Decimal("0.001"),
        verifier=lambda objective, outputs: (
            isinstance(objective, dict)
            and outputs[0]["result"]["break_even_quantity"] == 5
        ),
    )

    result = service.run(run_id)

    assert result.state is AgentRunState.COMPLETED
    persisted = repository.get_run(run_id, owner_id)
    assert persisted["state"] == AgentRunState.COMPLETED.value
    assert persisted["model_calls_used"] == 2
    assert persisted["steps_used"] == 1
    assert persisted["cost_usd"] == 0.002
    events = repository.list_events(run_id)
    assert [event["type"] for event in events] == [
        "RUN_ACCEPTED",
        "OBJECTIVE_VALID",
        "PLAN_VALIDATED",
        "CHECKPOINT_SAVED",
        "TOOL_RETURNED",
        "PLAN_COMPLETE",
        "ALL_CHECKS_PASS",
    ]
    assert events[4]["payload"]["result"]["break_even_quantity"] == 5
    checkpoint = repository.get_latest_checkpoint(run_id, owner_id)
    assert checkpoint["status"] == "SUCCEEDED"
    assert checkpoint["output"]["result"]["break_even_quantity"] == 5
    assert checkpoint["memento"]["next_step"] == 0

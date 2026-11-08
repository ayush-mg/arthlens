"""PostgreSQL integration tests for durable agent worker and checkpoint recovery.

Authoritative Specification:
- ArthLens Build Handbook v1.0 (Parts 8.2-8.5, 9.1).
- Atomic run claiming with SELECT ... FOR UPDATE SKIP LOCKED.
- Checkpoint-based crash recovery and safe resume.
- Bounded recovery attempts and explicit terminal failure.
- Concurrency and lease expiry protection.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from backend.arthlens.agent.budgets import RunBudgetReservation
from backend.arthlens.agent.checkpoints import RunStepCheckpoint
from backend.arthlens.agent.execution import ToolExecutionRegistry
from backend.arthlens.agent.orchestration import AgentRunOrchestrator
from backend.arthlens.agent.planning import ValidatedPlan
from backend.arthlens.agent.run_lifecycle import (
    AgentRunEvent,
    AgentRunState,
)
from backend.arthlens.agent.tool_registry import (
    CalculateBreakEvenInput,
    build_default_tool_registry,
)
from backend.arthlens.agent.worker import (
    execute_agent_run_background,
    run_worker_loop,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import AgentRunModel, AgentRunStepModel, RunEventModel
from backend.arthlens.infra.repositories import (
    PostgresAgentRunRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role


@pytest.fixture(autouse=True)
def clean_agent_runs():
    """Ensure a clean database state for each durable worker test."""
    session_factory = get_session_factory()
    with session_factory() as session:
        session.query(RunEventModel).delete()
        session.query(AgentRunStepModel).delete()
        session.query(AgentRunModel).delete()
        session.commit()
    yield
    with session_factory() as session:
        session.query(RunEventModel).delete()
        session.query(AgentRunStepModel).delete()
        session.query(AgentRunModel).delete()
        session.commit()


def _create_test_user() -> str:
    user_id = str(uuid.uuid4())
    PostgresUserRepository().save({
        "id": user_id,
        "email": f"worker-test-{user_id}@arthlens.test",
        "password_hash": "test-password-hash",
        "roles": [Role.ENTREPRENEUR.value],
    })
    return user_id


@pytest.mark.integration
def test_concurrent_workers_cannot_claim_same_run():
    """Verify that multiple concurrent workers claiming runs with SKIP LOCKED never claim the same run."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()

    # Create 5 pending runs
    run_ids = [
        repo.create_run(owner_id, {"objective": f"Run {i}", "supplied_slots": {}})
        for i in range(5)
    ]
    assert len(run_ids) == 5

    claimed_by_worker: list[dict] = []
    lock = threading.Lock()

    def worker_claim(worker_num: int):
        worker_id = f"worker-concurrent-{worker_num}"
        claimed = repo.claim_pending_run(worker_id=worker_id, lease_duration_seconds=60)
        if claimed:
            with lock:
                claimed_by_worker.append(claimed)

    # Launch 10 worker threads concurrently competing for 5 runs
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_claim, i) for i in range(10)]
        for f in futures:
            f.result()

    # Assert exactly 5 runs were claimed with 0 duplicates
    assert len(claimed_by_worker) == 5
    claimed_ids = [c["id"] for c in claimed_by_worker]
    assert len(set(claimed_ids)) == 5
    assert set(claimed_ids) == set(run_ids)

    # Verify each claimed run in DB has active lease and claimed_by set
    session_factory = get_session_factory()
    with session_factory() as session:
        for run_id in run_ids:
            model = session.get(AgentRunModel, uuid.UUID(run_id))
            assert model is not None
            assert model.claimed_by is not None
            assert model.claimed_by.startswith("worker-concurrent-")
            assert model.lease_expires_at is not None
            assert model.lease_expires_at > datetime.now(timezone.utc)

    # Subsequent claim returns None as all runs are leased
    assert repo.claim_pending_run(worker_id="extra-worker") is None


@pytest.mark.integration
def test_duplicate_execution_prevented():
    """Verify that a run claimed by one worker cannot be claimed or executed by another worker."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {"objective": "Exclusive execution", "supplied_slots": {}})

    # Worker 1 claims run by id
    worker_1 = "worker-alpha"
    assert repo.claim_run_by_id(run_id, worker_id=worker_1, lease_duration_seconds=120) is True

    # Worker 2 attempts to claim by id -> fails
    worker_2 = "worker-beta"
    assert repo.claim_run_by_id(run_id, worker_id=worker_2, lease_duration_seconds=120) is False

    # Worker 2 attempts to claim via pending queue -> fails (returns None)
    assert repo.claim_pending_run(worker_id=worker_2) is None

    # Worker 2 tries to run background execution -> returns already claimed reason
    bg_result = execute_agent_run_background(run_id, worker_id=worker_2, repository=repo)
    assert bg_result.reason == "already_claimed_or_completed"

    # Worker 1 releases claim
    assert repo.release_claim(run_id, worker_id=worker_1) is True

    # Now Worker 2 can claim it
    assert repo.claim_run_by_id(run_id, worker_id=worker_2, lease_duration_seconds=120) is True
    repo.release_claim(run_id, worker_id=worker_2)


@pytest.mark.integration
def test_lease_expiry_allows_reclaim():
    """Verify that when a worker's lease expires, another worker can safely claim the run."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {"objective": "Lease expiry test", "supplied_slots": {}})

    # Worker 1 claims run with lease
    claimed = repo.claim_pending_run(worker_id="worker-old", lease_duration_seconds=300)
    assert claimed is not None
    assert claimed["id"] == run_id

    # Another worker cannot claim it
    assert repo.claim_pending_run(worker_id="worker-new") is None

    # Simulate lease expiry by rewinding lease_expires_at in the database
    session_factory = get_session_factory()
    with session_factory() as session:
        model = session.get(AgentRunModel, uuid.UUID(run_id))
        assert model is not None
        model.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

    # Now Worker New can claim the expired run
    reclaimed = repo.claim_pending_run(worker_id="worker-new", lease_duration_seconds=300)
    assert reclaimed is not None
    assert reclaimed["id"] == run_id
    assert reclaimed["claimed_by"] == "worker-new"
    assert reclaimed["lease_expires_at"] > datetime.now(timezone.utc)

    repo.release_claim(run_id, worker_id="worker-new")


@pytest.mark.integration
def test_worker_crash_saves_checkpoint_and_recovers_to_resumable_state():
    """Verify that a crashed worker run with in-flight steps is transitioned to RECOVERING with step status RECOVERED."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {"objective": "Crash recovery", "supplied_slots": {}})

    # Claim and start run
    assert repo.claim_run_by_id(run_id, worker_id="crashed-worker", lease_duration_seconds=10) is True
    repo.transition(run_id, AgentRunEvent.RUN_ACCEPTED, expected_state=AgentRunState.CREATED)
    repo.transition(run_id, AgentRunEvent.OBJECTIVE_VALID, expected_state=AgentRunState.INTERPRETING)
    repo.transition(run_id, AgentRunEvent.PLAN_VALIDATED, {"step_count": 2}, expected_state=AgentRunState.PLANNING)

    # Save step 1 checkpoint with RUNNING status
    sample_plan = {
        "steps": [
            {
                "step_id": "step-1",
                "tool_name": "calculate_break_even",
                "tool_input": {"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
                "depends_on": [],
                "approval_required": False,
            },
            {
                "step_id": "step-2",
                "tool_name": "calculate_loan_schedule",
                "tool_input": {"principal": 10000.0, "annual_interest_rate": 0.1, "tenure_months": 12},
                "depends_on": [],
                "approval_required": False,
            },
        ]
    }
    checkpoint = RunStepCheckpoint(
        tool="calculate_break_even",
        input={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
        status="RUNNING",
        memento={
            "plan": sample_plan,
            "next_step": 0,
            "completed_outputs": {},
        },
    )
    decision = repo.reserve_budget(run_id, RunBudgetReservation(steps=1), checkpoint=checkpoint)
    assert decision.allowed is True

    # Simulate worker crash by expiring lease
    session_factory = get_session_factory()
    with session_factory() as session:
        model = session.get(AgentRunModel, uuid.UUID(run_id))
        assert model is not None
        model.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        session.commit()

    # Call recover_stale_runs
    recovered_count = repo.recover_stale_runs()
    assert recovered_count == 1

    # Inspect run and checkpoint in DB
    updated_run = repo.get_run(run_id)
    assert updated_run["state"] == AgentRunState.RECOVERING.value
    assert updated_run["claimed_by"] is None
    assert updated_run["lease_expires_at"] is None
    assert updated_run["recovery_attempts"] == 1

    latest_checkpoint = repo.get_latest_checkpoint(run_id)
    assert latest_checkpoint is not None
    assert latest_checkpoint["status"] == "RECOVERED"

    events = repo.list_events(run_id)
    recovery_events = [e for e in events if e["type"] == "WORKER_CRASH_RECOVERED"]
    assert len(recovery_events) == 1
    assert recovery_events[0]["payload"]["recovery_attempt"] == 1
    assert recovery_events[0]["payload"]["step_seq"] == 1


@pytest.mark.integration
def test_checkpoint_recovery_resumes_without_re_executing_prior_steps():
    """Verify that resuming a recovered run starts at the uncompleted step and never re-executes completed steps."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {
        "objective": "Multi-step plan execution",
        "supplied_slots": {
            "price": 100,
            "variable_cost": 40,
            "fixed_costs": 300,
            "principal": 10000,
            "annual_interest_rate": 0.1,
            "tenure_months": 12,
        },
    })

    # Track execution counts
    execution_counts = {"step_1": 0, "step_2": 0}

    def dummy_break_even(inp):
        if inp.price == 100.0:
            execution_counts["step_1"] += 1
            return {"break_even_quantity": 5.0, "quality_flags": []}
        else:
            execution_counts["step_2"] += 1
            return {"break_even_quantity": 6.0, "quality_flags": []}

    schemas = build_default_tool_registry()
    registry = ToolExecutionRegistry(
        schemas,
        {"calculate_break_even": dummy_break_even},
    )

    sample_plan = {
        "steps": [
            {
                "step_id": "step-1",
                "tool_name": "calculate_break_even",
                "tool_input": {"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
                "depends_on": [],
                "approval_required": False,
            },
            {
                "step_id": "step-2",
                "tool_name": "calculate_break_even",
                "tool_input": {"price": 120.0, "variable_cost": 50.0, "fixed_costs": 400.0},
                "depends_on": [],
                "approval_required": False,
            },
        ]
    }

    # Step 0 executes and completes successfully before crash
    repo.transition(run_id, AgentRunEvent.RUN_ACCEPTED, expected_state=AgentRunState.CREATED)
    repo.transition(run_id, AgentRunEvent.OBJECTIVE_VALID, expected_state=AgentRunState.INTERPRETING)
    repo.transition(run_id, AgentRunEvent.PLAN_VALIDATED, {"step_count": 2}, expected_state=AgentRunState.PLANNING)

    checkpoint_step0 = RunStepCheckpoint(
        tool="calculate_break_even",
        input={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
        status="RUNNING",
        memento={
            "plan": sample_plan,
            "next_step": 0,
            "completed_outputs": {},
        },
    )
    repo.reserve_budget(run_id, RunBudgetReservation(steps=1), checkpoint=checkpoint_step0)
    # Execute step 0
    res0 = dummy_break_even(CalculateBreakEvenInput(price=100.0, variable_cost=40.0, fixed_costs=300.0))
    repo.transition(
        run_id,
        AgentRunEvent.TOOL_RETURNED,
        {"step_id": "step-1", "tool_name": "calculate_break_even", "result": res0},
        expected_state=AgentRunState.EXECUTING,
    )
    # State is now OBSERVING, step 0 succeeded
    assert execution_counts["step_1"] == 1
    assert execution_counts["step_2"] == 0

    # Simulate worker crash before step 1 starts:
    session_factory = get_session_factory()
    with session_factory() as session:
        model = session.get(AgentRunModel, uuid.UUID(run_id))
        assert model is not None
        model.claimed_by = "crashed-worker"
        model.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

    # Recover the crashed run
    recovered = repo.recover_stale_runs()
    assert recovered == 1
    run_state = repo.get_run(run_id)["state"]
    assert run_state == AgentRunState.RECOVERING.value

    # Build an orchestrator using our dummy registry and verifier
    class DummyInterpreter:
        def interpret(self, obj, supplied_slots=None):
            return None

    class DummyPlanner:
        def plan(self, goal, replan=False, budget=None, replan_feedback=None):
            return ValidatedPlan.model_validate(sample_plan)

    def simple_verifier(obj, outputs):
        return len(outputs) == 2

    orch = AgentRunOrchestrator(
        repository=repo,
        goal_interpreter=DummyInterpreter(),
        planner=DummyPlanner(),
        executor=registry,
        model_call_cost=lambda t: Decimal("0.001"),
        verifier=simple_verifier,
    )

    # Worker resumes run
    claimed = repo.claim_pending_run(worker_id="resuming-worker", lease_duration_seconds=120)
    assert claimed is not None
    assert claimed["id"] == run_id

    result = orch.resume(run_id)
    assert result.state == AgentRunState.COMPLETED
    assert len(result.outputs) == 2

    # CRITICAL ASSERTION: Step 0 was NEVER re-executed! Step 1 was executed exactly once!
    assert execution_counts["step_1"] == 1
    assert execution_counts["step_2"] == 1

    repo.release_claim(run_id, worker_id="resuming-worker")


@pytest.mark.integration
def test_bounded_recovery_attempts_terminates_unrecoverable_run():
    """Verify that a run exceeding max_recovery_attempts is explicitly and terminally marked FAILED."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {"objective": "Flapping run", "supplied_slots": {}})

    # Put run into EXECUTING state
    repo.transition(run_id, AgentRunEvent.RUN_ACCEPTED, expected_state=AgentRunState.CREATED)
    repo.transition(run_id, AgentRunEvent.OBJECTIVE_VALID, expected_state=AgentRunState.INTERPRETING)
    repo.transition(run_id, AgentRunEvent.PLAN_VALIDATED, {"step_count": 1}, expected_state=AgentRunState.PLANNING)

    checkpoint = RunStepCheckpoint(
        tool="calculate_break_even",
        input={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
        status="RUNNING",
        memento={
            "plan": {
                "steps": [
                    {
                        "step_id": "step-1",
                        "tool_name": "calculate_break_even",
                        "tool_input": {"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
                        "depends_on": [],
                        "approval_required": False,
                    }
                ]
            },
            "next_step": 0,
            "completed_outputs": {},
        },
    )
    repo.reserve_budget(run_id, RunBudgetReservation(steps=1), checkpoint=checkpoint)

    session_factory = get_session_factory()

    def expire_lease():
        with session_factory() as session:
            model = session.get(AgentRunModel, uuid.UUID(run_id))
            assert model is not None
            model.claimed_by = "worker-crash"
            model.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            session.commit()

    # Recovery 1 (attempts: 0 -> 1)
    expire_lease()
    assert repo.recover_stale_runs() == 1
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.RECOVERING.value
    assert run["recovery_attempts"] == 1

    # Recovery 2 (attempts: 1 -> 2)
    expire_lease()
    assert repo.recover_stale_runs() == 1
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.RECOVERING.value
    assert run["recovery_attempts"] == 2

    # Recovery 3 (attempts: 2 -> 3)
    expire_lease()
    assert repo.recover_stale_runs() == 1
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.RECOVERING.value
    assert run["recovery_attempts"] == 3

    # Recovery 4: max_recovery_attempts (3) reached! Must terminate with FAILED!
    expire_lease()
    assert repo.recover_stale_runs() == 1
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.FAILED.value
    assert run["claimed_by"] is None
    assert run["lease_expires_at"] is None

    # Check terminal event logged
    events = repo.list_events(run_id)
    exhausted_events = [e for e in events if e["type"] == "WORKER_RECOVERY_EXHAUSTED"]
    assert len(exhausted_events) == 1
    assert exhausted_events[0]["payload"]["to_state"] == AgentRunState.FAILED.value

    # Subsequent recovery calls do not touch it
    assert repo.recover_stale_runs() == 0
    # Pending claim will not pick it up
    assert repo.claim_pending_run() is None


@pytest.mark.integration
def test_worker_loop_processes_recovering_run_end_to_end():
    """Verify that run_worker_loop discovers, recovers, claims, resumes, and completes a crashed run."""
    owner_id = _create_test_user()
    repo = PostgresAgentRunRepository()
    run_id = repo.create_run(owner_id, {
        "objective": "Calculate break-even quantity.",
        "supplied_slots": {
            "price": 100.0,
            "variable_cost": 40.0,
            "fixed_costs": 300.0,
        },
    })

    # Put run into EXECUTING state with a step
    repo.transition(run_id, AgentRunEvent.RUN_ACCEPTED, expected_state=AgentRunState.CREATED)
    repo.transition(run_id, AgentRunEvent.OBJECTIVE_VALID, expected_state=AgentRunState.INTERPRETING)
    repo.transition(run_id, AgentRunEvent.PLAN_VALIDATED, {"step_count": 1}, expected_state=AgentRunState.PLANNING)

    plan_data = {
        "steps": [
            {
                "step_id": "step-1",
                "tool_name": "calculate_break_even",
                "tool_input": {"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
                "depends_on": [],
                "approval_required": False,
            }
        ]
    }
    checkpoint = RunStepCheckpoint(
        tool="calculate_break_even",
        input={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 300.0},
        status="RUNNING",
        memento={
            "plan": plan_data,
            "next_step": 0,
            "completed_outputs": {},
        },
    )
    repo.reserve_budget(run_id, RunBudgetReservation(steps=1), checkpoint=checkpoint)

    # Crash the worker: expire lease
    session_factory = get_session_factory()
    with session_factory() as session:
        model = session.get(AgentRunModel, uuid.UUID(run_id))
        assert model is not None
        model.claimed_by = "dead-worker"
        model.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        session.commit()

    # Run the worker loop for 1 iteration
    stop_event = threading.Event()
    processed = run_worker_loop(
        poll_interval=0.01,
        stop_event=stop_event,
        max_iterations=1,
        repository=repo,
    )
    assert processed == 1

    # Verify run completed
    run = repo.get_run(run_id)
    assert run["state"] == AgentRunState.COMPLETED.value
    assert run["claimed_by"] is None
    assert run["lease_expires_at"] is None

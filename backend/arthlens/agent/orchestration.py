"""Explicit, budgeted execution of a persisted agent run.

This service is callable by a trusted worker or test harness; it does not start
background jobs or claim exactly-once recovery semantics.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Protocol

from backend.arthlens.agent.budgets import RunBudgetDecision, RunBudgetReservation
from backend.arthlens.agent.checkpoints import RunStepCheckpoint
from backend.arthlens.agent.execution import (
    ToolApprovalRequired,
    ToolExecutionRegistry,
)
from backend.arthlens.agent.planning import (
    GoalInterpreter,
    Planner,
    PlanValidationError,
    ReplanLimitReached,
    ValidatedPlan,
)
from backend.arthlens.agent.run_lifecycle import (
    AgentRunEvent,
    AgentRunState,
    IllegalRunTransition,
)


class AgentRunRepository(Protocol):
    def get_run(
        self,
        run_id: str,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    def transition(
        self,
        run_id: str,
        event: AgentRunEvent,
        payload: dict[str, Any] | None = None,
        *,
        expected_state: AgentRunState | None = None,
        plan_retry_available: bool = False,
    ) -> dict[str, Any]: ...

    def reserve_budget(
        self,
        run_id: str,
        reservation: RunBudgetReservation,
        *,
        checkpoint: RunStepCheckpoint | None = None,
    ) -> RunBudgetDecision: ...

    def get_latest_checkpoint(
        self,
        run_id: str,
        owner_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    def record_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


RunVerifier = Callable[[Mapping[str, Any], tuple[dict[str, Any], ...]], bool]
ModelCallCost = Callable[[str], Decimal]


@dataclass(frozen=True)
class OrchestrationResult:
    run_id: str
    state: AgentRunState
    outputs: tuple[dict[str, Any], ...] = ()
    missing_slots: tuple[str, ...] = ()
    reason: str | None = None


class AgentRunOrchestrator:
    """Run one persisted objective using the injected planner and tool executor."""

    def __init__(
        self,
        repository: AgentRunRepository,
        goal_interpreter: GoalInterpreter,
        planner: Planner,
        executor: ToolExecutionRegistry,
        *,
        model_call_cost: ModelCallCost,
        verifier: RunVerifier | None,
    ) -> None:
        if not callable(model_call_cost):
            raise TypeError("model_call_cost must be a callable cost estimator.")
        if verifier is not None and not callable(verifier):
            raise TypeError("verifier must be callable when provided.")
        self._repository = repository
        self._goal_interpreter = goal_interpreter
        self._planner = planner
        self._executor = executor
        self._model_call_cost = model_call_cost
        self._verifier = verifier

    def run(self, run_id: str) -> OrchestrationResult:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Agent run {run_id!s} was not found.")
        if run["state"] == AgentRunState.RECOVERING.value:
            return self.resume(run_id)
        if run["state"] != AgentRunState.CREATED.value:
            raise IllegalRunTransition(
                f"Orchestrator requires a CREATED run; current state is {run['state']}."
            )

        objective_payload = run["objective"]
        objective = objective_payload.get("objective")
        supplied_slots = objective_payload.get("supplied_slots")
        if supplied_slots is None:
            supplied_slots = {
                k: v for k, v in objective_payload.items() if k != "objective"
            }
        if not isinstance(objective, str) or not objective.strip():
            return self._fail(
                run_id,
                AgentRunState.CREATED,
                "objective_missing",
            )
        if not isinstance(supplied_slots, Mapping):
            return self._fail(
                run_id,
                AgentRunState.CREATED,
                "supplied_slots_invalid",
            )

        self._repository.transition(
            run_id,
            AgentRunEvent.RUN_ACCEPTED,
            expected_state=AgentRunState.CREATED,
        )
        try:
            if not self._reserve_model_call(run_id, "goal_interpretation"):
                return self._current_result(run_id, reason="budget_exhausted")
            goal = self._goal_interpreter.interpret(
                objective,
                supplied_slots=supplied_slots,
            )
            self._record_llm_fallback_events(run_id)
        except Exception:
            self._record_llm_fallback_events(run_id)
            return self._fail(
                run_id,
                AgentRunState.INTERPRETING,
                "goal_interpretation_failed",
            )

        if goal.missing_slots:
            self._repository.transition(
                run_id,
                AgentRunEvent.REQUIRED_SLOTS_MISSING,
                {"missing_slots": list(goal.missing_slots)},
                expected_state=AgentRunState.INTERPRETING,
            )
            return self._current_result(run_id, missing_slots=goal.missing_slots)

        self._repository.transition(
            run_id,
            AgentRunEvent.OBJECTIVE_VALID,
            expected_state=AgentRunState.INTERPRETING,
        )
        replan = False
        replan_feedback: str | None = None
        while True:
            if not self._reserve_model_call(run_id, "planning"):
                return self._current_result(run_id, reason="budget_exhausted")
            try:
                budget = self._budget_snapshot(run_id)
                plan = self._planner.plan(
                    goal,
                    replan=replan,
                    budget=budget if replan else None,
                    replan_feedback=replan_feedback,
                )
                self._record_llm_fallback_events(run_id)
                break
            except (PlanValidationError, ReplanLimitReached, ValueError, TypeError):
                self._record_llm_fallback_events(run_id)
                run = self._repository.get_run(run_id)
                if run is None:
                    raise KeyError(f"Agent run {run_id!s} disappeared during planning.")
                if run["state"] == AgentRunState.BUDGET_EXHAUSTED.value:
                    return self._current_result(run_id, reason="budget_exhausted")
                self._repository.transition(
                    run_id,
                    AgentRunEvent.PLAN_INVALID,
                    {"reason": "plan_rejected"},
                    expected_state=AgentRunState.PLANNING,
                )
                self._repository.transition(
                    run_id,
                    AgentRunEvent.NEEDS_REPLAN,
                    {"reason": "plan_rejected"},
                    expected_state=AgentRunState.RECOVERING,
                )
                run = self._repository.get_run(run_id)
                if run is None:
                    raise KeyError(f"Agent run {run_id!s} disappeared during recovery.")
                if run["state"] == AgentRunState.BUDGET_EXHAUSTED.value:
                    return self._current_result(run_id, reason="budget_exhausted")
                if run["state"] != AgentRunState.PLANNING.value:
                    return self._current_result(run_id, reason="plan_rejected")
                replan = True
                replan_feedback = (
                    "The prior proposal failed registered tool validation or did not "
                    "match caller supplied facts. Return a corrected plan using only "
                    "explicit supplied values and registered tools."
                )
            except Exception:
                self._record_llm_fallback_events(run_id)
                return self._fail(
                    run_id,
                    AgentRunState.PLANNING,
                    "planning_failed",
                )

        # OBJECTIVE_VALID enters PLANNING; PLAN_VALIDATED is emitted only after
        # the full model proposal passes every registered contract.
        self._repository.transition(
            run_id,
            AgentRunEvent.PLAN_VALIDATED,
            {"step_count": len(plan.steps)},
            expected_state=AgentRunState.PLANNING,
        )
        outputs = self._execute_plan(run_id, plan)
        if isinstance(outputs, OrchestrationResult):
            return outputs

        self._repository.transition(
            run_id,
            AgentRunEvent.PLAN_COMPLETE,
            expected_state=AgentRunState.OBSERVING,
        )
        if self._verifier is None:
            self._repository.transition(
                run_id,
                AgentRunEvent.CHECK_FAILS,
                {"reason": "verification_unavailable"},
                expected_state=AgentRunState.VERIFYING,
            )
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "verification_unavailable",
            )
        try:
            verified = self._verifier(objective_payload, tuple(outputs))
        except Exception:
            verified = False
        if not isinstance(verified, bool) or not verified:
            self._repository.transition(
                run_id,
                AgentRunEvent.CHECK_FAILS,
                {"reason": "verification_failed"},
                expected_state=AgentRunState.VERIFYING,
            )
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "verification_failed",
            )
        self._repository.transition(
            run_id,
            AgentRunEvent.ALL_CHECKS_PASS,
            expected_state=AgentRunState.VERIFYING,
        )
        return self._current_result(run_id, outputs=tuple(outputs))

    def resume(self, run_id: str) -> OrchestrationResult:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Agent run {run_id!s} was not found.")
        if run["state"] != AgentRunState.RECOVERING.value:
            raise IllegalRunTransition(
                f"Resume requires a RECOVERING run; current state is {run['state']}."
            )

        objective_payload = run["objective"]
        checkpoint = self._repository.get_latest_checkpoint(run_id)
        if checkpoint is None or not isinstance(checkpoint.get("memento"), dict):
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "no_checkpoint_available_for_resume",
            )

        memento = checkpoint["memento"]
        raw_plan = memento.get("plan")
        if not raw_plan:
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "corrupted_checkpoint_plan",
            )

        try:
            plan = ValidatedPlan.model_validate(raw_plan)
        except Exception:
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "corrupted_checkpoint_plan",
            )
        prior_step_idx = int(memento.get("next_step", 0))
        if checkpoint.get("status") == "SUCCEEDED":
            start_step_index = prior_step_idx + 1
        else:
            start_step_index = prior_step_idx

        if start_step_index >= len(plan.steps) and len(plan.steps) > 0:
            start_step_index = len(plan.steps) - 1

        completed_outputs_map = dict(memento.get("completed_outputs", {}))
        initial_outputs: list[dict[str, Any]] = []
        for s in plan.steps[:start_step_index]:
            initial_outputs.append({
                "step_id": s.step_id,
                "tool_name": s.tool_name,
                "tool_input": s.tool_input,
                "result": completed_outputs_map.get(s.step_id),
            })

        self._repository.transition(
            run_id,
            AgentRunEvent.RETRY_OR_ALTERNATE_TOOL,
            {
                "resumed_from_step": start_step_index,
                "checkpoint_seq": checkpoint.get("seq"),
            },
            expected_state=AgentRunState.RECOVERING,
        )

        outputs = self._execute_plan(
            run_id,
            plan,
            start_step_index=start_step_index,
            initial_outputs=initial_outputs,
            prior_outputs=completed_outputs_map,
        )
        if isinstance(outputs, OrchestrationResult):
            return outputs

        self._repository.transition(
            run_id,
            AgentRunEvent.PLAN_COMPLETE,
            expected_state=AgentRunState.OBSERVING,
        )
        if self._verifier is None:
            self._repository.transition(
                run_id,
                AgentRunEvent.CHECK_FAILS,
                {"reason": "verification_unavailable"},
                expected_state=AgentRunState.VERIFYING,
            )
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "verification_unavailable",
            )
        try:
            verified = self._verifier(objective_payload, tuple(outputs))
        except Exception:
            verified = False
        if not isinstance(verified, bool) or not verified:
            self._repository.transition(
                run_id,
                AgentRunEvent.CHECK_FAILS,
                {"reason": "verification_failed"},
                expected_state=AgentRunState.VERIFYING,
            )
            return self._fail(
                run_id,
                AgentRunState.RECOVERING,
                "verification_failed",
            )
        self._repository.transition(
            run_id,
            AgentRunEvent.ALL_CHECKS_PASS,
            expected_state=AgentRunState.VERIFYING,
        )
        return self._current_result(run_id, outputs=tuple(outputs))

    def _execute_plan(
        self,
        run_id: str,
        plan: ValidatedPlan,
        start_step_index: int = 0,
        initial_outputs: list[dict[str, Any]] | None = None,
        prior_outputs: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | OrchestrationResult:
        outputs: list[dict[str, Any]] = list(initial_outputs) if initial_outputs is not None else []
        prior_outputs_map: dict[str, Any] = dict(prior_outputs) if prior_outputs is not None else {}
        for index in range(start_step_index, len(plan.steps)):
            step = plan.steps[index]
            if step.approval_required:
                self._repository.transition(
                    run_id,
                    AgentRunEvent.GATED_ACTION_REACHED,
                    {"step_id": step.step_id, "tool_name": step.tool_name},
                    expected_state=AgentRunState.EXECUTING,
                )
                return self._current_result(run_id, outputs=tuple(outputs))

            checkpoint = RunStepCheckpoint(
                tool=step.tool_name,
                input=step.tool_input,
                status="RUNNING",
                memento={
                    "plan": plan.model_dump(mode="json"),
                    "next_step": index,
                    "completed_outputs": prior_outputs_map,
                },
                started_at=datetime.now(timezone.utc),
            )
            decision = self._repository.reserve_budget(
                run_id,
                RunBudgetReservation(steps=1),
                checkpoint=checkpoint,
            )
            if not decision.allowed:
                return self._current_result(run_id, reason="budget_exhausted")
            try:
                result = self._executor.execute(step.tool_name, step.tool_input)
            except ToolApprovalRequired:
                self._repository.transition(
                    run_id,
                    AgentRunEvent.GATED_ACTION_REACHED,
                    {"step_id": step.step_id, "tool_name": step.tool_name},
                    expected_state=AgentRunState.EXECUTING,
                )
                return self._current_result(run_id, outputs=tuple(outputs))
            except Exception:
                self._repository.transition(
                    run_id,
                    AgentRunEvent.ERROR_GAP_OR_CONTRADICTION,
                    {
                        "step_id": step.step_id,
                        "tool_name": step.tool_name,
                        "error": "tool_execution_failed",
                    },
                    expected_state=AgentRunState.EXECUTING,
                )
                return self._fail(
                    run_id,
                    AgentRunState.RECOVERING,
                    "tool_execution_failed",
                )

            output = {
                "step_id": step.step_id,
                "tool_name": step.tool_name,
                "tool_input": step.tool_input,
                "result": result,
            }
            self._repository.transition(
                run_id,
                AgentRunEvent.TOOL_RETURNED,
                output,
                expected_state=AgentRunState.EXECUTING,
            )
            outputs.append(output)
            prior_outputs_map[step.step_id] = result
            if index < len(plan.steps) - 1:
                self._repository.transition(
                    run_id,
                    AgentRunEvent.NEXT_STEP_READY,
                    {"step_id": plan.steps[index + 1].step_id},
                    expected_state=AgentRunState.OBSERVING,
                )
        return outputs

    def _reserve_model_call(self, run_id: str, task_type: str) -> bool:
        cost = self._model_call_cost(task_type)
        if not isinstance(cost, Decimal):
            raise TypeError("Model cost estimator must return Decimal.")
        decision = self._repository.reserve_budget(
            run_id,
            RunBudgetReservation(model_calls=1, cost_usd=cost),
        )
        return decision.allowed

    def _budget_snapshot(self, run_id: str) -> RunBudgetDecision:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Agent run {run_id!s} was not found.")
        return RunBudgetDecision(
            allowed=run["state"] not in {
                AgentRunState.BUDGET_EXHAUSTED.value,
                AgentRunState.FAILED.value,
                AgentRunState.CANCELLED.value,
            },
            exhausted_budget=None,
            steps_used=int(run.get("steps_used", 0)),
            replans_used=int(run.get("replans_used", 0)),
            model_calls_used=int(run.get("model_calls_used", 0)),
            cost_usd=Decimal(str(run.get("cost_usd", "0"))),
        )

    def _fail(
        self,
        run_id: str,
        state: AgentRunState,
        reason: str,
    ) -> OrchestrationResult:
        self._repository.transition(
            run_id,
            AgentRunEvent.UNRECOVERABLE,
            {"reason": reason},
            expected_state=state,
        )
        return self._current_result(run_id, reason=reason)

    def _current_result(
        self,
        run_id: str,
        *,
        outputs: tuple[dict[str, Any], ...] = (),
        missing_slots: tuple[str, ...] = (),
        reason: str | None = None,
    ) -> OrchestrationResult:
        run = self._repository.get_run(run_id)
        if run is None:
            raise KeyError(f"Agent run {run_id!s} disappeared during orchestration.")
        return OrchestrationResult(
            run_id=run_id,
            state=AgentRunState(run["state"]),
            outputs=outputs,
            missing_slots=missing_slots,
            reason=reason,
        )

    def _record_llm_fallback_events(self, run_id: str) -> None:
        """Query LLM clients for recorded fallback events and persist them safely."""
        from backend.arthlens.llm.provider import CredentialFirewall

        for component in (self._goal_interpreter, self._planner):
            client = getattr(component, "_llm_client", None)
            if client is not None and hasattr(client, "consume_fallback_events"):
                try:
                    events = client.consume_fallback_events()
                except Exception:
                    continue
                for fallback_event in events:
                    sanitized_event = {
                        k: CredentialFirewall.sanitize(str(v)) if isinstance(v, str) else v
                        for k, v in fallback_event.items()
                    }
                    if hasattr(self._repository, "record_event"):
                        try:
                            self._repository.record_event(
                                run_id,
                                "LLM_FALLBACK_ACTIVATED",
                                sanitized_event,
                            )
                        except Exception:
                            pass

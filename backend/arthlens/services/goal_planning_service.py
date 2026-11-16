"""Goal planning, task coordination, and evidence-backed actual-versus-plan evaluation."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping
import uuid

from sqlalchemy import select

from backend.arthlens.domain.business import GoalStatus, GoalType, Money
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    ActionPlanModel,
    ActionTaskModel,
    BusinessMembershipModel,
    GoalMilestoneModel,
    GoalModel,
    GoalProgressSnapshotModel,
)


class GoalPlanningNotFoundError(LookupError):
    pass


class GoalDeviationAnalyzer:
    """Explains profit goal variance using ledger-derived period comparisons."""

    @staticmethod
    def analyze_profit(current: Any, prior: Any, planned: Decimal, actual: Decimal) -> dict[str, Any]:
        gap = (planned - actual).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        current_categories = current.operating_expenses
        prior_categories = prior.operating_expenses
        drivers: list[dict[str, Any]] = []

        def add_driver(label: str, profit_impact: Decimal, current_amount: Decimal, prior_amount: Decimal) -> None:
            base = abs(prior_amount)
            percent = (profit_impact / base * Decimal("100")) if base else None
            drivers.append({
                "driver": label,
                "profit_impact": f"{profit_impact.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
                "current_period_value": f"{current_amount:.2f}",
                "prior_equal_length_period_value": f"{prior_amount:.2f}",
                "change_percent_vs_prior": f"{((current_amount - prior_amount) / base * Decimal('100')):.2f}" if base else None,
                "profit_impact_percent_of_prior_metric": f"{percent:.2f}" if percent is not None else None,
            })

        add_driver("Revenue movement", current.total_revenue.amount - prior.total_revenue.amount,
                   current.total_revenue.amount, prior.total_revenue.amount)
        add_driver("COGS movement", prior.cost_of_goods_sold.amount - current.cost_of_goods_sold.amount,
                   current.cost_of_goods_sold.amount, prior.cost_of_goods_sold.amount)
        category_names = sorted(set(current_categories) | set(prior_categories))
        for category in category_names:
            current_amount = current_categories.get(category, Money.zero()).amount
            prior_amount = prior_categories.get(category, Money.zero()).amount
            add_driver(f"{category} expense movement", prior_amount - current_amount, current_amount, prior_amount)
        total_attribution = sum((Decimal(item["profit_impact"]) for item in drivers), Decimal("0.00"))
        add_driver("Other ledger adjustments", (current.net_profit.amount - prior.net_profit.amount) - total_attribution,
                   current.net_profit.amount, prior.net_profit.amount)
        strongest = sorted(drivers, key=lambda item: abs(Decimal(item["profit_impact"])), reverse=True)[:3]
        return {
            "comparison_basis": "Prior equal-length period from posted ledger entries.",
            "current_period_net_profit": f"{current.net_profit.amount:.2f}",
            "prior_period_net_profit": f"{prior.net_profit.amount:.2f}",
            "period_over_period_net_profit_change": f"{current.net_profit.amount - prior.net_profit.amount:.2f}",
            "current_vs_plan_gap": f"{gap:.2f}",
            "drivers": drivers,
            "leading_drivers": strongest,
            "attribution_warning": "Period-over-period drivers explain ledger movement; they are not category budgets unless explicit budgets were recorded.",
        }


class GoalPlanningService:
    def __init__(self, session_factory=None, finance_engine: FinancialIntelligenceEngine | None = None):
        self.session_factory = session_factory or get_session_factory()
        self.finance_engine = finance_engine or FinancialIntelligenceEngine()

    @staticmethod
    def _goal(session, business_id: uuid.UUID, goal_id: uuid.UUID) -> GoalModel:
        goal = session.scalar(select(GoalModel).where(
            GoalModel.id == goal_id,
            GoalModel.business_id == business_id,
        ))
        if goal is None:
            raise GoalPlanningNotFoundError("Goal was not found in this workspace.")
        return goal

    @staticmethod
    def _milestone_dict(row: GoalMilestoneModel) -> dict[str, Any]:
        return {"id": str(row.id), "business_id": str(row.business_id), "goal_id": str(row.goal_id), "title": row.title,
                "target_date": row.target_date.isoformat(), "target_value": f"{Decimal(str(row.target_value)):.2f}",
                "created_at": row.created_at.isoformat() if row.created_at else None}

    @staticmethod
    def _plan_dict(row: ActionPlanModel, task_count: int = 0) -> dict[str, Any]:
        return {"id": str(row.id), "business_id": str(row.business_id), "goal_id": str(row.goal_id),
                "title": row.title, "description": row.description, "status": row.status,
                "task_count": task_count, "created_at": row.created_at.isoformat() if row.created_at else None}

    @staticmethod
    def _task_dict(row: ActionTaskModel) -> dict[str, Any]:
        return {"id": str(row.id), "business_id": str(row.business_id), "goal_id": str(row.goal_id),
                "plan_id": str(row.plan_id), "title": row.title, "description": row.description,
                "assigned_member_id": str(row.assigned_member_id) if row.assigned_member_id else None,
                "priority": row.priority, "status": row.status,
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "expected_financial_impact": f"{Decimal(str(row.expected_financial_impact)):.2f}",
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None}

    def create_milestone(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID,
                         title: str, target_date: date, target_value: Decimal) -> dict[str, Any]:
        with self.session_factory() as session, session.begin():
            goal = self._goal(session, business_id, goal_id)
            if target_date < goal.start_date or target_date > goal.target_date:
                raise ValueError("Milestone date must fall within the goal period.")
            if target_value < 0 or target_value > Decimal(str(goal.target_value)):
                raise ValueError("Milestone target must be non-negative and no greater than the goal target.")
            prior = session.scalars(select(GoalMilestoneModel).where(
                GoalMilestoneModel.business_id == business_id, GoalMilestoneModel.goal_id == goal_id,
            ).order_by(GoalMilestoneModel.target_date.asc())).all()
            if any(target_date == row.target_date for row in prior):
                raise ValueError("A milestone already exists for this date.")
            model = GoalMilestoneModel(business_id=business_id, goal_id=goal_id, title=title.strip(),
                                       target_date=target_date, target_value=target_value, created_by_user_id=user_id)
            session.add(model)
            session.flush()
            return self._milestone_dict(model)

    def list_milestones(self, business_id: uuid.UUID, goal_id: uuid.UUID) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            self._goal(session, business_id, goal_id)
            rows = session.scalars(select(GoalMilestoneModel).where(
                GoalMilestoneModel.business_id == business_id, GoalMilestoneModel.goal_id == goal_id,
            ).order_by(GoalMilestoneModel.target_date.asc())).all()
            return [self._milestone_dict(row) for row in rows]

    def delete_milestone(self, business_id: uuid.UUID, goal_id: uuid.UUID, milestone_id: uuid.UUID) -> None:
        with self.session_factory() as session, session.begin():
            self._goal(session, business_id, goal_id)
            milestone = session.scalar(select(GoalMilestoneModel).where(
                GoalMilestoneModel.id == milestone_id,
                GoalMilestoneModel.business_id == business_id,
                GoalMilestoneModel.goal_id == goal_id,
            ))
            if milestone is None:
                raise GoalPlanningNotFoundError("Milestone was not found in this workspace.")
            session.delete(milestone)

    def create_plan(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID,
                    title: str, description: str) -> dict[str, Any]:
        with self.session_factory() as session, session.begin():
            self._goal(session, business_id, goal_id)
            plan = ActionPlanModel(business_id=business_id, goal_id=goal_id, title=title.strip(),
                                   description=description.strip(), created_by_user_id=user_id)
            session.add(plan)
            session.flush()
            return self._plan_dict(plan)

    def list_plans(self, business_id: uuid.UUID, goal_id: uuid.UUID) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            self._goal(session, business_id, goal_id)
            plans = session.scalars(select(ActionPlanModel).where(
                ActionPlanModel.business_id == business_id, ActionPlanModel.goal_id == goal_id,
            ).order_by(ActionPlanModel.created_at.desc())).all()
            return [self._plan_dict(plan, len(session.scalars(select(ActionTaskModel.id).where(
                ActionTaskModel.business_id == business_id, ActionTaskModel.goal_id == goal_id,
                ActionTaskModel.plan_id == plan.id,
            )).all())) for plan in plans]

    def create_task(self, business_id: uuid.UUID, goal_id: uuid.UUID, plan_id: uuid.UUID, user_id: uuid.UUID,
                    *, title: str, description: str, assigned_member_id: uuid.UUID | None,
                    priority: int, status: str, due_date: date | None,
                    expected_financial_impact: Decimal) -> dict[str, Any]:
        if status not in {"TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"}:
            raise ValueError("Task status must be TODO, IN_PROGRESS, COMPLETED, or BLOCKED.")
        if not 1 <= priority <= 5:
            raise ValueError("Task priority must be between 1 and 5.")
        with self.session_factory() as session, session.begin():
            self._goal(session, business_id, goal_id)
            plan = session.scalar(select(ActionPlanModel).where(
                ActionPlanModel.id == plan_id, ActionPlanModel.business_id == business_id,
                ActionPlanModel.goal_id == goal_id,
            ))
            if plan is None:
                raise GoalPlanningNotFoundError("Action plan was not found in this workspace.")
            if assigned_member_id is not None:
                membership = session.scalar(select(BusinessMembershipModel.id).where(
                    BusinessMembershipModel.business_id == business_id,
                    BusinessMembershipModel.user_id == assigned_member_id,
                    BusinessMembershipModel.is_active.is_(True),
                ))
                if membership is None:
                    raise ValueError("Assigned user must be an active member of this workspace.")
            task = ActionTaskModel(
                business_id=business_id, goal_id=goal_id, plan_id=plan_id, title=title.strip(),
                description=description.strip(), assigned_member_id=assigned_member_id,
                priority=priority, status=status, due_date=due_date,
                expected_financial_impact=expected_financial_impact, created_by_user_id=user_id,
            )
            session.add(task)
            session.flush()
            return self._task_dict(task)

    def list_tasks(self, business_id: uuid.UUID, goal_id: uuid.UUID) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            self._goal(session, business_id, goal_id)
            rows = session.scalars(select(ActionTaskModel).where(
                ActionTaskModel.business_id == business_id, ActionTaskModel.goal_id == goal_id,
            ).order_by(ActionTaskModel.priority.asc(), ActionTaskModel.due_date.asc().nullslast(), ActionTaskModel.created_at.desc())).all()
            return [self._task_dict(row) for row in rows]

    def update_task(self, business_id: uuid.UUID, goal_id: uuid.UUID, task_id: uuid.UUID,
                    updates: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"title", "description", "assigned_member_id", "priority", "status", "due_date", "expected_financial_impact"}
        if set(updates) - allowed:
            raise ValueError("Unsupported task fields were supplied.")
        with self.session_factory() as session, session.begin():
            self._goal(session, business_id, goal_id)
            task = session.scalar(select(ActionTaskModel).where(
                ActionTaskModel.id == task_id, ActionTaskModel.business_id == business_id,
                ActionTaskModel.goal_id == goal_id,
            ).with_for_update())
            if task is None:
                raise GoalPlanningNotFoundError("Task was not found in this workspace.")
            if "status" in updates and updates["status"] not in {"TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"}:
                raise ValueError("Task status must be TODO, IN_PROGRESS, COMPLETED, or BLOCKED.")
            if "priority" in updates and not 1 <= updates["priority"] <= 5:
                raise ValueError("Task priority must be between 1 and 5.")
            assigned = updates.get("assigned_member_id", task.assigned_member_id)
            if assigned is not None:
                membership = session.scalar(select(BusinessMembershipModel.id).where(
                    BusinessMembershipModel.business_id == business_id,
                    BusinessMembershipModel.user_id == assigned,
                    BusinessMembershipModel.is_active.is_(True),
                ))
                if membership is None:
                    raise ValueError("Assigned user must be an active member of this workspace.")
            for key, value in updates.items():
                setattr(task, key, value)
            session.flush()
            return self._task_dict(task)

    def delete_task(self, business_id: uuid.UUID, goal_id: uuid.UUID, task_id: uuid.UUID) -> None:
        with self.session_factory() as session, session.begin():
            self._goal(session, business_id, goal_id)
            task = session.scalar(select(ActionTaskModel).where(
                ActionTaskModel.id == task_id, ActionTaskModel.business_id == business_id,
                ActionTaskModel.goal_id == goal_id,
            ))
            if task is None:
                raise GoalPlanningNotFoundError("Task was not found in this workspace.")
            session.delete(task)

    def _actual_value(self, business_id: uuid.UUID, goal: GoalModel, as_of: date) -> tuple[Decimal, dict[str, Any], list[dict[str, Any]]]:
        goal_type = GoalType(goal.goal_type)
        end_date = min(as_of, goal.target_date)
        if end_date < goal.start_date:
            end_date = goal.start_date
            zero = Decimal("0.00")
            return zero, {"formula": "Goal period has not started.", "source_counts": {}}, []
        pnl = self.finance_engine.calculate_pnl(business_id, goal.start_date, end_date)
        evidence: list[dict[str, Any]] = []
        formula = ""
        if goal_type == GoalType.REVENUE:
            actual = pnl.total_revenue.amount
            formula = "Posted net sales + posted other operating income during the goal period."
            for invoice in self.finance_engine.invoice_repo.list_by_business(business_id):
                if goal.start_date <= invoice.invoice_date <= end_date and invoice.status.value != "CANCELLED":
                    evidence.append({"source_type": "SALES_INVOICE", "record_id": str(invoice.id), "label": invoice.invoice_number,
                                     "metric_value": f"{invoice.total_amount.amount:.2f}", "timestamp": invoice.invoice_date.isoformat()})
        elif goal_type == GoalType.PROFIT:
            actual = pnl.net_profit.amount
            formula = "Posted revenue - verified COGS - operating expenses - interest and taxes recorded in the goal period."
            evidence.extend([
                {"source_type": "FINANCIAL_STATEMENT", "record_id": f"{business_id}:{goal.start_date}:{end_date}", "label": "Revenue", "metric_value": f"{pnl.total_revenue.amount:.2f}", "timestamp": end_date.isoformat()},
                {"source_type": "FINANCIAL_STATEMENT", "record_id": f"{business_id}:{goal.start_date}:{end_date}", "label": "COGS", "metric_value": f"{pnl.cost_of_goods_sold.amount:.2f}", "timestamp": end_date.isoformat()},
                {"source_type": "FINANCIAL_STATEMENT", "record_id": f"{business_id}:{goal.start_date}:{end_date}", "label": "Operating expenses", "metric_value": f"{pnl.total_operating_expenses.amount:.2f}", "timestamp": end_date.isoformat()},
                *[{"source_type": "EXPENSE_CATEGORY", "record_id": f"{business_id}:{category}", "label": category,
                   "metric_value": f"{amount.amount:.2f}", "timestamp": end_date.isoformat()}
                  for category, amount in pnl.operating_expenses.items()],
            ])
        elif goal_type == GoalType.CASH_RESERVE:
            wc = self.finance_engine.calculate_working_capital(business_id, end_date)
            actual = wc.cash_and_bank.amount
            formula = "Cash on hand + bank balance as of the evaluation date."
            evidence.append({"source_type": "FINANCIAL_SNAPSHOT", "record_id": f"{business_id}:{end_date}", "label": "Cash and bank", "metric_value": f"{actual:.2f}", "timestamp": end_date.isoformat()})
        elif goal_type == GoalType.DEBT_REDUCTION:
            suppliers = self.finance_engine.supplier_repo.list_by_business(business_id)
            payable_now = sum((supplier.current_balance.amount for supplier in suppliers), Decimal("0.00"))
            baseline = Decimal(str((goal.plan_details or {}).get("baseline_debt_total", payable_now)))
            actual = max(Decimal("0.00"), baseline - payable_now)
            formula = "Starting supplier payable balance - current supplier payable balance; loan principal is not included unless recorded in a tracked payable account."
            evidence.extend({"source_type": "SUPPLIER", "record_id": str(supplier.id), "label": supplier.name,
                             "metric_value": f"{supplier.current_balance.amount:.2f}", "timestamp": end_date.isoformat()} for supplier in suppliers)
        elif goal_type == GoalType.WORKING_CAPITAL:
            wc = self.finance_engine.calculate_working_capital(business_id, end_date)
            actual = wc.net_working_capital.amount
            formula = "Cash + receivables + inventory - payables - short-term liabilities as of the evaluation date."
            evidence.append({"source_type": "FINANCIAL_SNAPSHOT", "record_id": f"{business_id}:{end_date}", "label": "Net working capital", "metric_value": f"{actual:.2f}", "timestamp": end_date.isoformat()})
        else:
            raise ValueError(f"No deterministic actual-value adapter exists for goal type {goal_type.value}.")
        details = {
            "formula": formula,
            "start_date": goal.start_date.isoformat(), "end_date": end_date.isoformat(),
            "source_counts": {"evidence_items": len(evidence), "expense_categories": len(pnl.operating_expenses)},
            "data_quality_warnings": list(pnl.data_quality_warnings),
            "operating_expense_categories": {key: f"{value.amount:.2f}" for key, value in pnl.operating_expenses.items()},
            "revenue": f"{pnl.total_revenue.amount:.2f}",
            "cogs": f"{pnl.cost_of_goods_sold.amount:.2f}",
            "total_operating_expenses": f"{pnl.total_operating_expenses.amount:.2f}",
            "net_profit": f"{pnl.net_profit.amount:.2f}",
        }
        return Decimal(str(actual)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), details, evidence

    @staticmethod
    def _planned_value(goal: GoalModel, milestones: list[GoalMilestoneModel], as_of: date) -> Decimal:
        start_value = Decimal("0.00")
        end_value = Decimal(str(goal.target_value))
        end_date = goal.target_date
        if as_of <= goal.start_date:
            return start_value
        if as_of >= end_date:
            return end_value
        points = [(goal.start_date, start_value)]
        points.extend((item.target_date, Decimal(str(item.target_value))) for item in milestones)
        points.append((end_date, end_value))
        points.sort(key=lambda point: point[0])
        left = points[0]
        for right in points[1:]:
            if as_of <= right[0]:
                span = Decimal((right[0] - left[0]).days)
                if span <= 0:
                    return right[1].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                elapsed = Decimal((as_of - left[0]).days)
                value = left[1] + (right[1] - left[1]) * elapsed / span
                return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            left = right
        return end_value

    @staticmethod
    def classify_progress(actual: Decimal, planned: Decimal, target: Decimal) -> str:
        if actual >= target:
            return "ACHIEVED"
        if planned <= Decimal("0.00") or actual >= planned:
            return "ON_TRACK"
        gap_pct = (planned - actual) / max(abs(planned), Decimal("1.00")) * Decimal("100")
        return "AT_RISK" if gap_pct <= Decimal("30") else "BEHIND"

    def evaluate_goal_progress(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID,
                               as_of_date: date | None = None) -> dict[str, Any]:
        today = date.today()
        as_of = min(as_of_date or today, today)
        with self.session_factory() as session:
            goal = self._goal(session, business_id, goal_id)
            milestones = session.scalars(select(GoalMilestoneModel).where(
                GoalMilestoneModel.business_id == business_id, GoalMilestoneModel.goal_id == goal_id,
            ).order_by(GoalMilestoneModel.target_date.asc())).all()
            goal_values = {
                "id": goal.id, "type": goal.goal_type, "title": goal.title, "target": Decimal(str(goal.target_value)),
                "start": goal.start_date, "end": goal.target_date, "plan_details": dict(goal.plan_details or {}),
            }
        # Use a detached minimal view to keep calculation separate from the write transaction.
        goal = type("GoalSnapshot", (), {
            "goal_type": goal_values["type"], "title": goal_values["title"],
            "target_value": goal_values["target"], "start_date": goal_values["start"],
            "target_date": goal_values["end"], "plan_details": goal_values["plan_details"],
        })()
        actual, actual_details, evidence = self._actual_value(business_id, goal, as_of)
        planned = self._planned_value(goal, milestones, as_of)
        deviation = (actual - planned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        target = goal_values["target"]
        progress_status = self.classify_progress(actual, planned, target)
        deviation_analysis: dict[str, Any] | None = None
        if goal_values["type"] == GoalType.PROFIT.value and actual_details.get("start_date") and actual_details.get("end_date"):
            current_start = date.fromisoformat(actual_details["start_date"])
            current_end = date.fromisoformat(actual_details["end_date"])
            period_days = (current_end - current_start).days + 1
            prior_end = current_start - timedelta(days=1)
            prior_start = prior_end - timedelta(days=max(period_days - 1, 0))
            current_pnl = self.finance_engine.calculate_pnl(business_id, current_start, current_end)
            prior_pnl = self.finance_engine.calculate_pnl(business_id, prior_start, prior_end)
            deviation_analysis = GoalDeviationAnalyzer.analyze_profit(current_pnl, prior_pnl, planned, actual)
        explanation = {
            "status": progress_status,
            "summary": f"Actual {actual:.2f} against planned {planned:.2f}; variance {deviation:+.2f}.",
            "formula": actual_details["formula"],
            "actual_vs_plan": {"actual": f"{actual:.2f}", "planned": f"{planned:.2f}", "variance": f"{deviation:.2f}"},
            "drivers": actual_details,
            "deviation_analysis": deviation_analysis,
        }
        with self.session_factory() as session, session.begin():
            persisted_goal = session.scalar(select(GoalModel).where(
                GoalModel.id == goal_id, GoalModel.business_id == business_id,
            ).with_for_update())
            if persisted_goal is None:
                raise GoalPlanningNotFoundError("Goal was not found in this workspace.")
            persisted_goal.current_value = actual
            if persisted_goal.status != GoalStatus.CANCELLED.value:
                persisted_goal.status = GoalStatus(progress_status).value
            snapshot = GoalProgressSnapshotModel(
                business_id=business_id, goal_id=goal_id, as_of_date=as_of,
                planned_value=planned, actual_value=actual, deviation_value=deviation,
                status=progress_status, explanation=explanation, evidence_items=evidence,
                created_by_user_id=user_id,
            )
            session.add(snapshot)
            session.flush()
            return {
                "id": str(snapshot.id), "business_id": str(business_id), "goal_id": str(goal_id),
                "as_of_date": as_of.isoformat(), "planned_value": f"{planned:.2f}",
                "actual_value": f"{actual:.2f}", "deviation_value": f"{deviation:.2f}",
                "status": persisted_goal.status, "explanation": explanation, "evidence_items": evidence,
                "milestones": [self._milestone_dict(row) for row in milestones],
            }


_goal_planning_service: GoalPlanningService | None = None


def get_goal_planning_service() -> GoalPlanningService:
    global _goal_planning_service
    if _goal_planning_service is None:
        _goal_planning_service = GoalPlanningService()
    return _goal_planning_service

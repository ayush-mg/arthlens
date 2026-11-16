from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from backend.arthlens.domain.business import Money
from backend.arthlens.services.goal_planning_service import GoalDeviationAnalyzer, GoalPlanningService


def test_goal_plan_interpolates_between_milestones():
    goal = SimpleNamespace(start_date=date(2026, 1, 1), target_date=date(2026, 1, 11), target_value=Decimal("200"))
    milestones = [SimpleNamespace(target_date=date(2026, 1, 11), target_value=Decimal("200"))]

    planned = GoalPlanningService._planned_value(goal, milestones, date(2026, 1, 6))

    assert planned == Decimal("100.00")


def test_goal_progress_classification_is_deterministic():
    classify = GoalPlanningService.classify_progress
    assert classify(Decimal("100"), Decimal("100"), Decimal("1000")) == "ON_TRACK"
    assert classify(Decimal("80"), Decimal("100"), Decimal("1000")) == "AT_RISK"
    assert classify(Decimal("60"), Decimal("100"), Decimal("1000")) == "BEHIND"
    assert classify(Decimal("1000"), Decimal("100"), Decimal("1000")) == "ACHIEVED"


def test_profit_goal_deviation_explains_period_delta_with_reconciling_drivers():
    prior = SimpleNamespace(
        total_revenue=Money(Decimal("1000")),
        cost_of_goods_sold=Money(Decimal("400")),
        total_operating_expenses=Money(Decimal("300")),
        net_profit=Money(Decimal("300")),
        operating_expenses={"RENT": Money(Decimal("100"))},
    )
    current = SimpleNamespace(
        total_revenue=Money(Decimal("1200")),
        cost_of_goods_sold=Money(Decimal("500")),
        total_operating_expenses=Money(Decimal("350")),
        net_profit=Money(Decimal("350")),
        operating_expenses={"RENT": Money(Decimal("120")), "LOGISTICS": Money(Decimal("30"))},
    )

    analysis = GoalDeviationAnalyzer.analyze_profit(current, prior, Decimal("500"), Decimal("350"))
    driver_total = sum(Decimal(item["profit_impact"]) for item in analysis["drivers"])

    assert analysis["period_over_period_net_profit_change"] == "50.00"
    assert driver_total == Decimal("50.00")
    assert analysis["current_vs_plan_gap"] == "150.00"
    assert "not category budgets" in analysis["attribution_warning"]

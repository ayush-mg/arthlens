"""Explicit per-run budget limits from Handbook Section 8.3."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class RunBudgetLimits:
    max_steps: int = 25
    max_replans: int = 3
    max_model_calls: int = 30
    max_cost_usd: Decimal = Decimal("0.25")

    def __post_init__(self) -> None:
        for name in ("max_steps", "max_replans", "max_model_calls"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")

        try:
            max_cost = Decimal(str(self.max_cost_usd))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("max_cost_usd must be a finite non-negative decimal.") from exc
        if not max_cost.is_finite() or max_cost < 0:
            raise ValueError("max_cost_usd must be a finite non-negative decimal.")
        if max_cost.as_tuple().exponent < -4:
            raise ValueError("max_cost_usd may have at most four decimal places.")
        object.__setattr__(self, "max_cost_usd", max_cost)


@dataclass(frozen=True)
class RunBudgetReservation:
    steps: int = 0
    model_calls: int = 0
    cost_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        for name in ("steps", "model_calls"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} reservation must be a non-negative integer.")
        try:
            cost = Decimal(str(self.cost_usd))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError("cost reservation must be a finite non-negative decimal.") from exc
        if not cost.is_finite() or cost < 0:
            raise ValueError("cost reservation must be a finite non-negative decimal.")
        if self.steps == 0 and self.model_calls == 0 and cost == 0:
            raise ValueError("A budget reservation must consume at least one budget.")
        if cost.as_tuple().exponent < -4:
            raise ValueError("Cost reservations may have at most four decimal places.")
        object.__setattr__(self, "cost_usd", cost)


@dataclass(frozen=True)
class RunBudgetDecision:
    allowed: bool
    exhausted_budget: str | None
    steps_used: int
    replans_used: int
    model_calls_used: int
    cost_usd: Decimal
    checkpoint_seq: int | None = None

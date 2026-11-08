"""Fail-closed execution for tools with validated schemas and bound handlers."""

import json
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel

from backend.arthlens.agent.tool_registry import (
    CalculateBreakEvenInput,
    CalculateLoanScheduleInput,
    ToolSchema,
    ToolSchemaRegistry,
    build_default_tool_registry,
)
from backend.arthlens.finance import (
    LoanTerms,
    build_loan_schedule,
    calculate_break_even_quantity,
)

ToolHandler = Callable[[BaseModel], Any]
ApprovalCheck = Callable[[ToolSchema, BaseModel], bool]


class ToolApprovalRequired(PermissionError):
    """Raised when a tool requires an approval that has not been granted."""


class ToolExecutionRegistry:
    """Validates tool inputs and dispatches only explicitly bound handlers."""

    def __init__(
        self,
        schemas: ToolSchemaRegistry,
        handlers: Mapping[str, ToolHandler],
        *,
        approval_check: ApprovalCheck | None = None,
    ) -> None:
        self._schemas = schemas
        self._handlers = dict(handlers)
        self._approval_check = approval_check
        for name, handler in self._handlers.items():
            schemas.get(name)
            if not callable(handler):
                raise TypeError(f"Handler for tool {name!r} must be callable.")

    def execute(self, name: str, raw_input: Any) -> Any:
        tool = self._schemas.get(name)
        parsed_input = self._schemas.validate_input(name, raw_input)
        handler = self._handlers.get(name)
        if handler is None:
            raise KeyError(f"Tool {name!r} has no executable handler.")
        if tool.approval_required and (
            self._approval_check is None
            or not self._approval_check(tool, parsed_input)
        ):
            raise ToolApprovalRequired(f"Tool {name!r} requires explicit approval.")

        result = handler(parsed_input)
        try:
            json.dumps(result, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise TypeError(f"Tool {name!r} returned a non-JSON-compatible result.") from exc
        if tool.output_model is not None:
            validated_output = self._schemas.validate_output(name, result)
            return validated_output.model_dump(mode="json")
        return result


def build_default_tool_executor() -> ToolExecutionRegistry:
    """Bind only implemented, deterministic tools; other schemas remain unavailable."""
    schemas = build_default_tool_registry()
    return ToolExecutionRegistry(
        schemas,
        {
            "calculate_break_even": _calculate_break_even,
            "calculate_loan_schedule": _calculate_loan_schedule,
        },
    )


def _calculate_break_even(payload: BaseModel) -> dict[str, Any]:
    if not isinstance(payload, CalculateBreakEvenInput):
        raise TypeError("calculate_break_even received an unexpected input model.")
    quantity = calculate_break_even_quantity(
        payload.price,
        payload.variable_cost,
        payload.fixed_costs,
    )
    return {
        "break_even_quantity": quantity,
        "quality_flags": [] if quantity is not None else ["NO_BREAK_EVEN"],
    }


def _calculate_loan_schedule(payload: BaseModel) -> dict[str, Any]:
    if not isinstance(payload, CalculateLoanScheduleInput):
        raise TypeError("calculate_loan_schedule received an unexpected input model.")
    terms = LoanTerms(
        principal=payload.principal,
        annual_rate=payload.rate,
        repayment_months=payload.term,
        moratorium_months=payload.moratorium.months,
        moratorium_interest_treatment=payload.moratorium.interest_treatment,
        subsidy_amount=payload.subsidy_params.amount,
        subsidy_treatment=payload.subsidy_params.treatment,
        subsidy_release_month=payload.subsidy_params.release_month,
    )
    schedule = build_loan_schedule(terms)
    return {
        "financed_principal": schedule.financed_principal,
        "total_repaid": schedule.total_repaid,
        "rows": [
            {
                "month": row.month,
                "opening_balance": row.opening_balance,
                "interest": row.interest,
                "principal_paid": row.principal_paid,
                "subsidy_principal_adjustment": row.subsidy_principal_adjustment,
                "subsidy_cash_release": row.subsidy_cash_release,
                "debt_service": row.debt_service,
                "closing_balance": row.closing_balance,
            }
            for row in schedule.rows
        ],
    }

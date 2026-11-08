"""Visitors for evaluating policy-rule expression trees."""

import math
import operator
from dataclasses import dataclass
from typing import Iterable, Mapping

from backend.arthlens.domain.interfaces import RuleVisitor
from backend.arthlens.policy.rules import (
    AllOfNode,
    AnyOfNode,
    Comparison,
    ConstantNode,
    NotNode,
    PredicateNode,
    RuleNode,
    Scalar,
    TruthValue,
)


@dataclass(frozen=True)
class EvaluationTrace:
    node_type: str
    result: TruthValue
    reason: str
    fact: str | None = None
    comparison: Comparison | None = None
    observed: Scalar | None = None
    expected: Scalar | tuple[Scalar, ...] | None = None
    children: tuple["EvaluationTrace", ...] = ()


class EligibilityEvaluator(RuleVisitor):
    """Evaluate generic predicates with Kleene three-valued logic."""

    def __init__(self, facts: Mapping[str, Scalar | None]) -> None:
        if not isinstance(facts, Mapping):
            raise TypeError("Evaluation facts must be a mapping")
        for key, value in facts.items():
            if not isinstance(key, str):
                raise TypeError("Evaluation fact names must be strings")
            if value is not None and not isinstance(value, (bool, int, float, str)):
                raise TypeError(f"Fact {key!r} must be a scalar value or None")
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f"Fact {key!r} must be finite")
        self._facts = facts

    def evaluate(self, node: RuleNode) -> EvaluationTrace:
        trace = node.accept(self)
        if not isinstance(trace, EvaluationTrace):
            raise TypeError("Rule visitor returned an invalid evaluation trace")
        return trace

    def visit_constant(self, node: ConstantNode) -> EvaluationTrace:
        return EvaluationTrace(
            node_type="constant",
            result=node.value,
            reason=f"constant is {node.value.value.lower()}",
        )

    def visit_predicate(self, node: PredicateNode) -> EvaluationTrace:
        observed = self._facts.get(node.fact)
        if node.fact not in self._facts or observed is None:
            return EvaluationTrace(
                node_type="predicate",
                result=TruthValue.UNKNOWN,
                reason=f"fact {node.fact!r} is missing",
                fact=node.fact,
                comparison=node.comparison,
                expected=node.expected,
            )

        result = _compare(observed, node.comparison, node.expected)
        return EvaluationTrace(
            node_type="predicate",
            result=TruthValue.TRUE if result else TruthValue.FALSE,
            reason=(
                f"fact {node.fact!r} {node.comparison.value} "
                f"{node.expected!r} evaluated to {result}"
            ),
            fact=node.fact,
            comparison=node.comparison,
            observed=observed,
            expected=node.expected,
        )

    def visit_all_of(self, node: AllOfNode) -> EvaluationTrace:
        children = tuple(self.evaluate(child) for child in node.children)
        result = _kleene_and(child.result for child in children)
        return EvaluationTrace(
            node_type="all_of",
            result=result,
            reason=f"all_of evaluated to {result.value.lower()}",
            children=children,
        )

    def visit_any_of(self, node: AnyOfNode) -> EvaluationTrace:
        children = tuple(self.evaluate(child) for child in node.children)
        result = _kleene_or(child.result for child in children)
        return EvaluationTrace(
            node_type="any_of",
            result=result,
            reason=f"any_of evaluated to {result.value.lower()}",
            children=children,
        )

    def visit_not(self, node: NotNode) -> EvaluationTrace:
        child = self.evaluate(node.child)
        result = {
            TruthValue.TRUE: TruthValue.FALSE,
            TruthValue.FALSE: TruthValue.TRUE,
            TruthValue.UNKNOWN: TruthValue.UNKNOWN,
        }[child.result]
        return EvaluationTrace(
            node_type="not",
            result=result,
            reason=f"not {child.result.value.lower()} evaluated to {result.value.lower()}",
            children=(child,),
        )


def _compare(
    observed: Scalar,
    comparison: Comparison,
    expected: Scalar | tuple[Scalar, ...],
) -> bool:
    if comparison in (Comparison.IN, Comparison.NOT_IN):
        if not isinstance(expected, tuple):
            raise TypeError("Membership predicates require a tuple of expected values")
        matches = any(_equal(observed, value) for value in expected)
        return matches == (comparison is Comparison.IN)
    if isinstance(expected, tuple):
        raise TypeError("Only membership predicates may use tuple expected values")

    if comparison is Comparison.EQ:
        return _equal(observed, expected)
    if comparison is Comparison.NE:
        return not _equal(observed, expected)
    if comparison is Comparison.GT:
        _check_ordered_types(observed, expected)
        return operator.gt(observed, expected)
    if comparison is Comparison.GTE:
        _check_ordered_types(observed, expected)
        return operator.ge(observed, expected)
    if comparison is Comparison.LT:
        _check_ordered_types(observed, expected)
        return operator.lt(observed, expected)
    if comparison is Comparison.LTE:
        _check_ordered_types(observed, expected)
        return operator.le(observed, expected)
    raise ValueError(f"Unsupported comparison operator: {comparison}")


def _equal(left: Scalar, right: Scalar) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def _check_ordered_types(left: Scalar, right: Scalar) -> None:
    if isinstance(left, bool) != isinstance(right, bool):
        raise TypeError("Boolean and numeric facts cannot be ordered against each other")


def _kleene_and(values: Iterable[TruthValue]) -> TruthValue:
    results = tuple(values)
    if TruthValue.FALSE in results:
        return TruthValue.FALSE
    if TruthValue.UNKNOWN in results:
        return TruthValue.UNKNOWN
    return TruthValue.TRUE


def _kleene_or(values: Iterable[TruthValue]) -> TruthValue:
    results = tuple(values)
    if TruthValue.TRUE in results:
        return TruthValue.TRUE
    if TruthValue.UNKNOWN in results:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE

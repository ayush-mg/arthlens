"""Immutable policy-rule expression nodes."""

import math
from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from backend.arthlens.domain.interfaces import RuleNode, RuleVisitor

Scalar: TypeAlias = bool | int | float | str


class TruthValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"


class Comparison(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"


@dataclass(frozen=True)
class ConstantNode(RuleNode):
    value: TruthValue

    def __post_init__(self) -> None:
        if not isinstance(self.value, TruthValue):
            raise TypeError("ConstantNode value must be a TruthValue")

    def accept(self, visitor: RuleVisitor) -> object:
        return visitor.visit_constant(self)


@dataclass(frozen=True)
class PredicateNode(RuleNode):
    fact: str
    comparison: Comparison
    expected: Scalar | tuple[Scalar, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.fact, str):
            raise TypeError("Predicate fact name must be a string")
        if not self.fact.strip():
            raise ValueError("Predicate fact name must not be empty")
        if not isinstance(self.comparison, Comparison):
            raise TypeError("Predicate comparison must be a Comparison")
        if self.comparison in (Comparison.IN, Comparison.NOT_IN):
            if not isinstance(self.expected, tuple):
                raise TypeError("Membership predicates require a tuple of expected values")
        elif isinstance(self.expected, tuple):
            raise TypeError("Only membership predicates may use tuple expected values")
        if isinstance(self.expected, tuple):
            if any(not isinstance(value, (bool, int, float, str)) for value in self.expected):
                raise TypeError("Predicate expected values must be scalar")
            if any(isinstance(value, float) and not math.isfinite(value) for value in self.expected):
                raise ValueError("Predicate expected values must be finite")
        elif not isinstance(self.expected, (bool, int, float, str)):
            raise TypeError("Predicate expected value must be scalar")
        elif isinstance(self.expected, float) and not math.isfinite(self.expected):
            raise ValueError("Predicate expected value must be finite")

    def accept(self, visitor: RuleVisitor) -> object:
        return visitor.visit_predicate(self)


@dataclass(frozen=True)
class AllOfNode(RuleNode):
    children: tuple[RuleNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.children, tuple):
            raise TypeError("AllOfNode children must be an immutable tuple")
        if not self.children:
            raise ValueError("AllOfNode requires at least one child")
        if any(not isinstance(child, RuleNode) for child in self.children):
            raise TypeError("AllOfNode children must be RuleNode instances")

    def accept(self, visitor: RuleVisitor) -> object:
        return visitor.visit_all_of(self)


@dataclass(frozen=True)
class AnyOfNode(RuleNode):
    children: tuple[RuleNode, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.children, tuple):
            raise TypeError("AnyOfNode children must be an immutable tuple")
        if not self.children:
            raise ValueError("AnyOfNode requires at least one child")
        if any(not isinstance(child, RuleNode) for child in self.children):
            raise TypeError("AnyOfNode children must be RuleNode instances")

    def accept(self, visitor: RuleVisitor) -> object:
        return visitor.visit_any_of(self)


@dataclass(frozen=True)
class NotNode(RuleNode):
    child: RuleNode

    def __post_init__(self) -> None:
        if not isinstance(self.child, RuleNode):
            raise TypeError("NotNode child must be a RuleNode")

    def accept(self, visitor: RuleVisitor) -> object:
        return visitor.visit_not(self)

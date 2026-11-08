"""Strict JSON serialization for persisted policy expression trees."""

from __future__ import annotations

import math
from typing import Any

from backend.arthlens.policy.rules import (
    AllOfNode,
    AnyOfNode,
    Comparison,
    ConstantNode,
    NotNode,
    PredicateNode,
    RuleNode,
    TruthValue,
)


def parse_rule_ast(value: Any) -> RuleNode:
    """Parse a deliberately small JSON AST, rejecting unknown or malformed shapes."""
    if not isinstance(value, dict) or not isinstance(value.get("type"), str):
        raise ValueError("Each rule AST node must be an object with a type.")
    node_type = value["type"]
    if node_type == "constant":
        _require_keys(value, {"type", "value"})
        try:
            truth = TruthValue(value["value"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Constant value must be TRUE, FALSE, or UNKNOWN.") from exc
        return ConstantNode(truth)
    if node_type == "predicate":
        _require_keys(value, {"type", "fact", "comparison", "expected"})
        if not isinstance(value["fact"], str) or not value["fact"].strip():
            raise ValueError("Predicate fact must be a non-empty string.")
        try:
            comparison = Comparison(value["comparison"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Predicate comparison is unsupported.") from exc
        expected = value["expected"]
        if comparison in (Comparison.IN, Comparison.NOT_IN):
            if not isinstance(expected, list) or not expected:
                raise ValueError("Membership predicates require a non-empty expected list.")
            expected = tuple(_validate_scalar(item) for item in expected)
        else:
            expected = _validate_scalar(expected)
        return PredicateNode(value["fact"], comparison, expected)
    if node_type in ("all_of", "any_of"):
        _require_keys(value, {"type", "children"})
        children = value["children"]
        if not isinstance(children, list) or not children:
            raise ValueError(f"{node_type} requires a non-empty children list.")
        parsed = tuple(parse_rule_ast(child) for child in children)
        return AllOfNode(parsed) if node_type == "all_of" else AnyOfNode(parsed)
    if node_type == "not":
        _require_keys(value, {"type", "child"})
        return NotNode(parse_rule_ast(value["child"]))
    raise ValueError(f"Unsupported rule AST node type: {node_type!r}.")


def serialize_rule_ast(node: RuleNode) -> dict[str, Any]:
    if isinstance(node, ConstantNode):
        return {"type": "constant", "value": node.value.value}
    if isinstance(node, PredicateNode):
        expected = list(node.expected) if isinstance(node.expected, tuple) else node.expected
        return {
            "type": "predicate",
            "fact": node.fact,
            "comparison": node.comparison.value,
            "expected": expected,
        }
    if isinstance(node, AllOfNode):
        return {"type": "all_of", "children": [serialize_rule_ast(child) for child in node.children]}
    if isinstance(node, AnyOfNode):
        return {"type": "any_of", "children": [serialize_rule_ast(child) for child in node.children]}
    if isinstance(node, NotNode):
        return {"type": "not", "child": serialize_rule_ast(node.child)}
    raise TypeError(f"Unsupported policy rule node: {type(node).__name__}.")


def rule_facts(node: RuleNode) -> frozenset[str]:
    if isinstance(node, PredicateNode):
        return frozenset((node.fact,))
    if isinstance(node, (AllOfNode, AnyOfNode)):
        return frozenset().union(*(rule_facts(child) for child in node.children))
    if isinstance(node, NotNode):
        return rule_facts(node.child)
    if isinstance(node, ConstantNode):
        return frozenset()
    raise TypeError(f"Unsupported policy rule node: {type(node).__name__}.")


def _require_keys(value: dict[str, Any], expected: set[str]) -> None:
    if set(value) != expected:
        raise ValueError(
            f"Invalid AST fields: expected {sorted(expected)}, received {sorted(value)}."
        )


def _validate_scalar(value: Any) -> bool | int | float | str:
    if isinstance(value, bool) or isinstance(value, (int, str)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ValueError("Rule values must be finite JSON scalars (boolean, number, or string).")


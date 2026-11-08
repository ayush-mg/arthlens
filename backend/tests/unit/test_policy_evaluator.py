import pytest
from backend.arthlens.policy.rules import (
    AllOfNode,
    AnyOfNode,
    Comparison,
    ConstantNode,
    NotNode,
    PredicateNode,
    TruthValue,
)
from backend.arthlens.policy.visitors import EligibilityEvaluator


@pytest.mark.unit
@pytest.mark.parametrize(
    ("left", "right", "and_result", "or_result"),
    [
        (TruthValue.TRUE, TruthValue.TRUE, TruthValue.TRUE, TruthValue.TRUE),
        (TruthValue.TRUE, TruthValue.FALSE, TruthValue.FALSE, TruthValue.TRUE),
        (TruthValue.TRUE, TruthValue.UNKNOWN, TruthValue.UNKNOWN, TruthValue.TRUE),
        (TruthValue.FALSE, TruthValue.TRUE, TruthValue.FALSE, TruthValue.TRUE),
        (TruthValue.FALSE, TruthValue.FALSE, TruthValue.FALSE, TruthValue.FALSE),
        (TruthValue.FALSE, TruthValue.UNKNOWN, TruthValue.FALSE, TruthValue.UNKNOWN),
        (TruthValue.UNKNOWN, TruthValue.TRUE, TruthValue.UNKNOWN, TruthValue.TRUE),
        (TruthValue.UNKNOWN, TruthValue.FALSE, TruthValue.FALSE, TruthValue.UNKNOWN),
        (TruthValue.UNKNOWN, TruthValue.UNKNOWN, TruthValue.UNKNOWN, TruthValue.UNKNOWN),
    ],
)
def test_kleene_and_or_truth_tables(left, right, and_result, or_result):
    evaluator = EligibilityEvaluator({})
    left_node = ConstantNode(left)
    right_node = ConstantNode(right)

    assert evaluator.evaluate(AllOfNode((left_node, right_node))).result is and_result
    assert evaluator.evaluate(AnyOfNode((left_node, right_node))).result is or_result


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (TruthValue.TRUE, TruthValue.FALSE),
        (TruthValue.FALSE, TruthValue.TRUE),
        (TruthValue.UNKNOWN, TruthValue.UNKNOWN),
    ],
)
def test_kleene_not_truth_table(value, expected):
    result = EligibilityEvaluator({}).evaluate(NotNode(ConstantNode(value)))

    assert result.result is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("comparison", "observed", "expected", "result"),
    [
        (Comparison.EQ, 5, 5, TruthValue.TRUE),
        (Comparison.NE, 5, 4, TruthValue.TRUE),
        (Comparison.GT, 5, 4, TruthValue.TRUE),
        (Comparison.GTE, 5, 5, TruthValue.TRUE),
        (Comparison.LT, 4, 5, TruthValue.TRUE),
        (Comparison.LTE, 5, 5, TruthValue.TRUE),
        (Comparison.IN, "a", ("a", "b"), TruthValue.TRUE),
        (Comparison.NOT_IN, "c", ("a", "b"), TruthValue.TRUE),
    ],
)
def test_predicate_comparisons(comparison, observed, expected, result):
    node = PredicateNode("value", comparison, expected)

    assert EligibilityEvaluator({"value": observed}).evaluate(node).result is result


@pytest.mark.unit
@pytest.mark.parametrize("facts", [{}, {"value": None}])
def test_missing_or_null_fact_is_unknown_with_trace(facts):
    trace = EligibilityEvaluator(facts).evaluate(
        PredicateNode("value", Comparison.GTE, 18)
    )

    assert trace.result is TruthValue.UNKNOWN
    assert trace.fact == "value"
    assert trace.expected == 18
    assert trace.observed is None
    assert "missing" in trace.reason


@pytest.mark.unit
def test_nested_rule_trace_preserves_all_child_results():
    rule = AllOfNode(
        (
            PredicateNode("age", Comparison.GTE, 18),
            AnyOfNode(
                (
                    PredicateNode("resident", Comparison.EQ, True),
                    PredicateNode("income", Comparison.LT, 0),
                )
            ),
        )
    )

    trace = EligibilityEvaluator({"age": 20, "resident": False, "income": 10}).evaluate(
        rule
    )

    assert trace.result is TruthValue.FALSE
    assert len(trace.children) == 2
    assert trace.children[0].result is TruthValue.TRUE
    assert trace.children[1].result is TruthValue.FALSE
    assert tuple(child.result for child in trace.children[1].children) == (
        TruthValue.FALSE,
        TruthValue.FALSE,
    )


@pytest.mark.unit
def test_invalid_ordered_comparison_surfaces_type_error():
    node = PredicateNode("age", Comparison.GTE, "adult")

    with pytest.raises(TypeError):
        EligibilityEvaluator({"age": 20}).evaluate(node)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("comparison", "expected_result"),
    [
        (Comparison.EQ, TruthValue.FALSE),
        (Comparison.NE, TruthValue.TRUE),
        (Comparison.IN, TruthValue.FALSE),
        (Comparison.NOT_IN, TruthValue.TRUE),
    ],
)
def test_boolean_facts_do_not_compare_equal_to_integers(comparison, expected_result):
    expected = (1,) if comparison in (Comparison.IN, Comparison.NOT_IN) else 1

    result = EligibilityEvaluator({"flag": True}).evaluate(
        PredicateNode("flag", comparison, expected)
    )

    assert result.result is expected_result


@pytest.mark.unit
def test_non_finite_predicate_expected_value_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        PredicateNode("value", Comparison.GT, float("inf"))


@pytest.mark.unit
@pytest.mark.parametrize(
    "children",
    [(), []],
)
def test_composite_nodes_reject_empty_or_mutable_children(children):
    with pytest.raises((TypeError, ValueError)):
        AllOfNode(children)


@pytest.mark.unit
def test_composite_nodes_accept_nonempty_immutable_children():
    child = ConstantNode(TruthValue.TRUE)

    assert AllOfNode((child,)).children == (child,)


@pytest.mark.unit
def test_non_finite_fact_is_rejected():
    with pytest.raises(ValueError, match="finite"):
        EligibilityEvaluator({"income": float("nan")})

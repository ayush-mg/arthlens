from datetime import date

import pytest
from backend.arthlens.infra.in_memory import InMemoryPolicyRuleRepository
from backend.arthlens.policy.rules import TruthValue
from backend.arthlens.policy.serialization import parse_rule_ast, rule_facts, serialize_rule_ast
from backend.arthlens.policy.visitors import EligibilityEvaluator


def test_policy_ast_round_trip_and_fact_extraction():
    payload = {
        "type": "all_of",
        "children": [
            {"type": "predicate", "fact": "project_cost", "comparison": "lte", "expected": 500000},
            {"type": "not", "child": {"type": "constant", "value": "FALSE"}},
        ],
    }

    node = parse_rule_ast(payload)

    assert serialize_rule_ast(node) == payload
    assert rule_facts(node) == frozenset({"project_cost"})
    assert EligibilityEvaluator({"project_cost": 400000}).evaluate(node).result is TruthValue.TRUE


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "predicate", "fact": "x", "comparison": "gte", "expected": float("inf")},
        {"type": "constant", "value": "TRUE", "status": "APPROVED"},
        {"type": "all_of", "children": []},
        {"type": "unknown"},
    ],
)
def test_policy_ast_parser_rejects_untrusted_shapes(payload):
    with pytest.raises((TypeError, ValueError)):
        parse_rule_ast(payload)


def _draft(repo: InMemoryPolicyRuleRepository, *, version: str = "v1", starts: date = date(2026, 1, 1)):
    document_id = repo.save_document({
        "scheme_id": "fixture-scheme",
        "source_version_id": "fixture-source:sha256",
        "document_url": "https://example.invalid/policy.pdf",
        "sha256": "a" * 64,
    })
    citation = {
        "document_id": document_id,
        "source_version_id": "fixture-source:sha256",
        "document_url": "https://example.invalid/policy.pdf",
        "sha256": "a" * 64,
        "locator": "page 3, section 2",
    }
    rule_id = repo.save_rule({
        "scheme_id": "fixture-scheme",
        "rule_key": "test-eligibility",
        "version": version,
        "rule_ast": {
            "type": "predicate",
            "fact": "project_cost",
            "comparison": "lte",
            "expected": 500000,
        },
        "evidence_requirements": {
            "project_cost": {
                "definition_key": "finance.project_cost",
                "unit": "INR",
                "allowed_kinds": ["USER_ASSUMED"],
                "minimum_evidence_floor": 3,
            }
        },
        "source_references": [citation],
        "effective_from": starts,
        "effective_to": date(2026, 12, 31),
    })
    return document_id, rule_id, citation


def test_policy_rule_requires_steward_review_and_is_effective_dated():
    repo = InMemoryPolicyRuleRepository()
    document_id, rule_id, _ = _draft(repo)

    with pytest.raises(ValueError, match="steward-verified"):
        repo.approve_rule(rule_id, steward_id="steward", approval_note="reviewed")

    repo.review_document(document_id, reviewer_id="steward", verified=True, review_note="Source snapshot reviewed by a steward.")
    approved = repo.approve_rule(rule_id, steward_id="steward", approval_note="Rule checked against the cited source text.")

    assert approved["status"] == "APPROVED"
    assert len(repo.get_applicable_rules("fixture-scheme", "test-eligibility", date(2026, 6, 1))) == 1
    assert repo.get_applicable_rules("fixture-scheme", "test-eligibility", date(2027, 1, 1)) == []

    overlapping_document, overlapping_rule, _ = _draft(repo, version="v2", starts=date(2026, 6, 1))
    repo.review_document(overlapping_document, reviewer_id="steward", verified=True, review_note="Second source snapshot reviewed.")
    with pytest.raises(ValueError, match="overlaps"):
        repo.approve_rule(overlapping_rule, steward_id="steward", approval_note="Overlapping dates should be rejected.")


def test_policy_rule_rejects_mismatched_source_version_reference():
    repo = InMemoryPolicyRuleRepository()
    document_id, rule_id, _ = _draft(repo)
    repo.review_document(document_id, reviewer_id="steward", verified=True, review_note="Source snapshot reviewed by a steward.")
    # Mutate the stored test fixture to model a database record with a forged citation.
    repo._rules[rule_id]["source_references"][0]["source_version_id"] = "unrelated-source-id"
    with pytest.raises(ValueError, match="exact source version"):
        repo.approve_rule(rule_id, steward_id="steward", approval_note="Citation linkage must match the reviewed snapshot.")


def test_retired_policy_rule_is_no_longer_applicable():
    repo = InMemoryPolicyRuleRepository()
    document_id, rule_id, _ = _draft(repo)
    repo.review_document(document_id, reviewer_id="steward", verified=True, review_note="Source snapshot reviewed by a steward.")
    repo.approve_rule(rule_id, steward_id="steward", approval_note="Rule checked against the cited source text.")

    retired = repo.retire_rule(rule_id, steward_id="steward", retirement_reason="The source has been superseded by a newer circular.")

    assert retired["status"] == "RETIRED"
    assert repo.get_applicable_rules("fixture-scheme", "test-eligibility", date(2026, 6, 1)) == []

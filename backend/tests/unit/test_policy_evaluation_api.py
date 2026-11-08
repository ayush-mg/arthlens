import uuid
from datetime import date

from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.in_memory import (
    InMemoryPolicyRuleRepository,
    InMemoryQuantityRepository,
)
from backend.arthlens.security.rbac import AuthenticatedUser, get_current_user
from fastapi.testclient import TestClient


def test_policy_evaluation_fails_closed_for_missing_unrelated_and_mismatched_evidence(monkeypatch):
    from backend.arthlens.api import policy

    owner_id = str(uuid.uuid4())
    user = AuthenticatedUser(owner_id, "owner@example.test", ("ENTREPRENEUR",), "test-jti")
    policy_repo = InMemoryPolicyRuleRepository()
    quantity_repo = InMemoryQuantityRepository()
    document_id = policy_repo.save_document({
        "scheme_id": "fixture-scheme",
        "source_version_id": "fixture-source:sha256",
        "document_url": "https://example.invalid/terms.pdf",
        "sha256": "b" * 64,
    })
    citation = {
        "document_id": document_id,
        "source_version_id": "fixture-source:sha256",
        "document_url": "https://example.invalid/terms.pdf",
        "sha256": "b" * 64,
        "locator": "page 4, clause 3",
    }
    policy_repo.review_document(
        document_id,
        reviewer_id=owner_id,
        verified=True,
        review_note="Test fixture represents a steward-reviewed source snapshot.",
    )
    rule_id = policy_repo.save_rule({
        "scheme_id": "fixture-scheme",
        "rule_key": "cost-cap",
        "version": "fixture-v1",
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
        "effective_from": date(2026, 1, 1),
        "effective_to": None,
    })
    policy_repo.approve_rule(
        rule_id,
        steward_id=owner_id,
        approval_note="Test fixture represents a steward-approved rule version.",
    )
    valid_quantity_id = str(uuid.uuid4())
    quantity_repo.save(Quantity(
        id=valid_quantity_id,
        definition_key="finance.project_cost",
        value=400000,
        unit="INR",
        kind=Kind.USER_ASSUMED,
        evidence_floor=3,
        geo_unit_id="test:district",
        resolution=2,
        as_of="2026-05-01",
        source_refs=((f"user:{owner_id}", "test/input:project_cost", "2026-05-01"),),
        owner_id=owner_id,
    ))
    mismatched_id = str(uuid.uuid4())
    quantity_repo.save(Quantity(
        id=mismatched_id,
        definition_key="finance.other_amount",
        value=400000,
        unit="INR",
        kind=Kind.USER_ASSUMED,
        evidence_floor=3,
        geo_unit_id="test:district",
        resolution=2,
        as_of="2026-05-01",
        source_refs=((f"user:{owner_id}", "test/input:other_amount", "2026-05-01"),),
        owner_id=owner_id,
    ))
    monkeypatch.setattr(policy, "PostgresPolicyRuleRepository", lambda: policy_repo)
    monkeypatch.setattr(policy, "PostgresQuantityRepository", lambda: quantity_repo)
    monkeypatch.setattr(policy, "PostgresSourceRepository", lambda: object())

    class AuditRecorder:
        def record_event(self, *args, **kwargs):
            return 1

    monkeypatch.setattr(policy, "get_audit_service", lambda: AuditRecorder())
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    endpoint = "/policy/schemes/fixture-scheme/evaluate"
    base = {"rule_key": "cost-cap", "as_of": "2026-06-01"}

    missing = client.post(endpoint, json={**base, "fact_quantity_ids": {}})
    assert missing.status_code == 200
    assert missing.json()["status"] == "INSUFFICIENT_DATA"
    assert missing.json()["outcome"] == "UNKNOWN"

    unknown = client.post(endpoint, json={
        **base,
        "fact_quantity_ids": {"project_cost": str(uuid.uuid4())},
    })
    assert unknown.json()["status"] == "INSUFFICIENT_DATA"
    assert unknown.json()["outcome"] == "UNKNOWN"

    unrelated = client.post(endpoint, json={
        **base,
        "fact_quantity_ids": {"unrelated_fact": valid_quantity_id},
    })
    assert unrelated.json()["status"] == "INSUFFICIENT_DATA"
    assert unrelated.json()["outcome"] == "UNKNOWN"

    mismatched = client.post(endpoint, json={
        **base,
        "fact_quantity_ids": {"project_cost": mismatched_id},
    })
    assert mismatched.json()["status"] == "INSUFFICIENT_DATA"
    assert mismatched.json()["outcome"] == "UNKNOWN"

    valid = client.post(endpoint, json={
        **base,
        "fact_quantity_ids": {"project_cost": valid_quantity_id},
    })
    assert valid.status_code == 200
    assert valid.json()["status"] == "SCENARIO_ONLY"
    assert valid.json()["outcome"] == "TRUE"
    assert valid.json()["official_award_decision"] is False
    assert valid.json()["trace"]["facts"]["project_cost"]["quantity_id"] == valid_quantity_id

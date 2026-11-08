import uuid
from datetime import date

from backend.arthlens.api import policy
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.in_memory import InMemoryPolicyRuleRepository
from backend.arthlens.security.rbac import AuthenticatedUser


class _QuantityRepository:
    def __init__(self, quantity: Quantity):
        self.quantity = quantity

    def get(self, quantity_id):
        return self.quantity if str(quantity_id) == self.quantity.id else None


class _SourceRepository:
    def __init__(self, registered: bool):
        self.registered = registered

    def get_version(self, version_id):
        if not self.registered or version_id != "source-v1":
            return None
        return {
            "id": "source-v1",
            "source_id": "official-source",
            "source_url": "https://example.invalid/circular.pdf",
            "content_hash": "c" * 64,
            "status": "ACTIVE",
        }

    def get_source(self, source_id):
        return {"id": source_id, "status": "ACTIVE"} if self.registered else None


def test_source_backed_fact_requires_registered_exact_source_version(monkeypatch):
    owner_id = str(uuid.uuid4())
    user = AuthenticatedUser(owner_id, "owner@example.test", ("ENTREPRENEUR",), "jti")
    quantity_id = str(uuid.uuid4())
    policy_repo = InMemoryPolicyRuleRepository()
    document_id = policy_repo.save_document({
        "scheme_id": "fixture-scheme",
        "source_version_id": "source-v1",
        "document_url": "https://example.invalid/circular.pdf",
        "sha256": "c" * 64,
    })
    policy_repo.review_document(
        document_id,
        reviewer_id=owner_id,
        verified=True,
        review_note="Test fixture represents exact steward-reviewed source material.",
    )
    rule_id = policy_repo.save_rule({
        "scheme_id": "fixture-scheme",
        "rule_key": "source-backed-cap",
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
                "allowed_kinds": ["OBSERVED"],
                "minimum_evidence_floor": 4,
            }
        },
        "source_references": [{
            "document_id": document_id,
            "source_version_id": "source-v1",
            "document_url": "https://example.invalid/circular.pdf",
            "sha256": "c" * 64,
            "locator": "page 1, section 1",
        }],
        "effective_from": date(2026, 1, 1),
        "effective_to": None,
    })
    policy_repo.approve_rule(
        rule_id,
        steward_id=owner_id,
        approval_note="Test fixture records steward approval against the exact source snapshot.",
    )
    quantity = Quantity(
        id=quantity_id,
        definition_key="finance.project_cost",
        value=400000,
        unit="INR",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="test:district",
        resolution=2,
        as_of="2026-05-01",
        source_refs=(("source-v1", "table 1, row 2", "2026-05-01"),),
    )
    monkeypatch.setattr(policy, "PostgresPolicyRuleRepository", lambda: policy_repo)
    monkeypatch.setattr(policy, "PostgresQuantityRepository", lambda: _QuantityRepository(quantity))
    monkeypatch.setattr(policy, "get_audit_service", lambda: type("Audit", (), {"record_event": lambda *_a, **_k: 1})())

    monkeypatch.setattr(policy, "PostgresSourceRepository", lambda: _SourceRepository(registered=False))
    rejected = policy.evaluate_scheme_eligibility(
        "fixture-scheme",
        policy.PolicyEvaluationRequest(
            rule_key="source-backed-cap",
            as_of=date(2026, 6, 1),
            fact_quantity_ids={"project_cost": uuid.UUID(quantity_id)},
        ),
        user,
    )
    assert rejected["status"] == "INSUFFICIENT_DATA"
    assert rejected["outcome"] == "UNKNOWN"

    monkeypatch.setattr(policy, "PostgresSourceRepository", lambda: _SourceRepository(registered=True))
    assessed = policy.evaluate_scheme_eligibility(
        "fixture-scheme",
        policy.PolicyEvaluationRequest(
            rule_key="source-backed-cap",
            as_of=date(2026, 6, 1),
            fact_quantity_ids={"project_cost": uuid.UUID(quantity_id)},
        ),
        user,
    )
    assert assessed["status"] == "ASSESSED"
    assert assessed["outcome"] == "TRUE"
    assert assessed["trace"]["facts"]["project_cost"]["source_refs"][0][0] == "source-v1"

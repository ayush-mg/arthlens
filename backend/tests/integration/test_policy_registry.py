"""Database-backed source review, policy versioning, and eligibility trace checks."""

import uuid
from datetime import date

from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.database import get_engine
from backend.arthlens.infra.repositories import (
    PostgresQuantityRepository,
    PostgresSourceRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.rbac import AuthenticatedUser, get_current_user
from fastapi.testclient import TestClient
from sqlalchemy import text


def test_policy_registry_requires_verified_exact_source_and_persists_trace():
    owner_id = str(uuid.uuid4())
    source_id = f"policy-test-source-{uuid.uuid4()}"
    scheme_id = f"policy-test-scheme-{uuid.uuid4()}"
    source_hash = "e" * 64
    source_url = f"https://example.invalid/{source_id}.pdf"
    quantity_id = str(uuid.uuid4())
    today = date.today()
    user = AuthenticatedUser(owner_id, "policy-steward@example.test", ("STEWARD",), "policy-test-jti")

    PostgresUserRepository().save({
        "id": owner_id,
        "email": f"policy-steward-{owner_id}@example.test",
        "password_hash": "test-hash",
        "roles": ["STEWARD"],
        "quota_counters": {},
    })
    sources = PostgresSourceRepository()
    sources.save_source({"id": source_id, "name": "Policy fixture snapshot", "status": "ACTIVE"})
    source_version_id = sources.save_version({
        "source_id": source_id,
        "version": "fixture-v1",
        "source_url": source_url,
        "content_hash": source_hash,
        "retrieval_date": today.isoformat(),
        "status": "ACTIVE",
    })
    quantity = Quantity(
        id=quantity_id,
        definition_key="finance.project_cost",
        value=400000,
        unit="INR",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="test:district",
        resolution=2,
        as_of=today.isoformat(),
        source_refs=((source_version_id, "table 1, row 2", today.isoformat()),),
    )
    PostgresQuantityRepository().save(quantity)

    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: user
    client = TestClient(app)
    document_id = None
    try:
        registered = client.post("/policy/documents", json={
            "scheme_id": scheme_id,
            "source_version_id": source_version_id,
        })
        assert registered.status_code == 201
        document = registered.json()
        document_id = document["id"]
        assert document["status"] == "PENDING_REVIEW"
        assert document["document_url"] == source_url
        assert document["sha256"] == source_hash

        draft = client.post("/policy/rules", json={
            "scheme_id": scheme_id,
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
                    "allowed_kinds": ["OBSERVED"],
                    "minimum_evidence_floor": 4,
                }
            },
            "source_references": [{"document_id": document_id, "locator": "table 1, row 2"}],
            "effective_from": today.isoformat(),
        })
        assert draft.status_code == 201
        rule_id = draft.json()["id"]
        assert draft.json()["status"] == "DRAFT"

        premature = client.post(f"/policy/rules/{rule_id}/approve", json={
            "approval_note": "This rule still lacks the required source document review.",
        })
        assert premature.status_code == 409

        reviewed = client.post(f"/policy/documents/{document_id}/review", json={
            "verified": True,
            "review_note": "Source snapshot checked; version and document content match the record.",
        })
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "VERIFIED"

        approved = client.post(f"/policy/rules/{rule_id}/approve", json={
            "approval_note": "Predicate and locator checked against the steward-reviewed source snapshot.",
        })
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"
        assert approved.json()["approved_at"]
        assert approved.json()["source_references"][0]["source_version_id"] == source_version_id

        evaluated = client.post(f"/policy/schemes/{scheme_id}/evaluate", json={
            "rule_key": "cost-cap",
            "as_of": today.isoformat(),
            "fact_quantity_ids": {"project_cost": quantity_id},
        })
        assert evaluated.status_code == 200
        result = evaluated.json()
        assert result["outcome"] == "TRUE"
        assert result["status"] == "ASSESSED"
        assert result["official_award_decision"] is False
        assert result["trace"]["facts"]["project_cost"]["quantity_id"] == quantity_id
        assert result["trace"]["source_references"][0]["sha256"] == source_hash

        stored = client.get(f"/policy/evaluations/{result['id']}")
        assert stored.status_code == 200
        assert stored.json()["trace"] == result["trace"]

        retired = client.post(f"/policy/rules/{rule_id}/retire", json={
            "retirement_reason": "The policy source has been superseded and requires a new reviewed rule version.",
        })
        assert retired.status_code == 200
        unavailable = client.post(f"/policy/schemes/{scheme_id}/evaluate", json={
            "rule_key": "cost-cap",
            "as_of": today.isoformat(),
            "fact_quantity_ids": {"project_cost": quantity_id},
        })
        assert unavailable.json()["status"] == "RULE_UNAVAILABLE"
        assert unavailable.json()["outcome"] == "UNKNOWN"
    finally:
        app.dependency_overrides.clear()
        with get_engine().begin() as connection:
            connection.execute(text("DELETE FROM policy_evaluations WHERE owner_id = :owner_id"), {"owner_id": owner_id})
            connection.execute(text("DELETE FROM policy_rules WHERE scheme_id = :scheme_id"), {"scheme_id": scheme_id})
            connection.execute(text("DELETE FROM policy_documents WHERE scheme_id = :scheme_id"), {"scheme_id": scheme_id})
            connection.execute(text("DELETE FROM quantities WHERE id = :quantity_id"), {"quantity_id": quantity_id})
            connection.execute(text("DELETE FROM source_versions WHERE id = :source_version_id"), {"source_version_id": source_version_id})
            connection.execute(text("DELETE FROM sources WHERE id = :source_id"), {"source_id": source_id})
            connection.execute(text("DELETE FROM user_roles WHERE user_id = :owner_id"), {"owner_id": owner_id})
            connection.execute(text("DELETE FROM users WHERE id = :owner_id"), {"owner_id": owner_id})

"""
Integration tests for FIX 1: Exact Source-Version Resolution.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.1, 4.2, Part 10.1, 10.2).
Phase: Phase 2 Final Integration.

Verifies:
1. Resolve exact referenced source_version_id, never substitute a newer version.
2. Older Quantity resolves to its original version when multiple versions exist.
3. Missing exact provenance is reported as incomplete (provenance_complete=False).
4. Evidence graph renders exact source nodes.
"""

import uuid
from datetime import date

import pytest
from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import SourceModel, SourceVersionModel
from backend.arthlens.infra.repositories import (
    PostgresQuantityRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    return TestClient(create_app())


@pytest.fixture
def auth_cookie():
    repo = PostgresUserRepository()
    user_id = str(uuid.uuid4())
    email = f"user_{user_id[:8]}@arthlens.org"
    repo.save(
        {
            "id": user_id,
            "email": email,
            "password_hash": "dummy_hash",
            "roles": [Role.ENTREPRENEUR.value],
            "quota_counters": {"runs_today": 0},
        }
    )
    token, _ = create_access_token(user_id=user_id, email=email, roles=[Role.ENTREPRENEUR.value])
    return {get_auth_cookie_name(): token}


@pytest.mark.integration
def test_exact_source_version_resolution_older_version_preserved(api_client, auth_cookie):
    """
    Test FIX 1: When two versions of the same source exist, an older Quantity
    must ALWAYS resolve to its original version, never the latest version.
    """
    session_factory = get_session_factory()
    test_src_id = f"SRC_TEST_{uuid.uuid4().hex[:6]}"
    v1_id = f"{test_src_id}:v1"
    v2_id = f"{test_src_id}:v2"

    with session_factory() as session:
        # Create source
        src = SourceModel(
            id=test_src_id,
            name="Official Test Register",
            description="Testing exact source version resolution",
            licence_text="GODL-India",
            max_age_days=365,
            status="ACTIVE",
        )
        session.add(src)

        # Version 1 (older)
        v1 = SourceVersionModel(
            id=v1_id,
            source_id=test_src_id,
            version="2020.1",
            retrieval_date=date(2020, 1, 15),
            content_hash="1111111111111111111111111111111111111111111111111111111111111111",
            status="ACTIVE",
        )
        session.add(v1)

        # Version 2 (newer)
        v2 = SourceVersionModel(
            id=v2_id,
            source_id=test_src_id,
            version="2024.1",
            retrieval_date=date(2024, 6, 1),
            content_hash="2222222222222222222222222222222222222222222222222222222222222222",
            status="ACTIVE",
        )
        session.add(v2)
        session.commit()

    # Seed Quantity referencing v1 specifically
    q_repo = PostgresQuantityRepository()
    q_old_id = str(uuid.uuid4())
    q_old = Quantity(
        id=q_old_id,
        definition_key="population.total",
        value=500000.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2020-01-01",
        source_refs=((v1_id, "table_1.csv:row_42", "2020-01-15"),),
        quality_flags=frozenset(),
    )
    q_repo.save(q_old)

    # Seed Quantity referencing v2
    q_new_id = str(uuid.uuid4())
    q_new = Quantity(
        id=q_new_id,
        definition_key="population.total",
        value=550000.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2024-05-01",
        source_refs=((v2_id, "table_1.csv:row_42", "2024-06-01"),),
        quality_flags=frozenset(),
    )
    q_repo.save(q_new)

    # Query older quantity ledger detail
    res_old = api_client.get(f"/ledger/{q_old_id}", cookies=auth_cookie)
    assert res_old.status_code == 200
    p_old = res_old.json()

    # Invariant: Must resolve to v1, NOT v2!
    assert p_old["source_version"] == "2020.1"
    assert p_old["source_version_id"] == v1_id
    assert p_old["source_id"] == test_src_id
    assert p_old["source_provenance"][0]["provenance_complete"] is True
    assert (
        p_old["source_checksum"]
        == "1111111111111111111111111111111111111111111111111111111111111111"
    )
    assert p_old["provenance_complete"] is True
    graph_response = api_client.get(f"/ledger/{q_old_id}/graph", cookies=auth_cookie)
    assert graph_response.status_code == 200
    source_nodes = [
        node["data"]
        for node in graph_response.json()["elements"]["nodes"]
        if node["data"].get("type") == "source"
    ]
    assert len(source_nodes) == 1
    assert source_nodes[0]["id"] == f"src:{v1_id}"
    assert source_nodes[0]["provenance_complete"] is True
    assert "Official Test Register" in source_nodes[0]["label"]

    # Query newer quantity ledger detail
    res_new = api_client.get(f"/ledger/{q_new_id}", cookies=auth_cookie)
    assert res_new.status_code == 200
    p_new = res_new.json()

    # Invariant: Resolves to v2
    assert p_new["source_version"] == "2024.1"
    assert p_new["source_version_id"] == v2_id
    assert p_new["source_id"] == test_src_id
    assert p_new["source_provenance"][0]["retrieval_date"] == "2024-06-01"
    assert (
        p_new["source_checksum"]
        == "2222222222222222222222222222222222222222222222222222222222222222"
    )
    assert p_new["provenance_complete"] is True

    # A bare source ID cannot be upgraded to the newest registered version.
    q_ambiguous_id = str(uuid.uuid4())
    q_repo.save(
        Quantity(
            id=q_ambiguous_id,
            definition_key="population.total",
            value=525000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2024-05-01",
            source_refs=((test_src_id, "table_1.csv:row_43", "2024-06-01"),),
            quality_flags=frozenset(),
        )
    )
    ambiguous = api_client.get(f"/ledger/{q_ambiguous_id}", cookies=auth_cookie).json()
    assert ambiguous["provenance_complete"] is False
    assert ambiguous["source_version_id"] is None


@pytest.mark.integration
def test_missing_exact_provenance_reported_as_incomplete(api_client, auth_cookie):
    """
    Test FIX 1: When a Quantity references an unverified or missing source version ID,
    it must be reported with provenance_complete=False rather than silently inventing provenance.
    """
    q_repo = PostgresQuantityRepository()
    q_unverified_id = str(uuid.uuid4())
    fake_version_id = f"UNVERIFIED_SRC_{uuid.uuid4().hex[:6]}:v99"

    q_unverified = Quantity(
        id=q_unverified_id,
        definition_key="population.total",
        value=300000.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2022-01-01",
        source_refs=((fake_version_id, "doc:page_1", "2022-01-01"),),
        quality_flags=frozenset(),
    )
    q_repo.save(q_unverified)

    res = api_client.get(f"/ledger/{q_unverified_id}", cookies=auth_cookie)
    assert res.status_code == 200
    p = res.json()
    assert p["provenance_complete"] is False
    assert p["source_checksum"] is None
    assert p["source_version"] is None


@pytest.mark.integration
def test_retrieval_date_mismatch_does_not_complete_source_provenance(api_client, auth_cookie):
    session_factory = get_session_factory()
    source_id = f"SRC_TEST_{uuid.uuid4().hex[:8]}"
    version_id = f"{source_id}:v1"
    with session_factory() as session:
        session.add(
            SourceModel(
                id=source_id,
                name="Test Register",
                description="Retrieval date provenance test",
                licence_text="GODL-India",
                max_age_days=365,
                status="ACTIVE",
            )
        )
        session.add(
            SourceVersionModel(
                id=version_id,
                source_id=source_id,
                version="2020.1",
                retrieval_date=date(2020, 1, 15),
                content_hash="a" * 64,
                status="ACTIVE",
            )
        )
        session.commit()

    quantity_id = str(uuid.uuid4())
    PostgresQuantityRepository().save(
        Quantity(
            id=quantity_id,
            definition_key="population.total",
            value=123.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2020-01-01",
            source_refs=((version_id, "table:row:1", "2020-01-16"),),
        )
    )

    result = api_client.get(f"/ledger/{quantity_id}", cookies=auth_cookie)

    assert result.status_code == 200
    payload = result.json()
    assert payload["provenance_complete"] is False
    assert payload["source_id"] is None
    assert payload["source_provenance"][0]["source_version_id"] == version_id
    assert payload["source_provenance"][0]["provenance_complete"] is False
    assert payload["quality"]["primary_status"] == "INCOMPLETE"

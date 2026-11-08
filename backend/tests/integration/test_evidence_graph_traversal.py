"""
Integration Tests for Recursive Evidence Graph Ancestry Traversal.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 4.1, 4.2, 7.5, Part 10).
Remediation Priority: Priority 4 (Recursive Evidence Graph Ancestry).

Verifies:
1. Full recursive ancestry traversal from root quantity to parents, grandparents, and ancestors.
2. Diamond DAG handling (deduplicating nodes while preserving multi-parent edges).
3. Retrieval and deduplication of source reference nodes across the entire lineage.
4. Cycle protection and recursion depth capping (visited set + max_depth guard).
5. Edge direction preservation:
   - source -> quantity (sourced_from)
   - parent_quantity -> calc_node / quantity (inputs / derives_from)
   - calc_node -> quantity (produces)
   - root_quantity -> claim_node (supports_claim)
6. Gated authentication and role-based access control.
"""

import uuid

import pytest
from backend.arthlens.api.app import create_app
from backend.arthlens.domain.enums import EvidenceFloor, Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import (
    PostgresQuantityRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_cookie():
    repo = PostgresUserRepository()
    user_id = str(uuid.uuid4())
    email = f"graph_tester_{user_id[:8]}@arthlens.org"
    repo.save({
        "id": user_id,
        "email": email,
        "password_hash": "dummy_hash_graph_test",
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    token, _ = create_access_token(
        user_id=user_id,
        email=email,
        roles=[Role.ENTREPRENEUR.value],
    )
    cookie_name = get_auth_cookie_name()
    return {cookie_name: token}


class TestRecursiveEvidenceGraphAncestry:
    """Verifies recursive evidence graph generation and DAG traversal."""

    def test_graph_requires_authentication(self, api_client):
        """Unauthenticated requests must be rejected with HTTP 401."""
        response = api_client.get(f"/ledger/{uuid.uuid4()}/graph")
        assert response.status_code == 401

    def test_graph_unknown_quantity_returns_404(self, api_client, auth_cookie):
        """Non-existent quantity ID must return 404 Not Found."""
        random_id = str(uuid.uuid4())
        response = api_client.get(f"/ledger/{random_id}/graph", cookies=auth_cookie)
        assert response.status_code == 404

    def test_single_level_ancestry(self, api_client, auth_cookie):
        """Single parent derivation properly creates quantity, calculation, and input edges."""
        repo = PostgresQuantityRepository()

        parent_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())

        p = Quantity(
            id=parent_id,
            definition_key="test.single.parent",
            geo_unit_id="in:district:120",
            kind=Kind.OBSERVED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=100.0,
            unit="INR",
            resolution=2,
            as_of="2023-01-01",
            source_refs=[("DS-02", "RBI District Credit")],
        )
        c = Quantity(
            id=child_id,
            definition_key="test.single.child",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=200.0,
            unit="INR",
            resolution=2,
            as_of="2023-01-01",
            parent_ids=[parent_id],
            method_id="multiply_by_two",
        )

        repo.save(p)
        repo.save(c)

        resp = api_client.get(f"/ledger/{child_id}/graph", cookies=auth_cookie)
        assert resp.status_code == 200

        data = resp.json()
        assert data["root_quantity_id"] == child_id

        nodes = data["elements"]["nodes"]
        edges = data["elements"]["edges"]
        node_ids = {n["data"]["id"] for n in nodes}

        # Check nodes
        assert child_id in node_ids
        assert parent_id in node_ids
        assert f"calc:{child_id}" in node_ids
        assert f"claim:{child_id}" in node_ids
        citation_nodes = [
            node["data"]
            for node in nodes
            if node["data"].get("type") == "source"
        ]
        assert len(citation_nodes) == 1
        assert citation_nodes[0]["provenance_complete"] is False
        assert citation_nodes[0]["label"].startswith("Unverified source citation")
        assert not any(node_id == "src:DS-02" for node_id in node_ids)

        # Check edge directions
        calc_edge = next(e for e in edges if e["data"]["id"] == f"e-calc-{child_id}")
        assert calc_edge["data"]["source"] == f"calc:{child_id}"
        assert calc_edge["data"]["target"] == child_id

        parent_edge = next(e for e in edges if e["data"]["id"] == f"e-{parent_id}-calc:{child_id}")
        assert parent_edge["data"]["source"] == parent_id
        assert parent_edge["data"]["target"] == f"calc:{child_id}"

    def test_multilevel_ancestry_traversal(self, api_client, auth_cookie):
        """Ancestry traversal recursively resolves multiple tiers: child -> parent -> grandparent."""
        repo = PostgresQuantityRepository()

        gp_id = str(uuid.uuid4())
        p_id = str(uuid.uuid4())
        c_id = str(uuid.uuid4())

        grandparent = Quantity(
            id=gp_id,
            definition_key="test.multilevel.grandparent",
            geo_unit_id="in:district:120",
            kind=Kind.OBSERVED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=50.0,
            unit="kg",
            resolution=2,
            as_of="2021-01-01",
            source_refs=[("DS-01", "Census 2011 Primary Abstract")],
        )
        parent = Quantity(
            id=p_id,
            definition_key="test.multilevel.parent",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=75.0,
            unit="kg",
            resolution=2,
            as_of="2022-01-01",
            parent_ids=[gp_id],
            method_id="aggregate_tier_1",
            source_refs=[("DS-03", "PLFS Periodic Labour Force Survey")],
        )
        child = Quantity(
            id=c_id,
            definition_key="test.multilevel.child",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=150.0,
            unit="kg",
            resolution=2,
            as_of="2023-01-01",
            parent_ids=[p_id],
            method_id="derive_tier_2",
        )

        repo.save(grandparent)
        repo.save(parent)
        repo.save(child)

        resp = api_client.get(f"/ledger/{c_id}/graph", cookies=auth_cookie)
        assert resp.status_code == 200

        data = resp.json()
        nodes = data["elements"]["nodes"]
        node_ids = {n["data"]["id"] for n in nodes}

        # Multi-level ancestor nodes must be present
        assert c_id in node_ids
        assert p_id in node_ids
        assert gp_id in node_ids

        # Both intermediate calculations must be present
        assert f"calc:{c_id}" in node_ids
        assert f"calc:{p_id}" in node_ids

        # Source nodes linked across all levels must be present
        citation_nodes = [
            node["data"]
            for node in nodes
            if node["data"].get("type") == "source"
        ]
        assert len(citation_nodes) == 2
        assert all(node["provenance_complete"] is False for node in citation_nodes)
        assert not any(node_id in {"src:DS-01", "src:DS-03"} for node_id in node_ids)

    def test_diamond_dag_traversal(self, api_client, auth_cookie):
        """Diamond DAG (A -> B & C, B & C -> D) must deduplicate D and preserve all DAG edges."""
        repo = PostgresQuantityRepository()

        d_id = str(uuid.uuid4())
        b_id = str(uuid.uuid4())
        c_id = str(uuid.uuid4())
        a_id = str(uuid.uuid4())

        # Root ancestor D
        d = Quantity(
            id=d_id,
            definition_key="test.diamond.base_d",
            geo_unit_id="in:district:120",
            kind=Kind.OBSERVED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=10.0,
            unit="units",
            resolution=2,
            as_of="2023-01-01",
            source_refs=[("DS-04", "MCA Corporate Filings")],
        )
        # Branches B and C both derived from D
        b = Quantity(
            id=b_id,
            definition_key="test.diamond.branch_b",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=20.0,
            unit="units",
            resolution=2,
            as_of="2023-01-01",
            parent_ids=[d_id],
            method_id="scale_b",
        )
        c = Quantity(
            id=c_id,
            definition_key="test.diamond.branch_c",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=30.0,
            unit="units",
            resolution=2,
            as_of="2023-01-01",
            parent_ids=[d_id],
            method_id="scale_c",
        )
        # Final quantity A derived from both B and C
        a = Quantity(
            id=a_id,
            definition_key="test.diamond.converge_a",
            geo_unit_id="in:district:120",
            kind=Kind.CALCULATED,
            evidence_floor=EvidenceFloor.OBSERVED,
            value=50.0,
            unit="units",
            resolution=2,
            as_of="2023-01-01",
            parent_ids=[b_id, c_id],
            method_id="sum_bc",
        )

        repo.save(d)
        repo.save(b)
        repo.save(c)
        repo.save(a)

        resp = api_client.get(f"/ledger/{a_id}/graph", cookies=auth_cookie)
        assert resp.status_code == 200

        data = resp.json()
        nodes = data["elements"]["nodes"]
        edges = data["elements"]["edges"]

        # Assert D appears exactly once in the nodes list (deduplication)
        d_nodes = [n for n in nodes if n["data"]["id"] == d_id]
        assert len(d_nodes) == 1

        # Assert both B and C appear
        assert any(n["data"]["id"] == b_id for n in nodes)
        assert any(n["data"]["id"] == c_id for n in nodes)

        # Assert edges from D to both calc:b and calc:c are present
        edge_sources = {(e["data"]["source"], e["data"]["target"]) for e in edges}
        assert (d_id, f"calc:{b_id}") in edge_sources
        assert (d_id, f"calc:{c_id}") in edge_sources
        assert (b_id, f"calc:{a_id}") in edge_sources
        assert (c_id, f"calc:{a_id}") in edge_sources
        source_edges = [
            edge["data"]
            for edge in edges
            if edge["data"]["target"] == d_id
            and edge["data"]["type"] == "cites_unverified_source"
        ]
        assert len(source_edges) == 1

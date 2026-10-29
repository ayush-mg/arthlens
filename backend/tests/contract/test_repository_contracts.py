"""
Contract Tests for QuantityRepository Implementations.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1, 9.2, Part 12.1).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).

Verifies that InMemoryQuantityRepository and PostgresQuantityRepository satisfy the
identical behavioral contract, including:
- Save and retrieval of Quantity aggregates.
- Round-tripping of all 16 attributes + SimulationMetadata.
- Immutability enforcement (rejection of value or kind mutations).
- Parent lineage and DAG child containment queries.
- Missing record handling.
"""

import uuid
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    ImmutableQuantityError,
    QuantityRepository,
)
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.infra.in_memory import InMemoryQuantityRepository
from backend.arthlens.infra.repositories import PostgresQuantityRepository


@pytest.fixture
def in_memory_repo():
    repo = InMemoryQuantityRepository()
    yield repo
    repo.clear()


@pytest.fixture
def postgres_repo():
    repo = PostgresQuantityRepository()
    # Clean up quantities created during tests
    yield repo
    # Cleanup all quantities in test database
    from backend.arthlens.infra.database import get_engine
    from sqlalchemy import text
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE TABLE quantities CASCADE;"))


@pytest.fixture(params=["in_memory", "postgres"])
def quantity_repo(request, in_memory_repo, postgres_repo):
    """Parametrized fixture providing both implementations to enforce identical contracts."""
    if request.param == "in_memory":
        return in_memory_repo
    elif request.param == "postgres":
        return postgres_repo


def _create_sample_quantity(
    q_id: str,
    def_key: str = "population.total",
    value: float = 125000.0,
    unit: str = "persons",
    kind: Kind = Kind.OBSERVED,
    floor: int = 4,
    geo_id: str = "IND.MH.PU",
    res: int = 2,
    as_of: str = "2026-03-31",
    uncertainty="EXACT",
    source_refs=(("src_census_2011", "Table A-1", "2026-01-15"),),
    parent_ids=(),
    quality_flags=frozenset(),
    simulation_meta=None,
) -> Quantity:
    return Quantity(
        id=q_id,
        definition_key=def_key,
        value=value,
        unit=unit,
        kind=kind,
        evidence_floor=floor,
        geo_unit_id=geo_id,
        resolution=res,
        as_of=as_of,
        uncertainty=uncertainty,
        source_refs=source_refs,
        method_id="method.census.extrapolation",
        model_version="1.0.0",
        parent_ids=parent_ids,
        quality_flags=quality_flags,
        license_meta="GODL-India",
        simulation_meta=simulation_meta,
    )


@pytest.mark.contract
class TestQuantityRepositoryContract:
    """Contract tests enforced across all QuantityRepository implementations."""

    def test_save_and_retrieve_basic_quantity(self, quantity_repo: QuantityRepository):
        """Saving and retrieving a quantity preserves all core fields."""
        q_id = str(uuid.uuid4())
        q = _create_sample_quantity(q_id=q_id)

        quantity_repo.save(q)
        retrieved = quantity_repo.get(q_id)

        assert retrieved is not None
        assert retrieved.id == q_id
        assert retrieved.definition_key == "population.total"
        assert retrieved.value == 125000.0
        assert retrieved.unit == "persons"
        assert retrieved.kind == Kind.OBSERVED
        assert retrieved.evidence_floor == 4
        assert retrieved.geo_unit_id == "IND.MH.PU"
        assert retrieved.resolution == 2
        assert retrieved.as_of == "2026-03-31"
        assert retrieved.uncertainty == "EXACT"
        assert retrieved.source_refs == (("src_census_2011", "Table A-1", "2026-01-15"),)
        assert retrieved.method_id == "method.census.extrapolation"
        assert retrieved.model_version == "1.0.0"
        assert retrieved.parent_ids == ()
        assert retrieved.quality_flags == frozenset()
        assert retrieved.license_meta == "GODL-India"
        assert retrieved.simulation_meta is None

    def test_save_and_retrieve_with_simulation_metadata(self, quantity_repo: QuantityRepository):
        """P1-4 SimulationMetadata must survive persistence round-trip bitwise."""
        q_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())

        # Save parent quantity first
        parent = _create_sample_quantity(q_id=parent_id, kind=Kind.USER_ASSUMED, floor=3)
        quantity_repo.save(parent)

        sim_meta = SimulationMetadata(
            scenario_id="scenario_baseline_2026",
            model_version="sim_mc_v1.2",
            seed=4294967295,
            sample_count=5000,
            data_versions=("osm_2026_01", "rbi_2026_q1"),
        )

        sim_quantity = _create_sample_quantity(
            q_id=q_id,
            def_key="financial.monthly_cashflow_p50",
            value=45000.0,
            unit="INR/month",
            kind=Kind.SIMULATED,
            floor=1,
            parent_ids=(parent_id,),
            simulation_meta=sim_meta,
        )

        quantity_repo.save(sim_quantity)
        retrieved = quantity_repo.get(q_id)

        assert retrieved is not None
        assert retrieved.simulation_meta is not None
        assert retrieved.simulation_meta.scenario_id == "scenario_baseline_2026"
        assert retrieved.simulation_meta.model_version == "sim_mc_v1.2"
        assert retrieved.simulation_meta.seed == 4294967295
        assert retrieved.simulation_meta.sample_count == 5000
        assert retrieved.simulation_meta.data_versions == ("osm_2026_01", "rbi_2026_q1")
        assert retrieved.parent_ids == (parent_id,)

    def test_get_non_existent_returns_none(self, quantity_repo: QuantityRepository):
        """Querying a non-existent UUID returns None."""
        assert quantity_repo.get(str(uuid.uuid4())) is None
        assert not quantity_repo.exists(str(uuid.uuid4()))

    def test_exists_returns_true_for_stored_quantity(self, quantity_repo: QuantityRepository):
        """exists() returns True if and only if record is present."""
        q_id = str(uuid.uuid4())
        q = _create_sample_quantity(q_id=q_id)

        assert not quantity_repo.exists(q_id)
        quantity_repo.save(q)
        assert quantity_repo.exists(q_id)

    def test_immutability_blocks_value_change(self, quantity_repo: QuantityRepository):
        """Handbook Section 9.2: Quantities are immutable, never UPDATE value."""
        q_id = str(uuid.uuid4())
        q1 = _create_sample_quantity(q_id=q_id, value=100.0)
        quantity_repo.save(q1)

        # Attempt to save same ID with modified value
        q2 = _create_sample_quantity(q_id=q_id, value=105.0)
        with pytest.raises(ImmutableQuantityError, match="immutable: value"):
            quantity_repo.save(q2)

        # Verify original value remained intact
        persisted = quantity_repo.get(q_id)
        assert persisted.value == 100.0

    def test_immutability_blocks_kind_change(self, quantity_repo: QuantityRepository):
        """Handbook Section 9.2: Quantities are immutable, never UPDATE kind."""
        q_id = str(uuid.uuid4())
        q1 = _create_sample_quantity(q_id=q_id, kind=Kind.USER_ASSUMED, floor=3)
        quantity_repo.save(q1)

        # Attempt to save same ID with modified kind
        q2 = _create_sample_quantity(q_id=q_id, kind=Kind.POLICY_RULE, floor=4)
        with pytest.raises(ImmutableQuantityError, match="immutable.*kind"):
            quantity_repo.save(q2)

    def test_idempotent_save_succeeds(self, quantity_repo: QuantityRepository):
        """Saving the identical quantity a second time succeeds idempotently."""
        q_id = str(uuid.uuid4())
        q = _create_sample_quantity(q_id=q_id)

        quantity_repo.save(q)
        quantity_repo.save(q)  # Second save should not raise
        assert quantity_repo.get(q_id).value == q.value

    def test_updating_quality_flags_succeeds(self, quantity_repo: QuantityRepository):
        """Updating non-immutable metadata like supersession quality flags is allowed."""
        q_id = str(uuid.uuid4())
        q1 = _create_sample_quantity(q_id=q_id, quality_flags=frozenset())
        quantity_repo.save(q1)

        # Mark quantity superseded via quality flags
        q2 = _create_sample_quantity(q_id=q_id, quality_flags=frozenset(["SUPERSEDED"]))
        quantity_repo.save(q2)

        retrieved = quantity_repo.get(q_id)
        assert "SUPERSEDED" in retrieved.quality_flags

    def test_list_by_definition_query(self, quantity_repo: QuantityRepository):
        """list_by_definition retrieves all quantities matching the semantic key."""
        q1 = _create_sample_quantity(str(uuid.uuid4()), def_key="demand.sweet_shop.daily")
        q2 = _create_sample_quantity(str(uuid.uuid4()), def_key="demand.sweet_shop.daily")
        q3 = _create_sample_quantity(str(uuid.uuid4()), def_key="population.total")

        quantity_repo.save(q1)
        quantity_repo.save(q2)
        quantity_repo.save(q3)

        results = quantity_repo.list_by_definition("demand.sweet_shop.daily")
        result_ids = {r.id for r in results}
        assert result_ids == {q1.id, q2.id}

    def test_list_by_geo_unit_query(self, quantity_repo: QuantityRepository):
        """list_by_geo_unit retrieves quantities for a specific boundary."""
        q1 = _create_sample_quantity(str(uuid.uuid4()), geo_id="IND.MH.PU")
        q2 = _create_sample_quantity(str(uuid.uuid4()), geo_id="IND.MH.NG")

        quantity_repo.save(q1)
        quantity_repo.save(q2)

        results = quantity_repo.list_by_geo_unit("IND.MH.PU")
        assert len(results) == 1
        assert results[0].id == q1.id

    def test_get_parents_and_children_dag_queries(self, quantity_repo: QuantityRepository):
        """Parent and child lineage DAG queries work consistently."""
        p1 = _create_sample_quantity(str(uuid.uuid4()), def_key="parent1", kind=Kind.USER_ASSUMED, floor=3)
        p2 = _create_sample_quantity(str(uuid.uuid4()), def_key="parent2", kind=Kind.USER_ASSUMED, floor=3)
        quantity_repo.save(p1)
        quantity_repo.save(p2)

        child = _create_sample_quantity(
            str(uuid.uuid4()),
            def_key="child",
            kind=Kind.CALCULATED,
            floor=3,
            parent_ids=(p1.id, p2.id),
        )
        quantity_repo.save(child)

        # Test get_parents
        parents = quantity_repo.get_parents(child.id)
        parent_ids = {p.id for p in parents}
        assert parent_ids == {p1.id, p2.id}

        # Test get_children (queries parent_ids containment)
        p1_children = quantity_repo.get_children(p1.id)
        assert len(p1_children) == 1
        assert p1_children[0].id == child.id

        p2_children = quantity_repo.get_children(p2.id)
        assert len(p2_children) == 1
        assert p2_children[0].id == child.id

        child_children = quantity_repo.get_children(child.id)
        assert len(child_children) == 0

    def test_count_and_list_all(self, quantity_repo: QuantityRepository):
        """count() and list_all() return accurate repository size and items."""
        initial_count = quantity_repo.count()
        q1 = _create_sample_quantity(str(uuid.uuid4()))
        q2 = _create_sample_quantity(str(uuid.uuid4()))

        quantity_repo.save(q1)
        quantity_repo.save(q2)

        assert quantity_repo.count() == initial_count + 2
        all_quantities = quantity_repo.list_all()
        all_ids = {q.id for q in all_quantities}
        assert q1.id in all_ids
        assert q2.id in all_ids

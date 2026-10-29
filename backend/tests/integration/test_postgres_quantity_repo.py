"""
PostgreSQL + PostGIS Integration Tests for Quantity Persistence.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 4.1, 4.5, 4.7, Part 9.1, 9.2, Part 12.1).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).

Verifies:
- Session isolation across discrete database connections.
- UUID identity and parent_ids array round-trip.
- JSONB uncertainty and source_refs serialization fidelity.
- P1-4 SimulationMetadata bitwise persistence (including 64-bit seed limit).
- Database-level check constraints (evidence_floor, resolution, kind).
- Foreign-key constraints (quantities.owner_id -> users.id).
- Lineage traversal via Postgres GIN index.
"""

import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import ImmutableQuantityError
from backend.arthlens.domain.simulation import SimulationMetadata
from backend.arthlens.infra.database import get_engine, get_session_factory
from backend.arthlens.infra.models import QuantityModel, UserModel
from backend.arthlens.infra.repositories import (
    PostgresQuantityRepository,
    PostgresScenarioRepository,
    PostgresUserRepository,
)


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure clean table state before each integration test."""
        # Ensure clean table state before each integration test
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE quantities, scenarios, simulation_runs, users CASCADE;"))
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE quantities, scenarios, simulation_runs, users CASCADE;"))


@pytest.mark.integration
class TestPostgresQuantityPersistenceIntegration:
    """End-to-end integration tests running directly against PostgreSQL 16 + PostGIS 3.4."""

    def test_session_isolation_and_cross_session_retrieval(self):
        """A quantity committed in Session A is immediately and faithfully readable in Session B."""
        factory = get_session_factory()
        repo_a = PostgresQuantityRepository(session_factory=factory)
        repo_b = PostgresQuantityRepository(session_factory=factory)

        q_id = str(uuid.uuid4())
        q = Quantity(
            id=q_id,
            definition_key="energy.tariff.commercial",
            value=8.45,
            unit="INR/kWh",
            kind=Kind.POLICY_RULE,
            evidence_floor=4,
            geo_unit_id="IND.MH",
            resolution=1,
            as_of="2026-04-01",
            uncertainty={"type": "EXACT", "confidence": 1.0},
            source_refs=(("src_mahadiscom_2026", "Order 102", "2026-03-15"),),
            method_id="policy.tariff.extract",
            model_version="2.1.0",
            quality_flags=frozenset(["VERIFIED"]),
            license_meta="GODL-India",
        )

        repo_a.save(q)
        retrieved_b = repo_b.get(q_id)

        assert retrieved_b is not None
        assert retrieved_b.id == q_id
        assert retrieved_b.value == 8.45
        assert retrieved_b.unit == "INR/kWh"
        assert retrieved_b.kind == Kind.POLICY_RULE
        assert retrieved_b.evidence_floor == 4
        assert retrieved_b.uncertainty == {"type": "EXACT", "confidence": 1.0}
        assert retrieved_b.source_refs == (("src_mahadiscom_2026", "Order 102", "2026-03-15"),)
        assert retrieved_b.quality_flags == frozenset(["VERIFIED"])

    def test_simulation_metadata_full_persistence_fidelity(self):
        """SimulationMetadata with large 64-bit seed and multi-version inputs round-trips with zero loss."""
        repo = PostgresQuantityRepository()
        parent_id = str(uuid.uuid4())
        child_id = str(uuid.uuid4())

        # Seed parent
        parent = Quantity(
            id=parent_id,
            definition_key="interest_rate.base",
            value=0.085,
            unit="dimensionless",
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id="IND",
            resolution=0,
            as_of="2026-01-01",
        )
        repo.save(parent)

        # Simulation with maximum 64-bit unsigned seed
        sim_meta = SimulationMetadata(
            scenario_id="scenario_tarun_plus_expansion",
            model_version="finance_mc_v3.0.1",
            seed=18446744073709551615,  # 2^64 - 1
            sample_count=20000,
            data_versions=("osm_facilities_v4", "rbi_rates_2026_q2", "census_subdist_2011_v2"),
        )

        sim_quantity = Quantity(
            id=child_id,
            definition_key="financial.npv.p90",
            value=345000.50,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="IND.MH.PU",
            resolution=2,
            as_of="2026-03-31",
            parent_ids=(parent_id,),
            simulation_meta=sim_meta,
        )

        repo.save(sim_quantity)
        retrieved = repo.get(child_id)

        assert retrieved is not None
        assert retrieved.simulation_meta is not None
        assert retrieved.simulation_meta.scenario_id == "scenario_tarun_plus_expansion"
        assert retrieved.simulation_meta.model_version == "finance_mc_v3.0.1"
        assert retrieved.simulation_meta.seed == 18446744073709551615
        assert retrieved.simulation_meta.sample_count == 20000
        assert retrieved.simulation_meta.data_versions == (
            "osm_facilities_v4",
            "rbi_rates_2026_q2",
            "census_subdist_2011_v2",
        )

    def test_database_check_constraints_enforcement(self):
        """PostgreSQL enforces evidence_floor BETWEEN 1 AND 4, resolution 0-5, and valid kind."""
        engine = get_engine()

        # Test invalid evidence floor (> 4)
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO quantities (id, definition_key, value, unit, kind, evidence_floor, geo_unit_id, resolution, uncertainty, method_id, model_version)
                    VALUES (:id, 'test.bad_floor', 1.0, 'INR', 'OBSERVED', 5, 'IND', 0, '"EXACT"'::jsonb, 'm', 'v');
                    """),
                    {"id": uuid.uuid4()},
                )

        # Test invalid resolution (> 5)
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO quantities (id, definition_key, value, unit, kind, evidence_floor, geo_unit_id, resolution, uncertainty, method_id, model_version)
                    VALUES (:id, 'test.bad_res', 1.0, 'INR', 'OBSERVED', 4, 'IND', 6, '"EXACT"'::jsonb, 'm', 'v');
                    """),
                    {"id": uuid.uuid4()},
                )

        # Test invalid kind (not in enum set)
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO quantities (id, definition_key, value, unit, kind, evidence_floor, geo_unit_id, resolution, uncertainty, method_id, model_version)
                    VALUES (:id, 'test.bad_kind', 1.0, 'INR', 'FABRICATED', 4, 'IND', 0, '"EXACT"'::jsonb, 'm', 'v');
                    """),
                    {"id": uuid.uuid4()},
                )

    def test_user_ownership_foreign_key_constraint(self):
        """Owner ID on quantities references users.id; non-existent owner fails foreign key check."""
        engine = get_engine()
        user_repo = PostgresUserRepository()

        # Create real user
        valid_user_id = user_repo.save({
            "email": "entrepreneur@arthlens.org",
            "password_hash": "argon2_dummy_hash",
            "quota_counters": {"runs_today": 0},
        })

        # Save quantity with valid user ownership
        with engine.begin() as conn:
            q_id = uuid.uuid4()
            conn.execute(
                text("""
                INSERT INTO quantities (id, definition_key, value, unit, kind, evidence_floor, geo_unit_id, resolution, uncertainty, method_id, model_version, owner_id)
                VALUES (:id, 'user.custom_fact', 50000.0, 'INR/month', 'USER_ASSUMED', 3, 'IND.MH.PU', 2, '"EXACT"'::jsonb, 'input', '1.0', :owner_id);
                """),
                {"id": q_id, "owner_id": uuid.UUID(valid_user_id)},
            )
            count = conn.execute(text("SELECT count(*) FROM quantities WHERE owner_id = :owner_id"), {"owner_id": uuid.UUID(valid_user_id)}).scalar()
            assert count == 1

        # Save quantity with non-existent owner fails
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO quantities (id, definition_key, value, unit, kind, evidence_floor, geo_unit_id, resolution, uncertainty, method_id, model_version, owner_id)
                    VALUES (:id, 'user.bad_fact', 10.0, 'INR', 'USER_ASSUMED', 3, 'IND', 0, '"EXACT"'::jsonb, 'input', '1.0', :owner_id);
                    """),
                    {"id": uuid.uuid4(), "owner_id": uuid.uuid4()},
                )

    def test_multi_level_dag_lineage_and_gin_index(self):
        """
        Build a multi-level DAG:
            Root A (Observed)
              └── Child B (Calculated from A)
                    ├── Grandchild C (Simulated from B)
                    └── Grandchild D (Simulated from B)
        Verify that get_children using the GIN index navigates the exact lineage.
        """
        repo = PostgresQuantityRepository()

        a_id = str(uuid.uuid4())
        b_id = str(uuid.uuid4())
        c_id = str(uuid.uuid4())
        d_id = str(uuid.uuid4())

        q_a = Quantity(
            id=a_id,
            definition_key="pop.total",
            value=100000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="IND.MH.PU",
            resolution=2,
            as_of="2026-01-01",
        )
        q_b = Quantity(
            id=b_id,
            definition_key="demand.total",
            value=25000.0,
            unit="INR/month",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="IND.MH.PU",
            resolution=2,
            as_of="2026-01-01",
            parent_ids=(a_id,),
        )
        q_c = Quantity(
            id=c_id,
            definition_key="sim.revenue_scenario_1",
            value=22000.0,
            unit="INR/month",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="IND.MH.PU",
            resolution=2,
            as_of="2026-01-01",
            parent_ids=(b_id,),
            simulation_meta=SimulationMetadata(
                scenario_id="sc_1",
                model_version="1.0",
                seed=101,
                sample_count=1000,
                data_versions=("osm_v1",),
            ),
        )
        q_d = Quantity(
            id=d_id,
            definition_key="sim.revenue_scenario_2",
            value=28000.0,
            unit="INR/month",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="IND.MH.PU",
            resolution=2,
            as_of="2026-01-01",
            parent_ids=(b_id,),
            simulation_meta=SimulationMetadata(
                scenario_id="sc_2",
                model_version="1.0",
                seed=202,
                sample_count=1000,
                data_versions=("osm_v1",),
            ),
        )

        repo.save(q_a)
        repo.save(q_b)
        repo.save(q_c)
        repo.save(q_d)

        # A's children should be only B
        a_children = repo.get_children(a_id)
        assert len(a_children) == 1
        assert a_children[0].id == b_id

        # B's children should be C and D
        b_children = repo.get_children(b_id)
        b_child_ids = {c.id for c in b_children}
        assert b_child_ids == {c_id, d_id}

        # C's children should be empty
        c_children = repo.get_children(c_id)
        assert len(c_children) == 0

        # Parents check
        b_parents = repo.get_parents(b_id)
        assert len(b_parents) == 1
        assert b_parents[0].id == a_id

        c_parents = repo.get_parents(c_id)
        assert len(c_parents) == 1
        assert c_parents[0].id == b_id

    def test_database_trigger_rejects_direct_sql_value_update(self):
        """PostgreSQL trigger trg_quantities_immutable rejects direct SQL updates to value."""
        repo = PostgresQuantityRepository()
        q_id = str(uuid.uuid4())
        q = Quantity(
            id=q_id,
            definition_key="test.direct_sql.value",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="IND",
            resolution=0,
            as_of="2026-01-01",
        )
        repo.save(q)

        engine = get_engine()
        with pytest.raises(Exception, match="is immutable: value cannot be modified"):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE quantities SET value = 999.0 WHERE id = :id"),
                    {"id": uuid.UUID(q_id)},
                )

        # Confirm persisted value was protected
        persisted = repo.get(q_id)
        assert persisted.value == 100.0

    def test_database_trigger_rejects_direct_sql_kind_update(self):
        """PostgreSQL trigger trg_quantities_immutable rejects direct SQL updates to kind."""
        repo = PostgresQuantityRepository()
        q_id = str(uuid.uuid4())
        q = Quantity(
            id=q_id,
            definition_key="test.direct_sql.kind",
            value=250.0,
            unit="INR",
            kind=Kind.USER_ASSUMED,
            evidence_floor=3,
            geo_unit_id="IND",
            resolution=0,
            as_of="2026-01-01",
        )
        repo.save(q)

        engine = get_engine()
        with pytest.raises(Exception, match="is immutable: kind cannot be modified"):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE quantities SET kind = 'POLICY_RULE' WHERE id = :id"),
                    {"id": uuid.UUID(q_id)},
                )

        persisted = repo.get(q_id)
        assert persisted.kind == Kind.USER_ASSUMED

    def test_database_trigger_allows_supersession_metadata_update(self):
        """PostgreSQL trigger allows updating quality_flags for legitimate supersession."""
        repo = PostgresQuantityRepository()
        q_id = str(uuid.uuid4())
        q = Quantity(
            id=q_id,
            definition_key="test.supersession",
            value=500.0,
            unit="INR",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
            geo_unit_id="IND",
            resolution=0,
            as_of="2026-01-01",
            quality_flags=frozenset(),
        )
        repo.save(q)

        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE quantities SET quality_flags = ARRAY['SUPERSEDED'] WHERE id = :id"),
                {"id": uuid.UUID(q_id)},
            )

        persisted = repo.get(q_id)
        assert "SUPERSEDED" in persisted.quality_flags
        assert persisted.value == 500.0
        assert persisted.kind == Kind.ESTIMATED

    def test_simulation_run_seed_boundary_and_range_constraints(self):
        """
        simulation_runs.seed enforces 0 <= seed <= 18446744073709551615 without float precision loss.
        Tests:
        - Seed 0 (minimum valid)
        - Seed 1
        - Seed 9007199254740993 (2^53 + 1, exceeds consecutive float precision)
        - Seed 18446744073709551615 (2^64 - 1, maximum valid)
        - Seed -1 (rejected by check constraint)
        - Seed 18446744073709551616 (rejected by check constraint)
        """
        engine = get_engine()
        user_repo = PostgresUserRepository()
        scenario_repo = PostgresScenarioRepository()

        user_id = user_repo.save({
            "email": "sim_tester@arthlens.org",
            "password_hash": "dummy",
            "quota_counters": {},
        })

        scenario_id = scenario_repo.save_scenario({
            "owner_id": user_id,
            "name": "Exact Seed Test Scenario",
            "scenario": {"params": {}},
        })

        # Test seeds that must round-trip with bit-identical exactness
        exact_seeds = [
            0,
            1,
            9007199254740993,          # 2^53 + 1: fails in float (float(9007199254740993) == 9007199254740992)
            18446744073709551615,      # 2^64 - 1: fails in float (int(float(18446744073709551615)) == 18446744073709551616)
        ]

        for seed in exact_seeds:
            run_id = scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": seed,
                "model_version": "sim_mc_exact_v1",
                "data_version_ids": ["data_v1"],
            })

            retrieved = scenario_repo.get_simulation_run(run_id)
            assert retrieved is not None
            # Verify exact integer equality (proves no float conversion occurred)
            assert retrieved["seed"] == seed
            assert isinstance(retrieved["seed"], int)

            # Also check direct ORM model to verify SQLAlchemy Numeric(asdecimal=True) returns Decimal, not float
            with get_session_factory()() as session:
                from backend.arthlens.infra.models import SimulationRunModel
                from decimal import Decimal
                model = session.get(SimulationRunModel, uuid.UUID(run_id))
                assert isinstance(model.seed, Decimal), f"Expected Decimal from ORM, got {type(model.seed)}"
                assert int(model.seed) == seed

        # Test rejected types before persistence (Python validation)
        # 1. Boolean input rejected
        with pytest.raises(TypeError, match="Seed must be an integer, got bool"):
            scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": True,
                "model_version": "sim_mc_exact_v1",
            })

        # 2. Floating-point input rejected (avoids precision loss)
        with pytest.raises(TypeError, match="Floating-point seeds are rejected"):
            scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": 9007199254740993.0,
                "model_version": "sim_mc_exact_v1",
            })

        # 3. Fractional Decimal input rejected
        from decimal import Decimal
        with pytest.raises(ValueError, match="Fractional Decimal seed rejected"):
            scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": Decimal("123.45"),
                "model_version": "sim_mc_exact_v1",
            })

        # 4. Negative seed (< 0) rejected by validator
        with pytest.raises(ValueError, match="Seed must be non-negative"):
            scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": -1,
                "model_version": "sim_mc_exact_v1",
            })

        # 5. Seed exceeding uint64 limit (> 18446744073709551615) rejected by validator
        with pytest.raises(ValueError, match="Seed exceeds unsigned 64-bit maximum"):
            scenario_repo.save_simulation_run({
                "scenario_id": scenario_id,
                "seed": 18446744073709551616,
                "model_version": "sim_mc_exact_v1",
            })

        # 6. Direct SQL insertion of fractional seed is rejected by PostgreSQL check constraint
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO simulation_runs (id, scenario_id, seed, model_version)
                    VALUES (:id, :scenario_id, 123.45, 'sim_sql');
                    """),
                    {"id": uuid.uuid4(), "scenario_id": uuid.UUID(scenario_id)},
                )        # 7. Direct SQL insertion of negative seed rejected by PostgreSQL
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO simulation_runs (id, scenario_id, seed, model_version)
                    VALUES (:id, :scenario_id, -5, 'sim_sql');
                    """),
                    {"id": uuid.uuid4(), "scenario_id": uuid.UUID(scenario_id)},
                )        # 8. Direct SQL insertion of overflow seed rejected by PostgreSQL
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(
                    text("""
                    INSERT INTO simulation_runs (id, scenario_id, seed, model_version)
                    VALUES (:id, :scenario_id, 18446744073709551616, 'sim_sql');
                    """),
                    {"id": uuid.uuid4(), "scenario_id": uuid.UUID(scenario_id)},
                )

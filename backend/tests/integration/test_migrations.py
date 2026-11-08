"""
Migration and Schema Integration Tests for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2, Part 12.1).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).

Verifies:
- Alembic upgrade from base to head creates all 20 Part 9 tables.
- PostGIS 3.4 extension is available and geographic columns are functional.
- PostgreSQL check constraints and GIN indexes are properly applied.
- Clean rollback via downgrade base and idempotent re-upgrade.
"""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from backend.arthlens.infra.database import get_engine
from sqlalchemy import inspect, text


@pytest.fixture(scope="module")
def alembic_cfg():
    """Load backend/alembic.ini configuration."""
    backend_dir = Path(__file__).resolve().parents[2]
    ini_path = backend_dir / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    return cfg


@pytest.mark.integration
class TestAlembicMigrations:
    """Integration test suite executing Alembic migrations against PostgreSQL + PostGIS."""

    EXPECTED_TABLES = {
        "users",
        "roles",
        "user_roles",
        "sources",
        "source_versions",
        "geo_units",
        "facilities",
        "quantities",
        "policy_documents",
        "policy_rules",
        "business_profiles",
        "scenarios",
        "simulation_runs",
        "agent_runs",
        "agent_run_steps",
        "run_events",
        "jobs",
        "approvals",
        "tasks",
        "audit_events",
        "revoked_tokens",
        "rate_limits",
        "source_records",
    }

    def test_upgrade_head_creates_all_tables(self, alembic_cfg):
        """Applying migrations to head creates every Part 9 domain and system table."""
        engine = get_engine()

        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        missing_tables = self.EXPECTED_TABLES - existing_tables
        assert not missing_tables, f"Migration failed to create tables: {missing_tables}"

    def test_policy_lifecycle_migration_downgrades_unverified_legacy_records(self, alembic_cfg):
        """Legacy ACTIVE documents and APPROVED rules cannot survive as verified state."""
        engine = get_engine()
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "009_road_graph_spatial_index")
        user_id = str(uuid.uuid4())
        document_id = str(uuid.uuid4())
        rule_id = str(uuid.uuid4())
        email = f"policy-migration-{user_id}@example.test"
        try:
            with engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO users (id, email, password_hash) VALUES (:id, :email, 'test-hash')"),
                    {"id": user_id, "email": email},
                )
                connection.execute(
                    text(
                        "INSERT INTO policy_documents (id, scheme_id, document_url, sha256, status) "
                        "VALUES (:id, 'migration-fixture', 'https://example.invalid/policy.pdf', :sha256, 'ACTIVE')"
                    ),
                    {"id": document_id, "sha256": "d" * 64},
                )
                connection.execute(
                    text(
                        "INSERT INTO policy_rules (id, document_id, scheme_id, version, rule_ast, status, approved_by) "
                        "VALUES (:id, :document_id, 'migration-fixture', 'legacy-v1', '{\"type\":\"constant\",\"value\":\"TRUE\"}'::jsonb, 'APPROVED', :user_id)"
                    ),
                    {"id": rule_id, "document_id": document_id, "user_id": user_id},
                )
            command.upgrade(alembic_cfg, "head")
            with engine.connect() as connection:
                document = connection.execute(
                    text("SELECT status, verified_by, source_version_id FROM policy_documents WHERE id = :id"),
                    {"id": document_id},
                ).one()
                rule = connection.execute(
                    text("SELECT status, approved_by, approved_at FROM policy_rules WHERE id = :id"),
                    {"id": rule_id},
                ).one()
            assert document.status == "PENDING_REVIEW"
            assert document.verified_by is None
            assert document.source_version_id is None
            assert rule.status == "DRAFT"
            assert rule.approved_by is None
            assert rule.approved_at is None
        finally:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM policy_rules WHERE id = :id"), {"id": rule_id})
                connection.execute(text("DELETE FROM policy_documents WHERE id = :id"), {"id": document_id})
                connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            command.upgrade(alembic_cfg, "head")

    def test_postgis_extension_and_spatial_functions(self):
        """PostGIS 3.4 is enabled and spatial functions operate on geometry columns."""
        engine = get_engine()
        with engine.connect() as conn:
            # Verify PostGIS extension is loaded
            result = conn.execute(text("SELECT PostGIS_Version();")).scalar()
            assert result is not None
            assert "3." in str(result), f"Unexpected PostGIS version: {result}"

            # Test spatial operation using ST_MakePoint and ST_Distance
            pune = "ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)"
            mumbai = "ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)"
            dist_query = text(f"SELECT ST_Distance({pune}::geography, {mumbai}::geography);")
            distance_meters = conn.execute(dist_query).scalar()
            # Pune to Mumbai is roughly 120-150 km
            assert 110_000 < distance_meters < 160_000, f"Unexpected distance: {distance_meters}"

    def test_quantities_schema_and_gin_index(self):
        """Quantities table has required check constraints, GIN index, and columns."""
        engine = get_engine()
        inspector = inspect(engine)

        # Verify GIN index on parent_ids
        indexes = inspector.get_indexes("quantities")
        gin_index = next((idx for idx in indexes if idx["name"] == "quantities_parents_gin"), None)
        assert gin_index is not None, "quantities_parents_gin index not found on quantities"
        assert gin_index["column_names"] == ["parent_ids"]
        assert gin_index["dialect_options"].get("postgresql_using") == "gin"

        # Verify check constraints
        constraints = inspector.get_check_constraints("quantities")
        constraint_names = {c["name"] for c in constraints}
        assert "check_evidence_floor" in constraint_names
        assert "check_resolution" in constraint_names
        assert "check_quantity_kind" in constraint_names

        # Verify columns exist including simulation_meta JSONB
        columns = {c["name"]: c for c in inspector.get_columns("quantities")}
        assert "simulation_meta" in columns
        assert "source_refs" in columns
        assert "uncertainty" in columns
        assert "parent_ids" in columns
        assert "quality_flags" in columns

    def test_simulation_runs_seed_numeric_and_constraint(self):
        """simulation_runs.seed is NUMERIC with check_simulation_run_seed_range."""
        engine = get_engine()
        inspector = inspect(engine)

        columns = {c["name"]: c for c in inspector.get_columns("simulation_runs")}
        seed_col = columns.get("seed")
        assert seed_col is not None, "seed column missing from simulation_runs"
        assert "NUMERIC" in str(seed_col["type"]).upper(), f"Unexpected type: {seed_col['type']}"

        constraints = inspector.get_check_constraints("simulation_runs")
        constraint_names = {c["name"] for c in constraints}
        assert "check_simulation_run_seed_range" in constraint_names

    def test_quantities_immutability_trigger_installed(self):
        """PostgreSQL trigger trg_quantities_immutable is installed on quantities."""
        engine = get_engine()
        with engine.connect() as conn:
            query = text("""
            SELECT trigger_name
            FROM information_schema.triggers
            WHERE event_object_table = 'quantities'
              AND trigger_name = 'trg_quantities_immutable';
            """)
            result = conn.execute(query).scalar()
            assert result == "trg_quantities_immutable", "trg_quantities_immutable trigger not found"

    def test_audit_events_immutability_trigger_installed(self):
        """PostgreSQL trigger trg_audit_events_immutable is installed on audit_events."""
        engine = get_engine()
        with engine.connect() as conn:
            query = text("""
            SELECT trigger_name
            FROM information_schema.triggers
            WHERE event_object_table = 'audit_events'
              AND trigger_name = 'trg_audit_events_immutable';
            """)
            result = conn.execute(query).scalar()
            assert result == "trg_audit_events_immutable", "trg_audit_events_immutable trigger not found"

    def test_mvp_roles_seeded(self):
        """Migration 004 seeds the three MVP roles: ENTREPRENEUR, STEWARD, ADMIN."""
        engine = get_engine()
        with engine.connect() as conn:
            roles = set(conn.execute(text("SELECT id FROM roles;")).scalars().all())
            assert {"ENTREPRENEUR", "STEWARD", "ADMIN"}.issubset(roles)

    def test_migration_downgrade_and_reupgrade(self, alembic_cfg):
        """Supported downgrade to base cleanly drops tables, and re-upgrade restores them."""
        engine = get_engine()
        engine.dispose()

        # Downgrade to base
        command.downgrade(alembic_cfg, "base")

        engine.dispose()
        inspector = inspect(engine)
        remaining_tables = set(inspector.get_table_names())
        app_tables_remaining = self.EXPECTED_TABLES.intersection(remaining_tables)
        assert not app_tables_remaining, f"Downgrade failed to drop tables: {app_tables_remaining}"

        engine.dispose()
        # Re-upgrade to head to restore environment for downstream tests
        command.upgrade(alembic_cfg, "head")

        engine.dispose()
        inspector_after = inspect(engine)
        restored_tables = set(inspector_after.get_table_names())
        assert self.EXPECTED_TABLES.issubset(restored_tables), "Re-upgrade failed to restore all tables"

    def test_downgrade_out_of_range_seed_guard_and_safe_revert(self, alembic_cfg):
        """
        Downgrading 002 -> 001 safely protects against truncating unsigned 64-bit seeds:
        - If seeds > 9223372036854775807 (max signed BIGINT) exist, downgrade is refused.
        - Once out-of-range records are removed, downgrade succeeds without error.
        """
        engine = get_engine()
        engine.dispose()

        # Create user and scenario first
        user_id = "11111111-1111-1111-1111-111111111111"
        scenario_id = "22222222-2222-2222-2222-222222222222"
        run_id = "33333333-3333-3333-3333-333333333333"

        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO users (id, email, password_hash) VALUES (:id, 'guard@test.org', 'pwd') ON CONFLICT DO NOTHING;"),
                {"id": user_id},
            )
            conn.execute(
                text("INSERT INTO scenarios (id, owner_id, name, scenario) VALUES (:id, :owner_id, 'Guard', '{}'::jsonb);"),
                {"id": scenario_id, "owner_id": user_id},
            )
            # Insert seed > max signed BIGINT (18446744073709551615 > 9223372036854775807)
            conn.execute(
                text("""
                INSERT INTO simulation_runs (id, scenario_id, seed, model_version)
                VALUES (:id, :scenario_id, 18446744073709551615, 'model_guard');
                """),
                {"id": run_id, "scenario_id": scenario_id},
            )

        engine.dispose()

        # Downgrade 002 -> 001 must be REFUSED with clear ValueError
        with pytest.raises(ValueError, match="Cannot downgrade migration 002_seed_and_immutability: found 1 simulation_run record"):
            command.downgrade(alembic_cfg, "001_initial_schema")

        engine.dispose()

        # Remove out-of-range record
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM simulation_runs WHERE id = :id;"), {"id": run_id})
            conn.execute(text("DELETE FROM scenarios WHERE id = :id;"), {"id": scenario_id})
            conn.execute(text("DELETE FROM users WHERE id = :id;"), {"id": user_id})

        engine.dispose()

        # Safe downgrade now succeeds
        command.downgrade(alembic_cfg, "001_initial_schema")

        engine.dispose()
        # Verify simulation_runs.seed is back to BIGINT
        inspector = inspect(engine)
        seed_col = next(c for c in inspector.get_columns("simulation_runs") if c["name"] == "seed")
        assert "BIGINT" in str(seed_col["type"]).upper()

        engine.dispose()
        # Restore to head (002_seed_and_immutability)
        command.upgrade(alembic_cfg, "head")

        engine.dispose()
        inspector_head = inspect(engine)
        seed_col_head = next(c for c in inspector_head.get_columns("simulation_runs") if c["name"] == "seed")
        assert "NUMERIC" in str(seed_col_head["type"]).upper()

    def test_downgrade_003_to_002_and_safe_revert(self, alembic_cfg):
        """Downgrading 003 -> 002 succeeds safely and restores NUMERIC(20, 0)."""
        engine = get_engine()
        engine.dispose()

        # Downgrade 003 -> 002
        command.downgrade(alembic_cfg, "002_seed_and_immutability")
        engine.dispose()

        inspector = inspect(engine)
        seed_col = next(c for c in inspector.get_columns("simulation_runs") if c["name"] == "seed")
        assert "NUMERIC" in str(seed_col["type"]).upper()

        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")
        engine.dispose()
        inspector_head = inspect(engine)
        seed_col_head = next(c for c in inspector_head.get_columns("simulation_runs") if c["name"] == "seed")
        assert "NUMERIC" in str(seed_col_head["type"]).upper()

    def test_geo_coverage_status_migration_006(self, alembic_cfg):
        """Migration 006 decouples coverage_status, adds geometry/analytical status and census_code."""
        engine = get_engine()
        inspector = inspect(engine)

        columns = {c["name"]: c for c in inspector.get_columns("geo_units")}
        assert "coverage_status" in columns
        assert "geometry_status" in columns
        assert "analytical_status" in columns
        assert "census_code" in columns

        # Check default values
        assert "NAVIGABLE" in str(columns["coverage_status"].get("default", ""))
        assert "GEOMETRY_MISSING" in str(columns["geometry_status"].get("default", ""))
        assert "ANALYSIS_UNAVAILABLE" in str(columns["analytical_status"].get("default", ""))

        # Test safe downgrade to 005_source_records
        engine.dispose()
        command.downgrade(alembic_cfg, "005_source_records")
        engine.dispose()

        inspector_005 = inspect(engine)
        cols_005 = {c["name"]: c for c in inspector_005.get_columns("geo_units")}
        assert "geometry_status" not in cols_005
        assert "analytical_status" not in cols_005
        assert "census_code" not in cols_005
        assert "FULL" in str(cols_005["coverage_status"].get("default", ""))

        # Restore to head
        command.upgrade(alembic_cfg, "head")
        engine.dispose()

        inspector_restored = inspect(engine)
        cols_restored = {c["name"]: c for c in inspector_restored.get_columns("geo_units")}
        assert "geometry_status" in cols_restored
        assert "analytical_status" in cols_restored
        assert "census_code" in cols_restored

    def test_geo_coverage_check_constraints_migration_007(self, alembic_cfg):
        """Migration 007 applies CHECK constraints for coverage_status, geometry_status, and analytical_status."""
        engine = get_engine()
        inspector = inspect(engine)

        constraints = {c["name"] for c in inspector.get_check_constraints("geo_units")}
        assert "check_geo_unit_coverage_status" in constraints
        assert "check_geo_unit_geometry_status" in constraints
        assert "check_geo_unit_analytical_status" in constraints

        # Test downgrade to 006_geo_coverage_status
        engine.dispose()
        command.downgrade(alembic_cfg, "006_geo_coverage_status")
        engine.dispose()

        inspector_006 = inspect(engine)
        constraints_006 = {c["name"] for c in inspector_006.get_check_constraints("geo_units")}
        assert "check_geo_unit_coverage_status" not in constraints_006
        assert "check_geo_unit_geometry_status" not in constraints_006
        assert "check_geo_unit_analytical_status" not in constraints_006

        # Restore to head
        command.upgrade(alembic_cfg, "head")
        engine.dispose()

        inspector_head = inspect(engine)
        constraints_head = {c["name"] for c in inspector_head.get_check_constraints("geo_units")}
        assert "check_geo_unit_coverage_status" in constraints_head

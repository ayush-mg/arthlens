"""
Migration and Schema Integration Tests for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2, Part 12.1).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).

Verifies:
- Alembic upgrade from base to head creates the domain, system, and auth tables.
- PostGIS 3.4 extension is available and geographic columns are functional.
- PostgreSQL check constraints and GIN indexes are properly applied.
- Clean rollback via downgrade base and idempotent re-upgrade.
"""

import uuid
from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from backend.arthlens.infra.database import assert_safe_test_database, get_engine
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
        "inventory_cost_reconciliations",
        "inventory_cost_reconciliation_events",
        "business_scenarios",
        "business_scenario_versions",
        "business_simulation_runs",
        "goal_milestones",
        "goal_action_plans",
        "goal_action_tasks",
        "goal_progress_snapshots",
        "agent_proposed_actions",
        "auth_otp_challenges",
    }

    MIGRATION_SCHEMA = (
        (
            "020_inventory_cost_reconciliation",
            {
                "purchases": {"return_credit_amount"},
                "inventory_movements": {
                    "cost_reconciliation_status", "source_purchase_item_id", "reconciled_at",
                    "reconciled_by_user_id", "reconciliation_note",
                },
                "inventory_cost_reconciliations": {
                    "id", "business_id", "mode", "status", "created_by", "summary", "created_at",
                },
                "inventory_cost_reconciliation_events": {
                    "id", "reconciliation_id", "movement_id", "product_id", "classification",
                    "prior_cost_basis", "resolved_cost_basis", "source_evidence", "resolution_note",
                    "created_at",
                },
            },
        ),
        (
            "021_business_scenario_versions",
            {
                "business_scenarios": {
                    "id", "business_id", "created_by_user_id", "name", "description",
                    "current_version", "created_at", "updated_at",
                },
                "business_scenario_versions": {
                    "id", "scenario_id", "version_number", "assumptions", "baseline_snapshot_hash",
                    "created_by_user_id", "created_at",
                },
                "business_simulation_runs": {
                    "id", "business_id", "scenario_version_id", "random_seed", "iterations",
                    "distribution_config", "baseline_snapshot_hash", "model_version", "result",
                    "created_by_user_id", "created_at",
                },
            },
        ),
        (
            "022_goal_planning_records",
            {
                "goal_milestones": {
                    "id", "business_id", "goal_id", "title", "target_date", "target_value",
                    "created_by_user_id", "created_at",
                },
                "goal_action_plans": {
                    "id", "business_id", "goal_id", "title", "description", "status",
                    "created_by_user_id", "created_at",
                },
                "goal_action_tasks": {
                    "id", "business_id", "goal_id", "plan_id", "title", "description",
                    "assigned_member_id", "priority", "status", "due_date", "expected_financial_impact",
                    "created_by_user_id", "created_at", "updated_at",
                },
                "goal_progress_snapshots": {
                    "id", "business_id", "goal_id", "as_of_date", "planned_value", "actual_value",
                    "deviation_value", "status", "explanation", "evidence_items", "created_by_user_id",
                    "created_at",
                },
            },
        ),
        (
            "023_decision_version_graphs",
            {
                "decision_evaluations": {
                    "version_number", "parent_decision_id", "causal_graph", "evidence_items",
                },
            },
        ),
        (
            "024_agent_action_confirmation",
            {
                "agent_proposed_actions": {
                    "id", "business_id", "session_id", "action_type", "payload", "status",
                    "created_by_user_id", "confirmed_by_user_id", "result", "created_at", "updated_at",
                },
            },
        ),
        (
            "025_workspace_role_matrix",
            {"business_memberships": {"role"}},
        ),
        (
            "026_auth_otp_and_google_oauth",
            {
                "users": {
                    "email_verified", "google_sub", "auth_provider", "two_factor_enabled",
                },
                "auth_otp_challenges": {
                    "id", "user_id", "email", "purpose", "code_hash", "attempts",
                    "max_attempts", "expires_at", "consumed_at", "created_at",
                },
            },
        ),
    )

    @staticmethod
    def _assert_schema_columns(inspector, expected_columns):
        for table_name, expected in expected_columns.items():
            assert inspector.has_table(table_name), f"Migration did not create expected table: {table_name}"
            actual = {column["name"] for column in inspector.get_columns(table_name)}
            missing = set(expected) - actual
            assert not missing, f"{table_name} is missing expected columns: {sorted(missing)}"

    def test_upgrade_head_creates_all_tables(self, alembic_cfg):
        """Applying migrations to head creates every Part 9 domain and system table."""
        engine = get_engine()

        # Run migration upgrade to head
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        missing_tables = self.EXPECTED_TABLES - existing_tables
        assert not missing_tables, f"Migration failed to create tables: {missing_tables}"

    def test_migrations_020_through_026_upgrade_schema_incrementally(self, alembic_cfg):
        """Each 020–026 revision creates its declared tables/columns and advances Alembic in order."""
        engine = get_engine()
        assert_safe_test_database(engine)
        restore_head = False
        try:
            command.upgrade(alembic_cfg, "head")
            restore_head = True
            command.downgrade(alembic_cfg, "019_purchase_returns")
            engine.dispose()
            inspector = inspect(engine)
            assert not inspector.has_table("inventory_cost_reconciliations")
            assert not inspector.has_table("business_scenarios")
            assert not inspector.has_table("goal_milestones")
            assert not inspector.has_table("auth_otp_challenges")
            baseline_inventory_columns = {column["name"] for column in inspector.get_columns("inventory_movements")}
            assert "cost_reconciliation_status" not in baseline_inventory_columns
            baseline_user_columns = {column["name"] for column in inspector.get_columns("users")}
            assert not {"email_verified", "google_sub", "auth_provider", "two_factor_enabled"}.intersection(
                baseline_user_columns
            )

            for revision, expected_columns in self.MIGRATION_SCHEMA:
                command.upgrade(alembic_cfg, revision)
                engine.dispose()
                inspector = inspect(engine)
                self._assert_schema_columns(inspector, expected_columns)
                with engine.connect() as connection:
                    current_revision = connection.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).scalar_one()
                assert current_revision == revision, (
                    f"Expected Alembic revision {revision}, found {current_revision}"
                )

                if revision == "020_inventory_cost_reconciliation":
                    constraints = {
                        item["name"] for item in inspector.get_check_constraints("inventory_movements")
                    }
                    assert "check_inventory_cost_reconciliation_status" in constraints
                    purchase_constraints = {
                        item["name"] for item in inspector.get_check_constraints("purchases")
                    }
                    assert "check_purchase_return_credit_nonnegative" in purchase_constraints
                elif revision == "023_decision_version_graphs":
                    constraints = {
                        item["name"] for item in inspector.get_check_constraints("decision_evaluations")
                    }
                    assert "check_decision_version_number_positive" in constraints
                elif revision == "024_agent_action_confirmation":
                    constraints = {
                        item["name"] for item in inspector.get_check_constraints("agent_proposed_actions")
                    }
                    assert {
                        "check_agent_proposed_action_status", "check_agent_proposed_action_type",
                    }.issubset(constraints)
                elif revision == "025_workspace_role_matrix":
                    role_constraint = next(
                        item["sqltext"]
                        for item in inspector.get_check_constraints("business_memberships")
                        if item["name"] == "check_membership_role"
                    )
                    normalized_constraint = role_constraint.upper().replace(" ", "")
                    assert "'ADMIN'" in normalized_constraint
                    assert "'ANALYST'" in normalized_constraint
                    assert "'OWNER'" in normalized_constraint
                    assert "'MANAGER'" in normalized_constraint
                    assert "'ACCOUNTANT'" in normalized_constraint
                    assert "'VIEWER'" in normalized_constraint
                elif revision == "026_auth_otp_and_google_oauth":
                    constraints = {
                        item["name"] for item in inspector.get_check_constraints("auth_otp_challenges")
                    }
                    assert {
                        "check_auth_otp_purpose", "check_auth_otp_attempts",
                    }.issubset(constraints)
                    indexes = {
                        item["name"]: item for item in inspector.get_indexes("users")
                    }
                    assert indexes["ix_users_google_sub"]["unique"] is True
                    otp_indexes = {
                        item["name"] for item in inspector.get_indexes("auth_otp_challenges")
                    }
                    assert {
                        "ix_auth_otp_challenges_email",
                        "ix_auth_otp_challenges_active_email_purpose",
                    }.issubset(otp_indexes)
        finally:
            if restore_head:
                command.upgrade(alembic_cfg, "head")
            engine.dispose()

    def test_migrations_020_through_026_have_ordered_offline_ddl(self, alembic_cfg):
        """The 020–026 revisions form one ordered chain and emit their declared schema DDL."""
        expected_chain = (
            ("020_inventory_cost_reconciliation", "019_purchase_returns"),
            ("021_business_scenario_versions", "020_inventory_cost_reconciliation"),
            ("022_goal_planning_records", "021_business_scenario_versions"),
            ("023_decision_version_graphs", "022_goal_planning_records"),
            ("024_agent_action_confirmation", "023_decision_version_graphs"),
            ("025_workspace_role_matrix", "024_agent_action_confirmation"),
            ("026_auth_otp_and_google_oauth", "025_workspace_role_matrix"),
        )
        script = ScriptDirectory.from_config(alembic_cfg)
        assert script.get_heads() == ["026_auth_otp_and_google_oauth"]
        for revision, expected_parent in expected_chain:
            assert script.get_revision(revision).down_revision == expected_parent

        output = StringIO()
        alembic_cfg.output_buffer = output
        command.upgrade(alembic_cfg, "head", sql=True)
        generated_sql = " ".join(output.getvalue().lower().split())
        expected_ddl = (
            "cost_reconciliation_status",
            "create table inventory_cost_reconciliations",
            "create table business_scenarios",
            "create table business_simulation_runs",
            "create table goal_milestones",
            "create table goal_action_tasks",
            "alter table decision_evaluations add column version_number",
            "create table agent_proposed_actions",
            "alter table business_memberships add constraint check_membership_role check (role in ('owner', 'admin', 'manager', 'accountant', 'analyst', 'viewer'))",
            "alter table users add column email_verified",
            "alter table users add column google_sub",
            "alter table users add column auth_provider",
            "alter table users add column two_factor_enabled",
            "create unique index ix_users_google_sub on users (google_sub)",
            "create table auth_otp_challenges",
            "create index ix_auth_otp_challenges_email on auth_otp_challenges (email)",
            "create index ix_auth_otp_challenges_active_email_purpose on auth_otp_challenges (email, purpose, created_at)",
        )
        missing = [fragment for fragment in expected_ddl if fragment not in generated_sql]
        assert not missing, f"Offline migration plan omitted expected schema DDL: {missing}"
        ddl_positions = [generated_sql.index(fragment) for fragment in expected_ddl]
        assert ddl_positions == sorted(ddl_positions), "Migration DDL was emitted out of revision order."

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


    def test_task_priority_migration_013(self, alembic_cfg):
        """Migration 013 adds priority column and status/priority CHECK constraints to tasks."""
        engine = get_engine()
        inspector = inspect(engine)

        columns = {c["name"]: c for c in inspector.get_columns("tasks")}
        assert "priority" in columns
        assert "MEDIUM" in str(columns["priority"].get("default", ""))

        constraints = {c["name"] for c in inspector.get_check_constraints("tasks")}
        assert "check_task_status" in constraints
        assert "check_task_priority" in constraints

        # Test downgrade to 012_agent_run_worker_leases
        engine.dispose()
        command.downgrade(alembic_cfg, "012_agent_run_worker_leases")
        engine.dispose()

        inspector_012 = inspect(engine)
        cols_012 = {c["name"]: c for c in inspector_012.get_columns("tasks")}
        assert "priority" not in cols_012
        constraints_012 = {c["name"] for c in inspector_012.get_check_constraints("tasks")}
        assert "check_task_priority" not in constraints_012
        assert "check_task_status" not in constraints_012

        # Restore to head
        command.upgrade(alembic_cfg, "head")
        engine.dispose()

        inspector_restored = inspect(engine)
        cols_restored = {c["name"]: c for c in inspector_restored.get_columns("tasks")}
        assert "priority" in cols_restored
        constraints_restored = {c["name"] for c in inspector_restored.get_check_constraints("tasks")}
        assert "check_task_status" in constraints_restored
        assert "check_task_priority" in constraints_restored

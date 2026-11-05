"""
Integration Tests for Nationwide LGD Hierarchy Ingestion (P2-2 Stage 2).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.4, 9.1, Part 13).
Phase: Phase 2 (P2-2 Stage 2 Nationwide Hierarchy Population).
"""

from pathlib import Path
import pytest
from sqlalchemy import text

from backend.arthlens.data.geo_loader import (
    HierarchyIngestionResult,
    LGDHierarchyLoader,
    init_national_database,
)
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    NavigationStatus,
)
from backend.arthlens.domain.repositories import OrphanedGeoUnitError
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    get_session_factory,
)
from backend.arthlens.infra.in_memory import InMemoryGeoUnitRepository
from backend.arthlens.infra.repositories import PostgresGeoUnitRepository

STATES_CSV = Path(__file__).resolve().parents[2] / "fixtures" / "geo" / "lgd_states.csv"
DISTRICTS_CSV = Path(__file__).resolve().parents[2] / "fixtures" / "geo" / "lgd_districts.csv"


class TestLGDHierarchyIngestionInMemory:
    """Nationwide LGD ingestion contract against InMemory repository."""

    def test_ingest_nationwide_hierarchy_in_memory(self):
        repo = InMemoryGeoUnitRepository()
        loader = LGDHierarchyLoader(repo=repo)

        result = loader.ingest_national_hierarchy(
            states_csv_path=STATES_CSV,
            districts_csv_path=DISTRICTS_CSV,
        )

        assert result.states_loaded == 36
        assert result.districts_loaded == 763
        assert result.total_inserted == 36 + 763  # 36 states + 763 districts (root nation saved beforehand)

        # Verify root nation
        nation = repo.get_unit("in")
        assert nation is not None
        assert nation.name == "India"
        assert nation.level == ResolutionTier.NATION

        # Verify state UP
        up = repo.get_unit("in:state:09")
        assert up is not None
        assert up.parent_id == "in"
        assert up.name == "Uttar Pradesh"
        assert up.level == ResolutionTier.STATE
        assert up.lgd_code == "9"
        assert up.census_code == "09"

        # Verify Varanasi district
        varanasi = repo.get_unit("in:district:187")
        assert varanasi is not None
        assert varanasi.parent_id == "in:state:09"
        assert varanasi.name == "Varanasi"
        assert varanasi.level == ResolutionTier.DISTRICT
        assert varanasi.lgd_code == "187"
        assert varanasi.census_code == "197"
        assert varanasi.navigation_status == NavigationStatus.NAVIGABLE
        assert varanasi.geometry_status == GeometryStatus.GEOMETRY_MISSING
        assert varanasi.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Verify parent lookups
        states = repo.list_by_parent("in")
        assert len(states) == 36

        up_districts = repo.list_by_parent("in:state:09")
        assert len(up_districts) == 75

        # Verify idempotency
        idempotent_result = loader.ingest_national_hierarchy(
            states_csv_path=STATES_CSV,
            districts_csv_path=DISTRICTS_CSV,
        )
        assert idempotent_result.total_inserted == 0
        assert idempotent_result.total_existing == 36 + 763


@pytest.mark.integration
class TestLGDHierarchyIngestionPostgres:
    """Nationwide LGD ingestion against live PostgreSQL + PostGIS database."""

    @pytest.fixture(autouse=True)
    def clean_db(self):
        engine = get_engine()
        assert_safe_test_database(engine)
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE geo_units CASCADE;"))
        yield
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE geo_units CASCADE;"))

    def test_ingest_nationwide_hierarchy_postgres(self):
        factory = get_session_factory()
        repo = PostgresGeoUnitRepository(session_factory=factory)
        loader = LGDHierarchyLoader(repo=repo)

        result = loader.ingest_national_hierarchy(
            states_csv_path=STATES_CSV,
            districts_csv_path=DISTRICTS_CSV,
        )

        assert result.states_loaded == 36
        assert result.districts_loaded == 763
        assert result.total_inserted == 36 + 763

        # Verify root nation
        nation = repo.get_unit("in")
        assert nation is not None
        assert nation.name == "India"

        # Verify state UP
        up = repo.get_unit("in:state:09")
        assert up is not None
        assert up.parent_id == "in"
        assert up.name == "Uttar Pradesh"

        # Verify Varanasi district
        varanasi = repo.get_unit("in:district:187")
        assert varanasi is not None
        assert varanasi.parent_id == "in:state:09"
        assert varanasi.name == "Varanasi"
        assert varanasi.lgd_code == "187"
        assert varanasi.census_code == "197"
        assert varanasi.navigation_status == NavigationStatus.NAVIGABLE
        assert varanasi.geometry_status == GeometryStatus.GEOMETRY_MISSING
        assert varanasi.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Verify parent retrieval in PostgreSQL
        states = repo.list_by_parent("in")
        assert len(states) == 36

        up_districts = repo.list_by_parent("in:state:09")
        assert len(up_districts) == 75

        # Verify LGD code lookup in PostgreSQL
        by_lgd = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "187")
        assert by_lgd is not None
        assert by_lgd.id == "in:district:187"

        # Verify database check constraints directly
        engine = get_engine()
        with engine.connect() as conn:
            count = conn.execute(text("SELECT count(*) FROM geo_units;")).scalar()
            assert count == 1 + 36 + 763

    def test_init_national_database_reproducible_and_idempotent(self):
        """init_national_database executes reproducibly and idempotently against PostgreSQL."""
        factory = get_session_factory()
        repo = PostgresGeoUnitRepository(session_factory=factory)

        # First run: loads all 36 states and 763 districts
        res1 = init_national_database(
            states_csv=STATES_CSV,
            districts_csv=DISTRICTS_CSV,
            repo=repo,
        )
        assert res1.states_loaded == 36
        assert res1.districts_loaded == 763
        assert res1.total_inserted == 36 + 763

        engine = get_engine()
        with engine.connect() as conn:
            cnt1 = conn.execute(text("SELECT count(*) FROM geo_units;")).scalar()
            assert cnt1 == 800

        # Second run: completely idempotent, zero new records inserted
        res2 = init_national_database(
            states_csv=STATES_CSV,
            districts_csv=DISTRICTS_CSV,
            repo=repo,
        )
        assert res2.total_inserted == 0
        assert res2.total_existing == 36 + 763

        with engine.connect() as conn:
            cnt2 = conn.execute(text("SELECT count(*) FROM geo_units;")).scalar()
            assert cnt2 == 800

    def test_init_national_database_missing_file_raises_error(self):
        """Missing CSV file path raises FileNotFoundError without altering database."""
        factory = get_session_factory()
        repo = PostgresGeoUnitRepository(session_factory=factory)
        non_existent = Path("backend/fixtures/geo/does_not_exist.csv")

        with pytest.raises(FileNotFoundError, match="States master CSV not found"):
            init_national_database(states_csv=non_existent, districts_csv=DISTRICTS_CSV, repo=repo)

"""
Contract Tests for GeoUnitRepository Interface (P2-2.1).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 5.1, Part 9.1).
Phase: Phase 2 (P2-2.1 - Geographic Repository Contracts & Persistence).
"""

import pytest
from sqlalchemy import text
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
)
from backend.arthlens.domain.repositories import (
    ConflictingGeoUnitError,
    GeoUnitRepository,
    OrphanedGeoUnitError,
)
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    get_session_factory,
)
from backend.arthlens.infra.in_memory import InMemoryGeoUnitRepository
from backend.arthlens.infra.repositories import PostgresGeoUnitRepository


def create_sample_hierarchy():
    nation = GeoUnit(
        id="in",
        parent_id=None,
        level=ResolutionTier.NATION,
        name="India",
        lgd_code="IN",
    )
    up = GeoUnit(
        id="in:state:09",
        parent_id="in",
        level=ResolutionTier.STATE,
        name="Uttar Pradesh",
        lgd_code="09",
    )
    prayagraj = GeoUnit(
        id="in:district:120",
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Prayagraj",
        lgd_code="120",
        census_code="175",
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        analytical_status=AnalyticalStatus.ANALYSABLE,
    )
    raebareli = GeoUnit(
        id="in:district:175",
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Rae Bareli",
        lgd_code="175",
        census_code="158",
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_MISSING,
        analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
    )
    varanasi = GeoUnit(
        id="in:district:187",
        parent_id="in:state:09",
        level=ResolutionTier.DISTRICT,
        name="Varanasi",
        lgd_code="187",
        census_code="197",
        navigation_status=NavigationStatus.NAVIGABLE,
        geometry_status=GeometryStatus.GEOMETRY_MISSING,
        analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
    )
    sadar = GeoUnit(
        id="in:subdistrict:120:890",
        parent_id="in:district:120",
        level=ResolutionTier.SUBDISTRICT,
        name="Sadar",
        lgd_code="890",
        census_code="00890",
    )
    return [nation, up, prayagraj, raebareli, varanasi, sadar]


class BaseGeoRepositoryContract:
    """Base contract test suite ensuring both InMemory and Postgres repositories satisfy identical contracts."""

    @pytest.fixture
    def repo(self) -> GeoUnitRepository:
        raise NotImplementedError

    def test_save_and_get_unit(self, repo):
        units = create_sample_hierarchy()
        repo.save_unit(units[0])  # nation
        repo.save_unit(units[1])  # state

        fetched = repo.get_unit("in:state:09")
        assert fetched is not None
        assert fetched.id == "in:state:09"
        assert fetched.name == "Uttar Pradesh"
        assert fetched.level == ResolutionTier.STATE
        assert fetched.parent_id == "in"

    def test_save_units_batch(self, repo):
        units = create_sample_hierarchy()
        saved_count = repo.save_units(units)
        assert saved_count == len(units)

        # Retrieve all
        for u in units:
            fetched = repo.get_unit(u.id)
            assert fetched is not None
            assert fetched.name == u.name
            assert fetched.level == u.level

    def test_list_by_parent(self, repo):
        units = create_sample_hierarchy()
        repo.save_units(units)

        # Children of nation -> states
        states = repo.list_by_parent("in")
        assert len(states) == 1
        assert states[0].id == "in:state:09"

        # Children of UP -> districts
        districts = repo.list_by_parent("in:state:09")
        district_ids = {d.id for d in districts}
        assert district_ids == {"in:district:120", "in:district:175", "in:district:187"}

        # Children of Prayagraj -> subdistricts
        subdists = repo.list_by_parent("in:district:120")
        assert len(subdists) == 1
        assert subdists[0].id == "in:subdistrict:120:890"

        # Children of Varanasi -> empty
        assert len(repo.list_by_parent("in:district:187")) == 0

    def test_list_by_level(self, repo):
        units = create_sample_hierarchy()
        repo.save_units(units)

        districts = repo.list_by_level(ResolutionTier.DISTRICT)
        assert len(districts) == 3
        d_ids = {d.id for d in districts}
        assert d_ids == {"in:district:120", "in:district:175", "in:district:187"}

    def test_get_by_lgd_code(self, repo):
        units = create_sample_hierarchy()
        repo.save_units(units)

        # LGD 120 -> Prayagraj
        fetched_p = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "120")
        assert fetched_p is not None
        assert fetched_p.id == "in:district:120"
        assert fetched_p.name == "Prayagraj"
        assert fetched_p.census_code == "175"

        # LGD 175 -> Rae Bareli
        fetched_rb = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "175")
        assert fetched_rb is not None
        assert fetched_rb.id == "in:district:175"
        assert fetched_rb.name == "Rae Bareli"
        assert fetched_rb.census_code == "158"

        # LGD 187 -> Varanasi
        fetched_v = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "187")
        assert fetched_v is not None
        assert fetched_v.id == "in:district:187"
        assert fetched_v.name == "Varanasi"
        assert fetched_v.census_code == "197"

        missing = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "999")
        assert missing is None

    def test_prevent_orphaned_children(self, repo):
        """Saving a child whose parent does not exist must raise OrphanedGeoUnitError."""
        orphan_district = GeoUnit(
            id="in:district:120",
            parent_id="in:state:99",  # non-existent state
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
        )
        with pytest.raises(OrphanedGeoUnitError):
            repo.save_unit(orphan_district)

    def test_idempotent_save(self, repo):
        """Saving the exact same unit twice is idempotent and does not corrupt state."""
        units = create_sample_hierarchy()
        repo.save_unit(units[0])
        repo.save_unit(units[0])  # duplicate identical
        fetched = repo.get_unit("in")
        assert fetched is not None
        assert fetched.name == "India"

    def test_conflicting_id_rejected(self, repo):
        """Saving a different entity with an already existing ID raises ConflictingGeoUnitError."""
        units = create_sample_hierarchy()
        repo.save_unit(units[0])
        repo.save_unit(units[1])  # UP

        conflicting_up = GeoUnit(
            id="in:state:09",
            parent_id="in",
            level=ResolutionTier.STATE,
            name="Different State Name",
            lgd_code="99",
        )
        with pytest.raises(ConflictingGeoUnitError):
            repo.save_unit(conflicting_up)

    def test_self_parent_rejected(self, repo):
        """Self-parenting entities are rejected by level/hierarchy validation."""
        with pytest.raises(ValueError):
            GeoUnit(
                id="in:state:09",
                parent_id="in:state:09",
                level=ResolutionTier.STATE,
                name="Uttar Pradesh",
                lgd_code="09",
            )

    def test_batch_save_rollback_on_failure(self, repo):
        """Failure on any item in a batch guarantees 100% rollback so no partial units persist."""
        units = create_sample_hierarchy()
        nation = units[0]
        repo.save_unit(nation)

        up = units[1]
        orphan_district = GeoUnit(
            id="in:district:999",
            parent_id="in:state:nonexistent",
            level=ResolutionTier.DISTRICT,
            name="Orphan District",
            lgd_code="999",
        )

        # Batch contains one valid state and one orphan district
        with pytest.raises(OrphanedGeoUnitError):
            repo.save_units([up, orphan_district])

        # Assert up was NOT persisted (rolled back)
        assert repo.get_unit("in:state:09") is None

        # Assert repository remains usable after rollback
        repo.save_unit(up)
        assert repo.get_unit("in:state:09") is not None


class TestInMemoryGeoUnitRepository(BaseGeoRepositoryContract):
    """InMemory implementation contract test."""

    @pytest.fixture
    def repo(self) -> GeoUnitRepository:
        return InMemoryGeoUnitRepository()


@pytest.mark.integration
class TestPostgresGeoUnitRepository(BaseGeoRepositoryContract):
    """PostgreSQL implementation contract test running against actual database."""

    @pytest.fixture
    def repo(self) -> GeoUnitRepository:
        engine = get_engine()
        assert_safe_test_database(engine)
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE geo_units CASCADE;"))
        factory = get_session_factory()
        r = PostgresGeoUnitRepository(session_factory=factory)
        yield r
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE geo_units CASCADE;"))

    def test_polygon_persistence_and_retrieval(self, repo):
        """PostGIS Polygon geometry persists with SRID 4326 and deserializes as GeoJSON dict, not WKBElement."""
        units = create_sample_hierarchy()
        nation, up = units[0], units[1]
        repo.save_units([nation, up])

        poly_coords = [[[81.5, 24.5], [82.5, 24.5], [82.5, 25.5], [81.5, 25.5], [81.5, 24.5]]]
        geom = {"type": "Polygon", "coordinates": poly_coords}
        district = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            geometry=geom,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        )
        repo.save_unit(district)

        fetched = repo.get_unit("in:district:120")
        assert fetched is not None
        assert isinstance(fetched.geometry, dict)
        assert fetched.geometry["type"] == "Polygon"
        assert fetched.geometry["coordinates"] == poly_coords
        assert fetched.geometry_status == GeometryStatus.GEOMETRY_VERIFIED

        # Verify SRID 4326 in PostGIS directly
        engine = get_engine()
        with engine.connect() as conn:
            srid = conn.execute(
                text("SELECT ST_SRID(geometry) FROM geo_units WHERE id = 'in:district:120';")
            ).scalar()
            assert srid == 4326

    def test_multipolygon_persistence_and_retrieval(self, repo):
        """PostGIS MultiPolygon geometry persists and deserializes cleanly as GeoJSON dict."""
        units = create_sample_hierarchy()
        nation, up = units[0], units[1]
        repo.save_units([nation, up])

        mp_coords = [
            [[[81.0, 24.0], [81.5, 24.0], [81.5, 24.5], [81.0, 24.5], [81.0, 24.0]]],
            [[[82.0, 25.0], [82.5, 25.0], [82.5, 25.5], [82.0, 25.5], [82.0, 25.0]]],
        ]
        geom = {"type": "MultiPolygon", "coordinates": mp_coords}
        district = GeoUnit(
            id="in:district:187",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Varanasi",
            lgd_code="187",
            geometry=geom,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        )
        repo.save_unit(district)

        fetched = repo.get_unit("in:district:187")
        assert fetched is not None
        assert isinstance(fetched.geometry, dict)
        assert fetched.geometry["type"] == "MultiPolygon"
        assert fetched.geometry["coordinates"] == mp_coords

    def test_unvalidated_geometry_status(self, repo):
        """Geometry supplied without explicit status defaults to GEOMETRY_UNVALIDATED."""
        units = create_sample_hierarchy()
        nation, up = units[0], units[1]
        repo.save_units([nation, up])

        geom = {"type": "Polygon", "coordinates": [[[81.5, 24.5], [82.5, 24.5], [82.5, 25.5], [81.5, 25.5], [81.5, 24.5]]]}
        district = GeoUnit(
            id="in:district:175",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Rae Bareli",
            lgd_code="175",
            geometry=geom,
        )
        assert district.geometry_status == GeometryStatus.GEOMETRY_UNVALIDATED
        repo.save_unit(district)

        fetched = repo.get_unit("in:district:175")
        assert fetched is not None
        assert fetched.geometry_status == GeometryStatus.GEOMETRY_UNVALIDATED

    def test_search_units(self, repo):
        """Search returns matching units case-insensitively and respects limits."""
        units = create_sample_hierarchy()
        repo.save_units(units)

        # Substring search for 'praya'
        matches = repo.search("praya")
        assert len(matches) >= 1
        assert any(u.name == "Prayagraj" for u in matches)

        # Empty search
        assert repo.search("") == []

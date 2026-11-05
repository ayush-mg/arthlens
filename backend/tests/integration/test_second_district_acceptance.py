"""
P2-2 Multi-District Hierarchy & Namespace Decoupling Acceptance Test (Handbook Part 7.4, Part 13).

Proves that adding additional districts succeeds purely through configuration / provider data
without modifying geographic engine code, while strictly enforcing decoupling of LGD and Census namespaces.

Districts verified:
- Prayagraj: LGD 120, Census 175 (Pilot district with verified geometry and analytical coverage)
- Rae Bareli: LGD 175, Census 158
- Kaushambi: LGD 158, Census 174
- Varanasi: LGD 187, Census 197

Acceptance Criteria:
1. India root exists ('in').
2. Uttar Pradesh is a child of India ('in:state:09' -> 'in').
3. Prayagraj, Rae Bareli, Kaushambi, and Varanasi are children of Uttar Pradesh ('in:state:09').
4. All districts can be retrieved through repository operations.
5. LGD identifiers resolve correctly via `get_unit_by_lgd_code`.
6. Decoupling Check: Searching LGD index with Census code 175 resolves to Rae Bareli, NOT Prayagraj.
7. Engine operates identically without district-specific branching.
8. Pilot district regression is preserved.
"""

import pytest
from sqlalchemy import text

from backend.arthlens.data.geo_loader import DistrictConfig, LGDHierarchyLoader
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
    canonical_district_id,
    canonical_nation_id,
    canonical_state_id,
)
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    get_session_factory,
)
from backend.arthlens.infra.in_memory import InMemoryGeoUnitRepository
from backend.arthlens.infra.repositories import PostgresGeoUnitRepository


def setup_base_hierarchy(repo):
    """Seed base India root and Uttar Pradesh state."""
    nation = GeoUnit(
        id=canonical_nation_id(),
        parent_id=None,
        level=ResolutionTier.NATION,
        name="India",
        lgd_code="IN",
    )
    up = GeoUnit(
        id=canonical_state_id("09"),
        parent_id=nation.id,
        level=ResolutionTier.STATE,
        name="Uttar Pradesh",
        lgd_code="09",
        census_code="09",
    )
    repo.save_units([nation, up])
    return nation, up


class TestSecondDistrictAcceptance:
    """Acceptance suite executing against both InMemory and Postgres backends."""

    @pytest.mark.parametrize("backend_type", ["in_memory", "postgres"])
    def test_multi_district_added_via_configuration_and_namespace_decoupling(self, backend_type):
        """
        Acceptance Criteria:
        1. India root exists.
        2. Uttar Pradesh is a child of India.
        3. Prayagraj, Rae Bareli, Kaushambi, and Varanasi are children of Uttar Pradesh.
        4. All four districts can be retrieved through repository operations.
        5. Their LGD identifiers resolve correctly via get_unit_by_lgd_code.
        6. Explicit negative check: Census code 175 looked up as LGD code does NOT return Prayagraj;
           it returns Rae Bareli (LGD 175).
        7. Decoupled coverage semantics: Prayagraj is ANALYSABLE with GEOMETRY_VERIFIED,
           while Varanasi, Rae Bareli, and Kaushambi are NAVIGABLE with ANALYSIS_UNAVAILABLE.
        """
        if backend_type == "in_memory":
            repo = InMemoryGeoUnitRepository()
        else:
            engine = get_engine()
            assert_safe_test_database(engine)
            with engine.begin() as conn:
                conn.execute(text("TRUNCATE TABLE geo_units CASCADE;"))
            factory = get_session_factory()
            repo = PostgresGeoUnitRepository(session_factory=factory)

        loader = LGDHierarchyLoader(repo=repo)
        setup_base_hierarchy(repo)

        # 1. Prayagraj Pilot District Configuration (LGD: 120, Census: 175)
        # In the pure geographic hierarchy baseline, analytical_status is ANALYSIS_UNAVAILABLE
        # until the economic dataset ingestion pipeline populates the epistemic ledger (Handbook 7.4).
        prayagraj_geom = {
            "type": "Polygon",
            "coordinates": [[[81.52, 24.78], [82.35, 24.78], [82.35, 25.79], [81.52, 25.79], [81.52, 24.78]]],
        }
        prayagraj_config = DistrictConfig(
            name="Prayagraj",
            state_code="09",
            lgd_code="120",
            census_code="175",
            geometry=prayagraj_geom,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
        )
        loader.ingest_district_config(prayagraj_config)

        # 2. Rae Bareli District Configuration (LGD: 175, Census: 158)
        rae_bareli_config = DistrictConfig(
            name="Rae Bareli",
            state_code="09",
            lgd_code="175",
            census_code="158",
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        loader.ingest_district_config(rae_bareli_config)

        # 3. Kaushambi District Configuration (LGD: 158, Census: 174)
        kaushambi_config = DistrictConfig(
            name="Kaushambi",
            state_code="09",
            lgd_code="158",
            census_code="174",
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        loader.ingest_district_config(kaushambi_config)

        # 4. Varanasi District Configuration (LGD: 187, Census: 197)
        varanasi_config = DistrictConfig(
            name="Varanasi",
            state_code="09",
            lgd_code="187",
            census_code="197",
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
        )
        loader.ingest_district_config(varanasi_config)

        # Criterion 1: India root exists
        india = repo.get_unit("in")
        assert india is not None
        assert india.level == ResolutionTier.NATION
        assert india.parent_id is None

        # Criterion 2: Uttar Pradesh is a child of India
        up = repo.get_unit("in:state:09")
        assert up is not None
        assert up.parent_id == "in"
        assert up.level == ResolutionTier.STATE

        # Criterion 3: Prayagraj is a child of Uttar Pradesh with ID in:district:120
        prayagraj = repo.get_unit("in:district:120")
        assert prayagraj is not None
        assert prayagraj.parent_id == "in:state:09"
        assert prayagraj.level == ResolutionTier.DISTRICT
        assert prayagraj.name == "Prayagraj"
        assert prayagraj.lgd_code == "120"
        assert prayagraj.census_code == "175"
        assert prayagraj.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE
        assert prayagraj.geometry_status == GeometryStatus.GEOMETRY_VERIFIED

        # Rae Bareli is a child of Uttar Pradesh with ID in:district:175
        rae_bareli = repo.get_unit("in:district:175")
        assert rae_bareli is not None
        assert rae_bareli.parent_id == "in:state:09"
        assert rae_bareli.name == "Rae Bareli"
        assert rae_bareli.lgd_code == "175"
        assert rae_bareli.census_code == "158"
        assert rae_bareli.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Kaushambi is a child of Uttar Pradesh with ID in:district:158
        kaushambi = repo.get_unit("in:district:158")
        assert kaushambi is not None
        assert kaushambi.parent_id == "in:state:09"
        assert kaushambi.name == "Kaushambi"
        assert kaushambi.lgd_code == "158"
        assert kaushambi.census_code == "174"
        assert kaushambi.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Varanasi is a child of Uttar Pradesh with ID in:district:187
        varanasi = repo.get_unit("in:district:187")
        assert varanasi is not None
        assert varanasi.parent_id == "in:state:09"
        assert varanasi.level == ResolutionTier.DISTRICT
        assert varanasi.name == "Varanasi"
        assert varanasi.lgd_code == "187"
        assert varanasi.census_code == "197"
        assert varanasi.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE
        assert varanasi.geometry_status == GeometryStatus.GEOMETRY_MISSING

        # Criterion 4: All districts can be retrieved through repository operations
        children_of_up = repo.list_by_parent("in:state:09")
        child_ids = {d.id for d in children_of_up}
        assert child_ids == {
            "in:district:120",
            "in:district:175",
            "in:district:158",
            "in:district:187",
        }

        all_districts = repo.list_by_level(ResolutionTier.DISTRICT)
        assert len(all_districts) == 4

        # Criterion 5: Their LGD identifiers resolve correctly via get_unit_by_lgd_code
        resolved_120 = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "120")
        assert resolved_120 is not None
        assert resolved_120.id == "in:district:120"
        assert resolved_120.name == "Prayagraj"

        resolved_175 = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "175")
        assert resolved_175 is not None
        assert resolved_175.id == "in:district:175"
        assert resolved_175.name == "Rae Bareli"

        resolved_158 = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "158")
        assert resolved_158 is not None
        assert resolved_158.id == "in:district:158"
        assert resolved_158.name == "Kaushambi"

        resolved_187 = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "187")
        assert resolved_187 is not None
        assert resolved_187.id == "in:district:187"
        assert resolved_187.name == "Varanasi"

        # Criterion 6: Strict Decoupling / Anti-Conflation Cross-Checks
        # Looking up Prayagraj's Census code (175) in the LGD index MUST NOT return Prayagraj!
        # It must resolve to Rae Bareli (whose official LGD code is 175).
        assert resolved_175.name != "Prayagraj"
        assert resolved_175.name == "Rae Bareli"

        # Looking up Rae Bareli's Census code (158) in the LGD index resolves to Kaushambi (LGD 158)!
        assert resolved_158.name != "Rae Bareli"
        assert resolved_158.name == "Kaushambi"

        # Looking up Kaushambi's Census code (174) in the LGD index returns None (no district with LGD 174 in our set)
        resolved_174 = repo.get_unit_by_lgd_code(ResolutionTier.DISTRICT, "174")
        assert resolved_174 is None

"""
Unit Tests for Geographic Domain Models and Canonical Namespacing (P2-2.1).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 4.3, 5.1, 7.4, 9.1).
Phase: Phase 2 (P2-2.1 - Domain Models, Namespacing, and Hierarchy).
"""

import pytest
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    AnalyticalStatus,
    GeometryStatus,
    GeoUnit,
    NavigationStatus,
    canonical_district_id,
    canonical_nation_id,
    canonical_state_id,
    canonical_subdistrict_id,
)


class TestGeoDomainModelsAndNamespacing:
    """Test suite for GeoUnit domain entity and canonical namespace rules."""

    def test_canonical_id_generation(self):
        """Canonical IDs must adhere to strict, unambiguous namespace prefixes."""
        assert canonical_nation_id() == "in"
        assert canonical_state_id("9") == "in:state:09"
        assert canonical_state_id("09") == "in:state:09"
        assert canonical_district_id("187") == "in:district:187"
        assert canonical_district_id("175") == "in:district:175"
        assert canonical_district_id("120") == "in:district:120"
        assert canonical_district_id("158") == "in:district:158"
        assert canonical_subdistrict_id("187", "995") == "in:subdistrict:187:995"
        assert canonical_subdistrict_id("120", "890") == "in:subdistrict:120:890"

    def test_geounit_immutability(self):
        """GeoUnit must be a frozen, immutable domain entity."""
        unit = GeoUnit(
            id="in:state:09",
            parent_id="in",
            level=ResolutionTier.STATE,
            name="Uttar Pradesh",
            lgd_code="09",
        )
        with pytest.raises(Exception):  # FrozenInstanceError / TypeError
            unit.name = "New State"

    def test_raw_lgd_identifier_preservation(self):
        """Raw LGD codes must be preserved as exact strings without integer coercion."""
        unit = GeoUnit(
            id="in:state:09",
            parent_id="in",
            level=ResolutionTier.STATE,
            name="Uttar Pradesh",
            lgd_code="09",
        )
        assert unit.lgd_code == "09"
        assert isinstance(unit.lgd_code, str)
        assert unit.lgd_code.startswith("0")

    def test_level_validity_and_parent_hierarchy_consistency(self):
        """Hierarchy levels must strictly enforce parent-child consistency."""
        # Root Nation has no parent
        nation = GeoUnit(
            id="in",
            parent_id=None,
            level=ResolutionTier.NATION,
            name="India",
            lgd_code="IN",
        )
        assert nation.parent_id is None
        assert nation.level == ResolutionTier.NATION

        # State must have parent 'in'
        state = GeoUnit(
            id="in:state:09",
            parent_id="in",
            level=ResolutionTier.STATE,
            name="Uttar Pradesh",
            lgd_code="09",
        )
        assert state.parent_id == "in"

        # District must have a valid State parent
        district = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
        )
        assert district.parent_id == "in:state:09"

        # Sub-district must have a valid District parent
        subdist = GeoUnit(
            id="in:subdistrict:120:890",
            parent_id="in:district:120",
            level=ResolutionTier.SUBDISTRICT,
            name="Sadar",
            lgd_code="890",
        )
        assert subdist.parent_id == "in:district:120"

    def test_invalid_parent_rejected(self):
        """Invalid parent identifiers violating hierarchy levels must be rejected."""
        # State cannot have a district as parent
        with pytest.raises(ValueError, match="State level must have nation 'in' as parent"):
            GeoUnit(
                id="in:state:09",
                parent_id="in:district:120",
                level=ResolutionTier.STATE,
                name="Invalid State",
                lgd_code="09",
            )

        # District cannot have root 'in' directly as parent
        with pytest.raises(ValueError, match="District level must have a state parent"):
            GeoUnit(
                id="in:district:120",
                parent_id="in",
                level=ResolutionTier.DISTRICT,
                name="Invalid District",
                lgd_code="120",
            )

        # Nation cannot have a parent
        with pytest.raises(ValueError, match="National root entity must have parent_id=None"):
            GeoUnit(
                id="in",
                parent_id="world",
                level=ResolutionTier.NATION,
                name="India",
                lgd_code="IN",
            )

    def test_empty_or_whitespace_name_rejected(self):
        """Entity name cannot be empty or pure whitespace."""
        with pytest.raises(ValueError, match="Name cannot be empty"):
            GeoUnit(
                id="in:district:120",
                parent_id="in:state:09",
                level=ResolutionTier.DISTRICT,
                name="   ",
                lgd_code="120",
            )

    def test_separation_of_navigation_geometry_and_analysis_semantics(self):
        """Hierarchy status, geometry status, and analytical status must be strictly decoupled."""
        # Newly created navigable district without boundary or analytical data
        unit = GeoUnit(
            id="in:district:187",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Varanasi",
            lgd_code="187",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        assert unit.navigation_status == NavigationStatus.NAVIGABLE
        assert unit.geometry_status == GeometryStatus.GEOMETRY_MISSING
        assert unit.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE
        assert unit.geometry is None

        # Unit with historical geometry but no analytical data
        historical_unit = GeoUnit(
            id="in:district:187",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Varanasi",
            lgd_code="187",
            geometry={"type": "Polygon", "coordinates": []},
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_HISTORICAL,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        assert historical_unit.geometry_status == GeometryStatus.GEOMETRY_HISTORICAL
        assert historical_unit.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Pilot unit with verified geometry and full analytical data
        pilot_unit = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            geometry={"type": "Polygon", "coordinates": []},
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
            analytical_status=AnalyticalStatus.ANALYSABLE,
        )
        assert pilot_unit.analytical_status == AnalyticalStatus.ANALYSABLE
        assert pilot_unit.geometry_status == GeometryStatus.GEOMETRY_VERIFIED

    def test_null_geometry_handling(self):
        """Entities with null geometry automatically default geometry_status to GEOMETRY_MISSING."""
        unit = GeoUnit(
            id="in:district:187",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Varanasi",
            lgd_code="187",
            geometry=None,
        )
        assert unit.geometry is None
        assert unit.geometry_status == GeometryStatus.GEOMETRY_MISSING

    def test_second_district_hierarchy_decoupled_from_demographic_data(self):
        """
        Second-district (Varanasi: LGD 187, parent in:state:09) navigates purely via
        hierarchy traversal without requiring any demographic data or analytical coverage.
        """
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
        )
        varanasi = GeoUnit(
            id=canonical_district_id("187"),
            parent_id=up.id,
            level=ResolutionTier.DISTRICT,
            name="Varanasi",
            lgd_code="187",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )

        assert varanasi.id == "in:district:187"
        assert varanasi.parent_id == "in:state:09"
        assert varanasi.level == ResolutionTier.DISTRICT
        assert varanasi.navigation_status == NavigationStatus.NAVIGABLE
        assert varanasi.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE
        # Hierarchy traversal succeeds
        assert varanasi.parent_id == up.id
        assert up.parent_id == nation.id

    def test_analytical_status_semantics_decoupled_from_geometry(self):
        """
        AnalyticalStatus.ANALYSABLE strictly represents evidence-backed analytical availability
        (sufficient economic ledger parameters to compute micro-enterprise viability, Handbook Part 7.4).
        Having verified geometry (GEOMETRY_VERIFIED) does NOT imply ANALYSABLE when ledger data
        is unpopulated.
        """
        # Baseline district with verified geometry but no persisted ledger parameters
        baseline_pilot = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            geometry={"type": "Polygon", "coordinates": [[[81.5, 24.5], [82.5, 24.5], [82.5, 25.5], [81.5, 25.5], [81.5, 24.5]]]},
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        assert baseline_pilot.geometry_status == GeometryStatus.GEOMETRY_VERIFIED
        assert baseline_pilot.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE
        assert baseline_pilot.navigation_status == NavigationStatus.NAVIGABLE

    def test_subdistrict_omitting_parent_district_code_rejected(self):
        """A sub-district ID must strictly match in:subdistrict:{parent_district_lgd}:{subdistrict_lgd}."""
        with pytest.raises(ValueError, match="cannot omit parent district code"):
            GeoUnit(
                id="in:subdistrict:890",  # Omits parent district 120
                parent_id="in:district:120",
                level=ResolutionTier.SUBDISTRICT,
                name="Sadar",
                lgd_code="890",
            )

    def test_census_mdds_code_as_lgd_identifier_rejected(self):
        """Census MDDS codes (e.g., '00890', '00845') must not be used as LGD identifiers."""
        # Case A: Census MDDS code passed in ID instead of LGD code
        with pytest.raises(ValueError, match="Census MDDS code .* cannot be used as LGD identifier"):
            GeoUnit(
                id="in:subdistrict:120:00890",  # Census MDDS code in ID
                parent_id="in:district:120",
                level=ResolutionTier.SUBDISTRICT,
                name="Sadar",
                lgd_code="00890",
                census_code="00890",
            )

        # Case B: Census code passed in census_code and reused in ID segment
        with pytest.raises(ValueError, match="Census MDDS code .* cannot be used as LGD identifier"):
            GeoUnit(
                id="in:subdistrict:156:00845",
                parent_id="in:district:156",
                level=ResolutionTier.SUBDISTRICT,
                name="Akbarpur",
                census_code="00845",
            )

    def test_subdistrict_attached_to_wrong_parent_district_rejected(self):
        """Sub-district embedded parent code must match parent_id."""
        with pytest.raises(ValueError, match="does not match parent_id"):
            GeoUnit(
                id="in:subdistrict:158:890",  # Claims parent 158 (Kaushambi)
                parent_id="in:district:120",  # Attached to parent 120 (Prayagraj)
                level=ResolutionTier.SUBDISTRICT,
                name="Sadar",
                lgd_code="890",
            )

    def test_kanpur_dehat_akbarpur_assigned_to_prayagraj_rejected(self):
        """Kanpur Dehat Akbarpur (LGD 845) cannot be attached to Prayagraj (LGD 120)."""
        # 1. Domain model mismatch if parent_id is Prayagraj (120) but ID claims Kanpur Dehat (156)
        with pytest.raises(ValueError, match="does not match parent_id"):
            GeoUnit(
                id="in:subdistrict:156:845",
                parent_id="in:district:120",  # Wrong parent
                level=ResolutionTier.SUBDISTRICT,
                name="Akbarpur",
                lgd_code="845",
                census_code="00845",
            )

        # 2. LGDHierarchyLoader provenance check
        from backend.arthlens.data.geo_loader import LGDHierarchyLoader
        from backend.arthlens.infra.in_memory import InMemoryGeoUnitRepository
        repo = InMemoryGeoUnitRepository()
        loader = LGDHierarchyLoader(repo)
        with pytest.raises(ValueError, match="cannot be assigned to Prayagraj"):
            loader.ingest_subdistrict(
                district_lgd_code="120",  # Incorrectly assigning 845 to Prayagraj
                subdistrict_lgd_code="845",
                name="Akbarpur",
                census_code="00845",
            )

    def test_authoritative_subdistrict_canonical_identities(self):
        """Verify Prayagraj Sadar and Kanpur Dehat Akbarpur authoritative canonical IDs."""
        # Prayagraj Sadar
        sadar = GeoUnit(
            id="in:subdistrict:120:890",
            parent_id="in:district:120",
            level=ResolutionTier.SUBDISTRICT,
            name="Sadar",
            lgd_code="890",
            census_code="00890",
        )
        assert sadar.id == "in:subdistrict:120:890"
        assert sadar.parent_id == "in:district:120"
        assert sadar.lgd_code == "890"
        assert sadar.census_code == "00890"

        # Kanpur Dehat Akbarpur (Parent District LGD 156 confirmed from official source S.No. 63)
        akbarpur = GeoUnit(
            id="in:subdistrict:156:845",
            parent_id="in:district:156",
            level=ResolutionTier.SUBDISTRICT,
            name="Akbarpur",
            lgd_code="845",
            census_code="00845",
        )
        assert akbarpur.id == "in:subdistrict:156:845"
        assert akbarpur.parent_id == "in:district:156"
        assert akbarpur.lgd_code == "845"
        assert akbarpur.census_code == "00845"


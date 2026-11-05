"""
Unit Tests for Geographic Completeness, Decoupling, and Multi-Indicator Quality (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5 Step 10, Part 10.2).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

import pytest

from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import AnalyticalStatus, GeometryStatus, GeoUnit, NavigationStatus
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.evaluator import DataQualityEvaluator
from backend.arthlens.quality.vocabulary import CalculationSuitability, QualityStatus


class TestGeographicQualityAndDecoupling:
    """Tests evaluating geographic quality nuances and independence from geometry/navigation."""

    @pytest.fixture
    def evaluator(self):
        return DataQualityEvaluator(evaluation_date="2026-11-06")

    def test_different_quality_states_for_different_indicators_in_one_district(self, evaluator):
        """
        A single district (Prayagraj 'in:district:120') can simultaneously hold
        different quality statuses across different indicators.
        """
        prayagraj = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            census_code="175",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )

        quantities = [
            # Indicator 1: Population -> STALE (Census 2011, as_of 2011-03-01)
            Quantity(
                id="q_pop",
                definition_key="population.total",
                value=5954391.0,
                unit="persons",
                kind=Kind.OBSERVED,
                evidence_floor=4,
                geo_unit_id=prayagraj.id,
                resolution=2,
                as_of="2011-03-01",
                source_refs=("DS-05",),
                quality_flags=frozenset({"STALE"}),
            ),
            # Indicator 2: Commercial POIs -> CURRENT (OSM, as_of 2026-10-01)
            Quantity(
                id="q_poi",
                definition_key="pois.commercial",
                value=142.0,
                unit="dimensionless",
                kind=Kind.OBSERVED,
                evidence_floor=4,
                geo_unit_id=prayagraj.id,
                resolution=2,
                as_of="2026-10-01",
                source_refs=("DS-04",),
            ),
            # Indicator 3: Micro-enterprise Demand -> ESTIMATED (Modelled projection)
            Quantity(
                id="q_demand",
                definition_key="demand.monthly",
                value=125000.0,
                unit="INR/month",
                kind=Kind.ESTIMATED,
                evidence_floor=2,
                geo_unit_id=prayagraj.id,
                resolution=2,
                as_of="2026-10-01",
            ),
            # Indicator 4: Soil fertility index -> NOT in list (UNAVAILABLE)
        ]

        target_indicators = [
            "population.total",
            "pois.commercial",
            "demand.monthly",
            "agriculture.soil_fertility_index",
        ]

        # Register documented static fixture policy for DS-04 (90 days, per ds-04-osm.md line 42)
        from backend.arthlens.quality.freshness import FreshnessPolicy, FreshnessRegistry
        FreshnessRegistry.register_policy(FreshnessPolicy("DS-04", "OSM Static Fixtures", 90))
        try:
            suite = evaluator.evaluate_geo_unit_indicators(
                geo_unit=prayagraj,
                quantities=quantities,
                target_indicators=target_indicators,
            )

            # 1. Population is STALE (Orange #F97316)
            assert suite["population.total"].primary_status == QualityStatus.STALE
            assert suite["population.total"].shading.hex_color == "#F97316"
            assert suite["population.total"].suitability == CalculationSuitability.SUITABLE_HISTORICAL_ONLY

            # 2. POIs is CURRENT (Green #22C55E)
            assert suite["pois.commercial"].primary_status == QualityStatus.CURRENT
            assert suite["pois.commercial"].shading.hex_color == "#22C55E"
            assert suite["pois.commercial"].suitability == CalculationSuitability.SUITABLE_CURRENT

            # 3. Demand is ESTIMATED (Blue #3B82F6)
            assert suite["demand.monthly"].primary_status == QualityStatus.ESTIMATED
            assert suite["demand.monthly"].shading.hex_color == "#3B82F6"
            assert suite["demand.monthly"].suitability == CalculationSuitability.ESTIMATED_PROJECTION

            # 4. Soil index is UNAVAILABLE (Gray #94A3B8)
            assert suite["agriculture.soil_fertility_index"].primary_status == QualityStatus.UNAVAILABLE
            assert suite["agriculture.soil_fertility_index"].value is None
            assert suite["agriculture.soil_fertility_index"].shading.hex_color == "#94A3B8"
            assert suite["agriculture.soil_fertility_index"].suitability == CalculationSuitability.UNSUITABLE_MISSING
        finally:
            FreshnessRegistry.reset_defaults()

    def test_navigation_status_does_not_overwrite_quality(self, evaluator):
        """
        Being marked NAVIGABLE across the 800-unit hierarchy does NOT mean data is CURRENT.
        A navigable district with no quantities is UNAVAILABLE.
        """
        district = GeoUnit(
            id="in:district:175",  # Rae Bareli
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Rae Bareli",
            lgd_code="175",
            navigation_status=NavigationStatus.NAVIGABLE,
            geometry_status=GeometryStatus.GEOMETRY_MISSING,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        assert district.navigation_status == NavigationStatus.NAVIGABLE

        # Evaluating missing indicator for navigable district
        res = evaluator.evaluate_quantity(None, "population.total", district.id)
        assert res.primary_status == QualityStatus.UNAVAILABLE
        assert res.shading.hex_color == "#94A3B8"
        assert res.value is None

    def test_geometry_validity_does_not_imply_analytical_or_fresh_status(self, evaluator):
        """
        Prayagraj has GEOMETRY_VERIFIED, but that does NOT make its 2011 census data fresh,
        nor does it automatically promote analytical_status to ANALYSABLE.
        """
        prayagraj = GeoUnit(
            id="in:district:120",
            parent_id="in:state:09",
            level=ResolutionTier.DISTRICT,
            name="Prayagraj",
            lgd_code="120",
            geometry={"type": "Polygon", "coordinates": [[[81.52, 24.78], [82.35, 24.78], [82.35, 25.79], [81.52, 25.79], [81.52, 24.78]]]},
            geometry_status=GeometryStatus.GEOMETRY_VERIFIED,
            analytical_status=AnalyticalStatus.ANALYSIS_UNAVAILABLE,
        )
        assert prayagraj.geometry_status == GeometryStatus.GEOMETRY_VERIFIED
        assert prayagraj.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

        # Census quantity is STALE
        stale_census = Quantity(
            id="q_census_120",
            definition_key="population.total",
            value=5954391.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id=prayagraj.id,
            resolution=2,
            as_of="2011-03-01",
            source_refs=("DS-05",),
            quality_flags=frozenset({"STALE"}),
        )
        assessment = evaluator.evaluate_quantity(stale_census, "population.total", prayagraj.id)
        assert assessment.primary_status == QualityStatus.STALE
        assert assessment.shading.hex_color == "#F97316"
        assert prayagraj.analytical_status == AnalyticalStatus.ANALYSIS_UNAVAILABLE

    def test_missing_nationwide_indicator_is_strictly_unavailable_not_zero(self, evaluator):
        """Unpopulated districts return UNAVAILABLE, never numeric 0 or 0.0."""
        for district_id in ["in:district:158", "in:district:187", "in:district:700"]:
            assessment = evaluator.evaluate_quantity(None, "unemployment_rate", district_id)
            assert assessment.primary_status == QualityStatus.UNAVAILABLE
            assert assessment.value is None
            assert assessment.value != 0
            assert assessment.value != 0.0

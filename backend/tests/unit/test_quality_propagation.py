"""
Unit Tests for Epistemic Ledger Quality Propagation and Calculation Gating (P2-3).

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.2, 4.4, 4.7, Part 7.4).
Phase: Phase 2 (P2-3 - Data-Quality Layer and Staleness Flags).
"""

import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.propagation import (
    CalculationQualityContext,
    GatedCalculationError,
    inspect_calculation_inputs,
)
from backend.arthlens.quality.vocabulary import CalculationSuitability, QualityStatus


class TestQualityPropagationAndCalculationGating:
    """Tests ensuring calculations inherit quality restrictions and fail closed on missing inputs."""

    def test_stale_parent_propagates_stale_ancestry_and_historical_restriction(self):
        """
        When a calculation depends on STALE historical data (e.g. Census 2011):
        - Context inherits 'STALE_ANCESTRY' flag.
        - Primary status is STALE.
        - Suitability is SUITABLE_HISTORICAL_ONLY.
        - Carries explicit restriction warning.
        """
        stale_census = Quantity(
            id="q_census_pop",
            definition_key="population.total",
            value=5954391.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2011-03-01",
            quality_flags=frozenset({"STALE"}),
        )
        fresh_param = Quantity(
            id="q_per_capita_spend",
            definition_key="market.per_capita_spend",
            value=1200.0,
            unit="INR/month",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
        )

        ctx = inspect_calculation_inputs(
            inputs=[stale_census, fresh_param],
            input_names=["population", "spend"],
        )

        assert ctx.primary_status == QualityStatus.STALE
        assert "STALE_ANCESTRY" in ctx.propagated_flags
        assert ctx.suitability == CalculationSuitability.SUITABLE_HISTORICAL_ONLY
        assert ctx.is_historically_restricted is True
        assert any("stale historical" in r.lower() for r in ctx.restriction_reasons)
        assert set(ctx.parent_ids) == {"q_census_pop", "q_per_capita_spend"}

    def test_missing_input_raises_gated_calculation_error_never_silent_zero(self):
        """
        Missing or unavailable input strictly gates the calculation.
        Never silently substitutes 0 or 0.0.
        """
        valid_q = Quantity(
            id="q_fixed_cost",
            definition_key="finance.fixed_cost",
            value=50000.0,
            unit="INR/month",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
        )

        # Second input is missing (None)
        with pytest.raises(GatedCalculationError) as exc_info:
            inspect_calculation_inputs(
                inputs=[valid_q, None],
                input_names=["fixed_cost", "variable_cost"],
            )

        err = exc_info.value
        assert "variable_cost" in err.missing_inputs
        assert "UNAVAILABLE" in str(err)
        assert "strictly forbids silently substituting numeric zero" in str(err)

    def test_estimated_parent_forces_estimated_context(self):
        """
        When a calculation uses an ESTIMATED parent input:
        - Downstream evidence floor is <= 2.
        - Primary status is ESTIMATED.
        - Cannot claim to be directly observed.
        """
        est_demand = Quantity(
            id="q_est_demand",
            definition_key="demand.projected",
            value=80000.0,
            unit="INR/month",
            kind=Kind.ESTIMATED,
            evidence_floor=2,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
        )
        observed_price = Quantity(
            id="q_unit_price",
            definition_key="product.unit_price",
            value=100.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-10-01",
        )

        ctx = inspect_calculation_inputs(
            inputs=[est_demand, observed_price],
            input_names=["demand", "price"],
        )

        assert ctx.primary_status == QualityStatus.ESTIMATED
        assert ctx.evidence_floor <= 2
        assert ctx.suitability == CalculationSuitability.ESTIMATED_PROJECTION
        assert ctx.is_estimated is True

    def test_multiple_parents_with_different_statuses_preserves_all_provenance(self):
        """
        Calculation with 3 inputs: fresh (CURRENT), stale (STALE), and estimated (ESTIMATED):
        - Primary status is STALE (by precedence STALE > ESTIMATED > CURRENT).
        - Propagated context captures both historical and estimation restrictions.
        - Minimum evidence floor is 2.
        - All 3 parent IDs are preserved.
        """
        q_fresh = Quantity(id="q1", definition_key="k1", value=1.0, unit="dim", kind=Kind.OBSERVED, evidence_floor=4, geo_unit_id="in:district:120", resolution=2, as_of="2026-10-01")
        q_stale = Quantity(id="q2", definition_key="k2", value=2.0, unit="dim", kind=Kind.OBSERVED, evidence_floor=4, geo_unit_id="in:district:120", resolution=2, as_of="2011-03-01", quality_flags=frozenset({"STALE"}))
        q_est = Quantity(id="q3", definition_key="k3", value=3.0, unit="dim", kind=Kind.ESTIMATED, evidence_floor=2, geo_unit_id="in:district:120", resolution=2, as_of="2026-10-01")

        ctx = inspect_calculation_inputs(inputs=[q_fresh, q_stale, q_est])

        assert ctx.primary_status == QualityStatus.STALE
        assert ctx.is_historically_restricted is True
        assert ctx.is_estimated is True
        assert ctx.evidence_floor == 2
        assert ctx.parent_ids == ["q1", "q2", "q3"]
        assert len(ctx.restriction_reasons) >= 2

"""
Unit tests for DownscalingRegistry.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 4.3, 6.2).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

import pytest
from backend.arthlens.ledger.downscaling import DownscalingRegistry, downscale


class TestDownscalingRegistry:
    """Validate DownscalingRegistry registration, execution, and rejection of unregistered methods."""

    def test_popweight_v1_registered_by_default(self):
        """popweight_v1 must be pre-registered per Handbook Section 4.3 and 6.2."""
        assert DownscalingRegistry.is_registered("popweight_v1")

    def test_unregistered_method_rejected(self):
        """Calling downscale with an unregistered method name must raise ValueError."""
        with pytest.raises(ValueError, match="Unregistered downscaling method"):
            downscale(method="unregistered_method_xyz", total=100.0, weights=[0.5, 0.5])

    def test_custom_downscaling_registration(self):
        """Custom downscaling methods can be registered and dispatched."""
        def uniform_downscaling(total, weights):
            n = len(weights)
            return [total / n] * n

        DownscalingRegistry.register("uniform_test_v1", uniform_downscaling)
        assert DownscalingRegistry.is_registered("uniform_test_v1")

        result = downscale("uniform_test_v1", 300.0, [1.0, 2.0, 3.0])
        assert result == [100.0, 100.0, 100.0]
        assert sum(result) == 300.0

    def test_popweight_v1_conserves_totals_and_handles_large_finite_weights(self):
        assert downscale("popweight_v1", 120.0, [1.0, 2.0, 3.0]) == pytest.approx(
            [20.0, 40.0, 60.0]
        )
        assert downscale("popweight_v1", 100.0, [1e308, 1e308]) == pytest.approx(
            [50.0, 50.0]
        )
        assert downscale("popweight_v1", 0.0, [0.0, 2.0]) == [0.0, 0.0]

    @pytest.mark.parametrize(
        ("total", "weights", "message"),
        [
            (1.0, [], "empty weights"),
            (1.0, [0.0, 0.0], "positive"),
            (1.0, [1.0, -1.0], "non-negative"),
            (1.0, [1.0, float("nan")], "non-negative"),
            (float("inf"), [1.0], "Total must be finite"),
            (-1.0, [1.0], "Total must be finite"),
        ],
    )
    def test_popweight_v1_rejects_invalid_inputs(self, total, weights, message):
        with pytest.raises(ValueError, match=message):
            downscale("popweight_v1", total, weights)

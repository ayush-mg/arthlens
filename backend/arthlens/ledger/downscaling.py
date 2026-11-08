"""
Downscaling methods and registry for spatial resolution refinement.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.3, 6.2).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

A derived quantity takes the coarsest parent resolution unless an explicitly
registered downscaling method is applied.
Registered downscaling methods must satisfy a conservation test:
sum(downscale(method, total, weights)) == total.
"""

from math import fsum, isfinite
from typing import Callable, Dict, List, Sequence


def _popweight_v1(total: float, weights: Sequence[float]) -> List[float]:
    """
    popweight_v1: population-weighted allocation of a coarse total to fine zones.

    Handbook Reference: Section 6.2:
        E_z = D_district * (pop_z * w_z) / sum over zones (pop_k * w_k)
    Conserves totals: sum(E_z) == D_district.
    """
    if len(weights) == 0:
        raise ValueError("Cannot downscale with empty weights list.")
    try:
        total_value = float(total)
        weight_values = [float(weight) for weight in weights]
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Total and downscaling weights must be numeric.") from exc
    if not isfinite(total_value) or total_value < 0:
        raise ValueError("Total must be finite and non-negative.")
    if any(not isfinite(weight) or weight < 0 for weight in weight_values):
        raise ValueError("Downscaling weights must be finite and non-negative.")
    scale = max(weight_values)
    if scale <= 0:
        raise ValueError("Sum of weights must be positive, got 0")
    scaled_weights = [weight / scale for weight in weight_values]
    total_weight = fsum(scaled_weights)
    allocations = [
        total_value * (weight / total_weight)
        for weight in scaled_weights
    ]
    largest_weight_index = max(range(len(scaled_weights)), key=scaled_weights.__getitem__)
    allocations[largest_weight_index] = total_value - fsum(
        allocation
        for index, allocation in enumerate(allocations)
        if index != largest_weight_index
    )
    return allocations


class DownscalingRegistry:
    """
    Registry for authoritative spatial downscaling algorithms.

    Handbook Reference: Section 4.3.
    Callers cannot claim a downscaling method exists merely by passing an arbitrary string.
    """
    _methods: Dict[str, Callable[[float, Sequence[float]], List[float]]] = {
        "popweight_v1": _popweight_v1,
    }

    @classmethod
    def register(cls, name: str, method_fn: Callable[[float, Sequence[float]], List[float]]) -> None:
        """Register a new downscaling method."""
        if not name or not isinstance(name, str):
            raise ValueError("Downscaling method name must be a non-empty string.")
        cls._methods[name] = method_fn

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a downscaling method is registered."""
        return name in cls._methods

    @classmethod
    def get(cls, name: str) -> Callable[[float, Sequence[float]], List[float]]:
        """Retrieve a registered downscaling method by name."""
        if name not in cls._methods:
            raise ValueError(
                f"Unregistered downscaling method: '{name}'. "
                f"Available methods: {list(cls._methods.keys())}"
            )
        return cls._methods[name]


def downscale(method: str, total: float, weights: Sequence[float]) -> List[float]:
    """
    Execute a registered downscaling method to partition a coarse total into fine zone values.

    Handbook Reference: Section 4.3, 4.7 bullet 2, Section 6.2.
    """
    fn = DownscalingRegistry.get(method)
    return fn(total, weights)

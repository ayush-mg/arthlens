"""
Downscaling methods and registry for spatial resolution refinement.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.3, 6.2).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

A derived quantity takes the coarsest parent resolution unless an explicitly
registered downscaling method is applied.
Registered downscaling methods must satisfy a conservation test:
sum(downscale(method, total, weights)) == total.
"""

from typing import Callable, Dict, List, Sequence


def _popweight_v1(total: float, weights: Sequence[float]) -> List[float]:
    """
    popweight_v1: population-weighted allocation of a coarse total to fine zones.

    Handbook Reference: Section 6.2:
        E_z = D_district * (pop_z * w_z) / sum over zones (pop_k * w_k)
    Conserves totals: sum(E_z) == D_district.
    """
    if not weights:
        raise ValueError("Cannot downscale with empty weights list.")
    total_weight = sum(weights)
    if total_weight <= 0:
        raise ValueError(f"Sum of weights must be positive, got {total_weight}")
    return [float(total * (w / total_weight)) for w in weights]


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

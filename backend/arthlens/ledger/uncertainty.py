"""
Uncertainty representation and arithmetic propagation rules.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

States:
- EXACT
- INTERVAL(lo, hi)
- DISTRIBUTION(name, params)
- SAMPLES(reference)
- UNQUANTIFIED

Combination rules:
1. UNQUANTIFIED is contagious: if any parent is UNQUANTIFIED, a deterministic child is UNQUANTIFIED.
2. EXACT with EXACT stays EXACT.
3. Interval arithmetic correctly contains possible results.
4. Division is rejected when the divisor interval includes zero.
"""

from typing import Any, Sequence, Tuple, Union


def _extract_interval(unc: Any) -> Tuple[float, float]:
    """Extract (lo, hi) from interval uncertainty representation."""
    if isinstance(unc, (tuple, list)):
        if unc[0] == "INTERVAL" and len(unc) == 3:
            return float(unc[1]), float(unc[2])
    raise ValueError(f"Expected ('INTERVAL', lo, hi), got {unc}")


def combine_uncertainty(
    parent_uncertainties: Sequence[Any],
    operation: str = "deterministic",
) -> Any:
    """
    Combine parent uncertainties through mathematical or deterministic operations.

    Handbook Reference: Section 4.4, 4.7 bullet 4.
    """
    if not parent_uncertainties:
        return "EXACT"

    # Rule 1: UNQUANTIFIED is contagious
    for u in parent_uncertainties:
        if u == "UNQUANTIFIED":
            return "UNQUANTIFIED"

    # Rule 2: EXACT with EXACT stays EXACT
    if all(u == "EXACT" for u in parent_uncertainties):
        return "EXACT"

    # Interval arithmetic operations
    op = operation.lower()
    if op in ("add", "subtract", "multiply", "divide"):
        if len(parent_uncertainties) != 2:
            raise ValueError(f"Operation '{op}' requires exactly two parent uncertainties, got {len(parent_uncertainties)}")

        u_a = parent_uncertainties[0]
        u_b = parent_uncertainties[1]

        # Convert EXACT to degenerate interval if needed
        a_lo, a_hi = _extract_interval(u_a)
        b_lo, b_hi = _extract_interval(u_b)

        if op == "add":
            return ("INTERVAL", a_lo + b_lo, a_hi + b_hi)
        elif op == "subtract":
            return ("INTERVAL", a_lo - b_hi, a_hi - b_lo)
        elif op == "multiply":
            prods = [a_lo * b_lo, a_lo * b_hi, a_hi * b_lo, a_hi * b_hi]
            return ("INTERVAL", min(prods), max(prods))
        elif op == "divide":
            # Rule 4: Division only when divisor interval excludes zero
            if b_lo <= 0 <= b_hi:
                raise ZeroDivisionError(
                    f"Interval division rejected: divisor interval [{b_lo}, {b_hi}] contains zero (Handbook 4.4)."
                )
            divs = [a_lo / b_lo, a_lo / b_hi, a_hi / b_lo, a_hi / b_hi]
            return ("INTERVAL", min(divs), max(divs))

    # General deterministic propagation
    if op == "deterministic":
        # If any input is an interval or distribution, preserve uncertainty without collapsing to EXACT
        has_interval = any(isinstance(u, (tuple, list)) and u[0] == "INTERVAL" for u in parent_uncertainties)
        if has_interval and len(parent_uncertainties) == 1:
            return parent_uncertainties[0]
        return "EXACT"

    raise ValueError(f"Unsupported operation for uncertainty combination: '{operation}'")

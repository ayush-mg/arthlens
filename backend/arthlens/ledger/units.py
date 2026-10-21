"""
Pint-based unit configuration and dimensional compatibility checking.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.1, 4.5, 4.7).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

Custom definitions include currency (INR, rupee) and headcount (persons).
"""

from typing import Sequence
import pint
from pint.errors import DimensionalityError, UndefinedUnitError


def _create_unit_registry() -> pint.UnitRegistry:
    """Initialize Pint UnitRegistry with domain units."""
    registry = pint.UnitRegistry()
    registry.define("INR = [currency]")
    registry.define("rupee = INR")
    registry.define("rupees = INR")
    registry.define("person = [headcount]")
    registry.define("persons = person")
    registry.define("lakh = 100000")
    registry.define("crore = 10000000")
    return registry


_UREG = _create_unit_registry()


def get_unit_registry() -> pint.UnitRegistry:
    """Get the authoritative Pint UnitRegistry."""
    return _UREG


def check_unit_compatibility(operation: str, units: Sequence[str]) -> bool:
    """
    Check dimensional compatibility of units for an arithmetic operation.

    Handbook Reference: Section 4.5 (V6 UnitCompatibilitySpec), 4.7 bullet 5.
    Raises:
        DimensionalityError (inherits from ValueError): When units are dimensionally incompatible.
        ValueError: When operation is unsupported or units are invalid.
    """
    if not units:
        raise ValueError("Cannot check compatibility for an empty units sequence.")

    op = operation.lower()
    ureg = get_unit_registry()

    # Parse and validate unit expressions
    parsed_units = []
    for u in units:
        try:
            parsed = ureg.parse_units(u)
            parsed_units.append(parsed)
        except (UndefinedUnitError, Exception) as e:
            raise ValueError(f"Invalid unit definition: '{u}'") from e

    if op in ("add", "subtract"):
        if len(parsed_units) < 2:
            return True
        first = parsed_units[0]
        first_dim = ureg.get_dimensionality(first)
        for other in parsed_units[1:]:
            other_dim = ureg.get_dimensionality(other)
            if first_dim != other_dim:
                # Raise Pint's DimensionalityError (which subclasses ValueError)
                raise DimensionalityError(first, other, first_dim, other_dim)
        return True

    elif op in ("multiply", "divide"):
        # Multiplication and division of valid Pint units produce compound units
        # Check that operations are well-defined
        acc = ureg.Quantity(1.0, parsed_units[0])
        for other in parsed_units[1:]:
            if op == "multiply":
                acc = acc * ureg.Quantity(1.0, other)
            else:
                acc = acc / ureg.Quantity(1.0, other)
        return True

    raise ValueError(f"Unsupported operation for unit check: '{operation}'")

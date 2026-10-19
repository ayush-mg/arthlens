"""
Unit tests for Epistemic Ledger invariants.

Handbook reference: Section 4.1, 4.4, 4.5, 4.7 (required tests, write first)
Task: P0-5
Phase: 0 (tests only; implementation is P1-3)

Covers:
    - Incompatible unit combinations rejected (Handbook 4.5 / V6 UnitCompatibilitySpec)
    - STALE quality flag appears and propagates (Handbook 4.4)
    - Quantity records are immutable (Handbook 4.1, 5.1 @dataclass(frozen=True))

Dependencies:
    - pytest (test runner)
    - backend.arthlens.domain.enums (Kind enum) — P1-2
    - backend.arthlens.domain.quantity (Quantity dataclass) — P1-3
    - backend.arthlens.ledger (Ledger, units, propagation) — P1-3

Each test fails explicitly with a BLOCKED message when the production
implementation is not yet available (TDD red-stage contract).
"""

from dataclasses import FrozenInstanceError
import pytest

# ---------------------------------------------------------------------------
# Production implementation availability
# ---------------------------------------------------------------------------

try:
    from backend.arthlens.domain.enums import Kind
    from backend.arthlens.domain.quantity import Quantity
    _DOMAIN_AVAILABLE = True
except ImportError:
    _DOMAIN_AVAILABLE = False

try:
    from backend.arthlens.ledger.ledger import Ledger
    from backend.arthlens.ledger.units import check_unit_compatibility
    from backend.arthlens.ledger.propagation import propagate_quality_flags
    _LEDGER_AVAILABLE = True
except ImportError:
    _LEDGER_AVAILABLE = False

_IMPL_AVAILABLE = _DOMAIN_AVAILABLE and _LEDGER_AVAILABLE


def _require_implementation():
    """Fail explicitly if ledger implementation is not available."""
    if not _DOMAIN_AVAILABLE:
        pytest.fail(
            "BLOCKED: backend.arthlens.domain not available. "
            "Kind enum and Quantity dataclass are implemented in P1-2/P1-3."
        )
    if not _LEDGER_AVAILABLE:
        pytest.fail(
            "BLOCKED: backend.arthlens.ledger not available. "
            "Ledger, units, and propagation modules are implemented in P1-3."
        )


# ===================================================================
# UNIT COMPATIBILITY: incompatible units rejected
# Handbook 4.5 (V6 UnitCompatibilitySpec) / 4.7 bullet 5
# ===================================================================

class TestUnitCompatibility:
    """
    Handbook 4.5 (V6) / 4.7:
    'Operations require compatible Pint units.'
    'Unit tests: invalid unit combinations rejected.'

    Unit compatibility testing is strictly separated from arithmetic safety
    (e.g., zero divisor checks are handled under interval uncertainty).
    """

    def test_adding_compatible_units_accepted(self):
        """Adding INR + INR should succeed."""
        _require_implementation()

        result = check_unit_compatibility(
            operation="add",
            units=["INR", "INR"],
        )
        assert result is True, "Adding INR + INR should be compatible"

    def test_adding_incompatible_units_rejected(self):
        """
        Adding INR + kg must be rejected.
        Expects ValueError or Pint DimensionalityError (which inherits from ValueError).
        No custom exception class is invented ahead of production implementation.
        """
        _require_implementation()

        with pytest.raises((ValueError, TypeError)) as exc_info:
            check_unit_compatibility(
                operation="add",
                units=["INR", "kg"],
            )
        assert "INR" in str(exc_info.value) or "kg" in str(exc_info.value)

    def test_multiplication_produces_compound_unit(self):
        """Multiplying INR/kg * kg should produce INR."""
        _require_implementation()

        result = check_unit_compatibility(
            operation="multiply",
            units=["INR/kg", "kg"],
        )
        assert result is True, "INR/kg * kg should be valid (produces INR)"

    def test_compatible_division_units_accepted(self):
        """
        Dividing INR by INR is dimensionally compatible (produces dimensionless).
        Note: Value-level zero-divisor checks are tested separately in interval arithmetic.
        """
        _require_implementation()

        result = check_unit_compatibility(
            operation="divide",
            units=["INR", "INR"],
        )
        assert result is True, "INR / INR should be dimensionally valid"

    def test_adding_inr_to_inr_per_month_rejected(self):
        """
        INR + INR/month are dimensionally incompatible for addition.
        Expects ValueError or Pint DimensionalityError (inherits from ValueError).
        """
        _require_implementation()

        with pytest.raises((ValueError, TypeError)):
            check_unit_compatibility(
                operation="add",
                units=["INR", "INR/month"],
            )


# ===================================================================
# STALE FLAG: appears and propagates
# Handbook 4.4 / 4.7 bullet 5
# ===================================================================

class TestStaleFlagPropagation:
    """
    Handbook 4.4 / 4.7:
    'Each source has a configured maximum age. Beyond it the quantity
    gets the STALE flag; derived quantities inherit STALE.'
    """

    def test_stale_parent_propagates_to_child(self):
        """A derived quantity with a STALE parent must also be STALE."""
        _require_implementation()

        parent_flags = [frozenset({"STALE"}), frozenset()]
        result = propagate_quality_flags(parent_flags)
        assert "STALE" in result, (
            f"STALE must propagate from parent to child; got {result}"
        )

    def test_no_stale_parents_no_stale_child(self):
        """If no parents are STALE, the child should not inherit STALE."""
        _require_implementation()

        parent_flags = [frozenset(), frozenset({"LOW_COVERAGE"})]
        result = propagate_quality_flags(parent_flags)
        assert "STALE" not in result, (
            f"Child should not be STALE without STALE parents; got {result}"
        )

    def test_multiple_stale_parents(self):
        """Multiple STALE parents still produce one STALE flag (not duplicated)."""
        _require_implementation()

        parent_flags = [
            frozenset({"STALE"}),
            frozenset({"STALE", "INCOMPLETE_SOURCE"}),
        ]
        result = propagate_quality_flags(parent_flags)
        assert "STALE" in result
        assert isinstance(result, frozenset), (
            f"Quality flags should be a frozenset, got {type(result)}"
        )

    def test_other_flags_also_propagate(self):
        """
        INCOMPLETE_SOURCE and other quality flags should also propagate
        from parents to derived quantities (Handbook 4.1 field 12).
        """
        _require_implementation()

        parent_flags = [
            frozenset({"INCOMPLETE_SOURCE"}),
            frozenset({"LOW_COVERAGE"}),
        ]
        result = propagate_quality_flags(parent_flags)
        assert "INCOMPLETE_SOURCE" in result
        assert "LOW_COVERAGE" in result


# ===================================================================
# QUANTITY IMMUTABILITY
# Handbook 4.1 / 5.1: @dataclass(frozen=True)
# ===================================================================

class TestQuantityImmutability:
    """
    Handbook 4.1 / 5.1:
    Quantity is defined as @dataclass(frozen=True) with 15 explicit fields:
        id, definition_key, value, unit, kind, evidence_floor, geo_unit_id,
        resolution, as_of, uncertainty, source_refs, method_id, model_version,
        parent_ids, quality_flags, license_meta.
    Once registered, a Quantity record must not be modified.
    """

    def test_quantity_fields_are_frozen(self):
        """
        Attempting to modify any Quantity field must raise FrozenInstanceError
        (standard Python dataclasses error inheriting from AttributeError).
        """
        _require_implementation()

        q = Quantity(
            id="q_imm_001",
            definition_key="test.immutable",
            value=42.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="direct_observation",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )

        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.value = 99.0

        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.kind = Kind.ESTIMATED

        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.evidence_floor = 1

    def test_registered_quantity_not_modifiable(self):
        """
        Once registered in the ledger, retrieving a quantity must
        return an immutable record that rejects in-place attribute mutation.
        """
        _require_implementation()

        ledger = Ledger()
        q = Quantity(
            id="q_reg_001",
            definition_key="test.registered",
            value=55.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_002",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="census_ingest",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        q_id = ledger.register(q)
        retrieved = ledger.get(q_id)

        with pytest.raises((FrozenInstanceError, AttributeError)):
            retrieved.value = 0.0

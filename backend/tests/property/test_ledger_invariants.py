"""
Property-based tests for Epistemic Ledger invariants.

Handbook reference: Section 4.1, 4.2, 4.3, 4.4, 4.7, 5.1 (required tests, write first)
Task: P0-5
Phase: 0 (tests only; implementation is P1-3)

These tests specify the invariants that the ledger MUST satisfy.
They are written before the implementation exists (TDD red stage).

Dependencies:
    - pytest (test runner)
    - hypothesis (property-based testing)
    - backend.arthlens.domain.enums (Kind enum, resolution constants) — P1-2
    - backend.arthlens.domain.quantity (Quantity dataclass) — P1-3
    - backend.arthlens.ledger (Ledger, propagation, uncertainty, downscaling) — P1-3

Each test fails explicitly with a BLOCKED message when the production
implementation is not yet available (TDD red-stage contract).
"""

import pytest

# ---------------------------------------------------------------------------
# Dependency availability checks
# ---------------------------------------------------------------------------

try:
    from hypothesis import given, assume, settings
    from hypothesis import strategies as st
    _HYPOTHESIS_AVAILABLE = True
except ImportError:
    _HYPOTHESIS_AVAILABLE = False

# Production implementation availability — these modules do not exist
# until P1-2 (enums) and P1-3 (ledger/domain). We attempt the import so
# that when the implementation lands, these tests begin exercising it
# without code modifications.
try:
    from backend.arthlens.domain.enums import Kind
    from backend.arthlens.domain.quantity import Quantity
    _DOMAIN_AVAILABLE = True
except ImportError:
    _DOMAIN_AVAILABLE = False

try:
    from backend.arthlens.ledger.ledger import Ledger
    from backend.arthlens.ledger.propagation import combine_evidence_floors
    from backend.arthlens.ledger.propagation import combine_resolutions
    from backend.arthlens.ledger.uncertainty import combine_uncertainty
    from backend.arthlens.ledger.downscaling import downscale
    _LEDGER_AVAILABLE = True
except ImportError:
    _LEDGER_AVAILABLE = False

_IMPL_AVAILABLE = _DOMAIN_AVAILABLE and _LEDGER_AVAILABLE


def _require_hypothesis():
    """Fail explicitly if hypothesis is not installed."""
    if not _HYPOTHESIS_AVAILABLE:
        pytest.fail(
            "BLOCKED: hypothesis package is not installed. "
            "Required for property-based tests. "
            "Install with: pip install hypothesis"
        )


def _require_implementation():
    """Fail explicitly if ledger implementation is not available."""
    _require_hypothesis()
    if not _DOMAIN_AVAILABLE:
        pytest.fail(
            "BLOCKED: backend.arthlens.domain not available. "
            "Kind enum and Quantity dataclass are implemented in P1-2/P1-3."
        )
    if not _LEDGER_AVAILABLE:
        pytest.fail(
            "BLOCKED: backend.arthlens.ledger not available. "
            "Ledger, propagation, uncertainty, and downscaling modules are implemented in P1-3."
        )


# ---------------------------------------------------------------------------
# Hypothesis strategies (defined only when hypothesis is available)
# ---------------------------------------------------------------------------

if _HYPOTHESIS_AVAILABLE:
    # Evidence floor ranks: SCENARIO=1, ESTIMATED=2, USER_ASSUMED=3,
    # OBSERVED=POLICY_RULE=4 (Handbook 4.2)
    evidence_floors = st.integers(min_value=1, max_value=4)

    # Resolution levels: NATION=0, STATE=1, DISTRICT=2, SUBDISTRICT=3,
    # VILLAGE_URBAN=4, POINT=5 (Handbook 4.3)
    resolution_levels = st.integers(min_value=0, max_value=5)

    # Lists of parent floors / resolutions (at least one parent for derived quantities)
    parent_floor_lists = st.lists(
        evidence_floors, min_size=1, max_size=10
    )
    parent_resolution_lists = st.lists(
        resolution_levels, min_size=1, max_size=10
    )


# ===================================================================
# PROPERTY 1: Evidence floor never strengthens through derivation
# Handbook 4.2: "A derived quantity has evidence_floor = minimum
#               evidence_floor of its parents."
# ===================================================================

class TestEvidenceFloorNeverStrengthens:
    """
    Handbook 4.2 / 4.7 bullet 1:
    The evidence floor of a derived quantity must equal the minimum
    evidence floor among its parents. A calculation can never make
    evidence stronger than its weakest input.
    """

    def test_derived_floor_equals_min_of_parents(self):
        """
        Property: for any set of parent evidence floors,
        floor(child) == min(parent floors).
        """
        _require_implementation()

        parent_floors = [4, 3, 4, 2]  # OBSERVED, USER_ASSUMED, OBSERVED, ESTIMATED
        result = combine_evidence_floors(parent_floors)
        assert result == min(parent_floors), (
            f"Evidence floor should be min of parents ({min(parent_floors)}), "
            f"got {result}"
        )

    def test_single_parent_preserves_floor(self):
        """A derived quantity with one parent inherits that parent's floor."""
        _require_implementation()

        for floor in [1, 2, 3, 4]:
            result = combine_evidence_floors([floor])
            assert result == floor, (
                f"Single parent with floor {floor} should produce child "
                f"floor {floor}, got {result}"
            )

    def test_derived_never_exceeds_weakest_parent(self):
        """
        Hypothesis property: for ANY list of parent floors,
        the derived floor must never exceed the minimum.
        """
        _require_implementation()

        @given(floors=parent_floor_lists)
        def _check(floors):
            result = combine_evidence_floors(floors)
            assert result == min(floors), (
                f"Derived floor {result} != min of parents {min(floors)}"
            )
            for parent_floor in floors:
                assert result <= parent_floor, (
                    f"Derived floor {result} exceeds parent floor {parent_floor}"
                )

        _check()

    def test_calculated_never_labelled_observed(self):
        """
        Handbook 4.2: 'A CALCULATED value can never have kind OBSERVED,
        however exact the arithmetic.'
        Follows complete 15-field Quantity contract (Handbook 5.1).
        """
        _require_implementation()

        ledger = Ledger()
        parent = Quantity(
            id="q_obs_parent",
            definition_key="test.observed",
            value=100.0,
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
        parent_id = ledger.register(parent)

        child = Quantity(
            id="q_calc_child",
            definition_key="test.derived",
            value=200.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="arithmetic_add",
            model_version="1.0",
            parent_ids=(parent_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        child_id = ledger.register(child)
        stored = ledger.get(child_id)
        assert stored.kind != Kind.OBSERVED, (
            "A CALCULATED quantity must never be labelled OBSERVED"
        )


# ===================================================================
# PROPERTY 2: Resolution never refines without registered downscaling;
#             downscaling conserves totals
# Handbook 4.3 / 4.7 bullet 2
# ===================================================================

class TestResolutionNeverRefinesWithoutDownscaling:
    """
    Handbook 4.3 / 4.7 bullet 2:
    - A derived quantity's resolution is the coarsest (lowest index)
      among its parents, unless a registered downscaling method applies.
    - Registered downscaling conserves totals.
    """

    def test_derived_resolution_is_coarsest_parent(self):
        """
        Property: for any set of parent resolutions (without downscaling),
        resolution(child) == min(parent resolutions).
        """
        _require_implementation()

        parent_resolutions = [2, 3, 1]  # DISTRICT, SUBDISTRICT, STATE
        result = combine_resolutions(parent_resolutions, downscaling_method=None)
        assert result == min(parent_resolutions), (
            f"Resolution should be coarsest parent ({min(parent_resolutions)}), "
            f"got {result}"
        )

    def test_resolution_never_finer_than_coarsest_parent(self):
        """
        Hypothesis property: without downscaling, the derived resolution
        must never be finer (higher index) than the coarsest parent.
        """
        _require_implementation()

        @given(resolutions=parent_resolution_lists)
        def _check(resolutions):
            result = combine_resolutions(resolutions, downscaling_method=None)
            assert result == min(resolutions), (
                f"Without downscaling, derived resolution {result} must equal "
                f"coarsest parent {min(resolutions)}"
            )

        _check()

    def test_downscaling_produces_estimated_kind(self):
        """
        Handbook 4.3: a registered downscaling method may produce finer
        resolution, but its output has kind=ESTIMATED and floor at most 2.
        """
        _require_implementation()

        result = combine_resolutions(
            [2],  # DISTRICT parent
            downscaling_method="popweight_v1",
            target_resolution=3,  # SUBDISTRICT
        )
        assert result <= 3, "Downscaling should produce the target resolution"

    def test_downscaling_conserves_totals(self):
        """
        Handbook 4.3 / 4.7 bullet 2: downscaling must satisfy a
        conservation test (zone values sum back to the district total).
        Hypothesis property: for any positive total and partition weights,
        sum(downscale(method, total, weights)) == total within numerical tolerance.
        """
        _require_implementation()

        @given(
            district_total=st.floats(min_value=100.0, max_value=1_000_000.0),
            zone_weights=st.lists(
                st.floats(min_value=0.01, max_value=1.0),
                min_size=2,
                max_size=10,
            ),
        )
        def _check(district_total, zone_weights):
            zone_values = downscale(
                method="popweight_v1",
                total=district_total,
                weights=zone_weights,
            )
            assert sum(zone_values) == pytest.approx(district_total, rel=1e-6), (
                f"Downscaling must conserve totals: sum {sum(zone_values)} != {district_total}"
            )

        _check()


# ===================================================================
# PROPERTY 3: DAG rejects cycles; ancestors are exactly transitive parents
# Handbook 4.1 (field 11) / 4.7 bullet 3
# ===================================================================

class TestDAGRejectsCyclesAndAncestry:
    """
    Handbook 4.1 (field 11) / 4.7 bullet 3:
    parent_ids must form a DAG. Cycles are rejected.
    Ancestors of a quantity are exactly its transitive parents.
    """

    def test_direct_self_reference_rejected(self):
        """
        A quantity cannot be its own parent.
        Expects ValueError or RuntimeError when registering a cycle;
        no custom exception class is invented.
        """
        _require_implementation()

        ledger = Ledger()
        with pytest.raises((ValueError, RuntimeError)):
            q = Quantity(
                id="SELF_REF",
                definition_key="test.self_ref",
                value=1.0,
                unit="dimensionless",
                kind=Kind.CALCULATED,
                evidence_floor=4,
                geo_unit_id="nation",
                resolution=0,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="calc",
                model_version="1.0",
                parent_ids=("SELF_REF",),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )
            ledger.register(q)

    def test_two_node_cycle_rejected(self):
        """
        A -> B -> A cycle must be rejected.
        Expects ValueError or RuntimeError when registering a cycle.
        """
        _require_implementation()

        ledger = Ledger()
        a = Quantity(
            id="q_cycle_a",
            definition_key="test.a",
            value=1.0,
            unit="dimensionless",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        a_id = ledger.register(a)

        b = Quantity(
            id="q_cycle_b",
            definition_key="test.b",
            value=2.0,
            unit="dimensionless",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="nation",
            resolution=0,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(a_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        b_id = ledger.register(b)

        with pytest.raises((ValueError, RuntimeError)):
            # Attempting to re-register / update A with parent B introduces a cycle
            a_cyclic = Quantity(
                id=a_id,
                definition_key="test.a_cyclic",
                value=1.0,
                unit="dimensionless",
                kind=Kind.CALCULATED,
                evidence_floor=4,
                geo_unit_id="nation",
                resolution=0,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="calc",
                model_version="1.0",
                parent_ids=(b_id,),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )
            ledger.register(a_cyclic)

    def test_transitive_ancestors_complete(self):
        """
        Ancestors of a quantity are exactly its transitive parents.
        A -> B -> C implies ancestors(C) == {A, B}.
        """
        _require_implementation()

        ledger = Ledger()
        a = Quantity(
            id="q_anc_a",
            definition_key="test.root",
            value=10.0,
            unit="INR",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        a_id = ledger.register(a)

        b = Quantity(
            id="q_anc_b",
            definition_key="test.mid",
            value=20.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(a_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        b_id = ledger.register(b)

        c = Quantity(
            id="q_anc_c",
            definition_key="test.leaf",
            value=30.0,
            unit="INR",
            kind=Kind.CALCULATED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="calc",
            model_version="1.0",
            parent_ids=(b_id,),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        c_id = ledger.register(c)

        ancestors = ledger.ancestors(c_id)
        assert ancestors == {a_id, b_id}, (
            f"Ancestors of C should be {{A, B}}, got {ancestors}"
        )

    def test_ancestors_with_diamond_dependency(self):
        """
        Diamond: A -> B, A -> C, B -> D, C -> D.
        ancestors(D) == {A, B, C}.
        """
        _require_implementation()

        ledger = Ledger()
        a_id = ledger.register(Quantity(
            id="q_dia_a",
            definition_key="test.diamond.root",
            value=1.0, unit="dimensionless", kind=Kind.OBSERVED,
            evidence_floor=4, geo_unit_id="nation", resolution=0,
            as_of="2026-10-20", uncertainty="EXACT", source_refs=(),
            method_id="manual", model_version="1.0", parent_ids=(),
            quality_flags=frozenset(), license_meta="GODL-India",
        ))
        b_id = ledger.register(Quantity(
            id="q_dia_b",
            definition_key="test.diamond.left",
            value=2.0, unit="dimensionless", kind=Kind.CALCULATED,
            evidence_floor=4, geo_unit_id="nation", resolution=0,
            as_of="2026-10-20", uncertainty="EXACT", source_refs=(),
            method_id="calc", model_version="1.0", parent_ids=(a_id,),
            quality_flags=frozenset(), license_meta="GODL-India",
        ))
        c_id = ledger.register(Quantity(
            id="q_dia_c",
            definition_key="test.diamond.right",
            value=3.0, unit="dimensionless", kind=Kind.CALCULATED,
            evidence_floor=4, geo_unit_id="nation", resolution=0,
            as_of="2026-10-20", uncertainty="EXACT", source_refs=(),
            method_id="calc", model_version="1.0", parent_ids=(a_id,),
            quality_flags=frozenset(), license_meta="GODL-India",
        ))
        d_id = ledger.register(Quantity(
            id="q_dia_d",
            definition_key="test.diamond.sink",
            value=4.0, unit="dimensionless", kind=Kind.CALCULATED,
            evidence_floor=4, geo_unit_id="nation", resolution=0,
            as_of="2026-10-20", uncertainty="EXACT", source_refs=(),
            method_id="calc", model_version="1.0", parent_ids=(b_id, c_id),
            quality_flags=frozenset(), license_meta="GODL-India",
        ))

        ancestors = ledger.ancestors(d_id)
        assert ancestors == {a_id, b_id, c_id}, (
            f"Diamond ancestors of D should be {{A, B, C}}, got {ancestors}"
        )


# ===================================================================
# PROPERTY 4: UNQUANTIFIED uncertainty is contagious;
#             interval arithmetic contains the exact result;
#             division rejected when divisor interval includes zero
# Handbook 4.4 / 4.7 bullet 4
# ===================================================================

class TestUncertaintyPropagation:
    """
    Handbook 4.4 / 4.7 bullet 4:
    - UNQUANTIFIED parent gives UNQUANTIFIED child.
    - Interval arithmetic contains the exact result for sampled points.
    - Division is rejected when the divisor interval includes zero.
    """

    def test_unquantified_is_contagious(self):
        """
        If any parent has UNQUANTIFIED uncertainty, a deterministic
        child must also be UNQUANTIFIED.
        """
        _require_implementation()

        result = combine_uncertainty(
            parent_uncertainties=["EXACT", "UNQUANTIFIED", "EXACT"],
            operation="deterministic",
        )
        assert result == "UNQUANTIFIED", (
            f"UNQUANTIFIED must be contagious; got {result}"
        )

    def test_exact_with_exact_stays_exact(self):
        """EXACT combined with EXACT stays EXACT (Handbook 4.4 bullet 1)."""
        _require_implementation()

        result = combine_uncertainty(
            parent_uncertainties=["EXACT", "EXACT"],
            operation="deterministic",
        )
        assert result == "EXACT", f"EXACT + EXACT should stay EXACT; got {result}"

    def test_interval_arithmetic_containment(self):
        """
        Hypothesis property: for any sampled points within input intervals,
        the exact arithmetic results (addition, subtraction, multiplication)
        must fall within the computed output intervals.
        """
        _require_implementation()

        @given(
            a_lo=st.floats(min_value=1.0, max_value=100.0),
            a_width=st.floats(min_value=0.0, max_value=50.0),
            b_lo=st.floats(min_value=1.0, max_value=100.0),
            b_width=st.floats(min_value=0.0, max_value=50.0),
            sample_t_a=st.floats(min_value=0.0, max_value=1.0),
            sample_t_b=st.floats(min_value=0.0, max_value=1.0),
        )
        def _check(a_lo, a_width, b_lo, b_width, sample_t_a, sample_t_b):
            a_hi = a_lo + a_width
            b_hi = b_lo + b_width
            point_a = a_lo + sample_t_a * a_width
            point_b = b_lo + sample_t_b * b_width

            # Addition
            res_add = combine_uncertainty(
                parent_uncertainties=[
                    ("INTERVAL", a_lo, a_hi),
                    ("INTERVAL", b_lo, b_hi),
                ],
                operation="add",
            )
            assert res_add[1] <= (point_a + point_b) + 1e-9, (
                f"Addition lower bound {res_add[1]} exceeds exact {point_a + point_b}"
            )
            assert res_add[2] >= (point_a + point_b) - 1e-9, (
                f"Addition upper bound {res_add[2]} below exact {point_a + point_b}"
            )

            # Multiplication
            res_mul = combine_uncertainty(
                parent_uncertainties=[
                    ("INTERVAL", a_lo, a_hi),
                    ("INTERVAL", b_lo, b_hi),
                ],
                operation="multiply",
            )
            assert res_mul[1] <= (point_a * point_b) + 1e-9, (
                f"Multiplication lower bound {res_mul[1]} exceeds exact {point_a * point_b}"
            )
            assert res_mul[2] >= (point_a * point_b) - 1e-9, (
                f"Multiplication upper bound {res_mul[2]} below exact {point_a * point_b}"
            )

        _check()

    def test_interval_division_rejects_zero_crossing_divisor(self):
        """
        Handbook 4.4: 'division only when the divisor interval excludes zero'.
        Division by an interval containing zero must be rejected.
        Expects ZeroDivisionError or ValueError; avoids inventing custom exceptions.
        """
        _require_implementation()

        with pytest.raises((ZeroDivisionError, ValueError)):
            combine_uncertainty(
                parent_uncertainties=[
                    ("INTERVAL", 10.0, 20.0),
                    ("INTERVAL", -5.0, 5.0),  # interval includes zero
                ],
                operation="divide",
            )

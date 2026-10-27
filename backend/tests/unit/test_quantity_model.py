"""
Unit tests for the immutable Quantity domain model.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 4.1, 5.1).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).
"""

from dataclasses import FrozenInstanceError
import pytest

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity


class TestQuantityDomainModel:
    """Validate 15-field Quantity dataclass invariants, immutability, and validation."""

    def test_quantity_valid_creation(self):
        """A valid Quantity record can be instantiated with all 15 handbook fields."""
        q = Quantity(
            id="q_valid_001",
            definition_key="population.total",
            value=1250000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(("source_v1", "table_1"),),
            method_id="census_ingest",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        assert q.id == "q_valid_001"
        assert q.value == 1250000.0
        assert q.unit == "persons"
        assert q.kind == Kind.OBSERVED
        assert q.evidence_floor == 4
        assert q.resolution == 2

    def test_quantity_is_frozen_immutable(self):
        """Quantity instances reject attribute reassignment once constructed."""
        q = Quantity(
            id="q_frozen_001",
            definition_key="population.total",
            value=100.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="manual",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.value = 200.0
        with pytest.raises((FrozenInstanceError, AttributeError)):
            q.kind = Kind.CALCULATED

    def test_quantity_rejects_invalid_evidence_floor(self):
        """Evidence floor must be an integer between 1 and 4 (Handbook 4.2)."""
        with pytest.raises(ValueError, match="evidence_floor"):
            Quantity(
                id="q_invalid_floor",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.SCENARIO,
                evidence_floor=5,  # Invalid: must be 1..4
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

    def test_quantity_rejects_invalid_resolution(self):
        """Resolution must be an integer between 0 and 5 (Handbook 4.3)."""
        with pytest.raises(ValueError, match="resolution"):
            Quantity(
                id="q_invalid_res",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.SCENARIO,
                evidence_floor=1,
                geo_unit_id="nation",
                resolution=6,  # Invalid: must be 0..5
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="manual",
                model_version="1.0",
                parent_ids=(),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_rejects_observed_with_parents(self):
        """An OBSERVED quantity cannot have parent quantities (Handbook 4.1, 4.2)."""
        with pytest.raises(ValueError, match="OBSERVED"):
            Quantity(
                id="q_invalid_obs",
                definition_key="test.key",
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
                parent_ids=("parent_001",),  # Invalid for OBSERVED
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_rejects_empty_id(self):
        """Quantity id and definition_key cannot be empty strings."""
        with pytest.raises(ValueError, match="id"):
            Quantity(
                id="",
                definition_key="test.key",
                value=1.0,
                unit="dimensionless",
                kind=Kind.USER_ASSUMED,
                evidence_floor=3,
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

    def test_quantity_accepts_valid_simulation_meta(self):
        """A SIMULATED Quantity accepts a dedicated typed SimulationMetadata record."""
        from backend.arthlens.domain.simulation import SimulationMetadata

        sim_meta = SimulationMetadata(
            scenario_id="scenario_baseline",
            model_version="1.0.0",
            seed=42,
            sample_count=1000,
            data_versions=("census_2011_v1",),
        )
        q = Quantity(
            id="q_sim_001",
            definition_key="sim.revenue",
            value=100000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="monte_carlo",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
            simulation_meta=sim_meta,
        )
        assert q.simulation_meta is sim_meta
        assert q.simulation_meta.seed == 42
        assert q.simulation_meta.sample_count == 1000

    def test_quantity_rejects_wrong_simulation_meta_type(self):
        """Passing an object that is not a SimulationMetadata instance raises ValueError."""
        with pytest.raises(ValueError, match="simulation_meta must be an instance of SimulationMetadata"):
            Quantity(
                id="q_bad_meta",
                definition_key="sim.revenue",
                value=100000.0,
                unit="INR",
                kind=Kind.SIMULATED,
                evidence_floor=1,
                geo_unit_id="district_001",
                resolution=2,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(),
                method_id="monte_carlo",
                model_version="1.0.0",
                parent_ids=("p1",),
                quality_flags=frozenset(),
                license_meta="GODL-India",
                simulation_meta="seed=42_N=1000",  # String instead of typed dataclass
            )

    def test_quantity_rejects_simulation_meta_in_source_refs(self):
        """Storing SimulationMetadata or simulation parameter dicts in source_refs raises ValueError."""
        from backend.arthlens.domain.simulation import SimulationMetadata

        sim_meta = SimulationMetadata(
            scenario_id="scenario_baseline",
            model_version="1.0.0",
            seed=42,
            sample_count=1000,
            data_versions=("census_2011_v1",),
        )
        # Attempting to store SimulationMetadata in source_refs must fail
        with pytest.raises(ValueError, match="source_refs is reserved for external document citations"):
            Quantity(
                id="q_conflated_sources",
                definition_key="sim.revenue",
                value=100000.0,
                unit="INR",
                kind=Kind.SIMULATED,
                evidence_floor=1,
                geo_unit_id="district_001",
                resolution=2,
                as_of="2026-10-20",
                uncertainty="EXACT",
                source_refs=(sim_meta,),  # Violates citation contract
                method_id="monte_carlo",
                model_version="1.0.0",
                parent_ids=("p1",),
                quality_flags=frozenset(),
                license_meta="GODL-India",
            )

    def test_quantity_source_refs_retains_citation_semantics(self):
        """source_refs accepts external document citation tuples and maintains them cleanly."""
        citation = ("census_2011", "Table A-1, p. 12", "2026-10-20")
        q = Quantity(
            id="q_with_citation",
            definition_key="census.pop",
            value=50000.0,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(citation,),
            method_id="census",
            model_version="1.0",
            parent_ids=(),
            quality_flags=frozenset(),
            license_meta="GODL-India",
        )
        assert q.source_refs == (citation,)
        assert q.simulation_meta is None

    def test_quantity_with_simulation_meta_is_hashable_and_frozen(self):
        """Quantity instances containing simulation_meta remain frozen and hashable."""
        from backend.arthlens.domain.simulation import SimulationMetadata

        sim_meta = SimulationMetadata(
            scenario_id="scenario_baseline",
            model_version="1.0.0",
            seed=42,
            sample_count=1000,
            data_versions=("census_2011_v1",),
        )
        q = Quantity(
            id="q_hashable",
            definition_key="sim.revenue",
            value=100000.0,
            unit="INR",
            kind=Kind.SIMULATED,
            evidence_floor=1,
            geo_unit_id="district_001",
            resolution=2,
            as_of="2026-10-20",
            uncertainty="EXACT",
            source_refs=(),
            method_id="monte_carlo",
            model_version="1.0.0",
            parent_ids=("p1",),
            quality_flags=frozenset(),
            license_meta="GODL-India",
            simulation_meta=sim_meta,
        )
        # Hashable
        h = hash(q)
        assert isinstance(h, int)
        s = {q}
        assert q in s
        # Frozen
        with pytest.raises(FrozenInstanceError):
            q.simulation_meta = None  # type: ignore

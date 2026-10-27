"""
Quantity Domain Model for ArthLens Epistemic Ledger.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.1, 4.2, 4.3, 5.1).
Phase: P1-3 (Quantity, Epistemic Ledger, Propagation, Uncertainty and Units).

Encapsulation: Immutable (@dataclass(frozen=True)) once registered.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Tuple, Union

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.simulation import SimulationMetadata


@dataclass(frozen=True)
class Quantity:
    """
    Immutable representation of an epistemic ledger quantity.

    Handbook Reference: Section 4.1 (13 conceptual fields / 16 model attributes), Section 5.1.
    Attributes:
        id: Unique identifier (UUID string or domain key).
        definition_key: Semantic definition (e.g. population.total, scheme.pmfme.subsidy_rate).
        value: Numeric magnitude.
        unit: Unit of measurement (Pint string, e.g. INR, INR/month, kg/month, persons, dimensionless).
        kind: Epistemic provenance kind (OBSERVED, POLICY_RULE, USER_ASSUMED, ESTIMATED, SCENARIO, CALCULATED, SIMULATED).
        evidence_floor: Epistemic strength rank (1=SCENARIO, 2=ESTIMATED, 3=USER_ASSUMED, 4=POLICY_RULE/OBSERVED).
        geo_unit_id: Geographic entity identifier actually represented (e.g., LGD code or district id).
        resolution: Spatial granularity rank (0=NATION, 1=STATE, 2=DISTRICT, 3=SUBDISTRICT, 4=VILLAGE_URBAN, 5=POINT).
        as_of: Temporal support date (YYYY-MM-DD or date range).
        uncertainty: Structured uncertainty specification (EXACT, INTERVAL, DISTRIBUTION, SAMPLES, UNQUANTIFIED).
        source_refs: Tuple of source citations (version_id, locator, retrieval date).
        method_id: Identifier of computation/estimation method.
        model_version: Version of model/code producing the quantity.
        parent_ids: Tuple of immediate parent Quantity IDs in the ledger DAG.
        quality_flags: Frozen set of quality flags (e.g., STALE, INCOMPLETE_SOURCE, LOW_COVERAGE).
        license_meta: Attribution/licence string (e.g. GODL-India, ODbL).
        simulation_meta: Dedicated structured reproducibility metadata for SIMULATED quantities.
    """
    id: str
    definition_key: str
    value: float
    unit: str
    kind: Kind
    evidence_floor: int
    geo_unit_id: str
    resolution: int
    as_of: str
    uncertainty: Any = "EXACT"
    source_refs: tuple = field(default_factory=tuple)
    method_id: str = ""
    model_version: str = ""
    parent_ids: tuple = field(default_factory=tuple)
    quality_flags: frozenset = field(default_factory=frozenset)
    license_meta: str = ""
    simulation_meta: Optional[SimulationMetadata] = None

    def __post_init__(self) -> None:
        """Validate invariant constraints and normalize sequence attributes."""
        if not self.id:
            raise ValueError("Quantity id cannot be empty.")
        if not self.definition_key:
            raise ValueError("Quantity definition_key cannot be empty.")

        # Ensure float value
        try:
            object.__setattr__(self, "value", float(self.value))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Quantity value must be numeric, got {self.value}") from e

        # Normalize kind
        if isinstance(self.kind, str):
            try:
                object.__setattr__(self, "kind", Kind(self.kind))
            except ValueError as e:
                raise ValueError(f"Invalid kind: '{self.kind}'. Must be one of {list(Kind)}.") from e
        elif not isinstance(self.kind, Kind):
            raise ValueError(f"Invalid kind: '{self.kind}'. Must be a Kind enum member.")

        # Validate evidence_floor (Handbook 4.2: 1 to 4)
        if not isinstance(self.evidence_floor, int) or not (1 <= self.evidence_floor <= 4):
            raise ValueError(
                f"Invalid evidence_floor: {self.evidence_floor}. "
                "Must be an integer between 1 (SCENARIO) and 4 (OBSERVED/POLICY_RULE)."
            )

        # Validate resolution (Handbook 4.3: 0 to 5)
        if not isinstance(self.resolution, int) or not (0 <= self.resolution <= 5):
            raise ValueError(
                f"Invalid resolution: {self.resolution}. "
                "Must be an integer between 0 (NATION) and 5 (POINT)."
            )

        # Ensure parent_ids is a tuple
        if not isinstance(self.parent_ids, tuple):
            object.__setattr__(self, "parent_ids", tuple(self.parent_ids))

        # Ensure source_refs is a tuple
        if not isinstance(self.source_refs, tuple):
            object.__setattr__(self, "source_refs", tuple(self.source_refs))

        # Ensure quality_flags is a frozenset
        if not isinstance(self.quality_flags, frozenset):
            object.__setattr__(self, "quality_flags", frozenset(self.quality_flags))

        # Rule: A base quantity of kind OBSERVED cannot have parent inputs (Handbook 4.1, 4.2)
        if self.kind == Kind.OBSERVED and len(self.parent_ids) > 0:
            raise ValueError(
                "An OBSERVED quantity cannot have parent quantities. "
                "Calculated or derived values must be labelled CALCULATED, ESTIMATED, or SIMULATED."
            )

        # Validate simulation_meta type if provided
        if self.simulation_meta is not None:
            if not isinstance(self.simulation_meta, SimulationMetadata):
                raise ValueError(
                    f"simulation_meta must be an instance of SimulationMetadata, "
                    f"got {type(self.simulation_meta).__name__}."
                )

        # Enforce that source_refs contains external document citations, not simulation metadata records
        for ref in self.source_refs:
            if isinstance(ref, SimulationMetadata) or (isinstance(ref, dict) and "seed" in ref):
                raise ValueError(
                    "source_refs is reserved for external document citations "
                    "(version_id, locator, retrieval_date). Simulation metadata must be "
                    "stored in the dedicated 'simulation_meta' field."
                )

"""
Simulation Domain Model for ArthLens Epistemic Ledger.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.5, 4.7, 6.4).
Phase: P1-4 (Verification Specifications, LedgerVerifier, ReportRenderer).

Encapsulation: Immutable (@dataclass(frozen=True)).
"""

from dataclasses import dataclass, field
import re
from typing import Tuple


@dataclass(frozen=True)
class SimulationMetadata:
    """
    Structured reproducibility and parameter-pinning metadata for SIMULATED quantities.

    Handbook Reference: Section 4.5 (Rules V7, V9), Section 4.7, Section 6.4:
        'Every simulation result names scenario id, model version, seed, N and data versions.'
        'Reproducibility: identical scenario, seed, model version and data versions
        give identical outputs (bitwise for floats under the same library versions).'

    Attributes:
        scenario_id: Semantic scenario identifier (e.g. 'baseline', 'high_growth', 'pmfme_expanded').
        model_version: Software/code version or git commit hash of simulation model.
        seed: Random seed for pseudo-random number generator (constrained to unsigned 64-bit int for PCG64).
        sample_count: Number of simulation iterations / Monte Carlo draws (N > 0).
        data_versions: Tuple of input dataset versions used in the simulation run.
    """
    scenario_id: str
    model_version: str
    seed: int
    sample_count: int  # N
    data_versions: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate parameter ranges and unambiguous types."""
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be a non-empty string.")
        if not re.match(r"^[a-zA-Z0-9_\-\.]+$", self.scenario_id.strip()):
            raise ValueError(f"scenario_id contains invalid identifier characters: '{self.scenario_id}'.")

        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise ValueError("model_version must be a non-empty string.")

        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError(f"seed must be an integer, got {type(self.seed).__name__}: {self.seed}")
        if self.seed < 0:
            raise ValueError(f"seed must be non-negative (>= 0), got {self.seed}")
        if self.seed > 18446744073709551615:  # 2^64 - 1
            raise ValueError(f"seed exceeds 64-bit integer limit: {self.seed}")

        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int):
            raise ValueError(f"sample_count (N) must be an integer, got {type(self.sample_count).__name__}: {self.sample_count}")
        if self.sample_count <= 0:
            raise ValueError(f"sample_count (N) must be positive (> 0), got {self.sample_count}")

        if not isinstance(self.data_versions, tuple):
            if isinstance(self.data_versions, (list, set)):
                object.__setattr__(self, "data_versions", tuple(self.data_versions))
            else:
                raise ValueError("data_versions must be a sequence of version strings.")
        if len(self.data_versions) == 0:
            raise ValueError("data_versions must contain at least one input data version.")
        for dv in self.data_versions:
            if not isinstance(dv, str) or not dv.strip():
                raise ValueError(f"Invalid data version item: {dv}")


__all__ = ["SimulationMetadata"]

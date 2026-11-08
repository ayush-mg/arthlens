"""
Canonical End-to-End Workflow Loops (Loops A, B, and C).

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 2.3, 8.8, Part 13.1 P5-1).
"""

from backend.arthlens.workflows.loop_a import (
    LoopAResult,
    SpatialDemandInputs,
    run_loop_a_spatial_siting,
)
from backend.arthlens.workflows.loop_b import LoopBResult, run_loop_b_corridor_accessibility
from backend.arthlens.workflows.loop_c import LoopCResult, run_loop_c_scheme_viability

__all__ = [
    "LoopAResult",
    "SpatialDemandInputs",
    "LoopBResult",
    "LoopCResult",
    "run_loop_a_spatial_siting",
    "run_loop_b_corridor_accessibility",
    "run_loop_c_scheme_viability",
]

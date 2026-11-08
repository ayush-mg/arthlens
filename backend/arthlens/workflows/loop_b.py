"""
Loop B: Corridor Accessibility & Spatial Routing Workflow.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 2.3, 6.1, 8.8).
Phase: P5-1 (End-to-End Workflow Loops).
"""

from dataclasses import dataclass
from typing import Sequence

from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.geo.dijkstra import (
    CatchmentAnalysis,
    build_catchments,
    register_catchment_quantities,
)
from backend.arthlens.geo.road_graph import (
    Coordinate,
    RoadGraph,
    RoadSpeedScenario,
)
from backend.arthlens.ledger.ledger import Ledger


@dataclass(frozen=True)
class LoopBResult:
    status: str
    site_coordinate: Coordinate | None
    snapped_node_id: str | None
    snap_distance_m: float | None
    analysis: CatchmentAnalysis | None
    registered_quantity_ids: dict[str, str]
    missing_evidence: tuple[str, ...]


def run_loop_b_corridor_accessibility(
    ledger: Ledger,
    *,
    graph: RoadGraph | None = None,
    site_coordinate: Coordinate | None = None,
    thresholds_minutes: Sequence[float] | None = None,
    site_geo_unit_id: str | None = None,
    speed_scenario: RoadSpeedScenario | None = None,
    corridor_width_m: float | None = None,
    parent_quantities: Sequence[Quantity] = (),
    as_of: str | None = None,
    model_version: str | None = None,
) -> LoopBResult:
    """
    Compute a source-versioned, scenario-parameterized road catchment.

    This workflow never creates a pilot graph, a site, speeds, a corridor
    width, or a demographic parent. Missing inputs are surfaced as an explicit
    insufficient-data result.
    """
    missing_evidence: list[str] = []
    if graph is None:
        missing_evidence.append("source-versioned local road graph")
    elif not graph.source_version_ids:
        missing_evidence.append("exact OSM source version for local road graph")
    if site_coordinate is None:
        missing_evidence.append("user-selected site coordinate")
    if not thresholds_minutes:
        missing_evidence.append("explicit catchment travel-time thresholds")
    if speed_scenario is None:
        missing_evidence.append("explicit road-speed scenario")
    if corridor_width_m is None:
        missing_evidence.append("explicit corridor-width scenario assumption")
    if not parent_quantities:
        missing_evidence.append("registered site and routing input quantities")
    if not site_geo_unit_id:
        missing_evidence.append("site geographic unit")
    if not as_of:
        missing_evidence.append("analysis as-of date")
    if not model_version:
        missing_evidence.append("routing model version")
    if missing_evidence:
        return LoopBResult(
            status="INSUFFICIENT_DATA",
            site_coordinate=site_coordinate,
            snapped_node_id=None,
            snap_distance_m=None,
            analysis=None,
            registered_quantity_ids={},
            missing_evidence=tuple(missing_evidence),
        )

    assert graph is not None
    assert site_coordinate is not None
    assert thresholds_minutes is not None
    assert speed_scenario is not None
    assert corridor_width_m is not None
    assert site_geo_unit_id is not None
    assert as_of is not None
    assert model_version is not None

    analysis = build_catchments(
        graph,
        site=site_coordinate,
        speeds=speed_scenario,
        thresholds_minutes=thresholds_minutes,
        corridor_width_m=corridor_width_m,
    )

    registered_ids = register_catchment_quantities(
        analysis,
        ledger,
        parent_quantities=parent_quantities,
        site_geo_unit_id=site_geo_unit_id,
        as_of=as_of,
        model_version=model_version,
    )

    return LoopBResult(
        status="COMPLETED",
        site_coordinate=site_coordinate,
        snapped_node_id=analysis.snap.node_id,
        snap_distance_m=analysis.snap.distance_m,
        analysis=analysis,
        registered_quantity_ids=registered_ids,
        missing_evidence=(),
    )


__all__ = ["LoopBResult", "run_loop_b_corridor_accessibility"]

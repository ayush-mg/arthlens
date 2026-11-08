"""Site-local shortest paths and road-corridor catchments."""

import heapq
from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Mapping, Sequence
from uuid import uuid4

from pyproj import CRS, Transformer
from shapely import transform as transform_geometry
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import unary_union

from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.geo.road_graph import (
    Coordinate,
    RoadGraph,
    RoadSpeedScenario,
    _validate_coordinate,
    haversine_distance_m,
    largest_strongly_connected_component,
)
from backend.arthlens.ledger.ledger import Ledger


@dataclass(frozen=True)
class SiteSnap:
    node_id: str
    coordinate: Coordinate
    distance_m: float


@dataclass(frozen=True)
class Catchment:
    threshold_minutes: float
    reachable_node_ids: tuple[str, ...]
    travel_time_minutes: Mapping[str, float]
    geometry: dict
    method_id: str = "road_network_corridor_v1"
    is_corridor_approximation: bool = True


@dataclass(frozen=True)
class CatchmentAnalysis:
    snap: SiteSnap
    speed_scenario_id: str
    catchments: tuple[Catchment, ...]
    source_version_ids: frozenset[str] = frozenset()


def dijkstra_travel_times(
    graph: RoadGraph,
    source_node_id: str,
    speeds: RoadSpeedScenario,
    *,
    max_minutes: float | None = None,
) -> dict[str, float]:
    """Compute directed shortest travel times with heapq; no reference router is used at runtime."""
    if source_node_id not in graph.nodes:
        raise ValueError(f"Source road node '{source_node_id}' is not in the local graph.")
    if max_minutes is not None and (not isfinite(max_minutes) or max_minutes < 0):
        raise ValueError("max_minutes must be finite and non-negative when provided.")

    adjacency: dict[str, list[tuple[str, float]]] = {node_id: [] for node_id in graph.nodes}
    for edge in graph.edges:
        try:
            speed_kph = speeds.speed_kph_by_class[edge.road_class]
        except KeyError as exc:
            raise ValueError(
                f"No scenario speed supplied for road class '{edge.road_class}'."
            ) from exc
        minutes = edge.length_m / (speed_kph * 1000 / 60)
        adjacency[edge.source].append((edge.target, minutes))

    travel_times = {source_node_id: 0.0}
    queue: list[tuple[float, str]] = [(0.0, source_node_id)]
    while queue:
        current_minutes, current_node = heapq.heappop(queue)
        if current_minutes != travel_times.get(current_node):
            continue
        if max_minutes is not None and current_minutes > max_minutes:
            continue
        for neighbor, edge_minutes in adjacency[current_node]:
            candidate = current_minutes + edge_minutes
            if max_minutes is not None and candidate > max_minutes:
                continue
            if candidate < travel_times.get(neighbor, float("inf")):
                travel_times[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    return travel_times


def snap_site_to_road(graph: RoadGraph, site: Coordinate) -> SiteSnap:
    """Snap a WGS84 site to the closest actual node in the supplied local road graph."""
    _validate_coordinate(site)
    if not graph.nodes:
        raise ValueError("Cannot snap site: the local road graph contains no genuine road nodes.")
    node = min(
        graph.nodes.values(),
        key=lambda candidate: (
            haversine_distance_m(
                site,
                (candidate.longitude, candidate.latitude),
            ),
            candidate.id,
        ),
    )
    return SiteSnap(
        node_id=node.id,
        coordinate=(node.longitude, node.latitude),
        distance_m=haversine_distance_m(site, (node.longitude, node.latitude)),
    )


def build_catchments(
    graph: RoadGraph,
    *,
    site: Coordinate,
    speeds: RoadSpeedScenario,
    thresholds_minutes: Sequence[float] = (15, 30, 60),
    corridor_width_m: float,
) -> CatchmentAnalysis:
    """Build catchments on the largest SCC; the corridor width is an explicit scenario input."""
    _validate_coordinate(site)
    thresholds = tuple(float(value) for value in thresholds_minutes)
    if not thresholds or any(not isfinite(value) or value <= 0 for value in thresholds):
        raise ValueError("Catchment thresholds must be a non-empty sequence of positive finite minutes.")
    if len(set(thresholds)) != len(thresholds):
        raise ValueError("Catchment thresholds must be unique.")
    if not isfinite(corridor_width_m) or corridor_width_m <= 0:
        raise ValueError("corridor_width_m must be explicitly supplied as a positive finite scenario value.")

    routing_graph = largest_strongly_connected_component(graph)
    if not routing_graph.edges:
        raise ValueError("The local road graph has no strongly connected road component to analyze.")
    snap = snap_site_to_road(routing_graph, site)
    travel_times = dijkstra_travel_times(
        routing_graph,
        snap.node_id,
        speeds,
        max_minutes=max(thresholds),
    )
    ordered_edges = tuple(sorted(graph.edges, key=lambda edge: edge.id))
    ordered_times = dict(sorted(travel_times.items()))
    catchments = tuple(
        _build_one_catchment(
            routing_graph,
            snap,
            ordered_edges,
            ordered_times,
            speeds,
            threshold,
            corridor_width_m,
        )
        for threshold in sorted(thresholds)
    )
    return CatchmentAnalysis(
        snap,
        speeds.scenario_id,
        catchments,
        graph.source_version_ids,
    )


def intersect_catchment_zones(
    catchment_geometry: dict,
    zones: Mapping[str, dict],
) -> dict[str, dict]:
    """Return valid non-empty GeoJSON intersections keyed by their input zone IDs."""
    catchment_shape = shape(catchment_geometry)
    if catchment_shape.is_empty or not catchment_shape.is_valid:
        raise ValueError("Catchment geometry must be non-empty and valid.")
    intersections: dict[str, dict] = {}
    for zone_id, zone_geometry in zones.items():
        if not zone_id:
            raise ValueError("Zone IDs must be non-empty.")
        zone_shape = shape(zone_geometry)
        if zone_shape.is_empty or not zone_shape.is_valid:
            raise ValueError(f"Zone '{zone_id}' geometry must be non-empty and valid.")
        intersection = catchment_shape.intersection(zone_shape)
        if not intersection.is_empty and intersection.area > 0:
            intersections[zone_id] = mapping(intersection)
    return intersections


def register_catchment_quantities(
    analysis: CatchmentAnalysis,
    ledger: Ledger,
    *,
    parent_quantities: Sequence[Quantity],
    site_geo_unit_id: str,
    as_of: str,
    model_version: str,
) -> dict[str, str]:
    """Register numeric routing outputs with exact scenario/data ancestry in the ledger."""
    if not parent_quantities:
        raise ValueError("Catchment ledger registration requires its input quantities.")
    if not analysis.source_version_ids:
        raise ValueError("Catchment ledger registration requires exact road source version IDs.")
    if not site_geo_unit_id.strip() or not model_version.strip():
        raise ValueError("site_geo_unit_id and model_version are required.")
    date.fromisoformat(as_of)

    parent_ids = tuple(quantity.id for quantity in parent_quantities)
    if len(set(parent_ids)) != len(parent_ids):
        raise ValueError("Catchment input quantity IDs must be unique.")
    for quantity in parent_quantities:
        if ledger.get(quantity.id) != quantity:
            raise ValueError(f"Catchment input quantity '{quantity.id}' is not registered exactly.")

    evidence_floor = min(quantity.evidence_floor for quantity in parent_quantities)
    resolution = min(quantity.resolution for quantity in parent_quantities)
    quality_flags = frozenset(
        flag for quantity in parent_quantities for flag in quantity.quality_flags
    )
    source_refs = tuple(sorted(analysis.source_version_ids))
    registered: dict[str, str] = {}

    def register(definition_key: str, value: float, unit: str) -> str:
        quantity = Quantity(
            id=str(uuid4()),
            definition_key=definition_key,
            value=value,
            unit=unit,
            kind=Kind.CALCULATED,
            evidence_floor=evidence_floor,
            geo_unit_id=site_geo_unit_id,
            resolution=resolution,
            as_of=as_of,
            method_id="dijkstra_heapq_v1",
            model_version=model_version,
            parent_ids=parent_ids,
            quality_flags=quality_flags,
            source_refs=source_refs,
        )
        ledger.register(quantity)
        registered[definition_key] = quantity.id
        return quantity.id

    register(
        "catchment.site_snap_distance",
        analysis.snap.distance_m,
        "meter",
    )
    for catchment in analysis.catchments:
        register(
            f"catchment.{catchment.threshold_minutes:g}min.reachable_road_nodes",
            float(len(catchment.reachable_node_ids)),
            "dimensionless",
        )
        for node_id, minutes in catchment.travel_time_minutes.items():
            register(
                f"catchment.{catchment.threshold_minutes:g}min.travel_time.osm_node.{node_id}",
                minutes,
                "minute",
            )
    return registered


def _build_one_catchment(
    graph: RoadGraph,
    snap: SiteSnap,
    edges,
    travel_times: dict[str, float],
    speeds: RoadSpeedScenario,
    threshold: float,
    corridor_width_m: float,
) -> Catchment:
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={snap.coordinate[1]} +lon_0={snap.coordinate[0]} "
        "+datum=WGS84 +units=m +no_defs"
    )
    forward = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True).transform
    inverse = Transformer.from_crs(local_crs, "EPSG:4326", always_xy=True).transform
    corridors = [
        transform_geometry(Point(snap.coordinate), forward, interleaved=False).buffer(
            corridor_width_m
        )
    ]

    for edge in edges:
        source_minutes = travel_times.get(edge.source)
        if source_minutes is None or source_minutes >= threshold:
            continue
        speed_kph = speeds.speed_kph_by_class[edge.road_class]
        edge_minutes = edge.length_m / (speed_kph * 1000 / 60)
        fraction = min(1.0, (threshold - source_minutes) / edge_minutes)
        if fraction <= 0:
            continue
        source_node = graph.nodes[edge.source]
        target_node = graph.nodes[edge.target]
        endpoint = (
            source_node.longitude + (target_node.longitude - source_node.longitude) * fraction,
            source_node.latitude + (target_node.latitude - source_node.latitude) * fraction,
        )
        line = LineString(
            [(source_node.longitude, source_node.latitude), endpoint]
        )
        corridors.append(
            transform_geometry(line, forward, interleaved=False).buffer(corridor_width_m)
        )

    polygon = transform_geometry(unary_union(corridors), inverse, interleaved=False)
    if polygon.is_empty or not polygon.is_valid:
        raise ValueError("Could not construct a valid road-corridor catchment polygon.")
    reachable = tuple(
        node_id
        for node_id, minutes in travel_times.items()
        if minutes <= threshold
    )
    return Catchment(
        threshold_minutes=threshold,
        reachable_node_ids=reachable,
        travel_time_minutes={
            node_id: minutes
            for node_id, minutes in travel_times.items()
            if minutes <= threshold
        },
        geometry=mapping(polygon),
    )

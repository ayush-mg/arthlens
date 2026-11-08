"""Directed OSM road graph construction and site-local extraction."""

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from shapely.geometry import LineString, box

Coordinate = tuple[float, float]


@dataclass(frozen=True)
class RoadNode:
    id: str
    longitude: float
    latitude: float
    source_record_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Road node id cannot be empty.")
        if not isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise ValueError(f"Road node longitude must be within [-180, 180], got {self.longitude}.")
        if not isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise ValueError(f"Road node latitude must be within [-90, 90], got {self.latitude}.")


@dataclass(frozen=True)
class RoadEdge:
    id: str
    source: str
    target: str
    length_m: float
    road_class: str
    source_record_id: str | None = None
    osm_way_id: str | None = None
    segment_index: int | None = None
    direction: str | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.source or not self.target:
            raise ValueError("Road edge id, source, and target are required.")
        if self.source == self.target:
            raise ValueError(f"Road edge '{self.id}' cannot be a self-loop.")
        if not isfinite(self.length_m) or self.length_m <= 0:
            raise ValueError(f"Road edge length must be finite and positive, got {self.length_m}.")
        if not self.road_class:
            raise ValueError("Road edge road_class cannot be empty.")


@dataclass(frozen=True)
class RoadGraph:
    nodes: Mapping[str, RoadNode]
    edges: tuple[RoadEdge, ...]
    source_version_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        normalized_nodes = dict(self.nodes)
        if any(node_id != node.id for node_id, node in normalized_nodes.items()):
            raise ValueError("Road graph node keys must match RoadNode.id.")
        edge_ids: set[str] = set()
        for edge in self.edges:
            if edge.id in edge_ids:
                raise ValueError(f"Duplicate road edge id '{edge.id}'.")
            edge_ids.add(edge.id)
            if edge.source not in normalized_nodes or edge.target not in normalized_nodes:
                raise ValueError(f"Road edge '{edge.id}' references a missing node.")
        object.__setattr__(self, "nodes", MappingProxyType(normalized_nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "source_version_ids", frozenset(self.source_version_ids))


@dataclass(frozen=True)
class RoadSpeedScenario:
    """Explicit, scenario-owned speeds in kilometres per hour, keyed by OSM highway value."""

    scenario_id: str
    speed_kph_by_class: Mapping[str, float]

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("Road speed scenario_id is required.")
        speeds = dict(self.speed_kph_by_class)
        for road_class, speed in speeds.items():
            if not road_class.strip():
                raise ValueError("Road speed classes must be non-empty.")
            if not isfinite(speed) or speed <= 0:
                raise ValueError(
                    f"Scenario speed for road class '{road_class}' must be finite and positive."
                )
        object.__setattr__(self, "speed_kph_by_class", MappingProxyType(speeds))


def build_road_graph_from_osm(
    elements: Sequence[Mapping[str, Any]],
    *,
    source_version_id: str,
) -> RoadGraph:
    """Build directed segment edges from one bounded OSM snapshot and preserve record IDs."""
    if not source_version_id.strip():
        raise ValueError("An exact OSM source_version_id is required.")

    raw_nodes: dict[str, RoadNode] = {}
    ways: list[Mapping[str, Any]] = []

    for element in elements:
        element_type = element.get("type")
        element_id = element.get("id")
        if element_type == "node":
            if element_id is None or element.get("lon") is None or element.get("lat") is None:
                raise ValueError("OSM node must include id, longitude, and latitude.")
            node_id = str(element_id)
            raw_nodes[node_id] = RoadNode(
                node_id,
                float(element["lon"]),
                float(element["lat"]),
                f"{source_version_id}:osm:node:{node_id}",
            )
        elif element_type == "way" and (element.get("tags") or {}).get("highway"):
            if element_id is None:
                raise ValueError("OSM road way must include id.")
            ways.append(element)

    edges: list[RoadEdge] = []
    used_node_ids: set[str] = set()
    for way in ways:
        way_id = str(way["id"])
        node_ids = [str(node_id) for node_id in way.get("nodes", ())]
        if len(node_ids) < 2:
            raise ValueError(f"OSM road way {way_id} must reference at least two nodes.")
        missing = [node_id for node_id in node_ids if node_id not in raw_nodes]
        if missing:
            raise ValueError(f"OSM road way {way_id} is missing coordinate data for OSM node {missing[0]}.")

        tags = way.get("tags") or {}
        road_class = str(tags["highway"])
        oneway = str(tags.get("oneway", "")).lower()
        implied_oneway = (
            road_class in {"motorway", "motorway_link"}
            or str(tags.get("junction", "")).lower() in {"roundabout", "circular"}
        )
        direction = (
            "reverse"
            if oneway == "-1"
            else "forward"
            if oneway in {"yes", "true", "1"} or (not oneway and implied_oneway)
            else "both"
        )

        for segment_index, (first_id, second_id) in enumerate(zip(node_ids, node_ids[1:])):
            first = raw_nodes[first_id]
            second = raw_nodes[second_id]
            segment_length = haversine_distance_m(
                (first.longitude, first.latitude),
                (second.longitude, second.latitude),
            )
            if segment_length <= 0:
                raise ValueError(f"OSM way {way_id} contains a zero-length segment at node {first_id}.")
            source_record_id = f"{source_version_id}:osm:way:{way_id}"
            if direction == "reverse":
                edges.append(
                    RoadEdge(
                        f"{source_version_id}:way:{way_id}:{segment_index}:reverse",
                        second_id,
                        first_id,
                        segment_length,
                        road_class,
                        source_record_id,
                        way_id,
                        segment_index,
                        "reverse",
                    )
                )
            else:
                edges.append(
                    RoadEdge(
                        f"{source_version_id}:way:{way_id}:{segment_index}:forward",
                        first_id,
                        second_id,
                        segment_length,
                        road_class,
                        source_record_id,
                        way_id,
                        segment_index,
                        "forward",
                    )
                )
            if direction == "both":
                edges.append(
                    RoadEdge(
                        f"{source_version_id}:way:{way_id}:{segment_index}:reverse",
                        second_id,
                        first_id,
                        segment_length,
                        road_class,
                        source_record_id,
                        way_id,
                        segment_index,
                        "reverse",
                    )
                )
            used_node_ids.update((first_id, second_id))

    nodes = {node_id: raw_nodes[node_id] for node_id in used_node_ids}
    return RoadGraph(nodes, tuple(edges), frozenset({source_version_id}))


def haversine_distance_m(first: Coordinate, second: Coordinate) -> float:
    """Great-circle distance between two WGS84 longitude/latitude coordinates."""
    lon1, lat1 = first
    lon2, lat2 = second
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    hav = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    return 2 * 6_371_008.8 * asin(min(1.0, hav**0.5))


def bbox_around_site(site: Coordinate, radius_m: float = 15_000) -> tuple[float, float, float, float]:
    """Return a WGS84 bbox for a site-local query, with a configurable 15 km default."""
    longitude, latitude = site
    _validate_coordinate(site)
    if not isfinite(radius_m) or radius_m <= 0:
        raise ValueError("radius_m must be finite and positive.")
    latitude_delta = radius_m / 111_320
    longitude_scale = cos(radians(latitude))
    if abs(longitude_scale) < 1e-8:
        raise ValueError("A longitude/latitude bbox is undefined at the poles.")
    longitude_delta = radius_m / (111_320 * abs(longitude_scale))
    return (
        max(-180.0, longitude - longitude_delta),
        max(-90.0, latitude - latitude_delta),
        min(180.0, longitude + longitude_delta),
        min(90.0, latitude + latitude_delta),
    )


def extract_local_subgraph(
    graph: RoadGraph,
    site: Coordinate,
    *,
    radius_m: float = 15_000,
) -> RoadGraph:
    """Filter an already bounded graph to edges intersecting a site-centred bbox."""
    west, south, east, north = bbox_around_site(site, radius_m)
    bounds = box(west, south, east, north)
    local_edges = tuple(
        edge
        for edge in graph.edges
        if LineString(
            [
                (graph.nodes[edge.source].longitude, graph.nodes[edge.source].latitude),
                (graph.nodes[edge.target].longitude, graph.nodes[edge.target].latitude),
            ]
        ).intersects(bounds)
    )
    node_ids = {node_id for edge in local_edges for node_id in (edge.source, edge.target)}
    return RoadGraph(
        {node_id: graph.nodes[node_id] for node_id in node_ids},
        local_edges,
        graph.source_version_ids,
    )


def largest_strongly_connected_component(graph: RoadGraph) -> RoadGraph:
    """Keep the deterministically selected largest SCC before routing."""
    adjacency = {node_id: set() for node_id in graph.nodes}
    reverse_adjacency = {node_id: set() for node_id in graph.nodes}
    for edge in graph.edges:
        adjacency[edge.source].add(edge.target)
        reverse_adjacency[edge.target].add(edge.source)

    visited: set[str] = set()
    finish_order: list[str] = []
    for start in sorted(graph.nodes):
        if start in visited:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            node_id, expanded = stack.pop()
            if expanded:
                finish_order.append(node_id)
                continue
            if node_id in visited:
                continue
            visited.add(node_id)
            stack.append((node_id, True))
            for neighbor in sorted(adjacency[node_id], reverse=True):
                if neighbor not in visited:
                    stack.append((neighbor, False))

    components: list[set[str]] = []
    assigned: set[str] = set()
    for start in reversed(finish_order):
        if start in assigned:
            continue
        component: set[str] = set()
        stack = [start]
        assigned.add(start)
        while stack:
            node_id = stack.pop()
            component.add(node_id)
            for neighbor in reverse_adjacency[node_id]:
                if neighbor not in assigned:
                    assigned.add(neighbor)
                    stack.append(neighbor)
        components.append(component)

    if not components:
        return RoadGraph({}, (), graph.source_version_ids)
    selected = min(components, key=lambda nodes: (-len(nodes), tuple(sorted(nodes))))
    selected_edges = tuple(
        edge
        for edge in graph.edges
        if edge.source in selected and edge.target in selected
    )
    return RoadGraph(
        {node_id: graph.nodes[node_id] for node_id in selected},
        selected_edges,
        graph.source_version_ids,
    )


def _validate_coordinate(coordinate: Coordinate) -> None:
    if len(coordinate) != 2:
        raise ValueError("A WGS84 coordinate must contain longitude and latitude.")
    longitude, latitude = coordinate
    if not isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError(f"Site longitude must be within [-180, 180], got {longitude}.")
    if not isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError(f"Site latitude must be within [-90, 90], got {latitude}.")

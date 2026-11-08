import random
import uuid

import networkx as nx
import pytest
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.geo.dijkstra import (
    build_catchments,
    dijkstra_travel_times,
    intersect_catchment_zones,
    register_catchment_quantities,
    snap_site_to_road,
)
from backend.arthlens.geo.road_graph import (
    RoadEdge,
    RoadGraph,
    RoadNode,
    RoadSpeedScenario,
    build_road_graph_from_osm,
    extract_local_subgraph,
    largest_strongly_connected_component,
)
from backend.arthlens.ledger.ledger import Ledger
from shapely.geometry import shape


def _graph(nodes, edges, source_version_ids=()):
    return RoadGraph(
        nodes={node.id: node for node in nodes},
        edges=tuple(edges),
        source_version_ids=frozenset(source_version_ids),
    )


def test_dijkstra_matches_networkx_for_seeded_directed_graphs():
    for seed in range(10):
        rng = random.Random(seed)
        node_count = 12
        nodes = [
            RoadNode(str(node_id), longitude=-100 + node_id * 0.001, latitude=40)
            for node_id in range(node_count)
        ]
        edges = []
        graph_reference = nx.DiGraph()
        graph_reference.add_nodes_from(node.id for node in nodes)
        for source in range(node_count):
            for target in range(node_count):
                if source != target and rng.random() < 0.13:
                    length_m = rng.uniform(10, 500)
                    edge_id = f"{seed}:{source}:{target}"
                    edges.append(RoadEdge(edge_id, str(source), str(target), length_m, "residential"))
                    graph_reference.add_edge(
                        str(source),
                        str(target),
                        weight=length_m / (30 * 1000 / 60),
                    )

        graph = _graph(nodes, edges)
        actual = dijkstra_travel_times(
            graph,
            "0",
            RoadSpeedScenario("test-scenario", {"residential": 30}),
        )
        expected = nx.single_source_dijkstra_path_length(graph_reference, "0", weight="weight")
        assert actual.keys() == expected.keys()
        for node_id, expected_minutes in expected.items():
            assert actual[node_id] == pytest.approx(expected_minutes)


def test_osm_road_builder_preserves_oneway_and_exact_source_records():
    elements = [
        {"type": "node", "id": 1, "lon": -100.0, "lat": 40.0},
        {"type": "node", "id": 2, "lon": -99.999, "lat": 40.0},
        {
            "type": "way",
            "id": 50,
            "nodes": [1, 2],
            "tags": {"highway": "residential", "oneway": "yes"},
        },
        {
            "type": "way",
            "id": 51,
            "nodes": [2, 1],
            "tags": {"highway": "residential", "oneway": "-1"},
        },
    ]

    graph = build_road_graph_from_osm(elements, source_version_id="DS-04:version-1")

    assert {(edge.source, edge.target) for edge in graph.edges} == {("1", "2"), ("1", "2")}
    assert all(
        edge.source_record_id == "DS-04:version-1:osm:way:50"
        or edge.source_record_id == "DS-04:version-1:osm:way:51"
        for edge in graph.edges
    )
    assert all(node.source_record_id == f"DS-04:version-1:osm:node:{node.id}" for node in graph.nodes.values())


def test_osm_road_builder_fails_closed_for_missing_referenced_node():
    elements = [
        {"type": "node", "id": 1, "lon": -100.0, "lat": 40.0},
        {"type": "way", "id": 50, "nodes": [1, 2], "tags": {"highway": "residential"}},
    ]

    with pytest.raises(ValueError, match="missing coordinate data for OSM node 2"):
        build_road_graph_from_osm(elements, source_version_id="DS-04:version-1")


def test_local_subgraph_uses_site_centered_bounding_box():
    nodes = [
        RoadNode("a", -100.0, 40.0),
        RoadNode("b", -99.999, 40.0),
        RoadNode("c", -99.5, 40.0),
        RoadNode("d", -99.499, 40.0),
    ]
    edges = [
        RoadEdge("inside", "a", "b", 100, "residential"),
        RoadEdge("outside", "c", "d", 100, "residential"),
    ]

    local = extract_local_subgraph(_graph(nodes, edges), (-100.0, 40.0), radius_m=1500)

    assert {edge.id for edge in local.edges} == {"inside"}
    assert set(local.nodes) == {"a", "b"}


def test_largest_strongly_connected_component_excludes_one_way_dead_ends():
    graph = _graph(
        [
            RoadNode("a", -100.0, 40.0),
            RoadNode("b", -99.999, 40.0),
            RoadNode("c", -99.998, 40.0),
            RoadNode("dead-end", -99.997, 40.0),
        ],
        [
            RoadEdge("a-b", "a", "b", 100, "residential"),
            RoadEdge("b-a", "b", "a", 100, "residential"),
            RoadEdge("b-c", "b", "c", 100, "residential"),
            RoadEdge("c-b", "c", "b", 100, "residential"),
            RoadEdge("dead-end-link", "c", "dead-end", 100, "residential"),
        ],
        source_version_ids=("DS-04:fixture-v1",),
    )

    component = largest_strongly_connected_component(graph)

    assert set(component.nodes) == {"a", "b", "c"}
    assert {edge.id for edge in component.edges} == {"a-b", "b-a", "b-c", "c-b"}
    assert component.source_version_ids == graph.source_version_ids


def test_site_snaps_to_nearest_genuine_road_node_and_reports_distance():
    graph = _graph(
        [
            RoadNode("near", -100.0, 40.0),
            RoadNode("far", -99.9, 40.0),
        ],
        [],
    )

    snapped = snap_site_to_road(graph, (-99.9999, 40.0))

    assert snapped.node_id == "near"
    assert 0 < snapped.distance_m < 10


def test_dijkstra_preserves_direction_and_disconnected_graphs():
    graph = _graph(
        [
            RoadNode("a", -100, 40),
            RoadNode("b", -99.999, 40),
            RoadNode("isolated", -99.998, 40),
        ],
        [RoadEdge("one-way", "a", "b", 100, "primary")],
    )
    speeds = RoadSpeedScenario("scenario-1", {"primary": 30})

    assert dijkstra_travel_times(graph, "a", speeds) == {"a": 0.0, "b": 0.2}
    assert dijkstra_travel_times(graph, "b", speeds) == {"b": 0.0}


def test_missing_speed_assumption_is_not_replaced_by_a_default():
    graph = _graph(
        [RoadNode("a", -100, 40), RoadNode("b", -99.999, 40)],
        [RoadEdge("e", "a", "b", 100, "primary")],
    )

    with pytest.raises(ValueError, match="No scenario speed supplied for road class 'primary'"):
        dijkstra_travel_times(graph, "a", RoadSpeedScenario("scenario-1", {}))


def test_catchments_use_required_time_thresholds_and_return_valid_polygons():
    graph = _graph(
        [
            RoadNode("a", -100.0, 40.0),
            RoadNode("b", -99.99648, 40.0),
            RoadNode("c", -99.99296, 40.0),
        ],
        [
            RoadEdge("ab", "a", "b", 400, "residential"),
            RoadEdge("ba", "b", "a", 400, "residential"),
            RoadEdge("bc", "b", "c", 400, "residential"),
            RoadEdge("cb", "c", "b", 400, "residential"),
        ],
    )

    result = build_catchments(
        graph,
        site=(-100.0, 40.0),
        speeds=RoadSpeedScenario("scenario-1", {"residential": 30}),
        thresholds_minutes=(1, 2),
        corridor_width_m=50,
    )

    assert [item.threshold_minutes for item in result.catchments] == [1, 2]
    assert result.snap.node_id == "a"
    assert result.catchments[0].reachable_node_ids == ("a", "b")
    assert result.catchments[1].reachable_node_ids == ("a", "b", "c")
    assert result.catchments[0].geometry["type"] in {"Polygon", "MultiPolygon"}
    assert shape(result.catchments[0].geometry).is_valid
    assert result.catchments[0].is_corridor_approximation is True
    assert result.catchments[0].method_id == "road_network_corridor_v1"


def test_catchment_zone_intersections_return_only_intersecting_zones():
    graph = _graph(
        [RoadNode("a", -100.0, 40.0), RoadNode("b", -99.99648, 40.0)],
        [
            RoadEdge("ab", "a", "b", 400, "residential"),
            RoadEdge("ba", "b", "a", 400, "residential"),
        ],
        source_version_ids=("DS-04:fixture-v1",),
    )
    result = build_catchments(
        graph,
        site=(-100.0, 40.0),
        speeds=RoadSpeedScenario("scenario-1", {"residential": 30}),
        thresholds_minutes=(2,),
        corridor_width_m=50,
    )
    inside = {
        "type": "Polygon",
        "coordinates": [[[-100.01, 39.99], [-99.99, 39.99], [-99.99, 40.01], [-100.01, 40.01], [-100.01, 39.99]]],
    }
    outside = {
        "type": "Polygon",
        "coordinates": [[[-99.8, 39.99], [-99.79, 39.99], [-99.79, 40.01], [-99.8, 40.01], [-99.8, 39.99]]],
    }

    intersections = intersect_catchment_zones(
        result.catchments[0].geometry,
        {"inside": inside, "outside": outside},
    )

    assert set(intersections) == {"inside"}
    assert shape(intersections["inside"]).is_valid


def test_invalid_site_or_catchment_parameters_fail_closed():
    graph = _graph([RoadNode("a", -100.0, 40.0)], [])
    speeds = RoadSpeedScenario("scenario-1", {"residential": 30})

    with pytest.raises(ValueError, match="longitude"):
        snap_site_to_road(graph, (181.0, 40.0))
    with pytest.raises(ValueError, match="corridor_width_m"):
        build_catchments(
            graph,
            site=(-100.0, 40.0),
            speeds=speeds,
            thresholds_minutes=(15, 30, 60),
            corridor_width_m=0,
        )


def test_catchment_numeric_outputs_are_registered_with_input_ancestry():
    graph = _graph(
        [RoadNode("a", -100.0, 40.0), RoadNode("b", -99.99648, 40.0)],
        [
            RoadEdge("ab", "a", "b", 400, "residential"),
            RoadEdge("ba", "b", "a", 400, "residential"),
        ],
        source_version_ids=("DS-04:fixture-v1",),
    )
    analysis = build_catchments(
        graph,
        site=(-100.0, 40.0),
        speeds=RoadSpeedScenario("scenario-1", {"residential": 30}),
        thresholds_minutes=(2,),
        corridor_width_m=50,
    )
    ledger = Ledger()
    parents = (
        Quantity(
            id=str(uuid.uuid4()),
            definition_key="site.location",
            value=1,
            unit="dimensionless",
            kind=Kind.SCENARIO,
            evidence_floor=1,
            geo_unit_id="site:test",
            resolution=5,
            as_of="2026-01-01",
            quality_flags=frozenset({"SCENARIO_INPUT"}),
        ),
        Quantity(
            id=str(uuid.uuid4()),
            definition_key="routing.speed.residential",
            value=30,
            unit="km/hour",
            kind=Kind.SCENARIO,
            evidence_floor=1,
            geo_unit_id="site:test",
            resolution=5,
            as_of="2026-01-01",
            quality_flags=frozenset({"SCENARIO_INPUT"}),
        ),
    )
    for parent in parents:
        ledger.register(parent)

    registered = register_catchment_quantities(
        analysis,
        ledger,
        parent_quantities=parents,
        site_geo_unit_id="site:test",
        as_of="2026-01-01",
        model_version="test-version",
    )

    assert "catchment.site_snap_distance" in registered
    assert "catchment.2min.reachable_road_nodes" in registered
    assert "catchment.2min.travel_time.osm_node.a" in registered
    for quantity_id in registered.values():
        quantity = ledger.get(quantity_id)
        assert quantity.kind == Kind.CALCULATED
        assert quantity.parent_ids == tuple(parent.id for parent in parents)
        assert quantity.evidence_floor == 1
        assert quantity.resolution == 5
        assert quantity.quality_flags == frozenset({"SCENARIO_INPUT"})
        assert quantity.source_refs == ("DS-04:fixture-v1",)

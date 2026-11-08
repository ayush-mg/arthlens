import uuid
from datetime import date

import pytest
from backend.arthlens.geo.road_graph import build_road_graph_from_osm
from backend.arthlens.geo.road_repository import PostgresRoadGraphRepository
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    get_session_factory,
)
from backend.arthlens.infra.models import SourceModel, SourceRecordModel, SourceVersionModel
from sqlalchemy import text


@pytest.fixture
def persisted_osm_road_graph():
    engine = get_engine()
    assert_safe_test_database(engine)
    factory = get_session_factory()
    version_id = f"DS-04:road-test:{uuid.uuid4()}"
    way_record_id = f"{version_id}:osm:way:50"
    node_record_ids = {
        f"{version_id}:osm:node:11",
        f"{version_id}:osm:node:12",
        f"{version_id}:osm:node:13",
        f"{version_id}:osm:node:14",
    }

    elements = [
        {"type": "node", "id": 11, "lon": -100.0, "lat": 40.0},
        {"type": "node", "id": 12, "lon": -99.999, "lat": 40.0},
        {"type": "node", "id": 13, "lon": -99.5, "lat": 40.0},
        {"type": "node", "id": 14, "lon": -99.499, "lat": 40.0},
        {
            "type": "way",
            "id": 50,
            "nodes": [11, 12],
            "tags": {"highway": "residential", "oneway": "yes"},
        },
        {
            "type": "way",
            "id": 51,
            "nodes": [13, 14],
            "tags": {"highway": "residential", "oneway": "yes"},
        },
    ]
    with factory() as session:
        source = session.get(SourceModel, "DS-04")
        if source is None:
            session.add(
                SourceModel(
                    id="DS-04",
                    name="OpenStreetMap test source",
                    description="Integration-test source",
                    licence_text="ODbL 1.0",
                    max_age_days=90,
                    status="ACTIVE",
                )
            )
        session.add(
            SourceVersionModel(
                id=version_id,
                source_id="DS-04",
                version="road-test",
                retrieval_date=date.today(),
                content_hash=uuid.uuid4().hex * 2,
                status="ACTIVE",
            )
        )
        records = [
            SourceRecordModel(
                id=record_id,
                source_id="DS-04",
                source_version_id=version_id,
                record_id=record_id.removeprefix(f"{version_id}:"),
                original_fields={},
                normalized_fields={},
                canonical_units={},
                geo_resolved=False,
                license_name="ODbL 1.0",
                attribution="© OpenStreetMap contributors",
            )
            for record_id in node_record_ids | {way_record_id, f"{version_id}:osm:way:51"}
        ]
        session.add_all(records)
        session.commit()

    graph = build_road_graph_from_osm(elements, source_version_id=version_id)
    repository = PostgresRoadGraphRepository(session_factory=factory)
    inserted_count = repository.save_graph(graph, source_version_id=version_id)
    yield repository, version_id, inserted_count

    with factory() as session:
        version = session.get(SourceVersionModel, version_id)
        if version is not None:
            session.delete(version)
            session.commit()


@pytest.mark.integration
def test_postgis_road_graph_is_exactly_provenanced_and_spatially_indexed(
    persisted_osm_road_graph,
):
    repository, version_id, inserted_count = persisted_osm_road_graph
    assert inserted_count == 6

    graph = repository.extract_local_subgraph(
        source_version_id=version_id,
        site=(-100.0, 40.0),
        radius_m=1500,
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source_record_id == f"{version_id}:osm:way:50"
    assert edge.source == "11"
    assert edge.target == "12"
    assert graph.nodes["11"].source_record_id == f"{version_id}:osm:node:11"

    with get_engine().connect() as connection:
        index_definition = connection.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'road_edges' AND indexname = 'ix_road_edges_geometry_gist'"
            )
        ).scalar_one()
    assert "using gist" in index_definition.lower()


@pytest.mark.integration
def test_postgis_road_graph_persistence_is_idempotent(persisted_osm_road_graph):
    repository, version_id, _ = persisted_osm_road_graph
    graph = repository.extract_local_subgraph(
        source_version_id=version_id,
        site=(-100.0, 40.0),
        radius_m=1500,
    )

    assert repository.save_graph(graph, source_version_id=version_id) == 0

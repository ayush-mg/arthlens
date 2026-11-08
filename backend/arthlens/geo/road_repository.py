"""PostGIS persistence and indexed site-local extraction for OSM road graphs."""

from math import isclose
from typing import Optional

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from backend.arthlens.geo.road_graph import (
    RoadEdge,
    RoadGraph,
    RoadNode,
    bbox_around_site,
    build_road_graph_from_osm,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    RoadEdgeModel,
    RoadNodeModel,
    SourceRecordModel,
    SourceVersionModel,
)


class RoadGraphProvenanceError(ValueError):
    """Raised when a road graph cannot be tied to the exact OSM source records."""


class PostgresRoadGraphRepository:
    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or get_session_factory()

    def save_graph(
        self,
        graph: RoadGraph,
        *,
        source_version_id: str,
        session: Optional[Session] = None,
    ) -> int:
        """Persist a graph idempotently; caller may pass the source-ingestion transaction."""
        if graph.source_version_ids != frozenset({source_version_id}):
            raise RoadGraphProvenanceError(
                "Road graph must originate from exactly the requested source_version_id."
            )
        if session is not None:
            return self._save_graph(session, graph, source_version_id)
        with self._session_factory() as owned_session:
            with owned_session.begin():
                return self._save_graph(owned_session, graph, source_version_id)

    def extract_local_subgraph(
        self,
        *,
        source_version_id: str,
        site: tuple[float, float],
        radius_m: float = 15_000,
        session: Optional[Session] = None,
    ) -> RoadGraph:
        """Read only edges intersecting a site bbox through the PostGIS GiST index."""
        west, south, east, north = bbox_around_site(site, radius_m)
        if session is not None:
            return self._extract_local_subgraph(
                session, source_version_id, (west, south, east, north)
            )
        with self._session_factory() as owned_session:
            return self._extract_local_subgraph(
                owned_session, source_version_id, (west, south, east, north)
            )

    def ingest_osm_snapshot(
        self,
        elements,
        *,
        source_version_id: str,
        session: Optional[Session] = None,
    ) -> tuple[RoadGraph, int]:
        """Build and persist the directed graph while retaining exact source-record links."""
        graph = build_road_graph_from_osm(elements, source_version_id=source_version_id)
        if not graph.edges:
            return graph, 0
        inserted = self.save_graph(
            graph,
            source_version_id=source_version_id,
            session=session,
        )
        return graph, inserted

    def _save_graph(self, session: Session, graph: RoadGraph, source_version_id: str) -> int:
        version = session.get(SourceVersionModel, source_version_id)
        if version is None or version.source_id != "DS-04":
            raise RoadGraphProvenanceError(
                f"Source version '{source_version_id}' is not a registered DS-04 version."
            )

        if any(not node.source_record_id for node in graph.nodes.values()) or any(
            not edge.source_record_id for edge in graph.edges
        ):
            raise RoadGraphProvenanceError(
                "Every road node and edge must retain its exact SourceRecord ID."
            )
        source_record_ids = {
            node.source_record_id for node in graph.nodes.values()
        } | {edge.source_record_id for edge in graph.edges}
        records = session.execute(
            select(SourceRecordModel.id).where(
                SourceRecordModel.id.in_(source_record_ids),
                SourceRecordModel.source_version_id == source_version_id,
                SourceRecordModel.source_id == "DS-04",
            )
        ).scalars().all()
        if set(records) != source_record_ids:
            missing = sorted(source_record_ids - set(records))
            raise RoadGraphProvenanceError(
                f"Exact DS-04 source records are missing for road graph: {missing[:3]}."
            )

        inserted = 0
        for node in graph.nodes.values():
            if not node.source_record_id:
                raise RoadGraphProvenanceError(f"Road node '{node.id}' has no source record.")
            node_db_id = _database_node_id(source_version_id, node.id)
            existing = session.get(RoadNodeModel, node_db_id)
            if existing is None:
                session.add(
                    RoadNodeModel(
                        id=node_db_id,
                        source_version_id=source_version_id,
                        osm_node_id=node.id,
                        geometry=from_shape(Point(node.longitude, node.latitude), srid=4326),
                        source_record_id=node.source_record_id,
                    )
                )
                inserted += 1
            elif (
                existing.source_version_id != source_version_id
                or existing.osm_node_id != node.id
                or existing.source_record_id != node.source_record_id
                or not _same_point(session, node_db_id, node.longitude, node.latitude)
            ):
                raise RoadGraphProvenanceError(
                    f"Persisted road node '{node_db_id}' conflicts with its source snapshot."
                )
        session.flush()

        for edge in graph.edges:
            if (
                not edge.source_record_id
                or edge.osm_way_id is None
                or edge.segment_index is None
                or edge.direction not in {"forward", "reverse"}
            ):
                raise RoadGraphProvenanceError(
                    f"Road edge '{edge.id}' is missing OSM way, direction, or source-record metadata."
                )
            from_node_id = _database_node_id(source_version_id, edge.source)
            to_node_id = _database_node_id(source_version_id, edge.target)
            edge_geometry = LineString(
                [
                    (graph.nodes[edge.source].longitude, graph.nodes[edge.source].latitude),
                    (graph.nodes[edge.target].longitude, graph.nodes[edge.target].latitude),
                ]
            )
            existing_edge = session.get(RoadEdgeModel, edge.id)
            if existing_edge is None:
                session.add(
                    RoadEdgeModel(
                        id=edge.id,
                        source_version_id=source_version_id,
                        osm_way_id=edge.osm_way_id,
                        segment_index=edge.segment_index,
                        direction=edge.direction,
                        from_node_id=from_node_id,
                        to_node_id=to_node_id,
                        length_m=edge.length_m,
                        road_class=edge.road_class,
                        geometry=from_shape(edge_geometry, srid=4326),
                        source_record_id=edge.source_record_id,
                    )
                )
                inserted += 1
            elif (
                existing_edge.source_version_id != source_version_id
                or existing_edge.osm_way_id != edge.osm_way_id
                or existing_edge.segment_index != edge.segment_index
                or existing_edge.direction != edge.direction
                or existing_edge.from_node_id != from_node_id
                or existing_edge.to_node_id != to_node_id
                or not isclose(existing_edge.length_m, edge.length_m, rel_tol=1e-12)
                or existing_edge.road_class != edge.road_class
                or existing_edge.source_record_id != edge.source_record_id
            ):
                raise RoadGraphProvenanceError(
                    f"Persisted road edge '{edge.id}' conflicts with its source snapshot."
                )
        return inserted

    def _extract_local_subgraph(
        self,
        session: Session,
        source_version_id: str,
        bounds: tuple[float, float, float, float],
    ) -> RoadGraph:
        from_node = aliased(RoadNodeModel)
        to_node = aliased(RoadNodeModel)
        west, south, east, north = bounds
        envelope = func.ST_MakeEnvelope(west, south, east, north, 4326)
        statement = (
            select(
                RoadEdgeModel,
                from_node,
                to_node,
                func.ST_X(from_node.geometry).label("from_longitude"),
                func.ST_Y(from_node.geometry).label("from_latitude"),
                func.ST_X(to_node.geometry).label("to_longitude"),
                func.ST_Y(to_node.geometry).label("to_latitude"),
            )
            .join(from_node, RoadEdgeModel.from_node_id == from_node.id)
            .join(to_node, RoadEdgeModel.to_node_id == to_node.id)
            .where(
                RoadEdgeModel.source_version_id == source_version_id,
                RoadEdgeModel.geometry.op("&&")(envelope),
            )
            .order_by(RoadEdgeModel.id)
        )
        rows = session.execute(statement).all()

        nodes: dict[str, RoadNode] = {}
        edges: list[RoadEdge] = []
        for row in rows:
            edge, from_row, to_row = row[0], row[1], row[2]
            from_id, to_id = from_row.osm_node_id, to_row.osm_node_id
            nodes.setdefault(
                from_id,
                RoadNode(
                    from_id,
                    row.from_longitude,
                    row.from_latitude,
                    from_row.source_record_id,
                ),
            )
            nodes.setdefault(
                to_id,
                RoadNode(
                    to_id,
                    row.to_longitude,
                    row.to_latitude,
                    to_row.source_record_id,
                ),
            )
            edges.append(
                RoadEdge(
                    id=edge.id,
                    source=from_id,
                    target=to_id,
                    length_m=edge.length_m,
                    road_class=edge.road_class,
                    source_record_id=edge.source_record_id,
                    osm_way_id=edge.osm_way_id,
                    segment_index=edge.segment_index,
                    direction=edge.direction,
                )
            )
        return RoadGraph(nodes, tuple(edges), frozenset({source_version_id}))


def _database_node_id(source_version_id: str, osm_node_id: str) -> str:
    return f"{source_version_id}:node:{osm_node_id}"


def _same_point(
    session: Session,
    node_id: str,
    longitude: float,
    latitude: float,
) -> bool:
    row = session.execute(
        select(
            func.ST_X(RoadNodeModel.geometry),
            func.ST_Y(RoadNodeModel.geometry),
        ).where(RoadNodeModel.id == node_id)
    ).one()
    return isclose(row[0], longitude, abs_tol=1e-12) and isclose(
        row[1], latitude, abs_tol=1e-12
    )

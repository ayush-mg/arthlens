"""Persist directed OSM road graph segments with spatial indexes.

Revision ID: 009_road_graph_spatial_index
Revises: 008_geo_unit_geom_source
Create Date: 2026-11-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "009_road_graph_spatial_index"
down_revision: Union[str, None] = "008_geo_unit_geom_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "road_nodes",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.Text(),
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("osm_node_id", sa.Text(), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column(
            "source_record_id",
            sa.Text(),
            sa.ForeignKey("source_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_version_id",
            "osm_node_id",
            name="uq_road_nodes_version_osm_node",
        ),
    )
    op.create_index(
        "ix_road_nodes_geometry_gist",
        "road_nodes",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "road_edges",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "source_version_id",
            sa.Text(),
            sa.ForeignKey("source_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("osm_way_id", sa.Text(), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column(
            "from_node_id",
            sa.Text(),
            sa.ForeignKey("road_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "to_node_id",
            sa.Text(),
            sa.ForeignKey("road_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("length_m", sa.Double(), nullable=False),
        sa.Column("road_class", sa.Text(), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=False), nullable=False),
        sa.Column(
            "source_record_id",
            sa.Text(),
            sa.ForeignKey("source_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_version_id",
            "osm_way_id",
            "segment_index",
            "direction",
            name="uq_road_edges_version_way_segment_direction",
        ),
        sa.CheckConstraint("length_m > 0", name="check_road_edges_positive_length"),
        sa.CheckConstraint(
            "direction IN ('forward', 'reverse')",
            name="check_road_edges_direction",
        ),
    )
    op.create_index(
        "ix_road_edges_source_nodes",
        "road_edges",
        ["source_version_id", "from_node_id"],
    )
    op.create_index(
        "ix_road_edges_geometry_gist",
        "road_edges",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_road_edges_geometry_gist", table_name="road_edges")
    op.drop_index("ix_road_edges_source_nodes", table_name="road_edges")
    op.drop_table("road_edges")
    op.drop_index("ix_road_nodes_geometry_gist", table_name="road_nodes")
    op.drop_table("road_nodes")

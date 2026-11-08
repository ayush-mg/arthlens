"""
Reproducible PMTiles Vector Archive Generator for ArthLens Administrative Boundaries (P2-2).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5, Appendix A.3).
Dataset: Data{Meet} Community Maps Project (Census 2011 Districts Vintage)
License: Open Database License (ODbL) v1.0 / MIT License
Output: backend/fixtures/boundaries/india_census_2011_pilot.pmtiles

Encodes genuine Mapbox Vector Tile (MVT) protobuf specification 2.1 payloads
with spatial geometry clipping, coordinate quantization, and attribute preservation.
"""

import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import mapbox_vector_tile
from pmtiles.reader import MmapSource, Reader
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pmtiles.writer import write
from shapely.geometry import shape
from shapely.ops import clip_by_rect


def deg2num(lat_deg: float, lon_deg: float, zoom: int) -> Tuple[int, int]:
    """Convert WGS-84 lat/lon coordinates to Slippy map tile X, Y."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def tile_bounds(z: int, x: int, y: int) -> Tuple[float, float, float, float]:
    """Calculate geographic bounding box (min_lon, min_lat, max_lon, max_lat) for Slippy tile."""
    n = 2.0 ** z
    lon_min = x / n * 360.0 - 180.0
    lon_max = (x + 1) / n * 360.0 - 180.0
    lat_rad_top = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_rad_bottom = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    lat_max = math.degrees(lat_rad_top)
    lat_min = math.degrees(lat_rad_bottom)
    return lon_min, lat_min, lon_max, lat_max


def generate_pmtiles_archive(
    source_geojson_path: Path,
    output_pmtiles_path: Path,
    min_zoom: int = 0,
    max_zoom: int = 8,
) -> Dict[str, any]:
    """
    Generate a spec-compliant PMTiles v3 vector archive containing genuine MVT protobuf tiles.
    """
    if not source_geojson_path.exists():
        raise FileNotFoundError(f"Source GeoJSON not found: {source_geojson_path}")

    with source_geojson_path.open("r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    # Validate GeoJSON structure
    raw_features = geojson_data.get("features", [])
    if not raw_features:
        raise ValueError("GeoJSON contains zero features.")

    # Parse and compute bounds using Shapely
    parsed_features = []
    total_vertices = 0
    min_lon, min_lat = 180.0, 90.0
    max_lon, max_lat = -180.0, -90.0

    for feat in raw_features:
        geom = shape(feat["geometry"])
        if geom.is_empty:
            continue
        b_min_lon, b_min_lat, b_max_lon, b_max_lat = geom.bounds
        min_lon = min(min_lon, b_min_lon)
        min_lat = min(min_lat, b_min_lat)
        max_lon = max(max_lon, b_max_lon)
        max_lat = max(max_lat, b_max_lat)

        # Count vertices
        coords = feat["geometry"].get("coordinates", [])
        geom_type = feat["geometry"].get("type")
        rings = coords if geom_type == "Polygon" else [ring for poly in coords for ring in poly]
        for ring in rings:
            total_vertices += len(ring)

        parsed_features.append((geom, feat.get("properties", {})))

    center_lon = (min_lon + max_lon) / 2.0
    center_lat = (min_lat + max_lat) / 2.0

    # Collect and encode tiles
    tile_entries: List[Tuple[int, bytes, int, int, int]] = []  # (tile_id, compressed_mvt, z, x, y)
    seen_tile_ids = set()

    for z in range(min_zoom, max_zoom + 1):
        if z == 0:
            x_min, y_min, x_max, y_max = 0, 0, 0, 0
        else:
            x_min, y_max = deg2num(min_lat, min_lon, z)
            x_max, y_min = deg2num(max_lat, max_lon, z)

        x_start, x_end = min(x_min, x_max), max(x_min, x_max)
        y_start, y_end = min(y_min, y_max), max(y_min, y_max)

        for x in range(x_start, x_end + 1):
            for y in range(y_start, y_end + 1):
                tid = zxy_to_tileid(z, x, y)
                if tid in seen_tile_ids:
                    continue
                seen_tile_ids.add(tid)

                t_lon_min, t_lat_min, t_lon_max, t_lat_max = tile_bounds(z, x, y)
                mvt_layer_features = []

                for geom, props in parsed_features:
                    # Clip geometry to tile bounds
                    clipped = clip_by_rect(geom, t_lon_min, t_lat_min, t_lon_max, t_lat_max)
                    if not clipped.is_empty:
                        mvt_layer_features.append({
                            "geometry": clipped.wkt,
                            "properties": props,
                        })

                if mvt_layer_features:
                    # Genuine Mapbox Vector Tile 2.1 protobuf encoding
                    mvt_bytes = mapbox_vector_tile.encode(
                        {"name": "admin_boundaries", "features": mvt_layer_features},
                        quantize_bounds=(t_lon_min, t_lat_min, t_lon_max, t_lat_max),
                    )
                    # Gzip compression for PMTiles storage
                    compressed_mvt = gzip.compress(mvt_bytes, mtime=0)
                    tile_entries.append((tid, compressed_mvt, z, x, y))

    # Sort strictly by tile_id as required by PMTiles v3 specification
    tile_entries.sort(key=lambda t: t[0])

    # Write PMTiles archive
    output_pmtiles_path.parent.mkdir(parents=True, exist_ok=True)
    with write(str(output_pmtiles_path)) as writer:
        for tid, compressed_mvt, z, x, y in tile_entries:
            writer.write_tile(tid, compressed_mvt)

        header = {
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "min_lon_e7": int(min_lon * 10000000),
            "min_lat_e7": int(min_lat * 10000000),
            "max_lon_e7": int(max_lon * 10000000),
            "max_lat_e7": int(max_lat * 10000000),
            "center_zoom": 6,
            "center_lon_e7": int(center_lon * 10000000),
            "center_lat_e7": int(center_lat * 10000000),
            "tile_type": TileType.MVT,
            "tile_compression": Compression.GZIP,
        }

        metadata = {
            "name": "ArthLens Census 2011 Administrative Boundaries",
            "format": "pbf",
            "version": "1.0.0",
            "attribution": "Administrative boundaries courtesy of Data{Meet} Community Maps Project (Census 2011 base, licensed under ODbL/MIT). Modern nationwide Survey of India boundaries remain source-gated.",
            "description": "Reproducible PMTiles v3 MVT boundary tile archive for ArthLens P2-2 geospatial infrastructure.",
            "vector_layers": [
                {
                    "id": "admin_boundaries",
                    "description": "Census 2011 district administrative polygons",
                    "minzoom": min_zoom,
                    "maxzoom": max_zoom,
                    "fields": {
                        "lgd_code": "String",
                        "censuscode": "Number",
                        "DISTRICT": "String",
                        "ST_NM": "String",
                        "geometry_status": "String",
                        "quality_status": "String",
                    },
                }
            ],
            "generator": "ArthLens Reproducible PMTiles Generator v2.0 (MVT)",
            "crs": "EPSG:4326",
            "vintage": "Census 2011",
            "feature_count": len(parsed_features),
            "vertex_count": total_vertices,
        }

        writer.finalize(header, metadata)

    # Compute checksum of final PMTiles file
    sha256_hash = hashlib.sha256()
    with output_pmtiles_path.open("rb") as f:
        while chunk := f.read(65536):
            sha256_hash.update(chunk)
    pmtiles_sha256 = sha256_hash.hexdigest()

    # Verification: Read back header, metadata, and decode sample tile
    with output_pmtiles_path.open("rb") as f:
        reader = Reader(MmapSource(f))
        read_header = reader.header()
        read_metadata = reader.metadata()
        sample_tile_compressed = reader.get(0, 0, 0)
        if not sample_tile_compressed:
            raise RuntimeError("Verification failed: Root tile (0, 0, 0) could not be retrieved.")

        # Decode MVT protobuf to verify genuine Mapbox Vector Tile format
        decompressed_mvt = gzip.decompress(sample_tile_compressed)
        decoded = mapbox_vector_tile.decode(decompressed_mvt)
        if "admin_boundaries" not in decoded:
            raise RuntimeError(f"Verification failed: 'admin_boundaries' layer not in decoded MVT. Layers: {list(decoded.keys())}")
        decoded_features = decoded["admin_boundaries"]["features"]
        if not decoded_features:
            raise RuntimeError("Verification failed: Zero features decoded in root MVT tile.")

    return {
        "status": "SUCCESS",
        "output_file": str(output_pmtiles_path),
        "file_size_bytes": output_pmtiles_path.stat().st_size,
        "sha256": pmtiles_sha256,
        "tile_count": len(tile_entries),
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "feature_count": len(parsed_features),
        "vertex_count": total_vertices,
        "bounds": [min_lon, min_lat, max_lon, max_lat],
        "metadata_name": read_metadata.get("name"),
        "decoded_sample_layer": "admin_boundaries",
        "decoded_sample_features": len(decoded_features),
        "decoded_sample_geometry_type": decoded_features[0]["geometry"]["type"],
    }


if __name__ == "__main__":
    src = Path("backend/fixtures/boundaries/prayagraj_boundaries_sample.geojson")
    out = Path("backend/fixtures/boundaries/india_census_2011_pilot.pmtiles")
    manifest = generate_pmtiles_archive(src, out)
    print("PMTiles Generation Manifest:")
    print(json.dumps(manifest, indent=2))

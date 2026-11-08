"""
Administrative Boundaries Source Adapter and Ingestion Pipeline (DS-09).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5, Appendix A.3).
Licence: Government Open Data License - India (GODL-India) / ODbL v1.0.
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import urllib.request

from shapely.geometry import shape
from shapely.validation import explain_validity
from sqlalchemy.orm import Session

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.geo import (
    GeometryStatus,
    canonical_district_id,
    canonical_nation_id,
    canonical_state_id,
    canonical_subdistrict_id,
)
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import GeoUnitRepository
from backend.arthlens.infra.models import (
    GeoUnitModel,
    SourceModel,
    SourceRecordModel,
    SourceVersionModel,
)


SUPPORTED_BOUNDARY_GEOMETRY_TYPES: Set[str] = {"Polygon", "MultiPolygon"}
UNSUPPORTED_GEOMETRY_TYPES: Set[str] = {
    "Point",
    "LineString",
    "MultiPoint",
    "MultiLineString",
    "GeometryCollection",
}


def validate_boundary_geometry(geom: Any) -> Tuple[bool, List[str]]:
    """
    Validate that geometry is strictly an areal administrative boundary (Polygon or MultiPolygon).
    Explicitly rejects Point, LineString, MultiPoint, MultiLineString, GeometryCollection,
    unclosed rings, non-numeric coordinates, coordinates out of WGS84 range,
    and artificial axis-aligned bounding boxes.
    """
    errors: List[str] = []
    if not isinstance(geom, dict):
        return False, ["Geometry must be a dictionary."]
    geom_type = geom.get("type")
    if not geom_type:
        return False, ["Geometry missing 'type' field."]
    if geom_type in UNSUPPORTED_GEOMETRY_TYPES or geom_type not in SUPPORTED_BOUNDARY_GEOMETRY_TYPES:
        return False, [
            f"Unsupported geometry type '{geom_type}'. "
            f"Administrative boundaries must be Polygon or MultiPolygon."
        ]
    coords = geom.get("coordinates")
    if not coords or not isinstance(coords, list):
        return False, ["Geometry missing or invalid 'coordinates' list."]

    if geom_type == "Polygon":
        for r_idx, ring in enumerate(coords):
            if not isinstance(ring, list) or len(ring) < 4:
                errors.append(f"Polygon ring {r_idx} must contain at least 4 coordinates.")
            elif ring[0] != ring[-1]:
                errors.append(f"Polygon ring {r_idx} is unclosed: first vertex {ring[0]} != last vertex {ring[-1]}.")
            elif is_axis_aligned_bounding_box(ring):
                errors.append(f"Polygon ring {r_idx} is an artificial axis-aligned bounding box rectangle.")
            else:
                validate_ring_coordinates(ring, errors, f"Polygon ring {r_idx}")
    elif geom_type == "MultiPolygon":
        for p_idx, poly in enumerate(coords):
            if not isinstance(poly, list) or len(poly) == 0:
                errors.append(f"MultiPolygon polygon {p_idx} is empty or not a list.")
                continue
            for r_idx, ring in enumerate(poly):
                if not isinstance(ring, list) or len(ring) < 4:
                    errors.append(f"MultiPolygon poly {p_idx} ring {r_idx} has < 4 coords.")
                elif ring[0] != ring[-1]:
                    errors.append(f"MultiPolygon poly {p_idx} ring {r_idx} is unclosed.")
                elif is_axis_aligned_bounding_box(ring):
                    errors.append(f"MultiPolygon poly {p_idx} ring {r_idx} is an artificial axis-aligned bounding box rectangle.")
                else:
                    validate_ring_coordinates(ring, errors, f"MultiPolygon poly {p_idx} ring {r_idx}")

    # Shapely topological check
    try:
        s = shape(geom)
        if not s.is_valid:
            errors.append(f"Topologically invalid geometry: {explain_validity(s)}")
    except Exception as ex:
        errors.append(f"Geometry parsing error: {ex}")

    return len(errors) == 0, errors


def is_axis_aligned_bounding_box(coords: Union[List[Any], Dict[str, Any]]) -> bool:
    """Detect artificial 4-corner bounding box polygons."""
    if isinstance(coords, dict):
        geom_type = coords.get("type", "")
        raw_coords = coords.get("coordinates", [])
        if geom_type == "Polygon" and raw_coords:
            coords = raw_coords[0]
        elif geom_type == "MultiPolygon" and raw_coords and raw_coords[0]:
            coords = raw_coords[0][0]
        elif "geometry" in coords and isinstance(coords["geometry"], dict):
            return is_axis_aligned_bounding_box(coords["geometry"])
    if isinstance(coords, list) and len(coords) == 5:
        unique_x = {p[0] for p in coords if isinstance(p, (list, tuple)) and len(p) >= 2}
        unique_y = {p[1] for p in coords if isinstance(p, (list, tuple)) and len(p) >= 2}
        return len(unique_x) == 2 and len(unique_y) == 2
    return False


def validate_ring_coordinates(
    ring: List[Any],
    errors: Optional[List[str]] = None,
    label: str = "Ring",
) -> bool:
    """Validate that ring coordinates are valid numbers within geographic WGS84 bounds and form a closed ring."""
    if errors is None:
        errors = []
    if not isinstance(ring, list) or len(ring) < 4:
        errors.append(f"{label} must have at least 4 positions ({len(ring) if isinstance(ring, list) else 0}).")
        return False
    if ring[0] != ring[-1]:
        errors.append(f"{label} is not closed (first vertex {ring[0]} != last vertex {ring[-1]}).")
        return False
    for p_idx, pt in enumerate(ring):
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            errors.append(f"{label} point {p_idx} is not a 2D coordinate tuple.")
            return False
        lon, lat = pt[0], pt[1]
        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
            errors.append(f"{label} point {p_idx} coordinates must be numeric.")
            return False
        if not (-180.0 <= lon <= 180.0):
            errors.append(f"{label} point {p_idx} longitude {lon} is outside [-180, 180].")
            return False
        if not (-90.0 <= lat <= 90.0):
            errors.append(f"{label} point {p_idx} latitude {lat} is outside [-90, 90].")
            return False
    return True


@dataclass
class BoundaryReconciliationReport:
    """Comprehensive auditable report of administrative boundary ingestion and reconciliation."""
    source_id: str = "DS-09"
    source_name: str = "Data{Meet} Community Maps / Census 2011 Administrative Boundaries"
    content_hash: str = ""
    total_features: int = 0
    valid_geometries: int = 0
    invalid_geometries: int = 0
    artificial_bboxes_rejected: int = 0
    matched_units: int = 0
    unmatched_lgd: int = 0
    duplicate_features: int = 0
    persisted_geometries: int = 0
    preserved_existing_geometries: int = 0
    status_counts: Dict[str, int] = field(default_factory=dict)
    vintage_counts: Dict[str, int] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)
    unresolved_records: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    outcome: str = "SUCCESS"

    @property
    def matched_count(self) -> int:
        return self.matched_units

    @property
    def reconciled_count(self) -> int:
        return self.matched_units

    @property
    def duplicate_count(self) -> int:
        return self.duplicate_features


APPROVED_PILOT_SNAPSHOT_SHA256 = "a4ea61c773b99c443bd71a07260881011460eae0600f07be400ef25e2b406c18"
APPROVED_PILOT_GEO_ID = "in:district:120"
APPROVED_PILOT_LGD_CODE = "120"
APPROVED_PILOT_CENSUS_CODE = "175"
APPROVED_PILOT_NAMES: Set[str] = {"PRAYAGRAJ", "ALLAHABAD"}


def determine_boundary_geometry_status(
    content_hash: str,
    collection_provenance: Optional[Dict[str, Any]],
    geo_id: str,
    lgd_code: str,
    census_code: Optional[Union[str, int]] = None,
    name: Optional[str] = None,
    vintage: Optional[str] = None,
    adapter_source_sha256: str = APPROVED_PILOT_SNAPSHOT_SHA256,
) -> Tuple[GeometryStatus, str]:
    """
    Source-bound verification of candidate boundary geometry status.
    Requirements:
    1. Never trust feature-level geometry_status.
    2. GEOMETRY_VERIFIED strictly requires the exact approved DS-09 pilot snapshot (SHA-256 match,
       collection-level source identity DS-09, canonical Prayagraj geographic ID, LGD 120, Census 175,
       and recognized Prayagraj/Allahabad geographic name).
    3. Other Census 2011 geometries are classified as GEOMETRY_HISTORICAL.
    4. Unapproved geometry without supported vintage remains GEOMETRY_UNVALIDATED.
    """
    # 1. Check collection-level provenance and exact snapshot hash
    is_approved_snapshot = (
        bool(content_hash)
        and content_hash.lower() == adapter_source_sha256.lower()
        and collection_provenance is not None
        and isinstance(collection_provenance, dict)
        and collection_provenance.get("source_id") == "DS-09"
    )

    prov_census = str(collection_provenance.get("census_code", "")).strip() if collection_provenance else ""
    c_code_clean = str(census_code).strip() if census_code is not None else prov_census

    prov_name = str(collection_provenance.get("district_name_current", "")).strip().upper() if collection_provenance else ""
    name_clean = str(name).strip().upper() if name else prov_name

    is_approved_pilot = (
        is_approved_snapshot
        and geo_id == APPROVED_PILOT_GEO_ID
        and str(lgd_code).strip() == APPROVED_PILOT_LGD_CODE
        and c_code_clean == APPROVED_PILOT_CENSUS_CODE
        and (name_clean in APPROVED_PILOT_NAMES or any(n in name_clean for n in APPROVED_PILOT_NAMES))
    )

    if is_approved_pilot:
        return GeometryStatus.GEOMETRY_VERIFIED, "Approved DS-09 Prayagraj Pilot Snapshot"

    # 2. Check for supported historical vintage (Census 2011 baseline)
    v_str = str(vintage or "").upper()
    if "2011" in v_str or (collection_provenance and "2011" in str(collection_provenance.get("vintage", ""))):
        return GeometryStatus.GEOMETRY_HISTORICAL, "Census 2011 historical boundary"

    # 3. Unapproved geometry without supported vintage
    return GeometryStatus.GEOMETRY_UNVALIDATED, "Unapproved boundary geometry without supported vintage"


class AdminBoundariesAdapter(SourceAdapter):
    """
    Source Adapter for Official Administrative Boundaries and Polygons (DS-09).
    Reconciles DataMeet Community Maps (Census 2011 vintage baseline) with statutory boundary alignment policies.
    Verified Status: GO for pilot geographic boundaries; modern nationwide vector coverage is explicitly SOURCE-GATED.
    """

    source_id = "DS-09"
    source_name = "Data{Meet} Community Maps / Census 2011 Administrative Boundaries"
    publisher = "Data{Meet} Community Spatial Project (Census 2011 Vintage)"
    official_url = "https://github.com/datameet/maps"
    license_name = "Open Database License (ODbL) v1.0 / MIT License"
    attribution = "Administrative boundaries courtesy of Data{Meet} Community Maps Project (Census 2011 vintage, licensed under ODbL/MIT)."
    max_age_days = 3650  # 10 years (Historical Census vintage)
    as_of_default = "2011-03-01"
    crs = "EPSG:4326"
    source_sha256 = "a4ea61c773b99c443bd71a07260881011460eae0600f07be400ef25e2b406c18"

    def read_local(self, path: Union[Path, str]) -> Dict[str, Any]:
        """Read GeoJSON boundary collection from disk."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            return json.load(f)

    def fetch_live(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch administrative boundary GeoJSON from a remote static release over HTTP.
        params:
            url (str, optional): Remote URL to GeoJSON boundary dataset.
            timeout (int, optional): Request timeout in seconds (default 30).
        """
        url = params.get("url")
        if not url:
            raise ValueError(
                "Survey of India administrative boundary database requires interactive SMS/OTP "
                "authentication and EULA acceptance on onlinemaps.surveyofindia.gov.in. "
                "For automated ingestion, specify 'url' in params to an approved open data repository mirror, "
                "or use ingest_fixture()."
            )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ArthLens/1.0 (Boundary Ingestion Pipeline)"},
        )
        timeout = params.get("timeout", 30)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate GeoJSON structure, coordinate ranges, and RFC 7946 polygon ring closure."""
        errors: List[str] = []
        if isinstance(raw_content, str):
            try:
                raw_content = json.loads(raw_content)
            except Exception as e:
                return False, [f"Invalid JSON string: {e}"]

        if not isinstance(raw_content, dict):
            return False, ["GeoJSON payload must be a JSON object."]

        if raw_content.get("type") != "FeatureCollection":
            return False, [f"Expected FeatureCollection, got {raw_content.get('type')}."]

        features = raw_content.get("features")
        if not isinstance(features, list):
            return False, ["FeatureCollection missing 'features' list."]

        for idx, feat in enumerate(features):
            if not isinstance(feat, dict) or feat.get("type") != "Feature":
                errors.append(f"Feature at index {idx} is invalid.")
                continue

            geom = feat.get("geometry")
            if not geom or not isinstance(geom, dict):
                errors.append(f"Feature at index {idx} missing geometry.")
                continue

            is_geom_valid, geom_errors = validate_boundary_geometry(geom)
            if not is_geom_valid:
                for g_err in geom_errors:
                    errors.append(f"Feature {idx}: {g_err}")

        return len(errors) == 0, errors

    def parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Parse GeoJSON features into RawRecord instances."""
        if isinstance(raw_content, str):
            raw_content = json.loads(raw_content)

        features = raw_content.get("features", [])
        records: List[RawRecord] = []
        for idx, feat in enumerate(features):
            props = feat.get("properties") or {}
            lgd_code = props.get("lgd_code") or f"feat_{idx}"
            rec_id = f"boundary:{lgd_code}"
            records.append(RawRecord(record_id=rec_id, source_id=self.source_id, payload=feat))
        return records

    def normalize_record(self, record: RawRecord) -> NormalizedRecord:
        """Normalize GeoJSON properties and extract spatial boundaries."""
        feat = record.payload
        props = feat.get("properties") or {}
        orig = dict(props)

        geom = feat.get("geometry") or {}
        norm: Dict[str, Any] = {
            "name": props.get("SUBDISTRICT") or props.get("DISTRICT") or props.get("ST_NM"),
            "geometry": geom,
            "lgd_code": props.get("lgd_code"),
            "parent_lgd_code": props.get("parent_lgd_code"),
            "level": props.get("level"),
            "geometry_status": props.get("geometry_status"),
            "vintage": props.get("census_vintage") or "2011",
        }

        return NormalizedRecord(
            record_id=record.record_id,
            raw_record=record,
            original_fields=orig,
            normalized_fields=norm,
            canonical_units={},
            as_of=self.as_of_default,
        )

    def reconcile_geography(self, record: NormalizedRecord) -> GeographicReconciliation:
        """Reconcile boundary polygon to official LGD hierarchy."""
        props = record.original_fields
        lgd_code_raw = props.get("lgd_code")
        if lgd_code_raw is None or not str(lgd_code_raw).strip():
            return GeographicReconciliation(
                resolved=False,
                unresolved_raw_id=record.record_id,
                notes="Missing required 'lgd_code'",
            )

        lgd_code = str(lgd_code_raw).strip()

        level = props.get("level")
        if level is None or level not in (0, 1, 2, 3, 4, 5):
            return GeographicReconciliation(
                resolved=False,
                unresolved_raw_id=record.record_id,
                notes=f"Invalid or missing administrative level: {level}",
            )

        tier_map = {
            0: ResolutionTier.NATION,
            1: ResolutionTier.STATE,
            2: ResolutionTier.DISTRICT,
            3: ResolutionTier.SUBDISTRICT,
            4: ResolutionTier.VILLAGE_URBAN,
            5: ResolutionTier.POINT,
        }
        tier = tier_map[level]

        if tier == ResolutionTier.SUBDISTRICT:
            parent_lgd = props.get("parent_lgd_code")
            if parent_lgd is None or not str(parent_lgd).strip():
                return GeographicReconciliation(
                    resolved=False,
                    unresolved_raw_id=record.record_id,
                    notes="Sub-district boundary feature missing required 'parent_lgd_code'",
                )
            geo_id = canonical_subdistrict_id(str(parent_lgd).strip(), lgd_code)
        elif tier == ResolutionTier.DISTRICT:
            geo_id = canonical_district_id(lgd_code)
        elif tier == ResolutionTier.STATE:
            geo_id = canonical_state_id(lgd_code)
        elif tier == ResolutionTier.NATION:
            geo_id = canonical_nation_id()
        else:
            geo_id = f"in:unit:{lgd_code}"

        return GeographicReconciliation(
            resolved=True,
            geo_unit_id=geo_id,
            resolution_tier=tier,
            notes=f"Reconciled boundary polygon for LGD code {lgd_code}",
        )

    def extract_quantities(
        self,
        record: NormalizedRecord,
        recon: GeographicReconciliation,
        quality: QualityAssessment,
    ) -> List[Quantity]:
        """Administrative boundaries represent spatial polygons rather than numeric quantities."""
        return []


class AdminBoundaryIngestionService:
    """
    Executes reproducible, idempotent administrative boundary ingestion and PostGIS persistence.
    Enforces canonical LGD reconciliation, PostGIS ST_IsValid spatial verification,
    artificial bounding box rejection, and non-destructive persistence.
    """

    def __init__(
        self,
        session_factory: Optional[Callable[[], Session]] = None,
        geo_repo: Optional[GeoUnitRepository] = None,
    ) -> None:
        if session_factory is None:
            from backend.arthlens.infra.database import get_session_factory
            self.session_factory = get_session_factory()
        else:
            self.session_factory = session_factory

        if geo_repo is None:
            from backend.arthlens.infra.repositories import PostgresGeoUnitRepository
            self.geo_repo = PostgresGeoUnitRepository(session_factory=self.session_factory)
        else:
            self.geo_repo = geo_repo
        self.adapter = AdminBoundariesAdapter()

    def ingest(
        self,
        source_input: Optional[Union[Path, str]] = None,
        is_local: bool = True,
        fetch_params: Optional[Dict[str, Any]] = None,
        default_vintage: str = "Census 2011",
        as_of: str = "2011-03-01",
    ) -> BoundaryReconciliationReport:
        if source_input is None:
            source_input = (
                Path(__file__).resolve().parents[3]
                / "fixtures"
                / "boundaries"
                / "prayagraj_boundaries_sample.geojson"
            )
        return self.ingest_boundaries(
            source_input=source_input,
            is_local=is_local,
            fetch_params=fetch_params,
            default_vintage=default_vintage,
            as_of=as_of,
        )

    def ingest_boundaries(
        self,
        source_input: Union[Path, str],
        is_local: bool = True,
        fetch_params: Optional[Dict[str, Any]] = None,
        default_vintage: str = "Census 2011",
        as_of: str = "2011-03-01",
    ) -> BoundaryReconciliationReport:
        """
        Execute reproducible, idempotent boundary ingestion workflow from local file or remote source.
        Persists validated geometries to PostGIS and records provenance in sources/source_versions/source_records.
        """
        if is_local:
            p = Path(source_input)
            if not p.exists():
                raise FileNotFoundError(f"Boundary fixture not found at: {p}")
            with p.open("rb") as f:
                raw_bytes = f.read()
            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            raw_content = self.adapter.read_local(p)
        else:
            raw_content = self.adapter.fetch_live(fetch_params or {"url": str(source_input)})
            serialized = json.dumps(raw_content, sort_keys=True).encode("utf-8")
            content_hash = hashlib.sha256(serialized).hexdigest()

        report = BoundaryReconciliationReport(
            source_id=self.adapter.source_id,
            source_name=self.adapter.source_name,
            content_hash=content_hash,
        )

        # 1. Schema and structural validation
        is_valid_schema, schema_errors = self.adapter.validate_schema(raw_content)
        if not is_valid_schema:
            report.invalid_geometries += len(schema_errors)
            report.anomalies.extend(schema_errors)
            return report

        # 2. Process and validate all features in GeoJSON before transaction
        features = raw_content.get("features", [])
        report.total_features = len(features)
        seen_geo_ids: Set[str] = set()
        prepared_features: List[Dict[str, Any]] = []

        for idx, feat in enumerate(features):
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            lgd_code_raw = props.get("lgd_code")

            if lgd_code_raw is None or not str(lgd_code_raw).strip():
                report.unmatched_lgd += 1
                report.unresolved_records.append({
                    "feature_index": idx,
                    "reason": "MISSING_LGD_CODE",
                    "properties": props,
                })
                continue

            lgd_code = str(lgd_code_raw).strip()
            level = props.get("level")
            if level is None:
                report.unmatched_lgd += 1
                report.unresolved_records.append({
                    "feature_index": idx,
                    "reason": "MISSING_LEVEL",
                    "properties": props,
                })
                continue
            if isinstance(level, str) and level.isdigit():
                level = int(level)

            tier_map = {
                0: ResolutionTier.NATION,
                1: ResolutionTier.STATE,
                2: ResolutionTier.DISTRICT,
                3: ResolutionTier.SUBDISTRICT,
            }
            if level not in tier_map:
                report.unmatched_lgd += 1
                report.unresolved_records.append({
                    "feature_index": idx,
                    "reason": f"UNSUPPORTED_OR_INVALID_LEVEL_{level}",
                    "properties": props,
                })
                continue
            tier = tier_map[level]

            if tier == ResolutionTier.DISTRICT:
                geo_id = canonical_district_id(lgd_code)
            elif tier == ResolutionTier.STATE:
                geo_id = canonical_state_id(lgd_code)
            elif tier == ResolutionTier.SUBDISTRICT:
                parent_lgd = str(props.get("parent_lgd_code", "")).strip()
                if not parent_lgd:
                    report.unmatched_lgd += 1
                    report.unresolved_records.append({
                        "feature_index": idx,
                        "lgd_code": lgd_code,
                        "reason": "SUBDISTRICT_MISSING_PARENT_LGD",
                    })
                    continue
                geo_id = canonical_subdistrict_id(parent_lgd, lgd_code)
            elif tier == ResolutionTier.NATION:
                geo_id = canonical_nation_id()
            else:
                geo_id = f"in:unit:{lgd_code}"

            # Verify unit exists in database
            existing = self.geo_repo.get_unit(geo_id)
            if not existing:
                report.unmatched_lgd += 1
                report.unresolved_records.append({
                    "feature_index": idx,
                    "lgd_code": lgd_code,
                    "geo_id": geo_id,
                    "name": props.get("DISTRICT") or props.get("ST_NM") or props.get("SUBDISTRICT"),
                    "reason": "UNMATCHED_IN_LGD_HIERARCHY",
                })
                continue

            # Detect duplicates within the dataset
            if geo_id in seen_geo_ids:
                report.duplicate_features += 1
                report.anomalies.append(f"Duplicate boundary feature for {geo_id} (LGD {lgd_code}) in dataset.")
                continue
            seen_geo_ids.add(geo_id)

            # Strict Boundary Geometry Validation (Polygon/MultiPolygon, ring closure, bounds, non-AABB)
            is_valid_geom, geom_errs = validate_boundary_geometry(geom)
            if not is_valid_geom:
                report.invalid_geometries += 1
                report.anomalies.extend([f"Feature {idx} ({geo_id}): {e}" for e in geom_errs])
                continue

            # PostGIS ST_IsValid check
            is_pg_valid, pg_reason = self.geo_repo.verify_geometry_validity(geom)
            if not is_pg_valid:
                report.invalid_geometries += 1
                report.anomalies.append(f"PostGIS ST_IsValid rejection for {geo_id}: {pg_reason}")
                continue

            report.valid_geometries += 1
            report.matched_units += 1

            # 2. Extract collection-level provenance and verify status in a source-bound manner
            collection_provenance = raw_content.get("provenance") if isinstance(raw_content, dict) else None
            census_code_val = props.get("censuscode") or props.get("census_code")
            name_val = props.get("DISTRICT") or props.get("ST_NM") or props.get("SUBDISTRICT")
            vintage_val = props.get("census_vintage") or default_vintage

            status_to_assign, status_reason = determine_boundary_geometry_status(
                content_hash=content_hash,
                collection_provenance=collection_provenance,
                geo_id=geo_id,
                lgd_code=lgd_code,
                census_code=census_code_val,
                name=name_val,
                vintage=vintage_val,
                adapter_source_sha256=self.adapter.source_sha256,
            )

            # FIX 4: Only the approved Prayagraj snapshot may receive its registered Census 2011 vintage.
            # Other unverified snapshots must not inherit that vintage automatically.
            is_verified_pilot = (status_to_assign == GeometryStatus.GEOMETRY_VERIFIED)
            if is_verified_pilot:
                assigned_vintage = "Census 2011"
                assigned_as_of = "2011-03-01"
            elif props.get("census_vintage") and "2011" in str(props.get("census_vintage")):
                assigned_vintage = str(props.get("census_vintage"))
                assigned_as_of = "2011-03-01"
            else:
                assigned_vintage = None
                assigned_as_of = None

            prepared_features.append({
                "geo_id": geo_id,
                "geom": geom,
                "status_to_assign": status_to_assign,
                "lgd_code": lgd_code,
                "level": level,
                "tier": tier,
                "props": props,
                "vintage": assigned_vintage,
                "as_of": assigned_as_of,
            })

        # 3. Atomic persistence across geometry, source, and source records in a single transaction
        v_id = f"{self.adapter.source_id}:{content_hash[:16]}"
        pending_persisted = 0
        pending_preserved = 0
        pending_status_counts: Dict[str, int] = {}

        try:
            with self.session_factory() as session:
                with session.begin():
                    src = session.get(SourceModel, self.adapter.source_id)
                    if not src:
                        src = SourceModel(
                            id=self.adapter.source_id,
                            name=self.adapter.source_name,
                            description=self.adapter.attribution,
                            licence_text=self.adapter.license_name,
                            max_age_days=self.adapter.max_age_days,
                            status="ACTIVE",
                        )
                        session.add(src)
                        session.flush()

                    sver = session.get(SourceVersionModel, v_id)
                    if not sver:
                        sver = SourceVersionModel(
                            id=v_id,
                            source_id=self.adapter.source_id,
                            version=default_vintage,
                            retrieval_date=date.today(),
                            content_hash=content_hash,
                            source_url=self.adapter.official_url,
                            status="ACTIVE",
                        )
                        session.add(sver)
                        session.flush()

                    for feat_data in prepared_features:
                        geo_id = feat_data["geo_id"]
                        geom = feat_data["geom"]
                        status_to_assign = feat_data["status_to_assign"]
                        lgd_code = feat_data["lgd_code"]
                        level = feat_data["level"]
                        tier = feat_data["tier"]
                        props = feat_data["props"]

                        feat_vintage = feat_data.get("vintage")
                        feat_as_of = feat_data.get("as_of")
                        sr_id = f"{v_id}:boundary:{lgd_code}"
                        sr = session.get(SourceRecordModel, sr_id)
                        if not sr:
                            sr = SourceRecordModel(
                                id=sr_id,
                                source_id=self.adapter.source_id,
                                source_version_id=v_id,
                                record_id=f"boundary:{lgd_code}",
                                original_fields=dict(props),
                                normalized_fields={
                                    "name": props.get("DISTRICT") or props.get("ST_NM") or props.get("SUBDISTRICT"),
                                    "lgd_code": lgd_code,
                                    "level": level,
                                    "geometry_status": status_to_assign.value,
                                    "vintage": feat_vintage,
                                },
                                canonical_units={},
                                geo_resolved=True,
                                geo_unit_id=geo_id,
                                resolution_tier=int(tier),
                                as_of=date.fromisoformat(feat_as_of) if feat_as_of else None,
                                license_name=self.adapter.license_name,
                                attribution=self.adapter.attribution,
                            )
                            session.add(sr)
                            session.flush()

                        persisted = self.geo_repo.update_geometry(
                            unit_id=geo_id,
                            geometry=geom,
                            geometry_status=status_to_assign,
                            preserve_existing=True,
                            geometry_source_record_id=sr_id,
                            session=session,
                        )
                        if persisted:
                            pending_persisted += 1
                            pending_status_counts[status_to_assign.value] = (
                                pending_status_counts.get(status_to_assign.value, 0) + 1
                            )
                        else:
                            pending_preserved += 1

            # Transaction committed successfully! Apply counters to report
            report.persisted_geometries += pending_persisted
            report.preserved_existing_geometries += pending_preserved
            for st, cnt in pending_status_counts.items():
                report.status_counts[st] = report.status_counts.get(st, 0) + cnt

        except Exception as tx_err:
            report.success = False
            report.outcome = "FAILED"
            report.anomalies.append(f"Atomic boundary persistence failure: {tx_err}")

        if report.persisted_geometries == 0 and report.preserved_existing_geometries == 0:
            report.success = False
            report.outcome = "FAILED"
        elif report.invalid_geometries > 0 or report.unmatched_lgd > 0:
            report.outcome = "PARTIAL"
        else:
            report.outcome = "SUCCESS"

        return report

"""
OpenStreetMap Source Adapter (DS-04).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5, Appendix A.3).
Licence: Open Database Commons Open Database License (ODbL 1.0).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.parse
import urllib.request

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.quantity import Quantity


class OpenStreetMapAdapter(SourceAdapter):
    """
    Source Adapter for OpenStreetMap Overpass API and Geofabrik extracts (DS-04).
    Verified Status: GO (Approved with Completeness Caveat).
    """

    source_id = "DS-04"
    source_name = "OpenStreetMap Overpass API / Geofabrik Regional Extracts"
    publisher = "OpenStreetMap Foundation and Contributors"
    official_url = "https://www.openstreetmap.org"
    license_name = "ODbL 1.0"
    attribution = "© OpenStreetMap contributors. Open Database Commons ODbL 1.0. https://www.openstreetmap.org/copyright"
    max_age_days = 90
    as_of_default = None

    def read_local(self, path: Union[Path, str]) -> Dict[str, Any]:
        """Read OSM Overpass JSON fixture from disk."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            return json.load(f)

    def fetch_live(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch OSM data live via Overpass API for a bounded box.
        params:
            bbox: Tuple of (min_lon, min_lat, max_lon, max_lat)
            timeout: Query timeout in seconds (default 25)
        """
        min_lon, min_lat, max_lon, max_lat = params["bbox"]
        timeout = params.get("timeout", 25)
        query = (
            f"[out:json][timeout:{timeout}];"
            f"("
            f"node({min_lat},{min_lon},{max_lat},{max_lon});"
            f"way({min_lat},{min_lon},{max_lat},{max_lon});"
            f");"
            f"out body;>;out skel qt;"
        )
        url = "https://overpass-api.de/api/interpreter"
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"User-Agent": "ArthLens/1.0 (academic/portfolio data ingestion pipeline)"},
        )
        with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate Overpass JSON elements, types, and coordinate bounds."""
        errors: List[str] = []
        if isinstance(raw_content, str):
            try:
                raw_content = json.loads(raw_content)
            except Exception as e:
                return False, [f"Invalid JSON string: {e}"]

        if not isinstance(raw_content, dict):
            return False, ["OSM payload must be a JSON dictionary."]

        elements = raw_content.get("elements")
        if not isinstance(elements, list):
            return False, ["OSM payload must contain an 'elements' list."]

        for idx, el in enumerate(elements):
            if not isinstance(el, dict):
                errors.append(f"Element at index {idx} is not a dictionary.")
                continue

            el_type = el.get("type")
            if el_type not in ("node", "way", "relation"):
                errors.append(f"Element at index {idx} has unknown type '{el_type}'.")

            if el.get("id") is None:
                errors.append(f"Element at index {idx} is missing an 'id'.")

            # Validate coordinate bounds for nodes
            if el_type == "node":
                lat = el.get("lat")
                lon = el.get("lon")
                if lat is None or lon is None:
                    errors.append(f"Node {el.get('id')} missing lat/lon coordinates.")
                else:
                    try:
                        lat_f = float(lat)
                        lon_f = float(lon)
                        if not (-90.0 <= lat_f <= 90.0):
                            errors.append(f"Node {el.get('id')} has invalid latitude: {lat_f} (must be between -90 and 90).")
                        if not (-180.0 <= lon_f <= 180.0):
                            errors.append(f"Node {el.get('id')} has invalid longitude: {lon_f} (must be between -180 and 180).")
                    except (ValueError, TypeError):
                        errors.append(f"Node {el.get('id')} has non-numeric lat/lon.")

        return len(errors) == 0, errors

    def parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Parse OSM elements into RawRecord instances."""
        if isinstance(raw_content, str):
            raw_content = json.loads(raw_content)

        elements = raw_content.get("elements", [])
        records: List[RawRecord] = []
        for el in elements:
            rec_id = f"osm:{el.get('type')}:{el.get('id')}"
            records.append(RawRecord(record_id=rec_id, source_id=self.source_id, payload=el))
        return records

    def normalize_record(self, record: RawRecord) -> NormalizedRecord:
        """Normalize OSM elements into physical facility domain attributes."""
        el = record.payload
        tags = el.get("tags") or {}
        orig = dict(tags)
        orig["id"] = str(el.get("id"))
        orig["type"] = str(el.get("type"))
        if "lat" in el:
            orig["lat"] = str(el.get("lat"))
        if "lon" in el:
            orig["lon"] = str(el.get("lon"))

        norm: Dict[str, Any] = {}
        if "name" in tags:
            norm["facility.name"] = tags["name"]
        if "brand" in tags:
            norm["facility.brand"] = tags["brand"]

        category = tags.get("amenity") or tags.get("shop") or tags.get("highway")
        if category:
            norm["facility.category"] = category

        if "lat" in el and "lon" in el:
            norm["coordinates"] = (float(el["lon"]), float(el["lat"]))

        return NormalizedRecord(
            record_id=record.record_id,
            raw_record=record,
            original_fields=orig,
            normalized_fields=norm,
            canonical_units={},
            as_of=None,
        )

    def reconcile_geography(self, record: NormalizedRecord) -> GeographicReconciliation:
        """Reconcile OSM elements to geographic coordinates / POINT tier."""
        el = record.raw_record.payload
        el_type = el.get("type")
        el_id = el.get("id")

        return GeographicReconciliation(
            resolved=True,
            geo_unit_id=f"osm:{el_type}:{el_id}",
            resolution_tier=ResolutionTier.POINT,
            notes=f"OSM {el_type} entity",
        )

    def extract_quantities(
        self,
        record: NormalizedRecord,
        recon: GeographicReconciliation,
        quality: QualityAssessment,
    ) -> List[Quantity]:
        """
        OSM entities represent physical facilities and spatial geometries rather than
        macroeconomic ledger quantities. Returns an empty list of quantities.
        """
        return []


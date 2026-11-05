"""
Administrative Boundaries Source Adapter (DS-09).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5, Appendix A.3).
Licence: Government Open Data License - India (GODL-India).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.quantity import Quantity


class AdminBoundariesAdapter(SourceAdapter):
    """
    Source Adapter for Official Administrative Boundaries and Polygons (DS-09).
    Verified Status: GO (Approved for Atlas Display & Spatial Boundaries).
    """

    source_id = "DS-09"
    source_name = "Survey of India / LGD Administrative Boundaries"
    publisher = "Survey of India / Local Government Directory (MoPR)"
    official_url = "https://surveyofindia.gov.in"
    license_name = "Government Open Data License - India (GODL)"
    attribution = "Source: Administrative boundaries based on Survey of India and Local Government Directory (MoPR), Government of India."
    max_age_days = 1825  # 5 years
    as_of_default = "2024-01-01"

    def read_local(self, path: Union[Path, str]) -> Dict[str, Any]:
        """Read GeoJSON boundary collection from disk."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            return json.load(f)

    def fetch_live(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Administrative boundaries are sourced from verified official master shapefiles/GeoJSON."""
        raise NotImplementedError("Live spatial vector tiling provided via PMTiles/PostGIS backend.")

    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate GeoJSON structure and RFC 7946 polygon ring closure."""
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

            geom_type = geom.get("type")
            coords = geom.get("coordinates")
            if geom_type == "Polygon" and isinstance(coords, list):
                for r_idx, ring in enumerate(coords):
                    if not isinstance(ring, list) or len(ring) < 4:
                        errors.append(f"Feature {idx} ring {r_idx} must contain at least 4 coordinates.")
                    elif ring[0] != ring[-1]:
                        errors.append(
                            f"Feature {idx} ring {r_idx} is unclosed: first coordinate {ring[0]} != last coordinate {ring[-1]}."
                        )
            elif geom_type == "MultiPolygon" and isinstance(coords, list):
                for p_idx, poly in enumerate(coords):
                    if isinstance(poly, list):
                        for r_idx, ring in enumerate(poly):
                            if not isinstance(ring, list) or len(ring) < 4:
                                errors.append(f"Feature {idx} poly {p_idx} ring {r_idx} has < 4 coords.")
                            elif ring[0] != ring[-1]:
                                errors.append(f"Feature {idx} poly {p_idx} ring {r_idx} is unclosed.")

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
            "level": props.get("level", 2),
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
        lgd_code = str(props.get("lgd_code", ""))
        level = props.get("level", 2)

        tier_map = {
            0: ResolutionTier.NATION,
            1: ResolutionTier.STATE,
            2: ResolutionTier.DISTRICT,
            3: ResolutionTier.SUBDISTRICT,
            4: ResolutionTier.VILLAGE_URBAN,
            5: ResolutionTier.POINT,
        }
        tier = tier_map.get(level, ResolutionTier.DISTRICT)

        parent_lgd = props.get("parent_lgd_code")
        if parent_lgd:
            geo_id = f"in:lgd:{parent_lgd}:{lgd_code}"
        else:
            geo_id = f"in:lgd:{lgd_code}"

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
        """
        Administrative boundaries represent spatial polygons rather than numeric
        ledger quantities. Returns an empty list of quantities.
        """
        return []


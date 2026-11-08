"""
Central Government Scheme Guidelines Source Adapter (DS-08).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.5, Appendix A.3).
Licence: Government Open Data License - India (GODL-India).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from datetime import date
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.request
import uuid

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import canonical_nation_id
from backend.arthlens.domain.quantity import Quantity


class SchemeGuidelinesAdapter(SourceAdapter):
    """
    Source Adapter for Government Entrepreneurship and MSME Scheme Guidelines (DS-08).
    Verified Status: GO (Verified 42 parameters & hashed PDFs).
    """

    source_id = "DS-08"
    source_name = "Central Government Entrepreneurship & MSME Scheme Guidelines"
    publisher = "Ministry of Food Processing Industries, Ministry of MSME, and Department of Financial Services"
    official_url = "https://pmfme.mofpi.gov.in"
    license_name = "Government Open Data License - India (GODL)"
    attribution = "Source: Ministry of Food Processing Industries (MoFPI), Ministry of Micro, Small & Medium Enterprises (MoMSME), and Department of Financial Services (DFS), Ministry of Finance, Government of India."
    max_age_days = None  # Statutory policy rules do not have an invented expiration shelf-life unless gazetted
    as_of_default = None  # Never apply a blanket fallback date; preserve explicit document dates

    def read_local(self, path: Union[Path, str]) -> Dict[str, Any]:
        """Read scheme parameter JSON fixture from disk."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            return json.load(f)

    def fetch_live(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch statutory scheme parameters from a remote notification/gazette JSON release over HTTP.
        params:
            url (str, optional): Remote URL to scheme guidelines parameter matrix.
            timeout (int, optional): Request timeout in seconds (default 20).
        """
        url = params.get("url")
        if not url:
            raise ValueError(
                "Statutory scheme guidelines are gazetted in official PDF documents. "
                "Specify 'url' in params to retrieve a remote parameter matrix or verified PDF, "
                "or use ingest_fixture()."
            )
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ArthLens/1.0 (Scheme Parameters Pipeline)"},
        )
        timeout = params.get("timeout", 20)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate parameter schema and structural types."""
        errors: List[str] = []
        if isinstance(raw_content, str):
            try:
                raw_content = json.loads(raw_content)
            except Exception as e:
                return False, [f"Invalid JSON string: {e}"]

        if not isinstance(raw_content, dict):
            return False, ["Scheme guidelines payload must be a JSON object."]

        parameters = raw_content.get("parameters")
        if not isinstance(parameters, list):
            return False, ["Scheme guidelines payload must contain a 'parameters' list."]

        for idx, param in enumerate(parameters):
            if not isinstance(param, dict):
                errors.append(f"Parameter at index {idx} is not a dictionary.")
                continue

            if not param.get("definition_key"):
                errors.append(f"Parameter at index {idx} missing 'definition_key'.")

            val = param.get("value")
            if val is None or not isinstance(val, (int, float)):
                errors.append(f"Parameter at index {idx} has invalid numeric value: {val}.")

            if not param.get("unit"):
                errors.append(f"Parameter at index {idx} missing 'unit'.")

        return len(errors) == 0, errors

    def parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Parse scheme parameters into RawRecord instances."""
        if isinstance(raw_content, str):
            raw_content = json.loads(raw_content)

        parameters = raw_content.get("parameters", [])
        records: List[RawRecord] = []
        for idx, p in enumerate(parameters):
            rec_id = f"scheme:{p.get('scheme_id', 'gen')}:{p.get('definition_key', idx)}"
            records.append(RawRecord(record_id=rec_id, source_id=self.source_id, payload=p))
        return records

    def normalize_record(self, record: RawRecord) -> NormalizedRecord:
        """Normalize parameter fields to ArthLens schema definitions."""
        p = record.payload
        orig = dict(p)

        def_key = p["definition_key"]
        val = float(p["value"])
        unit = p["unit"]

        norm = {def_key: val}
        units = {def_key: unit}

        # Preserve publication dates, effective dates, and retrieval dates separately
        pub_date = p.get("publication_date")
        eff_date = p.get("effective_from") or p.get("effective_date")
        ret_date = p.get("retrieval_date")
        as_of = p.get("as_of") or eff_date or pub_date or None

        return NormalizedRecord(
            record_id=record.record_id,
            raw_record=record,
            original_fields=orig,
            normalized_fields=norm,
            canonical_units=units,
            as_of=as_of,
            metadata={
                "document": p.get("document"),
                "page": p.get("page"),
                "clause": p.get("clause"),
                "mechanism": p.get("mechanism"),
                "publication_date": pub_date,
                "effective_date": eff_date,
                "retrieval_date": ret_date,
            },
        )

    def reconcile_geography(self, record: NormalizedRecord) -> GeographicReconciliation:
        """Central government MSME schemes apply nationwide (NATION tier)."""
        return GeographicReconciliation(
            resolved=True,
            geo_unit_id=canonical_nation_id(),
            resolution_tier=ResolutionTier.NATION,
            notes="Nationwide central government scheme policy rule",
        )

    def extract_quantities(
        self,
        record: NormalizedRecord,
        recon: GeographicReconciliation,
        quality: QualityAssessment,
        version_id: Optional[str] = None,
        retrieval_date: Optional[str] = None,
    ) -> List[Quantity]:
        """
        Extract immutable Quantity domain models.
        Scheme parameters are Kind.POLICY_RULE with evidence_floor=4.
        """
        quantities: List[Quantity] = []
        as_of = str(record.as_of) if record.as_of else ""
        p = record.raw_record.payload
        v_id = version_id or f"{self.source_id}:snapshot"
        ret_date = retrieval_date or p.get("retrieval_date") or date.today().isoformat()

        for def_key, val in record.normalized_fields.items():
            unit = record.canonical_units.get(def_key, "dimensionless")
            q_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.source_id}:{recon.geo_unit_id}:{def_key}:{as_of}:{float(val)}"))

            doc_ref = f"doc:{p.get('document', '')}:p{p.get('page', '')}"
            q = Quantity(
                id=q_id,
                definition_key=def_key,
                value=float(val),
                unit=unit,
                kind=Kind.POLICY_RULE,
                evidence_floor=4,
                geo_unit_id=recon.geo_unit_id or canonical_nation_id(),
                resolution=int(ResolutionTier.NATION),
                as_of=as_of,
                uncertainty="EXACT",
                source_refs=((v_id, doc_ref, ret_date),),
                quality_flags=frozenset(),
                license_meta=self.license_name,
            )
            quantities.append(q)

        return quantities


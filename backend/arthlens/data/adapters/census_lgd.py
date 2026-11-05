"""
Census 2011 and Local Government Directory (LGD) Crosswalk Source Adapter (DS-05).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.4, 7.5, Appendix A.3).
Licence: Government Open Data License - India (GODL-India).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    NormalizedRecord,
    QualityAssessment,
    RawRecord,
)
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.geo import canonical_district_id, canonical_subdistrict_id
from backend.arthlens.domain.quantity import Quantity


class CensusLGDAdapter(SourceAdapter):
    """
    Source Adapter for Census 2011 PCA & LGD Administrative Crosswalk (DS-05).
    Verified Status: GO (Approved for Core MVP Foundation).
    """

    source_id = "DS-05"
    source_name = "Census of India 2011 Primary Census Abstract & LGD Crosswalk"
    publisher = "Office of the Registrar General & Census Commissioner, India (ORGI) & Ministry of Panchayati Raj (MoPR)"
    official_url = "https://censusindia.gov.in / https://lgdirectory.gov.in"
    license_name = "Government Open Data License - India (GODL)"
    attribution = "Source: Primary Census Abstract 2011 (ORGI) & Local Government Directory (MoPR), Government of India."
    max_age_days = 3650  # 10 years; 2011 census is strictly stale
    as_of_default = "2011-03-01"

    def read_local(self, path: Union[Path, str]) -> List[Dict[str, str]]:
        """Read CSV crosswalk table from disk, ignoring comment lines."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(line for line in f if not line.strip().startswith("#"))
            return [dict(row) for row in reader]

    def fetch_live(self, params: Dict[str, Any]) -> List[Dict[str, str]]:
        """Official Census 2011 data is distributed via static files/archives."""
        raise NotImplementedError("Live dynamic API not supported for historical Census 2011 PCA.")

    def validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Validate CSV columns, numeric constraints, and non-negative populations."""
        errors: List[str] = []
        rows: List[Dict[str, Any]] = []

        if isinstance(raw_content, str):
            lines = [l for l in raw_content.splitlines() if not l.strip().startswith("#")]
            reader = csv.DictReader(lines)
            rows = [dict(r) for r in reader]
        elif isinstance(raw_content, list):
            rows = raw_content
        else:
            return False, ["Census/LGD payload must be a CSV string or list of row dicts."]

        if not rows:
            return False, ["Payload contains no rows."]

        required_cols = {"lgd_state_code", "lgd_district_code", "total_population"}
        header = set(rows[0].keys())
        missing = required_cols - header
        if missing:
            errors.append(f"Missing required CSV columns: {missing}")

        for idx, row in enumerate(rows):
            # Check negative populations
            for pop_col in ("total_population", "male_population", "female_population", "total_households"):
                val_str = row.get(pop_col)
                if val_str is not None and val_str.strip():
                    try:
                        val = float(val_str)
                        if val < 0:
                            errors.append(f"Row {idx}: {pop_col} cannot be negative (got {val}). Validation failed.")
                    except ValueError:
                        errors.append(f"Row {idx}: {pop_col} has non-numeric value '{val_str}'.")

        return len(errors) == 0, errors

    def parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Parse CSV rows into RawRecord instances."""
        rows: List[Dict[str, Any]] = []
        if isinstance(raw_content, str):
            lines = [l for l in raw_content.splitlines() if not l.strip().startswith("#")]
            reader = csv.DictReader(lines)
            rows = [dict(r) for r in reader]
        elif isinstance(raw_content, list):
            rows = raw_content

        records: List[RawRecord] = []
        for idx, row in enumerate(rows):
            rec_id = f"census_2011:row_{idx}"
            records.append(RawRecord(record_id=rec_id, source_id=self.source_id, payload=row))
        return records

    def normalize_record(self, record: RawRecord) -> NormalizedRecord:
        """Normalize Census/LGD attributes to ArthLens demographic quantity definitions."""
        row = record.payload
        orig = dict(row)

        norm: Dict[str, Any] = {}
        units: Dict[str, str] = {}

        if row.get("total_population") and row["total_population"].strip():
            try:
                norm["population.total"] = float(row["total_population"])
                units["population.total"] = "persons"
            except ValueError:
                pass

        if row.get("male_population") and row["male_population"].strip():
            try:
                norm["population.male"] = float(row["male_population"])
                units["population.male"] = "persons"
            except ValueError:
                pass

        if row.get("female_population") and row["female_population"].strip():
            try:
                norm["population.female"] = float(row["female_population"])
                units["population.female"] = "persons"
            except ValueError:
                pass

        if row.get("total_households") and row["total_households"].strip():
            try:
                norm["households.total"] = float(row["total_households"])
                units["households.total"] = "dimensionless"
            except ValueError:
                pass

        as_of = row.get("as_of", self.as_of_default)

        return NormalizedRecord(
            record_id=record.record_id,
            raw_record=record,
            original_fields=orig,
            normalized_fields=norm,
            canonical_units=units,
            as_of=as_of,
        )

    def reconcile_geography(self, record: NormalizedRecord) -> GeographicReconciliation:
        """
        Reconcile geographic references to official LGD hierarchy while preserving Census MDDS codes.
        LGD codes and Census MDDS codes are distinct identifier schemes.
        """
        row = record.original_fields
        state_code = (row.get("lgd_state_code") or "").strip()
        district_code = (row.get("lgd_district_code") or "").strip()
        subdistrict_code = (row.get("subdistrict_lgd_code") or "").strip()
        census_subdist = (row.get("census_mdds_subdistrict_code") or "").strip()

        # Reject unmapped/unknown codes without fuzzy guessing
        if state_code == "99" or district_code == "999" or subdistrict_code in ("09999", "9999"):
            raw_id = f"{state_code}:{district_code}:{subdistrict_code}"
            return GeographicReconciliation(
                resolved=False,
                unresolved_raw_id=raw_id,
                notes=f"Unresolved geographic entity: code '{raw_id}' not found in official LGD master register.",
            )

        if subdistrict_code:
            notes = f"Reconciled to LGD subdistrict {subdistrict_code} ({row.get('subdistrict_name', '')})"
            if census_subdist:
                notes += f", Census 2011 MDDS: {census_subdist}"
            return GeographicReconciliation(
                resolved=True,
                geo_unit_id=canonical_subdistrict_id(district_code, subdistrict_code),
                resolution_tier=ResolutionTier.SUBDISTRICT,
                notes=notes,
            )
        elif district_code:
            census_dist = (row.get("census_district_code") or row.get("census_mdds_district_code") or "").strip()
            pub_id = (row.get("census_publication_id") or "").strip()
            notes = f"Reconciled to LGD district {district_code} ({row.get('district_name', '')})"
            if census_dist:
                notes += f", Census Geographic Code: 09 {census_dist}"
            if pub_id:
                notes += f", Publication ID: {pub_id}"
            return GeographicReconciliation(
                resolved=True,
                geo_unit_id=canonical_district_id(district_code),
                resolution_tier=ResolutionTier.DISTRICT,
                notes=notes,
            )

        return GeographicReconciliation(
            resolved=False,
            unresolved_raw_id=f"{state_code}:{district_code}",
            notes="Missing valid LGD district or subdistrict code.",
        )

    def extract_quantities(
        self,
        record: NormalizedRecord,
        recon: GeographicReconciliation,
        quality: QualityAssessment,
    ) -> List[Quantity]:
        """
        Extract immutable Quantity objects for empirical census counts.
        Demographic counts from official Primary Census Abstract are Kind.OBSERVED with evidence_floor=4.
        Synthetic test data is strictly prohibited from entering the ledger as Kind.OBSERVED.
        """
        if not recon.resolved or not recon.geo_unit_id or recon.resolution_tier is None:
            return []

        row = record.original_fields
        is_synthetic = (
            (row.get("is_synthetic") or "").strip().lower() in ("true", "1", "yes")
            or "synthetic" in str(record.record_id).lower()
        )

        quantities: List[Quantity] = []
        flags = set()
        if quality.is_stale:
            flags.add("STALE")
        if is_synthetic:
            flags.add("SYNTHETIC_DATA")

        # Invariant: Synthetic data MUST NEVER be registered as Kind.OBSERVED
        target_kind = Kind.ESTIMATED if is_synthetic else Kind.OBSERVED
        target_floor = 2 if is_synthetic else 4

        as_of = record.as_of or self.as_of_default

        for def_key, val in record.normalized_fields.items():
            unit = record.canonical_units.get(def_key, "persons")
            # Generate deterministic UUID for idempotent ledger persistence
            q_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"{self.source_id}:{recon.geo_unit_id}:{def_key}:{as_of}:{float(val)}:{target_kind.value}",
                )
            )

            q = Quantity(
                id=q_id,
                definition_key=def_key,
                value=float(val),
                unit=unit,
                kind=target_kind,
                evidence_floor=target_floor,
                geo_unit_id=recon.geo_unit_id,
                resolution=int(recon.resolution_tier),
                as_of=as_of,
                uncertainty="EXACT",
                source_refs=((self.source_id, f"row:{record.record_id}", as_of),),
                quality_flags=frozenset(flags),
                license_meta=self.license_name,
            )
            quantities.append(q)

        return quantities


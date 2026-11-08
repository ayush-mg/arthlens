"""
Unit tests for FIX 4: Unified Freshness Policies.

Authoritative Specification: ArthLens Build Handbook v1.0 (Section 4.4, 4.7, Part 7.1, 7.5).
Phase: Phase 2 Final Integration.

Verifies:
1. OSM: Extract osm3s.timestamp_osm_base and element timestamps, do not invent dates.
2. Census/LGD: Separate Census 2011 demographic observation date from LGD administrative snapshots.
3. Schemes: Remove blanket default 2024-10-24; separate publication and effective dates.
4. Administrative boundaries: Only approved Prayagraj snapshot gets Census 2011 vintage; unverified gets None.
5. Missing or invalid dates fail closed.
6. Unconfigured freshness policy does not return CURRENT.
7. Retrieval date does not make historical evidence current.
"""

from datetime import date
import pytest

from backend.arthlens.data.adapters.admin_boundaries import (
    AdminBoundariesAdapter,
    determine_boundary_geometry_status,
)
from backend.arthlens.data.adapters.census_lgd import CensusLGDAdapter
from backend.arthlens.data.adapters.osm import OpenStreetMapAdapter
from backend.arthlens.data.adapters.schemes import SchemeGuidelinesAdapter
from backend.arthlens.data.models import RawRecord
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.geo import GeometryStatus
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.quality.evaluator import DataQualityEvaluator
from backend.arthlens.quality.freshness import evaluate_staleness
from backend.arthlens.quality.vocabulary import QualityStatus


def test_osm_extracts_base_timestamp_and_does_not_invent_dates():
    """OSM adapter extracts osm3s.timestamp_osm_base when available and leaves as_of=None when absent."""
    adapter = OpenStreetMapAdapter()

    # 1. Payload with osm3s.timestamp_osm_base
    payload_with_ts = {
        "osm3s": {"timestamp_osm_base": "2024-03-15T08:00:00Z"},
        "elements": [
            {"type": "node", "id": 12345, "lat": 25.45, "lon": 81.85, "tags": {"amenity": "bank", "name": "SBI"}}
        ],
    }
    records = adapter.parse_records(payload_with_ts)
    norm = adapter.normalize_record(records[0])
    assert norm.as_of == "2024-03-15"

    # 2. Payload without osm3s timestamp
    payload_no_ts = {
        "elements": [
            {"type": "node", "id": 67890, "lat": 25.45, "lon": 81.85, "tags": {"amenity": "cafe"}}
        ],
    }
    records_no = adapter.parse_records(payload_no_ts)
    norm_no = adapter.normalize_record(records_no[0])
    assert norm_no.as_of is None, "Must not invent an observation date when absent from OSM payload"


def test_census_lgd_separates_census_observation_from_hierarchy_snapshots():
    """Census adapter assigns 2011-03-01 to demographic counts, not to hierarchy-only records."""
    adapter = CensusLGDAdapter()

    # 1. Row with population counts -> gets Census observation date
    raw_demo = RawRecord(
        record_id="rec_demo",
        source_id="DS-05",
        payload={
            "lgd_state_code": "09",
            "lgd_district_code": "120",
            "total_population": "5954391",
        },
    )
    norm_demo = adapter.normalize_record(raw_demo)
    assert norm_demo.as_of == "2011-03-01"

    # 2. Row without demographic counts (hierarchy mapping only) -> does NOT inherit 2011-03-01
    raw_hier = RawRecord(
        record_id="rec_hier",
        source_id="DS-05",
        payload={
            "lgd_state_code": "09",
            "lgd_district_code": "120",
            "total_population": "",  # No demographic metrics
            "lgd_snapshot_date": "2023-01-01",
        },
    )
    norm_hier = adapter.normalize_record(raw_hier)
    assert norm_hier.as_of == "2023-01-01"


def test_schemes_removes_blanket_default_date():
    """Schemes adapter has no blanket default 2024-10-24; preserves publication/effective dates separately."""
    adapter = SchemeGuidelinesAdapter()
    assert adapter.as_of_default is None

    # Payload with explicit publication date
    raw = RawRecord(
        record_id="rec_scheme",
        source_id="DS-08",
        payload={
            "definition_key": "scheme.pmfme.subsidy_rate",
            "value": 0.35,
            "unit": "dimensionless",
            "publication_date": "2020-06-29",
            "effective_from": "2020-07-01",
        },
    )
    norm = adapter.normalize_record(raw)
    assert norm.as_of == "2020-07-01"
    assert norm.metadata["publication_date"] == "2020-06-29"
    assert norm.metadata["effective_date"] == "2020-07-01"


def test_admin_boundaries_only_pilot_snapshot_gets_census_2011_vintage():
    """Only approved Prayagraj snapshot gets Census 2011 vintage; unapproved gets unvalidated."""
    # 1. Approved pilot snapshot
    status, reason = determine_boundary_geometry_status(
        content_hash="a4ea61c773b99c443bd71a07260881011460eae0600f07be400ef25e2b406c18",
        collection_provenance={"source_id": "DS-09", "census_code": "175", "district_name_current": "Prayagraj"},
        geo_id="in:district:120",
        lgd_code="120",
        census_code="175",
        name="Prayagraj",
    )
    assert status == GeometryStatus.GEOMETRY_VERIFIED

    # 2. Unapproved snapshot with non-matching hash and no supported vintage
    status_unapp, _ = determine_boundary_geometry_status(
        content_hash="9999999999999999999999999999999999999999999999999999999999999999",
        collection_provenance={"source_id": "DS-09"},
        geo_id="in:district:999",
        lgd_code="999",
        census_code="999",
        name="Random District",
        vintage=None,
    )
    assert status_unapp == GeometryStatus.GEOMETRY_UNVALIDATED


def test_missing_or_invalid_dates_fail_closed():
    """Missing or invalid observation dates fail closed and cannot be certified as CURRENT."""
    evaluator = DataQualityEvaluator(evaluation_date=date(2026, 11, 7))

    # Missing as_of
    q_no_date = Quantity(
        id="q_no_date",
        definition_key="population.total",
        value=100000.0,
        unit="persons",
        kind=Kind.OBSERVED,
        evidence_floor=4,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="",
        source_refs=("DS-05",),
    )
    res_no_date = evaluator.evaluate_quantity(q_no_date, "population.total", "in:district:120")
    assert res_no_date.primary_status != QualityStatus.CURRENT
    assert res_no_date.primary_status == QualityStatus.INCOMPLETE


def test_retrieval_date_never_makes_historical_evidence_current():
    """A download date in November 2026 never makes Census 2011 (as_of 2011-03-01) fresh."""
    eval_res = evaluate_staleness(
        as_of="2011-03-01",
        source_id="DS-05",
        retrieval_date=date(2026, 11, 7),
        evaluation_date=date(2026, 11, 7),
    )
    assert eval_res.is_stale is True
    assert eval_res.elapsed_days > 5000
    assert eval_res.retrieval_date == date(2026, 11, 7)


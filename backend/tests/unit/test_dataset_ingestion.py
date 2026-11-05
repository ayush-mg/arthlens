"""
Unit and Integration Tests for DatasetIngestionPipeline and Source Adapters (P2-1).

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.4, 7.5, Part 13.1 P2-1).
Phase: Phase 2 (Real-Data Foundation and Atlas).

Verifies the 16 mandatory acceptance test requirements:
 1. Adapter reads its fixture.
 2. Adapter validates its source schema.
 3. Pipeline records the source version and checksum.
 4. Normalization preserves original values.
 5. Unit conversion with Pint is correct.
 6. Geographic reconciliation succeeds for known valid identifiers.
 7. Unresolved geography is preserved as unresolved without fuzzy guessing.
 8. Duplicate detection works.
 9. Missingness and outlier checks work.
10. Temporal and geographic support are recorded.
11. Licence and provenance metadata are retained.
12. OBSERVED quantities are registered correctly for genuine numeric observations.
13. Staleness is calculated from the configured source maximum age.
14. Coverage and quality statuses are published.
15. Re-ingesting the same source version does not silently duplicate records.
16. Invalid inputs fail safely.
"""

import csv
from datetime import date
import hashlib
import os
from pathlib import Path
import pytest

from backend.arthlens.data.adapters.admin_boundaries import AdminBoundariesAdapter
from backend.arthlens.data.adapters.census_lgd import CensusLGDAdapter
from backend.arthlens.data.adapters.osm import OpenStreetMapAdapter
from backend.arthlens.data.adapters.schemes import SchemeGuidelinesAdapter
from backend.arthlens.data.pipeline import DatasetIngestionPipeline
from backend.arthlens.data.quality import QualityStatus
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.infra.in_memory import InMemoryQuantityRepository


FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
TEST_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
OSM_FIXTURE = FIXTURES_DIR / "osm" / "prayagraj_sample.json"
OSM_INVALID_FIXTURE = FIXTURES_DIR / "osm" / "invalid_sample.json"
CENSUS_FIXTURE = FIXTURES_DIR / "geo" / "lgd_census_crosswalk.csv"
SYNTHETIC_CENSUS_FIXTURE = TEST_FIXTURES_DIR / "synthetic_census_crosswalk.csv"
CENSUS_INVALID_FIXTURE = FIXTURES_DIR / "geo" / "invalid_crosswalk.csv"
SCHEMES_FIXTURE = FIXTURES_DIR / "schemes" / "scheme_parameters_sample.json"
BOUNDARIES_FIXTURE = FIXTURES_DIR / "boundaries" / "prayagraj_boundaries_sample.geojson"
BOUNDARIES_INVALID_FIXTURE = FIXTURES_DIR / "boundaries" / "invalid_boundaries.geojson"


# ==============================================================================
# 1. Adapter Reads Its Fixture
# ==============================================================================

def test_01_adapters_read_their_fixtures():
    """Requirement 1: Each approved adapter successfully reads and parses its fixture."""
    # DS-04 OSM
    osm_adapter = OpenStreetMapAdapter()
    osm_raw = osm_adapter.read_local(OSM_FIXTURE)
    osm_records = osm_adapter.parse_records(osm_raw)
    assert len(osm_records) >= 4, "OSM adapter must parse elements from fixture"

    # DS-05 Census / LGD
    census_adapter = CensusLGDAdapter()
    census_raw = census_adapter.read_local(CENSUS_FIXTURE)
    census_records = census_adapter.parse_records(census_raw)
    assert len(census_records) >= 8, "Census adapter must parse rows from CSV"

    # DS-08 Schemes
    scheme_adapter = SchemeGuidelinesAdapter()
    scheme_raw = scheme_adapter.read_local(SCHEMES_FIXTURE)
    scheme_records = scheme_adapter.parse_records(scheme_raw)
    assert len(scheme_records) >= 5, "Scheme adapter must parse parameters from fixture"

    # DS-09 Boundaries
    boundary_adapter = AdminBoundariesAdapter()
    boundary_raw = boundary_adapter.read_local(BOUNDARIES_FIXTURE)
    boundary_records = boundary_adapter.parse_records(boundary_raw)
    assert len(boundary_records) >= 2, "Boundary adapter must parse features from GeoJSON"


# ==============================================================================
# 2. Adapter Validates Its Source Schema
# ==============================================================================

def test_02_adapter_validates_source_schema():
    """Requirement 2: Adapter validates expected schema and rejects malformed payloads."""
    osm_adapter = OpenStreetMapAdapter()
    valid_raw = osm_adapter.read_local(OSM_FIXTURE)
    is_valid, errors = osm_adapter.validate_schema(valid_raw)
    assert is_valid is True
    assert len(errors) == 0

    invalid_raw = osm_adapter.read_local(OSM_INVALID_FIXTURE)
    is_valid_inv, errors_inv = osm_adapter.validate_schema(invalid_raw)
    assert is_valid_inv is False
    assert any("latitude" in e.lower() for e in errors_inv)


# ==============================================================================
# 3. Pipeline Records Source Version and Checksum
# ==============================================================================

def test_03_pipeline_records_source_version_and_checksum():
    """Requirement 3: Pipeline records retrieval timestamp, content hash, and source version."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    assert result.success is True

    # Calculate expected SHA-256
    with open(CENSUS_FIXTURE, "rb") as f:
        expected_hash = hashlib.sha256(f.read()).hexdigest()

    assert result.version_info.content_hash == expected_hash
    assert result.version_info.source_id == "DS-05"
    assert result.version_info.retrieval_date == date.today()


# ==============================================================================
# 4. Normalization Preserves Original Values
# ==============================================================================

def test_04_normalization_preserves_original_values():
    """Requirement 4: Original field names, values, and units are preserved alongside normalized values."""
    adapter = CensusLGDAdapter()
    raw_content = adapter.read_local(CENSUS_FIXTURE)
    records = adapter.parse_records(raw_content)

    normalized = adapter.normalize_record(records[0])
    assert "total_population" in normalized.original_fields
    assert normalized.original_fields["total_population"] == "5954391"
    assert normalized.normalized_fields["population.total"] == 5954391.0
    assert normalized.raw_record is records[0]


# ==============================================================================
# 5. Unit Conversion with Pint is Correct
# ==============================================================================

def test_05_unit_conversion_with_pint():
    """Requirement 5: Units are explicitly mapped and validated through Pint UnitRegistry."""
    from backend.arthlens.ledger.units import get_unit_registry

    ureg = get_unit_registry()
    q_persons = 100 * ureg.persons
    assert str(q_persons.units) in ("person", "persons")

    adapter = CensusLGDAdapter()
    raw_content = adapter.read_local(CENSUS_FIXTURE)
    records = adapter.parse_records(raw_content)
    normalized = adapter.normalize_record(records[0])

    assert normalized.canonical_units["population.total"] == "persons"
    assert normalized.canonical_units["households.total"] == "dimensionless"


# ==============================================================================
# 6. Geographic Reconciliation for Known Valid Identifiers
# ==============================================================================

def test_06_geographic_reconciliation_valid_identifiers():
    """Requirement 6: LGD identifiers reconcile to canonical geo_unit_ids."""
    adapter = CensusLGDAdapter()
    raw_content = adapter.read_local(CENSUS_FIXTURE)
    records = adapter.parse_records(raw_content)

    # Sadar Tehsil (record 3)
    sadar_norm = adapter.normalize_record(records[3])
    recon = adapter.reconcile_geography(sadar_norm)

    assert recon.resolved is True
    assert recon.geo_unit_id == "in:subdistrict:120:890"
    assert recon.resolution_tier == ResolutionTier.SUBDISTRICT


# ==============================================================================
# 7. Unresolved Geography Preserved as Unresolved
# ==============================================================================

def test_07_unresolved_geography_preserved():
    """Requirement 7: Unresolved geographic identifiers are recorded without fuzzy guessing."""
    adapter = CensusLGDAdapter()
    raw_content = adapter.read_local(SYNTHETIC_CENSUS_FIXTURE)
    records = adapter.parse_records(raw_content)

    # Record 9 in synthetic fixture is 'Unmapped State', code 999/09999
    unmapped_norm = adapter.normalize_record(records[9])
    recon = adapter.reconcile_geography(unmapped_norm)

    assert recon.resolved is False
    assert recon.unresolved_raw_id == "99:999:09999"
    assert "unresolved" in recon.notes.lower()


# ==============================================================================
# 8. Duplicate Detection
# ==============================================================================

def test_08_duplicate_detection_works():
    """Requirement 8: Duplicate records in input are identified and flagged."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    # Synthesize records containing a duplicate LGD code
    raw_content = adapter.read_local(CENSUS_FIXTURE)
    records = adapter.parse_records(raw_content)
    duplicate_records = records + [records[1]]  # Duplicate Soraon tehsil

    normalized = [adapter.normalize_record(r) for r in duplicate_records]
    reconciliations = [adapter.reconcile_geography(n) for n in normalized]
    quality = pipeline.step_6_check_quality(normalized, reconciliations, as_of="2011-03-01")

    assert any(a.anomaly_type == "DUPLICATE_RECORD" for a in quality.anomalies)


# ==============================================================================
# 9. Missingness and Outlier Checks Work
# ==============================================================================

def test_09_missingness_and_outlier_checks():
    """Requirement 9: Missing values and range anomalies are detected."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    # Synthetic fixture contains an intentionally empty female_population
    result = pipeline.ingest(source_input=SYNTHETIC_CENSUS_FIXTURE, is_local=True)
    missing_anomalies = [a for a in result.quality_assessment.anomalies if a.anomaly_type == "MISSING_VALUE"]
    assert len(missing_anomalies) >= 1
    assert any("female_population" in a.field_name for a in missing_anomalies)

    # Production fixture contains zero missing demographic values
    prod_result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    prod_missing = [a for a in prod_result.quality_assessment.anomalies if a.anomaly_type == "MISSING_VALUE"]
    assert len(prod_missing) == 0, "Authentic Census production fixture must have zero missing values"


# ==============================================================================
# 10. Temporal and Geographic Support Recorded
# ==============================================================================

def test_10_temporal_and_geographic_support_recorded():
    """Requirement 10: Geographic resolution and temporal as_of dates are recorded."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    assert len(result.quantities_registered) > 0

    first_q = result.quantities_registered[0]
    assert first_q.as_of == "2011-03-01"
    assert first_q.resolution in (ResolutionTier.DISTRICT, ResolutionTier.SUBDISTRICT)


# ==============================================================================
# 11. Licence and Provenance Metadata Retained
# ==============================================================================

def test_11_licence_and_provenance_metadata_retained():
    """Requirement 11: Publisher, licence, and mandatory attribution strings are preserved."""
    repo = InMemoryQuantityRepository()
    adapter = OpenStreetMapAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=OSM_FIXTURE, is_local=True)
    assert result.provenance.license_name == "ODbL 1.0"
    assert "OpenStreetMap" in result.provenance.attribution
    assert "https://www.openstreetmap.org/copyright" in result.provenance.attribution


# ==============================================================================
# 12. OBSERVED Quantities Registered in Ledger
# ==============================================================================

def test_12_observed_quantities_registered_as_observed():
    """Requirement 12: Empirical census counts are registered as Kind.OBSERVED with evidence_floor=4."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    observed_quantities = [q for q in result.quantities_registered if q.definition_key == "population.total"]

    assert len(observed_quantities) >= 8
    for q in observed_quantities:
        assert q.kind == Kind.OBSERVED
        assert q.evidence_floor == 4
        assert q.value > 0
        assert q.unit == "persons"


# ==============================================================================
# 13. Staleness Calculated from Source Max Age
# ==============================================================================

def test_13_staleness_calculated_from_source_max_age():
    """Requirement 13: 2011 Census exceeds max_age_days and receives STALE quality flag."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    assert result.quality_assessment.is_stale is True

    for q in result.quantities_registered:
        assert "STALE" in q.quality_flags


# ==============================================================================
# 14. Coverage and Quality Statuses Published
# ==============================================================================

def test_14_coverage_and_quality_statuses_published():
    """Requirement 14: Quality vocabulary (CURRENT, INCOMPLETE, STALE, UNAVAILABLE) is published."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    # Since census has unresolved state 99 and 2011 date, it is both STALE and INCOMPLETE
    assert result.coverage_quality_status in (QualityStatus.STALE.value, QualityStatus.INCOMPLETE.value)


# ==============================================================================
# 15. Re-ingesting Same Version Does Not Duplicate
# ==============================================================================

def test_15_idempotent_reingestion_no_duplicates():
    """Requirement 15: Ingesting the same snapshot version twice does not create duplicate entries."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    # First ingestion
    result1 = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    count1 = repo.count()
    assert count1 > 0

    # Second ingestion with same snapshot
    result2 = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    count2 = repo.count()
    assert count2 == count1, "Idempotent re-ingestion must not create duplicate quantities"


# ==============================================================================
# 16. Invalid Inputs Fail Safely
# ==============================================================================

def test_16_invalid_inputs_fail_safely():
    """Requirement 16: Malformed payloads raise SchemaValidationError without crashing the pipeline."""
    repo = InMemoryQuantityRepository()
    adapter = CensusLGDAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=CENSUS_INVALID_FIXTURE, is_local=True)
    assert result.success is False
    assert len(result.errors) > 0
    assert any("negative" in err.lower() or "validation" in err.lower() for err in result.errors)


# ==============================================================================
# 17. Scheme Guidelines Adapter Tests (DS-08)
# ==============================================================================

def test_17_scheme_guidelines_adapter():
    """Requirement: DS-08 Scheme Guidelines adapter verifies document hashes and registers policy parameters."""
    repo = InMemoryQuantityRepository()
    adapter = SchemeGuidelinesAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)

    result = pipeline.ingest(source_input=SCHEMES_FIXTURE, is_local=True)
    assert result.success is True

    # Scheme parameters must be registered as POLICY_RULE, NOT OBSERVED!
    policy_quantities = result.quantities_registered
    assert len(policy_quantities) >= 5
    for q in policy_quantities:
        assert q.kind == Kind.POLICY_RULE
        assert q.evidence_floor == 4


# ==============================================================================
# 18. Administrative Boundaries Adapter Tests (DS-09)
# ==============================================================================

def test_18_admin_boundaries_adapter():
    """Requirement: DS-09 Administrative Boundaries adapter validates polygon GeoJSON and populates geo metadata."""
    adapter = AdminBoundariesAdapter()
    pipeline = DatasetIngestionPipeline(adapter=adapter)

    result = pipeline.ingest(source_input=BOUNDARIES_FIXTURE, is_local=True)
    assert result.success is True
    # Check that boundaries do NOT generate fake numeric quantities
    assert len(result.quantities_registered) == 0
    assert len(result.normalized_records) >= 2


# ==============================================================================
# 19. Optional Live Retrieval Test (Excluded from Default CI)
# ==============================================================================

@pytest.mark.skipif(
    os.environ.get("ARTHLENS_RUN_LIVE_TESTS") != "1",
    reason="Live tests require ARTHLENS_RUN_LIVE_TESTS=1 environment variable to prevent CI instability",
)
def test_19_optional_live_osm_retrieval():
    """Optional live retrieval test for OpenStreetMap Overpass API (opt-in only)."""
    adapter = OpenStreetMapAdapter()
    # Bounded query for a small 100m box in Prayagraj
    live_content = adapter.fetch_live({
        "bbox": (81.834, 25.448, 81.838, 25.452),
        "timeout": 25,
    })
    assert live_content is not None
    is_valid, errors = adapter.validate_schema(live_content)
    assert is_valid is True


# ==============================================================================
# 20. Authentic Census Hierarchy, Identifier Separation & Synthetic Isolation
# ==============================================================================

def test_20_authentic_census_hierarchy_and_synthetic_isolation():
    """
    Requirement:
    1. Census MDDS codes remain distinct from LGD codes.
    2. All eight tehsil mappings are correct.
    3. All verified population values match official 2011 PCA source records.
    4. Sub-district population totals reconcile exactly with the district total.
    5. Male, female, and household counts reconcile to district aggregates.
    6. Koraon has its authentic 2011 observation (not derived by subtraction).
    7. Synthetic test data is quarantined and can NEVER enter the ledger as Kind.OBSERVED.
    """
    adapter = CensusLGDAdapter()
    raw_rows = adapter.read_local(CENSUS_FIXTURE)
    assert len(raw_rows) == 9, "Production fixture must contain exactly 1 district + 8 tehsils"

    # 1. District aggregate verification
    dist_row = raw_rows[0]
    assert dist_row["lgd_district_code"] == "120"
    assert dist_row["census_district_code"] == "175"
    assert dist_row["census_publication_id"] == "0944"
    assert dist_row["district_name"] == "Prayagraj"
    assert dist_row["total_population"] == "5954391"
    assert dist_row["male_population"] == "3131807"
    assert dist_row["female_population"] == "2822584"
    assert dist_row["total_households"] == "976733"

    # 2. Tehsil benchmark registry (Official Census 2011 Primary Census Abstract Table A-1 & Table 30)
    expected_tehsils = {
        "Soraon": {"mdds": "00888", "lgd": "888", "pop": 823190, "m": 427214, "f": 395976, "hh": 136863},
        "Phulpur": {"mdds": "00889", "lgd": "889", "pop": 859421, "m": 446824, "f": 412597, "hh": 135991},
        "Sadar": {"mdds": "00890", "lgd": "890", "pop": 1395816, "m": 758719, "f": 637097, "hh": 248662},
        "Bara": {"mdds": "00891", "lgd": "891", "pop": 365605, "m": 192517, "f": 173088, "hh": 65850},
        "Karchhana": {"mdds": "00892", "lgd": "892", "pop": 606924, "m": 318185, "f": 288739, "hh": 95034},
        "Handia": {"mdds": "00893", "lgd": "893", "pop": 944717, "m": 487606, "f": 457111, "hh": 144880},
        "Meja": {"mdds": "00894", "lgd": "894", "pop": 579879, "m": 302343, "f": 277536, "hh": 87482},
        "Koraon": {"mdds": "00895", "lgd": "895", "pop": 378839, "m": 198399, "f": 180440, "hh": 61971},
    }

    sub_rows = raw_rows[1:]
    assert len(sub_rows) == 8

    sum_pop = 0
    sum_male = 0
    sum_female = 0
    sum_hh = 0

    for r in sub_rows:
        name = r["subdistrict_name"]
        assert name in expected_tehsils, f"Unexpected tehsil: {name}"
        exp = expected_tehsils[name]

        # Census MDDS codes must NOT equal LGD codes
        assert r["census_mdds_subdistrict_code"] != r["subdistrict_lgd_code"], (
            f"Conflation error in {name}: Census MDDS ({r['census_mdds_subdistrict_code']}) "
            f"cannot equal LGD ({r['subdistrict_lgd_code']})"
        )
        assert r["census_mdds_subdistrict_code"] == exp["mdds"]
        assert r["subdistrict_lgd_code"] == exp["lgd"]

        # Exact population counts
        p = int(r["total_population"])
        m = int(r["male_population"])
        f = int(r["female_population"])
        hh = int(r["total_households"])

        assert p == exp["pop"], f"{name} total pop mismatch: got {p}, expected {exp['pop']}"
        assert m == exp["m"], f"{name} male pop mismatch: got {m}, expected {exp['m']}"
        assert f == exp["f"], f"{name} female pop mismatch: got {f}, expected {exp['f']}"
        assert hh == exp["hh"], f"{name} households mismatch: got {hh}, expected {exp['hh']}"

        # Internal consistency
        assert m + f == p, f"{name}: male + female must equal total population"

        sum_pop += p
        sum_male += m
        sum_female += f
        sum_hh += hh

    # 3. Arithmetic reconciliation against district totals
    assert sum_pop == 5954391, f"Tehsil populations sum to {sum_pop}, expected 5954391"
    assert sum_male == 3131807, f"Tehsil males sum to {sum_male}, expected 3131807"
    assert sum_female == 2822584, f"Tehsil females sum to {sum_female}, expected 2822584"
    assert sum_hh == 976733, f"Tehsil households sum to {sum_hh}, expected 976733"

    # 4. Pipeline Ingestion & Kind.OBSERVED enforcement for authentic data
    repo = InMemoryQuantityRepository()
    pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=repo)
    result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
    assert result.success is True

    # Every registered quantity from production fixture MUST be Kind.OBSERVED with evidence_floor=4
    for q in result.quantities_registered:
        assert q.kind == Kind.OBSERVED, f"Authentic census quantity {q.id} must be Kind.OBSERVED"
        assert q.evidence_floor == 4
        assert "STALE" in q.quality_flags

    # 5. Synthetic Isolation: Synthetic test data can NEVER enter as Kind.OBSERVED
    synthetic_repo = InMemoryQuantityRepository()
    synthetic_pipeline = DatasetIngestionPipeline(adapter=adapter, quantity_repo=synthetic_repo)
    synth_result = synthetic_pipeline.ingest(source_input=SYNTHETIC_CENSUS_FIXTURE, is_local=True)

    # In synthetic fixture, all quantities must be Kind.ESTIMATED and carry SYNTHETIC_DATA
    for q in synth_result.quantities_registered:
        assert q.kind == Kind.ESTIMATED, f"Synthetic quantity {q.id} was illegally registered as {q.kind}"
        assert q.evidence_floor == 2
        assert "SYNTHETIC_DATA" in q.quality_flags
        assert q.kind != Kind.OBSERVED, "Synthetic data must NEVER be registered as Kind.OBSERVED"


def test_21_subdistrict_provenance_and_crosswalk_reproducibility():
    """
    Sub-district Provenance Verification (Handbook Part 7.1, 7.4, Appendix A.3).
    Verifies that the Prayagraj sub-district crosswalk is 100% reproducible from the official
    LGD sub-district master export (backend/fixtures/geo/lgd_subdistricts.csv).
    """
    subdist_csv = FIXTURES_DIR / "geo" / "lgd_subdistricts.csv"
    assert subdist_csv.exists(), "Official LGD subdistricts export fixture must be preserved"

    with subdist_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # 1. Prayagraj (District 120) sub-districts in official LGD export
    prayagraj_subs = {
        r["Sub-district Code"]: r["Sub-district Name"].strip()
        for r in rows
        if r.get("District Code") == "120"
    }
    assert len(prayagraj_subs) == 8, f"Expected 8 subdistricts in Prayagraj (120), got {len(prayagraj_subs)}"

    expected_codes = {
        "888": "Soraon",
        "889": "Phulpur",
        "890": "Allahabad",  # Sadar tehsil
        "891": "Bara",
        "892": "Karchhana",
        "893": "Handia",
        "894": "Meja",
        "895": "Koraon",
    }
    assert set(prayagraj_subs.keys()) == set(expected_codes.keys())
    for code, name in expected_codes.items():
        assert prayagraj_subs[code].lower() == name.lower(), f"Subdistrict {code} name mismatch: {prayagraj_subs[code]}"

    # 2. Kanpur Dehat (District 156) Akbarpur verification
    kanpur_dehat_845 = [
        r for r in rows
        if r.get("District Code") == "156" and r.get("Sub-district Code") == "845"
    ]
    assert len(kanpur_dehat_845) == 1
    assert kanpur_dehat_845[0]["Sub-district Name"] == "Akbarpur"
    assert kanpur_dehat_845[0]["Census 2011 code"] == "00845"

    # 3. Prayagraj does NOT contain 845
    assert "845" not in prayagraj_subs



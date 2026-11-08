"""
PostgreSQL Integration Tests for Dataset Ingestion Pipeline & Persistence (P2-1 Step 9).

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.5 Step 9, Part 9.1).
Phase: Phase 2 (P2-1 Step 9 Persistence Completion).

Verifies the 12 mandatory persistence requirements directly against PostgreSQL 16 + PostGIS 3.4:
 1. SourceVersionInfo is persisted and retrievable from PostgreSQL.
 2. NormalizedRecord is persisted and retrievable after the ingestion result is gone.
 3. Original raw values survive database round-tripping.
 4. Normalized values and units survive round-tripping.
 5. Provenance and licence references survive round-tripping.
 6. Geographic and temporal support survive round-tripping.
 7. Unresolved geographic identifiers remain unresolved after retrieval.
 8. OBSERVED quantities remain correctly persisted.
 9. POLICY_RULE records retain their correct classification.
10. Identical snapshot re-ingestion creates no duplicates.
11. A new content hash creates a new historical source version.
12. Transaction failure does not leave partially persisted ingestion data.
"""

from datetime import date
from pathlib import Path

import pytest
from backend.arthlens.data.adapters.census_lgd import CensusLGDAdapter
from backend.arthlens.data.adapters.osm import OpenStreetMapAdapter
from backend.arthlens.data.adapters.schemes import SchemeGuidelinesAdapter
from backend.arthlens.data.pipeline import DatasetIngestionPipeline
from backend.arthlens.domain.enums import Kind, ResolutionTier
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.infra.database import (
    assert_safe_test_database,
    get_engine,
    get_session_factory,
)
from backend.arthlens.infra.repositories import (
    PostgresQuantityRepository,
    PostgresSourceRecordRepository,
    PostgresSourceRepository,
)
from sqlalchemy import text

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"
TEST_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
CENSUS_FIXTURE = FIXTURES_DIR / "geo" / "lgd_census_crosswalk.csv"
SYNTHETIC_CENSUS_FIXTURE = TEST_FIXTURES_DIR / "synthetic_census_crosswalk.csv"
SCHEMES_FIXTURE = FIXTURES_DIR / "schemes" / "scheme_parameters_sample.json"
OSM_FIXTURE = FIXTURES_DIR / "osm" / "prayagraj_sample.json"


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure clean table state before and after each integration test."""
    engine = get_engine()
    assert_safe_test_database(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE source_records, source_versions, sources, quantities CASCADE;"))
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE source_records, source_versions, sources, quantities CASCADE;"))


@pytest.mark.integration
class TestDatasetPersistencePostgresIntegration:
    """Integration test suite executing real database transactions against PostgreSQL 16 + PostGIS."""

    def test_01_source_version_persisted_and_retrievable_postgres(self):
        """Requirement 1: SourceVersionInfo is persisted and retrievable from PostgreSQL."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        assert result.success is True
        assert result.version_info.version_id is not None

        # Retrieve version directly from PostgreSQL via a separate connection
        v = source_repo.get_version(result.version_info.version_id)
        assert v is not None
        assert v["source_id"] == "DS-05"
        assert v["content_hash"] == result.version_info.content_hash
        assert v["retrieval_date"] == date.today()
        assert v["source_url"] == adapter.official_url

    def test_02_normalized_record_persisted_and_retrievable(self):
        """Requirement 2: NormalizedRecord is persisted and retrievable after ingestion result is cleared."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        version_id = result.version_info.version_id

        # Discard the in-memory result object
        del result

        # Query database via separate repository call
        records = record_repo.list_by_version(version_id)
        assert len(records) >= 8

    def test_03_original_raw_values_survive_roundtrip(self):
        """Requirement 3: Original raw field values survive database round-tripping."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        version_id = result.version_info.version_id

        # Row 3 is Sadar Tehsil
        record = record_repo.get_record(version_id, "census_2011:row_3")
        assert record is not None
        assert record.original_fields["subdistrict_name"] == "Sadar"
        assert record.original_fields["district_name"] == "Prayagraj"
        assert record.original_fields["total_population"] == "1395816"
        assert record.original_fields["male_population"] == "758719"
        assert record.original_fields["female_population"] == "637097"
        assert record.original_fields["total_households"] == "248662"

    def test_04_normalized_values_and_units_survive_roundtrip(self):
        """Requirement 4: Normalized numeric values and canonical units survive round-tripping."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        record = record_repo.get_record(result.version_info.version_id, "census_2011:row_3")

        assert record is not None
        assert record.normalized_fields["population.total"] == 1395816.0
        assert record.normalized_fields["population.male"] == 758719.0
        assert record.normalized_fields["households.total"] == 248662.0
        assert record.canonical_units["population.total"] == "persons"
        assert record.canonical_units["households.total"] == "dimensionless"

    def test_05_provenance_and_licence_survive_roundtrip(self):
        """Requirement 5: Provenance and licence references survive round-tripping."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        record = record_repo.get_record(result.version_info.version_id, "census_2011:row_0")

        assert record is not None
        assert record.license_name == "Government Open Data License - India (GODL)"
        assert "Primary Census Abstract 2011" in record.attribution
        assert "Local Government Directory" in record.attribution

    def test_06_geographic_and_temporal_support_survive_roundtrip(self):
        """Requirement 6: Geographic resolution and as_of temporal support survive round-tripping."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        record = record_repo.get_record(result.version_info.version_id, "census_2011:row_3")

        assert record is not None
        assert record.as_of == "2011-03-01"
        assert record.geo_resolved is True
        assert record.geo_unit_id == "in:subdistrict:120:890"
        assert record.resolution_tier == int(ResolutionTier.SUBDISTRICT)

    def test_07_unresolved_geography_remains_unresolved(self):
        """Requirement 7: Unresolved geographic identifiers remain unresolved after database retrieval."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=SYNTHETIC_CENSUS_FIXTURE, is_local=True)
        # Row 9 in synthetic fixture is unmapped code 999
        record = record_repo.get_record(result.version_info.version_id, "census_2011:row_9")

        assert record is not None
        assert record.geo_resolved is False
        assert record.unresolved_raw_id == "99:999:09999"
        assert record.geo_unit_id is None

    def test_08_observed_quantities_remain_persisted(self):
        """Requirement 8: OBSERVED quantities remain correctly persisted in PostgreSQL quantities table."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)

        observed = quantity_repo.list_by_definition("population.total")
        assert len(observed) >= 8
        for q in observed:
            assert q.kind == Kind.OBSERVED
            assert q.evidence_floor == 4
            assert q.unit == "persons"
            assert "STALE" in q.quality_flags

    def test_09_policy_rule_records_classification(self):
        """Requirement 9: POLICY_RULE records retain their correct classification in PostgreSQL."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = SchemeGuidelinesAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        pipeline.ingest(source_input=SCHEMES_FIXTURE, is_local=True)

        subsidy = quantity_repo.list_by_definition("scheme.pmfme.subsidy_rate")
        assert len(subsidy) == 1
        q = subsidy[0]
        assert q.kind == Kind.POLICY_RULE
        assert q.evidence_floor == 4
        assert q.value == 0.35
        assert q.unit == "dimensionless"

    def test_10_identical_snapshot_reingestion_no_duplicates(self):
        """Requirement 10: Repeated ingestion of identical snapshot creates zero duplicate rows."""
        engine = get_engine()
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        # First ingestion
        pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)

        with engine.connect() as conn:
            v_count1 = conn.execute(text("SELECT count(*) FROM source_versions WHERE source_id = 'DS-05';")).scalar()
            r_count1 = conn.execute(text("SELECT count(*) FROM source_records WHERE source_id = 'DS-05';")).scalar()
            q_count1 = conn.execute(text("SELECT count(*) FROM quantities;")).scalar()

        assert v_count1 == 1
        assert r_count1 > 0
        assert q_count1 > 0

        # Second ingestion with identical snapshot
        pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)

        with engine.connect() as conn:
            v_count2 = conn.execute(text("SELECT count(*) FROM source_versions WHERE source_id = 'DS-05';")).scalar()
            r_count2 = conn.execute(text("SELECT count(*) FROM source_records WHERE source_id = 'DS-05';")).scalar()
            q_count2 = conn.execute(text("SELECT count(*) FROM quantities;")).scalar()

        assert v_count2 == v_count1, "Snapshot version count must be unchanged"
        assert r_count2 == r_count1, "Source record count must be unchanged"
        assert q_count2 == q_count1, "Quantity count must be unchanged"

    def test_11_new_content_hash_creates_historical_version(self, tmp_path):
        """Requirement 11: A new content hash creates a new historical source version without overwriting."""
        engine = get_engine()
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        # 1. Ingest original snapshot
        res1 = pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)
        v1_id = res1.version_info.version_id

        # 2. Synthesize updated snapshot file (e.g. revision update with new hash)
        updated_file = tmp_path / "census_updated.csv"
        content = CENSUS_FIXTURE.read_text(encoding="utf-8")
        # Change a population value to create a new content hash
        updated_content = content.replace("5954391", "5954399")
        updated_file.write_text(updated_content, encoding="utf-8")

        # Ingest updated snapshot
        res2 = pipeline.ingest(source_input=updated_file, is_local=True)
        v2_id = res2.version_info.version_id

        assert v1_id != v2_id, "New content hash must yield a distinct version ID"

        # Verify both versions exist in database
        versions = source_repo.list_versions("DS-05")
        assert len(versions) == 2
        v_ids = {v["id"] for v in versions}
        assert v1_id in v_ids
        assert v2_id in v_ids

        # Verify historical records exist for both versions
        v1_records = record_repo.list_by_version(v1_id)
        v2_records = record_repo.list_by_version(v2_id)
        assert len(v1_records) >= 8
        assert len(v2_records) >= 8

    def test_12_transaction_failure_aborts_completely(self, monkeypatch):
        """Requirement 12: A failure mid-transaction leaves no partially persisted ingestion data."""
        engine = get_engine()
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = CensusLGDAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        # Monkeypatch step_7_extract_quantities to introduce an unrecoverable failure during persistence
        def failing_save(q, session=None):
            raise RuntimeError("Injected database failure during quantity persistence")

        monkeypatch.setattr(quantity_repo, "save", failing_save)

        # Ingestion must raise the exception and abort
        with pytest.raises(RuntimeError, match="Injected database failure"):
            pipeline.ingest(source_input=CENSUS_FIXTURE, is_local=True)

        # Verify complete atomic rollback across all tables
        with engine.connect() as conn:
            v_count = conn.execute(text("SELECT count(*) FROM source_versions WHERE source_id = 'DS-05';")).scalar()
            r_count = conn.execute(text("SELECT count(*) FROM source_records WHERE source_id = 'DS-05';")).scalar()
            q_count = conn.execute(text("SELECT count(*) FROM quantities;")).scalar()

        assert v_count == 0, "source_versions must have rolled back completely"
        assert r_count == 0, "source_records must have rolled back completely"
        assert q_count == 0, "quantities must have rolled back completely"

    def test_13_osm_fixture_persistence_and_retrieval_postgres(self):
        """Requirement: OpenStreetMap (DS-04) approved GO adapter fixture persists and round-trips via PostgreSQL."""
        factory = get_session_factory()
        source_repo = PostgresSourceRepository(session_factory=factory)
        record_repo = PostgresSourceRecordRepository(session_factory=factory)
        quantity_repo = PostgresQuantityRepository(session_factory=factory)

        adapter = OpenStreetMapAdapter()
        pipeline = DatasetIngestionPipeline(
            adapter=adapter,
            quantity_repo=quantity_repo,
            source_repo=source_repo,
            record_repo=record_repo,
            session_factory=factory,
        )

        result = pipeline.ingest(source_input=OSM_FIXTURE, is_local=True)
        assert result.success is True
        assert result.version_info.source_id == "DS-04"
        version_id = result.version_info.version_id

        # Verify version retrievable from PostgreSQL
        v = source_repo.get_version(version_id)
        assert v is not None
        assert v["source_id"] == "DS-04"
        assert v["source_url"] == adapter.official_url

        # Verify raw records retrievable from PostgreSQL
        records = record_repo.list_by_version(version_id)
        assert len(records) >= 4
        assert any("node" in r.record_id for r in records)

        with get_engine().connect() as connection:
            road_node_count = connection.execute(
                text("SELECT count(*) FROM road_nodes WHERE source_version_id = :version_id"),
                {"version_id": version_id},
            ).scalar_one()
            road_edge_count = connection.execute(
                text("SELECT count(*) FROM road_edges WHERE source_version_id = :version_id"),
                {"version_id": version_id},
            ).scalar_one()
            unlinked_road_record_count = connection.execute(
                text(
                    "SELECT count(*) FROM road_edges e "
                    "LEFT JOIN source_records r ON r.id = e.source_record_id "
                    "WHERE e.source_version_id = :version_id AND r.id IS NULL"
                ),
                {"version_id": version_id},
            ).scalar_one()
        assert road_node_count >= 2
        assert road_edge_count >= 1
        assert unlinked_road_record_count == 0


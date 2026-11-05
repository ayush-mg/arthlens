"""
Reusable DatasetIngestionPipeline implementing the Template Method Pattern.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.5: 10 Steps).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from dataclasses import replace
from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from backend.arthlens.data.adapters.base import SourceAdapter
from backend.arthlens.data.models import (
    GeographicReconciliation,
    IngestionResult,
    NormalizedRecord,
    QualityAnomaly,
    QualityAssessment,
    RawRecord,
    SourceRecord,
    SourceVersionInfo,
)
from backend.arthlens.data.quality import QualityStatus
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.domain.repositories import (
    QuantityRepository,
    SourceRecordRepository,
    SourceRepository,
)
from backend.arthlens.ledger.staleness import is_source_stale


class DatasetIngestionPipeline:
    """
    Template Method pipeline executing the authoritative 10-step ingestion lifecycle:
    1. Retrieve raw snapshot (local file or live fetch, record timestamp, compute SHA-256 hash).
    2. Validate source schema and structural integrity constraints.
    3. Parse raw records into unnormalized structures.
    4. Normalize attributes, preserving original values alongside canonical mappings.
    5. Reconcile geography against official LGD hierarchy without fuzzy guessing.
    6. Assess quality (duplicate detection, missingness checks, range checks, staleness).
    7. Extract and construct immutable Quantity domain models.
    8. Derive and publish coverage and quality status.
    9. Persist snapshot and quantities idempotently in the epistemic ledger.
    10. Generate ingestion result summary.
    """

    def __init__(
        self,
        adapter: SourceAdapter,
        quantity_repo: Optional[QuantityRepository] = None,
        source_repo: Optional[SourceRepository] = None,
        record_repo: Optional[SourceRecordRepository] = None,
        session_factory: Optional[Callable[[], Any]] = None,
        geo_repo: Optional[Any] = None,
        facility_repo: Optional[Any] = None,
    ) -> None:
        self.adapter = adapter
        self.quantity_repo = quantity_repo
        self.source_repo = source_repo
        self.record_repo = record_repo
        self.session_factory = session_factory
        self.geo_repo = geo_repo
        self.facility_repo = facility_repo

    # ==========================================================================
    # Step 1: Retrieve Raw Content & Compute Cryptographic Hash
    # ==========================================================================
    def step_1_retrieve(
        self,
        source_input: Any,
        is_local: bool = True,
        fetch_params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, SourceVersionInfo]:
        """Step 1: Retrieve raw payload and compute deterministic SHA-256 content hash."""
        if is_local:
            path_obj = Path(source_input)
            with path_obj.open("rb") as f:
                raw_bytes = f.read()
            content_hash = hashlib.sha256(raw_bytes).hexdigest()
            raw_content = self.adapter.read_local(path_obj)
        else:
            raw_content = self.adapter.fetch_live(fetch_params or {})
            serialized = json.dumps(raw_content, sort_keys=True).encode("utf-8")
            content_hash = hashlib.sha256(serialized).hexdigest()

        version_info = SourceVersionInfo(
            source_id=self.adapter.source_id,
            content_hash=content_hash,
            retrieval_date=date.today(),
            version_tag=None,
        )
        return raw_content, version_info

    # ==========================================================================
    # Step 2: Validate Source Schema
    # ==========================================================================
    def step_2_validate_schema(self, raw_content: Any) -> Tuple[bool, List[str]]:
        """Step 2: Validate payload against source-specific integrity constraints."""
        return self.adapter.validate_schema(raw_content)

    # ==========================================================================
    # Step 3: Parse Raw Records
    # ==========================================================================
    def step_3_parse_records(self, raw_content: Any) -> List[RawRecord]:
        """Step 3: Parse raw payload into unnormalized RawRecord instances."""
        return self.adapter.parse_records(raw_content)

    # ==========================================================================
    # Step 4: Normalize Records
    # ==========================================================================
    def step_4_normalize(self, records: List[RawRecord]) -> List[NormalizedRecord]:
        """Step 4: Normalize records while preserving original fields and units."""
        return [self.adapter.normalize_record(r) for r in records]

    # ==========================================================================
    # Step 5: Reconcile Geography
    # ==========================================================================
    def step_5_reconcile_geography(
        self, normalized_records: List[NormalizedRecord]
    ) -> List[GeographicReconciliation]:
        """Step 5: Reconcile references to LGD codes without fuzzy guessing."""
        return [self.adapter.reconcile_geography(n) for n in normalized_records]

    # ==========================================================================
    # Step 6: Assess Quality & Detect Anomalies
    # ==========================================================================
    def step_6_check_quality(
        self,
        normalized_records: List[NormalizedRecord],
        reconciliations: List[GeographicReconciliation],
        as_of: Optional[str] = None,
    ) -> QualityAssessment:
        """
        Step 6: Evaluate data quality, detecting duplicates, missing values, and staleness.
        """
        anomalies: List[QualityAnomaly] = []

        # 1. Duplicate detection
        seen_keys: Dict[str, NormalizedRecord] = {}
        for rec, recon in zip(normalized_records, reconciliations):
            # Prefer canonical geo_unit_id or entity identifier
            key = recon.geo_unit_id or rec.record_id
            if key in seen_keys:
                anomalies.append(
                    QualityAnomaly(
                        anomaly_type="DUPLICATE_RECORD",
                        field_name="record_id",
                        description=f"Duplicate entity identifier detected: '{key}'",
                        record_id=rec.record_id,
                    )
                )
            else:
                seen_keys[key] = rec

        # 2. Missingness and field checks
        expected_fields: List[str] = []
        if self.adapter.source_id == "DS-05":
            expected_fields = ["total_population", "male_population", "female_population", "total_households"]

        for rec in normalized_records:
            for ef in expected_fields:
                val = rec.original_fields.get(ef)
                if val is None or (isinstance(val, str) and not val.strip()):
                    anomalies.append(
                        QualityAnomaly(
                            anomaly_type="MISSING_VALUE",
                            field_name=ef,
                            description=f"Missing or empty expected field '{ef}' in record {rec.record_id}",
                            record_id=rec.record_id,
                        )
                    )

        # 3. Staleness evaluation
        target_as_of = as_of or self.adapter.as_of_default
        stale = False
        if target_as_of:
            try:
                stale = is_source_stale(target_as_of, self.adapter.max_age_days)
            except Exception:
                stale = False

        # 4. Status determination
        has_unresolved = any(not r.resolved for r in reconciliations)
        has_missing = any(a.anomaly_type == "MISSING_VALUE" for a in anomalies)

        if not normalized_records:
            status = QualityStatus.UNAVAILABLE.value
        elif stale:
            status = QualityStatus.STALE.value
        elif has_unresolved or has_missing:
            status = QualityStatus.INCOMPLETE.value
        else:
            status = QualityStatus.CURRENT.value

        completeness = 1.0
        if expected_fields and normalized_records:
            total_slots = len(expected_fields) * len(normalized_records)
            missing_count = sum(1 for a in anomalies if a.anomaly_type == "MISSING_VALUE")
            completeness = max(0.0, 1.0 - (missing_count / total_slots))

        return QualityAssessment(
            is_stale=stale,
            anomalies=anomalies,
            completeness_score=completeness,
            status=status,
        )

    # ==========================================================================
    # Step 7: Extract Epistemic Quantities
    # ==========================================================================
    def step_7_extract_quantities(
        self,
        normalized_records: List[NormalizedRecord],
        reconciliations: List[GeographicReconciliation],
        quality_assessment: QualityAssessment,
    ) -> List[Quantity]:
        """Step 7: Extract immutable Quantity objects with correct kind, units, and flags."""
        quantities: List[Quantity] = []
        for norm, recon in zip(normalized_records, reconciliations):
            qs = self.adapter.extract_quantities(norm, recon, quality_assessment)
            for q in qs:
                # Ensure STALE flag is propagated if quality assessment indicates staleness
                if quality_assessment.is_stale and "STALE" not in q.quality_flags:
                    flags = frozenset(set(q.quality_flags) | {"STALE"})
                    q = replace(q, quality_flags=flags)
                quantities.append(q)
        return quantities

    # ==========================================================================
    # Step 8: Derive Coverage and Quality Status
    # ==========================================================================
    def step_8_derive_coverage_status(
        self,
        reconciliations: List[GeographicReconciliation],
        quality_assessment: QualityAssessment,
    ) -> str:
        """Step 8: Publish coverage and quality status."""
        return quality_assessment.status

    # ==========================================================================
    # Step 9: Persist Idempotently
    # ==========================================================================
    def step_9_persist(
        self,
        version_info: SourceVersionInfo,
        quantities_or_normalized: Any = None,
        reconciliations: Optional[List[GeographicReconciliation]] = None,
        quantities: Optional[List[Quantity]] = None,
        geo_units: Optional[List[Any]] = None,
        facilities: Optional[List[Any]] = None,
        normalized_records: Optional[List[NormalizedRecord]] = None,
    ) -> None:
        """
        Step 9: Persist source metadata, source version, normalized records, and ledger quantities.
        Guarantees:
        - Atomic transactional execution when session_factory is present.
        - Idempotency across repeated ingestions of identical snapshots.
        - Preservation of historical snapshot versions when content hash changes.
        """
        # Determine parameter mapping for backwards compatibility
        norm_records: List[NormalizedRecord] = []
        actual_quantities: List[Quantity] = []

        if normalized_records is not None:
            norm_records = normalized_records
        elif isinstance(quantities_or_normalized, list) and quantities_or_normalized and isinstance(quantities_or_normalized[0], NormalizedRecord):
            norm_records = quantities_or_normalized

        if quantities is not None:
            actual_quantities = quantities
        elif isinstance(quantities_or_normalized, list) and quantities_or_normalized and isinstance(quantities_or_normalized[0], Quantity):
            actual_quantities = quantities_or_normalized

        # Execute persistence transactionally if session_factory is configured
        if self.session_factory is not None:
            with self.session_factory() as session:
                with session.begin():
                    self._persist_with_session(
                        session=session,
                        version_info=version_info,
                        norm_records=norm_records,
                        reconciliations=reconciliations,
                        quantities=actual_quantities,
                    )
        else:
            self._persist_with_repositories(
                version_info=version_info,
                norm_records=norm_records,
                reconciliations=reconciliations,
                quantities=actual_quantities,
            )

    def _persist_with_session(
        self,
        session: Any,
        version_info: SourceVersionInfo,
        norm_records: List[NormalizedRecord],
        reconciliations: Optional[List[GeographicReconciliation]],
        quantities: List[Quantity],
    ) -> None:
        """Execute persistence inside an active database session transaction."""
        # 1. Source metadata
        if self.source_repo is not None and hasattr(self.source_repo, "save_source"):
            self.source_repo.save_source(
                {
                    "id": self.adapter.source_id,
                    "name": self.adapter.source_name,
                    "description": self.adapter.attribution,
                    "licence_text": self.adapter.license_name,
                    "max_age_days": self.adapter.max_age_days,
                    "status": "ACTIVE",
                },
                session=session,
            )

        # 2. Source version
        v_id = version_info.version_id or f"{self.adapter.source_id}:{version_info.content_hash[:16]}"
        if self.source_repo is not None and hasattr(self.source_repo, "save_version"):
            v_id = self.source_repo.save_version(
                {
                    "source_id": self.adapter.source_id,
                    "version": version_info.version_tag or version_info.content_hash[:8],
                    "retrieval_date": version_info.retrieval_date,
                    "content_hash": version_info.content_hash,
                    "source_url": self.adapter.official_url,
                    "status": "ACTIVE",
                },
                session=session,
            )
        version_info.version_id = v_id

        # 3. Normalized records
        if self.record_repo is not None and norm_records:
            source_records = self._build_source_records(
                version_id=v_id,
                norm_records=norm_records,
                reconciliations=reconciliations,
            )
            if hasattr(self.record_repo, "save_records"):
                self.record_repo.save_records(source_records, session=session)
            else:
                for sr in source_records:
                    self.record_repo.save_record(sr)

        # 4. Epistemic ledger quantities
        if self.quantity_repo is not None and quantities:
            for q in quantities:
                if hasattr(self.quantity_repo, "save") and "session" in self.quantity_repo.save.__code__.co_varnames:
                    self.quantity_repo.save(q, session=session)
                else:
                    self.quantity_repo.save(q)

    def _persist_with_repositories(
        self,
        version_info: SourceVersionInfo,
        norm_records: List[NormalizedRecord],
        reconciliations: Optional[List[GeographicReconciliation]],
        quantities: List[Quantity],
    ) -> None:
        """Execute persistence using standalone repository instances (offline / in-memory)."""
        # 1. Source metadata
        if self.source_repo is not None:
            self.source_repo.save_source(
                {
                    "id": self.adapter.source_id,
                    "name": self.adapter.source_name,
                    "description": self.adapter.attribution,
                    "licence_text": self.adapter.license_name,
                    "max_age_days": self.adapter.max_age_days,
                    "status": "ACTIVE",
                }
            )

        # 2. Source version
        v_id = version_info.version_id or f"{self.adapter.source_id}:{version_info.content_hash[:16]}"
        if self.source_repo is not None:
            v_id = self.source_repo.save_version(
                {
                    "source_id": self.adapter.source_id,
                    "version": version_info.version_tag or version_info.content_hash[:8],
                    "retrieval_date": version_info.retrieval_date,
                    "content_hash": version_info.content_hash,
                    "source_url": self.adapter.official_url,
                    "status": "ACTIVE",
                }
            )
        version_info.version_id = v_id

        # 3. Normalized records
        if self.record_repo is not None and norm_records:
            source_records = self._build_source_records(
                version_id=v_id,
                norm_records=norm_records,
                reconciliations=reconciliations,
            )
            self.record_repo.save_records(source_records)

        # 4. Epistemic ledger quantities
        if self.quantity_repo is not None and quantities:
            for q in quantities:
                self.quantity_repo.save(q)

    def _build_source_records(
        self,
        version_id: str,
        norm_records: List[NormalizedRecord],
        reconciliations: Optional[List[GeographicReconciliation]],
    ) -> List[SourceRecord]:
        """Convert normalized records and reconciliation results to persistent SourceRecord models."""
        source_records: List[SourceRecord] = []
        prov = self.adapter.get_provenance()
        recons = reconciliations or [None] * len(norm_records)

        for norm, recon in zip(norm_records, recons):
            tier_int = int(recon.resolution_tier) if (recon and recon.resolution_tier is not None) else None
            sr_id = f"{version_id}:{norm.record_id}"
            sr = SourceRecord(
                id=sr_id,
                source_id=self.adapter.source_id,
                source_version_id=version_id,
                record_id=norm.record_id,
                original_fields=norm.original_fields,
                normalized_fields=norm.normalized_fields,
                canonical_units=norm.canonical_units,
                geo_resolved=bool(recon.resolved) if recon else False,
                geo_unit_id=recon.geo_unit_id if recon else None,
                unresolved_raw_id=recon.unresolved_raw_id if recon else None,
                resolution_tier=tier_int,
                as_of=norm.as_of,
                temporal_support=norm.temporal_support,
                license_name=prov.license_name,
                attribution=prov.attribution,
            )
            source_records.append(sr)
        return source_records

    # ==========================================================================
    # Step 10: Generate Ingestion Result Summary
    # ==========================================================================
    def step_10_summarize(
        self,
        success: bool,
        version_info: SourceVersionInfo,
        raw_records: Optional[List[RawRecord]] = None,
        normalized_records: Optional[List[NormalizedRecord]] = None,
        reconciliations: Optional[List[GeographicReconciliation]] = None,
        quality_assessment: Optional[QualityAssessment] = None,
        quantities: Optional[List[Quantity]] = None,
        coverage_status: Optional[str] = None,
        errors: Optional[List[str]] = None,
    ) -> IngestionResult:
        """Step 10: Compile the authoritative IngestionResult output summary."""
        prov = self.adapter.get_provenance()
        qa = quality_assessment or QualityAssessment()
        cov = coverage_status or qa.status

        return IngestionResult(
            success=success,
            source_id=self.adapter.source_id,
            version_info=version_info,
            provenance=prov,
            raw_records=raw_records or [],
            normalized_records=normalized_records or [],
            reconciliations=reconciliations or [],
            quality_assessment=qa,
            quantities_registered=quantities or [],
            coverage_quality_status=cov,
            errors=errors or [],
        )

    # ==========================================================================
    # Template Method
    # ==========================================================================
    def ingest(
        self,
        source_input: Any,
        is_local: bool = True,
        fetch_params: Optional[Dict[str, Any]] = None,
        as_of: Optional[str] = None,
    ) -> IngestionResult:
        """
        Execute the authoritative 10-step template method workflow.
        """
        # Step 1: Retrieve raw content and version hash
        try:
            raw_content, version_info = self.step_1_retrieve(
                source_input=source_input,
                is_local=is_local,
                fetch_params=fetch_params,
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                source_id=self.adapter.source_id,
                version_info=SourceVersionInfo(
                    source_id=self.adapter.source_id,
                    content_hash="",
                    retrieval_date=date.today(),
                ),
                provenance=self.adapter.get_provenance(),
                errors=[f"Step 1 Retrieval failed: {e}"],
            )

        # Step 2: Validate schema
        is_valid, validation_errors = self.step_2_validate_schema(raw_content)
        if not is_valid:
            return self.step_10_summarize(
                success=False,
                version_info=version_info,
                errors=validation_errors,
            )

        # Step 3: Parse records
        raw_records = self.step_3_parse_records(raw_content)

        # Step 4: Normalize records
        normalized_records = self.step_4_normalize(raw_records)

        # Step 5: Reconcile geography
        reconciliations = self.step_5_reconcile_geography(normalized_records)

        # Step 6: Assess quality & detect anomalies
        quality_assessment = self.step_6_check_quality(
            normalized_records=normalized_records,
            reconciliations=reconciliations,
            as_of=as_of,
        )

        # Step 7: Extract quantities
        quantities = self.step_7_extract_quantities(
            normalized_records=normalized_records,
            reconciliations=reconciliations,
            quality_assessment=quality_assessment,
        )

        # Step 8: Derive coverage and quality status
        coverage_status = self.step_8_derive_coverage_status(
            reconciliations=reconciliations,
            quality_assessment=quality_assessment,
        )

        # Step 9: Persist idempotently
        self.step_9_persist(
            version_info=version_info,
            normalized_records=normalized_records,
            reconciliations=reconciliations,
            quantities=quantities,
        )

        # Step 10: Generate IngestionResult summary
        return self.step_10_summarize(
            success=True,
            version_info=version_info,
            raw_records=raw_records,
            normalized_records=normalized_records,
            reconciliations=reconciliations,
            quality_assessment=quality_assessment,
            quantities=quantities,
            coverage_status=coverage_status,
            errors=[],
        )


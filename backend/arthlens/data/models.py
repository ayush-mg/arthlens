"""
Data models and transfer objects for DatasetIngestionPipeline and Source Adapters.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.1, 7.2, 7.4, 7.5, Part 13.1 P2-1).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from backend.arthlens.domain.enums import ResolutionTier
from backend.arthlens.domain.quantity import Quantity


@dataclass
class RawRecord:
    """Raw record extracted directly from source payload before normalization."""
    record_id: str
    source_id: str
    payload: Dict[str, Any]


@dataclass
class NormalizedRecord:
    """Record normalized to ArthLens domain taxonomy with original fields preserved."""
    record_id: str
    raw_record: RawRecord
    original_fields: Dict[str, Any]
    normalized_fields: Dict[str, Any]
    canonical_units: Dict[str, str] = field(default_factory=dict)
    as_of: Optional[str] = None
    temporal_support: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeographicReconciliation:
    """Outcome of geographic reconciliation against official LGD hierarchy."""
    resolved: bool
    geo_unit_id: Optional[str] = None
    resolution_tier: Optional[ResolutionTier] = None
    unresolved_raw_id: Optional[str] = None
    notes: str = ""


@dataclass
class QualityAnomaly:
    """Specific quality issue or data anomaly detected during ingestion."""
    anomaly_type: str  # DUPLICATE_RECORD, MISSING_VALUE, OUTLIER, SCHEMA_MISMATCH
    field_name: str
    description: str
    record_id: Optional[str] = None


@dataclass
class QualityAssessment:
    """Summary of data quality checks, staleness, and detected anomalies."""
    is_stale: bool = False
    anomalies: List[QualityAnomaly] = field(default_factory=list)
    completeness_score: float = 1.0
    status: str = "CURRENT"


@dataclass
class SourceVersionInfo:
    """Cryptographic hash and retrieval metadata for snapshot idempotency."""
    source_id: str
    content_hash: str
    retrieval_date: date
    version_tag: Optional[str] = None
    version_id: Optional[str] = None


@dataclass
class SourceRecord:
    """Persisted normalized record preserving raw, normalized, and provenance attributes."""
    id: str  # Deterministic: f"{source_version_id}:{record_id}"
    source_id: str
    source_version_id: str
    record_id: str
    original_fields: Dict[str, Any]
    normalized_fields: Dict[str, Any]
    canonical_units: Dict[str, str] = field(default_factory=dict)
    geo_resolved: bool = False
    geo_unit_id: Optional[str] = None
    unresolved_raw_id: Optional[str] = None
    resolution_tier: Optional[int] = None
    as_of: Optional[str] = None
    temporal_support: Optional[Dict[str, Any]] = None
    license_name: Optional[str] = None
    attribution: Optional[str] = None


@dataclass
class ProvenanceMetadata:
    """Authoritative legal, licensing, and attribution metadata."""
    source_id: str
    source_name: str
    publisher: str
    official_url: str
    license_name: str
    attribution: str


@dataclass
class IngestionResult:
    """Final result produced by DatasetIngestionPipeline executing the 10 steps."""
    success: bool
    source_id: str
    version_info: SourceVersionInfo
    provenance: ProvenanceMetadata
    raw_records: List[RawRecord] = field(default_factory=list)
    normalized_records: List[NormalizedRecord] = field(default_factory=list)
    reconciliations: List[GeographicReconciliation] = field(default_factory=list)
    quality_assessment: QualityAssessment = field(default_factory=QualityAssessment)
    quantities_registered: List[Quantity] = field(default_factory=list)
    coverage_quality_status: str = "CURRENT"
    errors: List[str] = field(default_factory=list)


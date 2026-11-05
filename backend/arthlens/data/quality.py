"""
Quality vocabulary and anomaly evaluation for data ingestion.

Authoritative Specification: ArthLens Build Handbook v1.0 (Part 7.4, 7.5, Part 4.4).
Phase: Phase 2 (Real-Data Foundation and Atlas).
"""

from datetime import date
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence

from backend.arthlens.data.models import GeographicReconciliation, NormalizedRecord, QualityAnomaly, QualityAssessment
from backend.arthlens.ledger.staleness import is_source_stale, parse_as_of_date


class QualityStatus(str, Enum):
    """
    Quality and coverage vocabulary published by ArthLens data pipelines.
    Handbook Reference: Section 7.5, Part 13.1 P2-1 Requirement 14.
    """
    CURRENT = "CURRENT"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    ESTIMATED = "ESTIMATED"
    UNAVAILABLE = "UNAVAILABLE"


def detect_duplicates(
    records: Sequence[NormalizedRecord],
    identity_func: Optional[Callable[[NormalizedRecord], str]] = None,
) -> List[QualityAnomaly]:
    """
    Detect duplicate records in the incoming batch.
    """
    seen: Dict[str, NormalizedRecord] = {}
    anomalies: List[QualityAnomaly] = []

    for rec in records:
        key = identity_func(rec) if identity_func else rec.record_id
        if key in seen:
            anomalies.append(
                QualityAnomaly(
                    anomaly_type="DUPLICATE_RECORD",
                    field_name="record_id",
                    description=f"Duplicate record detected with identifier: '{key}'",
                    record_id=rec.record_id,
                )
            )
        else:
            seen[key] = rec

    return anomalies


def check_missing_values(
    records: Sequence[NormalizedRecord],
    expected_fields: Sequence[str],
) -> List[QualityAnomaly]:
    """
    Check for missing or empty values across required fields.
    """
    anomalies: List[QualityAnomaly] = []

    for rec in records:
        for field_name in expected_fields:
            raw_val = rec.original_fields.get(field_name)
            if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
                anomalies.append(
                    QualityAnomaly(
                        anomaly_type="MISSING_VALUE",
                        field_name=field_name,
                        description=f"Missing expected value for '{field_name}' in record {rec.record_id}",
                        record_id=rec.record_id,
                    )
                )

    return anomalies


def evaluate_quality(
    normalized_records: Sequence[NormalizedRecord],
    reconciliations: Sequence[GeographicReconciliation],
    as_of: Optional[str],
    max_age_days: int,
    expected_fields: Optional[Sequence[str]] = None,
    identity_func: Optional[Callable[[NormalizedRecord], str]] = None,
) -> QualityAssessment:
    """
    Perform comprehensive quality assessment across normalized records.
    """
    anomalies: List[QualityAnomaly] = []

    # 1. Duplicate detection
    anomalies.extend(detect_duplicates(normalized_records, identity_func=identity_func))

    # 2. Missingness checks
    if expected_fields:
        anomalies.extend(check_missing_values(normalized_records, expected_fields))

    # 3. Staleness evaluation
    stale = False
    if as_of:
        try:
            stale = is_source_stale(as_of, max_age_days)
        except Exception:
            stale = False

    # 4. Determine overall quality status
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

    # Compute completeness score
    total_checks = max(1, len(normalized_records) * (len(expected_fields) if expected_fields else 1))
    missing_count = sum(1 for a in anomalies if a.anomaly_type == "MISSING_VALUE")
    completeness = max(0.0, min(1.0, 1.0 - (missing_count / total_checks)))

    return QualityAssessment(
        is_stale=stale,
        anomalies=anomalies,
        completeness_score=completeness,
        status=status,
    )


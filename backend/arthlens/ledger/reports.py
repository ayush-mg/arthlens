"""Verified report artifacts and deterministic JSON/CSV exports."""

import csv
import json
from dataclasses import asdict, dataclass
from io import StringIO
from math import isfinite
from typing import Any

from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.renderer import AllowlistConfig, ReportRenderer


class ReportRejected(ValueError):
    """Raised when a draft fails ledger verification or free-number scanning."""

    def __init__(self, rejection_reason: str) -> None:
        super().__init__(rejection_reason)
        self.rejection_reason = rejection_reason


@dataclass(frozen=True)
class VerifiedReport:
    """A report body accepted by ReportRenderer and its referenced quantities."""

    rendered_text: str
    quantity_records_json: tuple[str, ...]

    @property
    def quantity_records(self) -> tuple[dict[str, Any], ...]:
        """Return independent records so callers cannot mutate the artifact."""
        return tuple(json.loads(record) for record in self.quantity_records_json)


def build_verified_report(
    template: str,
    ledger: Ledger,
    *,
    renderer: ReportRenderer | None = None,
    allowlist: AllowlistConfig | None = None,
) -> VerifiedReport:
    """Render a draft through the ledger gate and snapshot its referenced quantities."""
    result = (renderer or ReportRenderer()).render(template, ledger, allowlist)
    if not result.passed:
        raise ReportRejected(result.rejection_reason)

    records: list[str] = []
    seen_ids: set[str] = set()
    for quantity in result.resolved_quantities:
        if quantity.id in seen_ids:
            continue
        seen_ids.add(quantity.id)
        record = _quantity_record(quantity)
        records.append(_canonical_json(record))
    return VerifiedReport(result.rendered_text, tuple(records))


def export_report_json(report: VerifiedReport) -> str:
    """Serialize report text and referenced quantity metadata as strict JSON."""
    _require_report(report)
    payload = {
        "schema_version": 1,
        "rendered_text": report.rendered_text,
        "quantities": list(report.quantity_records),
    }
    return _canonical_json(payload)


def export_report_csv(report: VerifiedReport) -> str:
    """Export a report row and one metadata row per unique referenced quantity."""
    _require_report(report)
    columns = (
        "record_type",
        "rendered_text",
        "quantity_id",
        "definition_key",
        "value",
        "unit",
        "kind",
        "evidence_floor",
        "geo_unit_id",
        "resolution",
        "as_of",
        "uncertainty",
        "source_refs",
        "method_id",
        "model_version",
        "parent_ids",
        "quality_flags",
        "license_meta",
        "simulation_meta",
    )
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "record_type": "report",
            "rendered_text": _spreadsheet_safe(report.rendered_text),
        }
    )
    for record in report.quantity_records:
        row: dict[str, Any] = {"record_type": "quantity"}
        for column in columns:
            source_key = "id" if column == "quantity_id" else column
            if source_key not in record:
                continue
            value = record[source_key]
            if isinstance(value, (dict, list)):
                value = _canonical_json(value)
            row[column] = _spreadsheet_safe(value)
        writer.writerow(row)
    return output.getvalue()


def _quantity_record(quantity: Quantity) -> dict[str, Any]:
    if not isfinite(quantity.value):
        raise ValueError(f"Quantity {quantity.id!r} has a non-finite value.")
    simulation_meta = (
        asdict(quantity.simulation_meta)
        if quantity.simulation_meta is not None
        else None
    )
    return {
        "id": quantity.id,
        "definition_key": quantity.definition_key,
        "value": quantity.value,
        "unit": quantity.unit,
        "kind": quantity.kind.value,
        "evidence_floor": quantity.evidence_floor,
        "geo_unit_id": quantity.geo_unit_id,
        "resolution": quantity.resolution,
        "as_of": quantity.as_of,
        "uncertainty": quantity.uncertainty,
        "source_refs": quantity.source_refs,
        "method_id": quantity.method_id,
        "model_version": quantity.model_version,
        "parent_ids": quantity.parent_ids,
        "quality_flags": sorted(quantity.quality_flags),
        "license_meta": quantity.license_meta,
        "simulation_meta": simulation_meta,
    }


def _canonical_json(value: Any) -> str:
    _validate_json_value(value)
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_json_value(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("Report metadata must contain only finite numbers.")
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Report metadata object keys must be strings.")
            _validate_json_value(item)
        return
    raise TypeError(
        f"Report metadata value of type {type(value).__name__} is not JSON-compatible."
    )


def _spreadsheet_safe(value: Any) -> str | int | float | None:
    if not isinstance(value, str):
        return value
    first_nonspace = value.lstrip(" \t\r\n")[:1]
    if value.startswith(("\t", "\r")) or first_nonspace in {"=", "+", "-", "@"}:
        return "'" + value
    return value


def _require_report(report: VerifiedReport) -> None:
    if not isinstance(report, VerifiedReport):
        raise TypeError("report must be a VerifiedReport instance.")
    if not isinstance(report.rendered_text, str):
        raise TypeError("Verified report text must be a string.")

import csv
import json
from io import BytesIO, StringIO

import openpyxl
import pytest
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.ledger.ledger import Ledger
from backend.arthlens.ledger.renderer import AllowlistConfig
from backend.arthlens.ledger.reports import (
    ReportRejected,
    build_verified_report,
    export_report_csv,
    export_report_json,
)
from backend.arthlens.reporting.dossier_generator import (
    generate_dossier_csv,
    generate_dossier_json,
    generate_dossier_pdf,
    generate_dossier_xlsx,
)
from pypdf import PdfReader


def _ledger(*, unit: str = "persons") -> Ledger:
    ledger = Ledger()
    ledger.register(
        Quantity(
            id="quantity-1",
            definition_key="population.total",
            value=1200,
            unit=unit,
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district-1",
            resolution=2,
            as_of="2026-11-07",
            uncertainty=("INTERVAL", 1100.0, 1300.0),
            source_refs=(("dataset-v1", "table-1", "2026-11-07"),),
            method_id="census",
            model_version="1",
            quality_flags=frozenset({"LOW_COVERAGE"}),
            license_meta="GODL-India",
        )
    )
    return ledger


@pytest.mark.unit
def test_verified_report_exports_consistent_strict_json_and_csv():
    report = build_verified_report(
        "Population: {{q:quantity-1}}.",
        _ledger(),
    )

    payload = json.loads(export_report_json(report))
    rows = list(csv.DictReader(StringIO(export_report_csv(report))))

    assert payload["schema_version"] == 1
    assert payload["rendered_text"] == report.rendered_text
    assert payload["quantities"][0]["value"] == 1200
    assert payload["quantities"][0]["source_refs"] == [
        ["dataset-v1", "table-1", "2026-11-07"]
    ]
    assert len(rows) == 2
    assert rows[0]["record_type"] == "report"
    assert rows[0]["rendered_text"] == report.rendered_text
    assert rows[1]["record_type"] == "quantity"
    assert rows[1]["quantity_id"] == "quantity-1"
    assert json.loads(rows[1]["source_refs"]) == [
        ["dataset-v1", "table-1", "2026-11-07"]
    ]


@pytest.mark.unit
def test_report_builder_rejects_unverified_drafts_and_deduplicates_quantities():
    with pytest.raises(ReportRejected, match="unsupported numeric literal"):
        build_verified_report("Unsupported value: 500.", _ledger())

    report = build_verified_report(
        "{{q:quantity-1}}; again {{q:quantity-1}}.",
        _ledger(),
    )
    assert len(report.quantity_records) == 1


@pytest.mark.unit
@pytest.mark.parametrize("formula", ["=1+1", "+SUM(A1:A2)", "-1+2", "@SUM(A1:A2)", "\t=1"])
def test_csv_export_escapes_spreadsheet_formula_prefixes(formula):
    report = build_verified_report(
        formula,
        _ledger(),
        allowlist=AllowlistConfig(allowed_numbers=frozenset({"1", "2"})),
    )
    rows = list(csv.DictReader(StringIO(export_report_csv(report))))
    assert rows[0]["rendered_text"].startswith("'")


@pytest.mark.unit
def test_report_export_rejects_non_json_uncertainty_metadata():
    # Replace the fixture quantity with an otherwise valid record carrying unsupported metadata.
    unsafe = Ledger()
    unsafe.register(
        Quantity(
            id="quantity-unsafe",
            definition_key="population.total",
            value=1,
            unit="persons",
            kind=Kind.OBSERVED,
            evidence_floor=4,
            geo_unit_id="district-1",
            resolution=2,
            as_of="2026-11-07",
            uncertainty=object(),
            source_refs=(("dataset-v1", "table-1", "2026-11-07"),),
            method_id="census",
            model_version="1",
            license_meta="GODL-India",
        )
    )

    with pytest.raises(TypeError, match="not JSON-compatible"):
        build_verified_report("Population: {{q:quantity-unsafe}}.", unsafe)


@pytest.mark.unit
def test_dossier_exports_do_not_upgrade_missing_provenance_or_quality():
    data = {
        "geo_name": "Test District",
        "indicators": [
            {
                "quantity_id": "quantity-unverified",
                "definition_key": "population.total",
                "value": 12.0,
                "unit": "persons",
                "source_refs": [["unregistered-version", "table:row:1", "2026-11-07"]],
                "parent_ids": [],
                "provenance_complete": False,
            }
        ],
    }

    csv_rows = list(csv.reader(StringIO(generate_dossier_csv(data).decode("utf-8"))))
    csv_headers = next(row for row in csv_rows if "Ledger Quantity ID" in row)
    csv_record = next(row for row in csv_rows if "quantity-unverified" in row)
    csv_values = dict(zip(csv_headers, csv_record))
    assert csv_values["Evidence Floor"] == ""
    assert csv_values["Quality Status"] == "UNCLASSIFIED"
    assert csv_values["Source Name"] == ""
    assert csv_values["Source Version ID"] == ""
    assert csv_values["Provenance Complete"] == "False"

    workbook = openpyxl.load_workbook(BytesIO(generate_dossier_xlsx(data)))
    sheet = workbook["Ledger Indicators"]
    xlsx_headers = [cell.value for cell in sheet[1]]
    xlsx_values = dict(zip(xlsx_headers, [cell.value for cell in sheet[2]]))
    assert xlsx_values["Floor"] is None
    assert xlsx_values["Quality Status"] == "UNCLASSIFIED"
    assert xlsx_values["Source Name"] is None
    assert xlsx_values["Source Version ID"] is None
    assert xlsx_values["Provenance Complete"] is False

    pdf = PdfReader(BytesIO(generate_dossier_pdf(data)))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "quantity-unverified" in pdf_text
    assert "Provenance incomplete" in pdf_text
    assert "VERIFIED" not in pdf_text


@pytest.mark.unit
def test_dossier_exports_include_reproducible_simulation_and_lineage():
    simulation = {
        "run_id": "run-simulation-1",
        "status": "COMPLETED",
        "metadata": {
            "scenario_id": "scenario-1",
            "model_version": "arthlens-financial-simulation-v1",
            "seed": 17,
            "sample_count": 100,
        },
        "configuration": {"quantile_levels": [0.1, 0.5, 0.9]},
        "input_quantity_ids": {"projection": {"initial_quantity": "input-quantity-1"}},
        "converged": True,
        "metrics": {
            "minimum_cash": {
                "mean": 250.0,
                "mean_quantity_id": "simulated-mean-1",
                "standard_error": 3.0,
                "standard_error_quantity_id": "simulated-se-1",
                "converged": True,
                "quantiles": {
                    "0.1": {"value": -20.0, "quantity_id": "simulated-q10-1"},
                    "0.5": {"value": 200.0, "quantity_id": "simulated-q50-1"},
                    "0.9": {"value": 500.0, "quantity_id": "simulated-q90-1"},
                },
            }
        },
        "cash_shortfall_probability": {
            "value": 0.1,
            "quantity_id": "simulated-shortfall-1",
            "standard_error": 0.03,
            "standard_error_quantity_id": "simulated-shortfall-se-1",
            "converged": True,
        },
        "sensitivity": {
            "baseline_outputs": {},
            "points": [{
                "parameter": "price_per_unit_by_month.1",
                "value": 90.0,
                "parameter_quantity_id": "sensitivity-input-1",
                "outputs": {
                    "minimum_cash": {
                        "value": 100.0,
                        "quantity_id": "sensitivity-output-1",
                        "delta": -150.0,
                        "delta_quantity_id": "sensitivity-delta-1",
                    }
                },
            }],
        },
    }
    data = {
        "geo_name": "Test District",
        "scenario": {
            "name": "Test enterprise",
            "calculations": {},
            "financial_simulation": simulation,
        },
    }

    json_payload = json.loads(generate_dossier_json(data))
    assert json_payload["scenario"]["financial_simulation"]["metadata"]["seed"] == 17
    assert json_payload["scenario"]["financial_simulation"]["metrics"]["minimum_cash"]["mean_quantity_id"] == "simulated-mean-1"

    csv_text = generate_dossier_csv(data).decode("utf-8-sig")
    assert "REPRODUCIBLE MONTE CARLO AND SENSITIVITY ANALYSIS" in csv_text
    assert "simulated-q10-1" in csv_text
    assert "sensitivity-delta-1" in csv_text
    assert "input-quantity-1" in csv_text

    workbook = openpyxl.load_workbook(BytesIO(generate_dossier_xlsx(data)))
    assert "Simulation Metadata" in workbook.sheetnames
    assert "Simulation Analysis" in workbook.sheetnames
    assert "simulated-mean-1" in [cell.value for row in workbook["Simulation Analysis"].iter_rows() for cell in row]
    assert "input-quantity-1" in str(workbook["Simulation Metadata"]["B8"].value)

    pdf = PdfReader(BytesIO(generate_dossier_pdf(data)))
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    assert "Reproducible Monte Carlo and Sensitivity Analysis" in pdf_text
    assert "run-simulation-1" in pdf_text
    assert "simulated-q10-1" in pdf_text

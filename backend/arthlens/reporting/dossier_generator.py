"""
Decision Dossier Report Generator for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 10.3, Part 4.6).
Supported Formats: JSON, CSV, XLSX, PDF.
Security: Enforces formula-injection sanitization for CSV and XLSX exports (OWASP CSV Injection).
"""

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _simulation_metric_unit(metric_name: str) -> str:
    units = {
        "total_revenue": "INR",
        "total_debt_service": "INR",
        "minimum_cash": "INR",
    }
    return units.get(metric_name, "")


def sanitize_for_spreadsheet(val: Any) -> Any:
    """
    Sanitize text to prevent CSV/formula injection in spreadsheet viewers.
    Any string starting with =, +, -, @, \\t, or \\r is prefixed with a single quote.
    """
    if val is None:
        return ""
    if isinstance(val, (int, float, bool)):
        return val
    text = str(val)
    if text.startswith(DANGEROUS_FORMULA_PREFIXES) or text.strip().startswith(
        DANGEROUS_FORMULA_PREFIXES
    ):
        return f"'{text}"
    return text


def generate_dossier_json(data: Dict[str, Any]) -> bytes:
    """Generate structured JSON representation of the decision dossier."""
    payload = {
        "report_type": "ARTHLENS_DECISION_DOSSIER",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "epistemic_standard": "Handbook v1.0 epistemic classification",
        **data,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def generate_dossier_csv(data: Dict[str, Any]) -> bytes:
    """Generate CSV format with formula injection protection."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Section 1: Masthead Metadata
    writer.writerow(["ARTHLENS DECISION DOSSIER", "EVIDENCE AND ASSUMPTION BRIEF"])
    writer.writerow(
        ["Generated At", sanitize_for_spreadsheet(datetime.now(timezone.utc).isoformat())]
    )
    writer.writerow(["Territory Name", sanitize_for_spreadsheet(data.get("geo_name", "N/A"))])
    writer.writerow(["Territory LGD Code", sanitize_for_spreadsheet(data.get("lgd_code", "N/A"))])
    writer.writerow(
        ["Territory Census Code", sanitize_for_spreadsheet(data.get("census_code", "N/A"))]
    )
    writer.writerow([])

    # Section 2: Ledger quantities with per-row classification and provenance.
    writer.writerow(["LEDGER QUANTITIES (EVIDENCE CLASSIFICATION PER ROW)"])
    writer.writerow(
        [
            "Definition Key",
            "Observed Value",
            "Unit",
            "Ledger Quantity ID",
            "Kind",
            "Evidence Floor",
            "Quality Status",
            "Source Name",
            "Source ID",
            "Source Version ID",
            "Source References",
            "Lineage Source Versions",
            "Input Quantity IDs",
            "Provenance Complete",
            "As Of",
        ]
    )
    indicators: List[Dict[str, Any]] = data.get("indicators", [])
    if indicators:
        for ind in indicators:
            writer.writerow(
                [
                    sanitize_for_spreadsheet(ind.get("definition_key", "")),
                    sanitize_for_spreadsheet(ind.get("value", "")),
                    sanitize_for_spreadsheet(ind.get("unit", "")),
                    sanitize_for_spreadsheet(ind.get("quantity_id")),
                    sanitize_for_spreadsheet(ind.get("kind")),
                    sanitize_for_spreadsheet(ind.get("evidence_floor")),
                    sanitize_for_spreadsheet(ind.get("quality_status", "UNCLASSIFIED")),
                    sanitize_for_spreadsheet(ind.get("source_name")),
                    sanitize_for_spreadsheet(ind.get("source_id")),
                    sanitize_for_spreadsheet(ind.get("source_version_id")),
                    sanitize_for_spreadsheet(json.dumps(ind.get("source_refs", []), ensure_ascii=False)),
                    sanitize_for_spreadsheet(
                        json.dumps(ind.get("lineage_source_provenance", []), ensure_ascii=False)
                    ),
                    sanitize_for_spreadsheet(json.dumps(ind.get("parent_ids", []), ensure_ascii=False)),
                    sanitize_for_spreadsheet(ind.get("provenance_complete", False)),
                    sanitize_for_spreadsheet(ind.get("as_of", "")),
                ]
            )
    else:
        writer.writerow(["No indicators observed for this territory", "", "", "", "", "", ""])
    writer.writerow([])

    # Section 3: Scenario Business Assumptions & Calculations (Floor 1)
    scenario: Optional[Dict[str, Any]] = data.get("scenario")
    if scenario:
        writer.writerow(["SCENARIO BUSINESS MODEL & FINANCIAL SIMULATION (FLOOR 1 MODEL)"])
        writer.writerow(
            [
                "Scenario Name",
                sanitize_for_spreadsheet(scenario.get("name", "Exploratory Scenario")),
            ]
        )
        calc = scenario.get("calculations") or {}
        writer.writerow(
            ["User Capital (INR)", sanitize_for_spreadsheet(scenario.get("capital", "N/A"))]
        )
        writer.writerow(
            [
                "Target Monthly Units",
                sanitize_for_spreadsheet(calc.get("target_monthly_units", "N/A")),
            ]
        )
        writer.writerow(
            [
                "Unit Selling Price (INR)",
                sanitize_for_spreadsheet(calc.get("price_per_unit", "N/A")),
            ]
        )
        writer.writerow(
            [
                "Variable Cost / Unit (INR)",
                sanitize_for_spreadsheet(calc.get("variable_cost_per_unit", "N/A")),
            ]
        )
        writer.writerow(
            [
                "Fixed Costs / Month (INR)",
                sanitize_for_spreadsheet(calc.get("fixed_costs_per_month", "N/A")),
            ]
        )
        writer.writerow(
            [
                "Break-Even Volume (Units)",
                sanitize_for_spreadsheet(calc.get("break_even_units", "N/A")),
            ]
        )
        writer.writerow(
            [
                "Contribution Margin (INR)",
                sanitize_for_spreadsheet(calc.get("contribution_margin", "N/A")),
            ]
        )
        writer.writerow(
            ["Monthly Loan EMI (INR)", sanitize_for_spreadsheet(calc.get("monthly_emi", "N/A"))]
        )
        writer.writerow(
            ["Total Loan Repaid (INR)", sanitize_for_spreadsheet(calc.get("total_repaid", "N/A"))]
        )
        spatial_demand = calc.get("spatial_demand_allocated")
        spatial_status = calc.get("spatial_demand_status")
        spatial_display = spatial_demand if spatial_status == "COMPLETED" else "INSUFFICIENT_DATA"
        writer.writerow(["Spatial Demand Share (Units)", sanitize_for_spreadsheet(spatial_display)])
        writer.writerow(
            [
                "Feasibility Verdict",
                sanitize_for_spreadsheet(calc.get("feasibility_status", "CALCULATED")),
            ]
        )
        simulation = scenario.get("financial_simulation") or {}
        if simulation.get("status") == "COMPLETED":
            metadata = simulation.get("metadata") or {}
            writer.writerow([])
            writer.writerow(["REPRODUCIBLE MONTE CARLO AND SENSITIVITY ANALYSIS"])
            writer.writerow(["Simulation Run ID", sanitize_for_spreadsheet(simulation.get("run_id"))])
            writer.writerow(["Seed", sanitize_for_spreadsheet(metadata.get("seed"))])
            writer.writerow(["Sample Count", sanitize_for_spreadsheet(metadata.get("sample_count"))])
            writer.writerow(["Model Version", sanitize_for_spreadsheet(metadata.get("model_version"))])
            writer.writerow(["Converged", sanitize_for_spreadsheet(simulation.get("converged"))])
            writer.writerow(["Configuration", sanitize_for_spreadsheet(json.dumps(simulation.get("configuration") or {}, ensure_ascii=False))])
            writer.writerow(["Input Quantity IDs", sanitize_for_spreadsheet(json.dumps(simulation.get("input_quantity_ids") or {}, ensure_ascii=False))])
            writer.writerow(["Metric", "Mean", "Unit", "Mean Quantity ID", "Standard Error", "Standard Error Quantity ID", "Converged"])
            for metric_name, metric in (simulation.get("metrics") or {}).items():
                writer.writerow([
                    sanitize_for_spreadsheet(metric_name),
                    sanitize_for_spreadsheet(metric.get("mean")),
                    _simulation_metric_unit(metric_name),
                    sanitize_for_spreadsheet(metric.get("mean_quantity_id")),
                    sanitize_for_spreadsheet(metric.get("standard_error")),
                    sanitize_for_spreadsheet(metric.get("standard_error_quantity_id")),
                    sanitize_for_spreadsheet(metric.get("converged")),
                ])
                for level, quantile in (metric.get("quantiles") or {}).items():
                    writer.writerow([
                        sanitize_for_spreadsheet(metric_name),
                        sanitize_for_spreadsheet(f"Quantile {level}"),
                        sanitize_for_spreadsheet(quantile.get("value")),
                        _simulation_metric_unit(metric_name),
                        sanitize_for_spreadsheet(quantile.get("quantity_id")),
                        "",
                        "",
                    ])
            shortfall = simulation.get("cash_shortfall_probability") or {}
            writer.writerow([
                "Cash Shortfall Probability",
                sanitize_for_spreadsheet(shortfall.get("value")),
                "probability",
                sanitize_for_spreadsheet(shortfall.get("quantity_id")),
                sanitize_for_spreadsheet(shortfall.get("standard_error")),
                sanitize_for_spreadsheet(shortfall.get("standard_error_quantity_id")),
                sanitize_for_spreadsheet(shortfall.get("converged")),
            ])
            writer.writerow(["Sensitivity Parameter", "Alternative Value", "Metric", "Output", "Unit", "Output Quantity ID", "Delta", "Delta Quantity ID"])
            for point in (simulation.get("sensitivity") or {}).get("points", []):
                for metric_name, sensitivity_output in (point.get("outputs") or {}).items():
                    writer.writerow([
                        sanitize_for_spreadsheet(point.get("parameter")),
                        sanitize_for_spreadsheet(point.get("value")),
                        sanitize_for_spreadsheet(metric_name),
                        sanitize_for_spreadsheet(sensitivity_output.get("value")),
                        _simulation_metric_unit(metric_name),
                        sanitize_for_spreadsheet(sensitivity_output.get("quantity_id")),
                        sanitize_for_spreadsheet(sensitivity_output.get("delta")),
                        sanitize_for_spreadsheet(sensitivity_output.get("delta_quantity_id")),
                    ])
        writer.writerow([])

    # Section 4: Epistemic Declaration
    writer.writerow(["EPISTEMIC ATTESTATION"])
    writer.writerow(
        [
            "Statement",
            "Every quantity above represents an auditable entry in the ArthLens PostgreSQL epistemic ledger.",
        ]
    )
    writer.writerow(
        [
            "Invariant",
            "Floor 1 scenario assumptions are sandboxed and never overwrite Floor 4 empirical facts.",
        ]
    )

    return output.getvalue().encode("utf-8-sig")


def generate_dossier_xlsx(data: Dict[str, Any]) -> bytes:
    """Generate Excel workbook with formatted sheets and formula injection defense."""
    wb = openpyxl.Workbook()

    # Style presets
    header_fill = PatternFill(
        start_color="1A3A2F", end_color="1A3A2F", fill_type="solid"
    )  # Editorial Forest
    alt_row_fill = PatternFill(
        start_color="F9F7F1", end_color="F9F7F1", fill_type="solid"
    )  # Editorial Paper
    white_font_bold = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Georgia", size=14, bold=True, color="1A3A2F")
    section_font = Font(name="Georgia", size=12, bold=True, color="1A3A2F")
    regular_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)
    thin_border = Border(
        left=Side(style="thin", color="D1C7B7"),
        right=Side(style="thin", color="D1C7B7"),
        top=Side(style="thin", color="D1C7B7"),
        bottom=Side(style="thin", color="D1C7B7"),
    )

    # Sheet 1: Executive Summary
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_summary.views.sheetView[0].showGridLines = True

    ws_summary.cell(row=1, column=1, value="ArthLens Decision Dossier").font = title_font
    ws_summary.cell(
        row=2, column=1, value="Auditable Evidence Brief & Micro-Enterprise Feasibility"
    ).font = regular_font

    meta_rows = [
        ("Target Jurisdiction", sanitize_for_spreadsheet(data.get("geo_name", "N/A"))),
        ("LGD Code", sanitize_for_spreadsheet(data.get("lgd_code", "N/A"))),
        ("Census 2011 Code", sanitize_for_spreadsheet(data.get("census_code", "N/A"))),
        ("Resolution Tier", sanitize_for_spreadsheet(data.get("level"))),
        ("Generated At (UTC)", sanitize_for_spreadsheet(datetime.now(timezone.utc).isoformat())),
        ("Epistemic Standard", "Handbook v1.0 (Strict Four-Floor Epistemic Separation)"),
    ]

    for r_idx, (k, v) in enumerate(meta_rows, start=4):
        c_k = ws_summary.cell(row=r_idx, column=1, value=k)
        c_k.font = bold_font
        c_k.fill = alt_row_fill
        c_k.border = thin_border
        c_v = ws_summary.cell(row=r_idx, column=2, value=v)
        c_v.font = regular_font
        c_v.border = thin_border

    # Scenario highlights if available
    scenario: Optional[Dict[str, Any]] = data.get("scenario")
    start_r = 12
    if scenario:
        ws_summary.cell(
            row=start_r, column=1, value="Scenario Simulation Highlights (Floor 1)"
        ).font = section_font
        calc = scenario.get("calculations") or {}
        scen_rows = [
            ("Scenario Name", sanitize_for_spreadsheet(scenario.get("name", "Exploratory"))),
            ("Initial Capital (INR)", sanitize_for_spreadsheet(scenario.get("capital", "N/A"))),
            (
                "Monthly Break-Even Volume",
                sanitize_for_spreadsheet(calc.get("break_even_units", "N/A")),
            ),
            (
                "Unit Contribution Margin",
                sanitize_for_spreadsheet(calc.get("contribution_margin", "N/A")),
            ),
            ("Monthly Loan EMI (INR)", sanitize_for_spreadsheet(calc.get("monthly_emi", "N/A"))),
            (
                "Spatial Demand Allocation",
                sanitize_for_spreadsheet(
                    calc.get("spatial_demand_allocated")
                    if calc.get("spatial_demand_status") == "COMPLETED"
                    else "INSUFFICIENT_DATA"
                ),
            ),
            (
                "Feasibility Status",
                sanitize_for_spreadsheet(calc.get("feasibility_status", "CALCULATED")),
            ),
        ]
        for idx, (k, v) in enumerate(scen_rows, start=start_r + 2):
            ck = ws_summary.cell(row=idx, column=1, value=k)
            ck.font = bold_font
            ck.fill = alt_row_fill
            ck.border = thin_border
            cv = ws_summary.cell(row=idx, column=2, value=v)
            cv.font = regular_font
            cv.border = thin_border

    # Sheet 2: Ledger quantities with evidence classification per row.
    ws_ind = wb.create_sheet(title="Ledger Indicators")
    ws_ind.views.sheetView[0].showGridLines = True
    headers = [
        "Definition Key",
        "Value",
        "Unit",
        "Ledger Quantity ID",
        "Kind",
        "Floor",
        "Quality Status",
        "Source Name",
        "Source ID",
        "Source Version ID",
        "Source References",
        "Lineage Source Versions",
        "Input Quantity IDs",
        "Provenance Complete",
        "As Of",
    ]
    for c_idx, h in enumerate(headers, start=1):
        cell = ws_ind.cell(row=1, column=c_idx, value=h)
        cell.font = white_font_bold
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    indicators = data.get("indicators", [])
    for r_idx, ind in enumerate(indicators, start=2):
        row_vals = [
            sanitize_for_spreadsheet(ind.get("definition_key", "")),
            sanitize_for_spreadsheet(ind.get("value", "")),
            sanitize_for_spreadsheet(ind.get("unit", "")),
            sanitize_for_spreadsheet(ind.get("quantity_id")),
            sanitize_for_spreadsheet(ind.get("kind")),
            sanitize_for_spreadsheet(ind.get("evidence_floor")),
            sanitize_for_spreadsheet(ind.get("quality_status", "UNCLASSIFIED")),
            sanitize_for_spreadsheet(ind.get("source_name")),
            sanitize_for_spreadsheet(ind.get("source_id")),
            sanitize_for_spreadsheet(ind.get("source_version_id")),
            sanitize_for_spreadsheet(json.dumps(ind.get("source_refs", []), ensure_ascii=False)),
            sanitize_for_spreadsheet(
                json.dumps(ind.get("lineage_source_provenance", []), ensure_ascii=False)
            ),
            sanitize_for_spreadsheet(json.dumps(ind.get("parent_ids", []), ensure_ascii=False)),
            sanitize_for_spreadsheet(ind.get("provenance_complete", False)),
            sanitize_for_spreadsheet(ind.get("as_of", "")),
        ]
        for c_idx, val in enumerate(row_vals, start=1):
            c = ws_ind.cell(row=r_idx, column=c_idx, value=val)
            c.font = regular_font
            c.border = thin_border
            if r_idx % 2 == 1:
                c.fill = alt_row_fill

    simulation = (data.get("scenario") or {}).get("financial_simulation") or {}
    if simulation.get("status") == "COMPLETED":
        metadata = simulation.get("metadata") or {}
        ws_metadata = wb.create_sheet(title="Simulation Metadata")
        metadata_rows = [
            ("Run ID", sanitize_for_spreadsheet(simulation.get("run_id"))),
            ("Scenario ID", sanitize_for_spreadsheet(metadata.get("scenario_id"))),
            ("Model Version", sanitize_for_spreadsheet(metadata.get("model_version"))),
            ("Seed", sanitize_for_spreadsheet(metadata.get("seed"))),
            ("Sample Count", sanitize_for_spreadsheet(metadata.get("sample_count"))),
            ("Converged", sanitize_for_spreadsheet(simulation.get("converged"))),
            ("Configuration", sanitize_for_spreadsheet(json.dumps(simulation.get("configuration") or {}, ensure_ascii=False))),
            ("Input Quantity IDs", sanitize_for_spreadsheet(json.dumps(simulation.get("input_quantity_ids") or {}, ensure_ascii=False))),
        ]
        for row in metadata_rows:
            ws_metadata.append(row)
        for cell in ws_metadata["A"]:
            cell.font = bold_font
            cell.fill = alt_row_fill
            cell.border = thin_border
        for column in ws_metadata.columns:
            max_len = max(len(str(cell.value or "")) for cell in column)
            ws_metadata.column_dimensions[get_column_letter(column[0].column)].width = max(max_len + 4, 18)

        ws_simulation = wb.create_sheet(title="Simulation Analysis")
        ws_simulation.append(["Metric", "Statistic", "Value", "Unit", "Ledger Quantity ID", "Standard Error", "Converged"])
        for cell in ws_simulation[1]:
            cell.font = white_font_bold
            cell.fill = header_fill
            cell.border = thin_border
        for metric_name, metric in (simulation.get("metrics") or {}).items():
            ws_simulation.append([
                sanitize_for_spreadsheet(metric_name),
                "Mean",
                sanitize_for_spreadsheet(metric.get("mean")),
                _simulation_metric_unit(metric_name),
                sanitize_for_spreadsheet(metric.get("mean_quantity_id")),
                sanitize_for_spreadsheet(metric.get("standard_error")),
                sanitize_for_spreadsheet(metric.get("converged")),
            ])
            for level, quantile in (metric.get("quantiles") or {}).items():
                ws_simulation.append([
                    sanitize_for_spreadsheet(metric_name),
                    sanitize_for_spreadsheet(f"Quantile {level}"),
                    sanitize_for_spreadsheet(quantile.get("value")),
                    _simulation_metric_unit(metric_name),
                    sanitize_for_spreadsheet(quantile.get("quantity_id")),
                    None,
                    None,
                ])
        shortfall = simulation.get("cash_shortfall_probability") or {}
        ws_simulation.append([
            "Cash shortfall probability",
            "Probability",
            sanitize_for_spreadsheet(shortfall.get("value")),
            "probability",
            sanitize_for_spreadsheet(shortfall.get("quantity_id")),
            sanitize_for_spreadsheet(shortfall.get("standard_error")),
            sanitize_for_spreadsheet(shortfall.get("converged")),
        ])
        for point in (simulation.get("sensitivity") or {}).get("points", []):
            for metric_name, output in (point.get("outputs") or {}).items():
                ws_simulation.append([
                    sanitize_for_spreadsheet(point.get("parameter")),
                    sanitize_for_spreadsheet(f"Sensitivity at {point.get('value')}"),
                    sanitize_for_spreadsheet(output.get("value")),
                    _simulation_metric_unit(metric_name),
                    sanitize_for_spreadsheet(output.get("quantity_id")),
                    sanitize_for_spreadsheet(output.get("delta")),
                    sanitize_for_spreadsheet(output.get("delta_quantity_id")),
                ])
        for column in ws_simulation.columns:
            max_len = max(len(str(cell.value or "")) for cell in column)
            ws_simulation.column_dimensions[get_column_letter(column[0].column)].width = max(max_len + 4, 14)

    # Auto-fit columns
    for ws in (ws_summary, ws_ind):
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_dossier_pdf(data: Dict[str, Any]) -> bytes:
    """Generate high-fidelity publication-quality PDF dossier."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DossierTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A3A2F"),
    )
    subtitle_style = ParagraphStyle(
        "DossierSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#645B50"),
    )
    section_style = ParagraphStyle(
        "DossierSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1A3A2F"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "DossierBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2C2621"),
    )
    bold_style = ParagraphStyle(
        "DossierBold",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    elements: List[Any] = []

    # Title & Masthead
    elements.append(Paragraph("ArthLens Decision Dossier", title_style))
    elements.append(
        Paragraph("Auditable Territorial Evidence Brief • Handbook v1.0 Compliant", subtitle_style)
    )
    elements.append(Spacer(1, 10))
    elements.append(
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#C29B38"), spaceAfter=12)
    )

    # Territory Information Box
    geo_name = str(data.get("geo_name", "Prayagraj"))
    lgd_code = str(data.get("lgd_code", "120"))
    census_code = str(data.get("census_code", "175"))
    meta_table_data = [
        [
            Paragraph("<b>Target Jurisdiction:</b>", body_style),
            Paragraph(f"<b>{geo_name}</b>", bold_style),
            Paragraph("<b>LGD Code:</b>", body_style),
            Paragraph(lgd_code, body_style),
        ],
        [
            Paragraph("<b>Census 2011 Code:</b>", body_style),
            Paragraph(census_code, body_style),
            Paragraph("<b>Generated At:</b>", body_style),
            Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), body_style),
        ],
    ]
    meta_table = Table(meta_table_data, colWidths=[120, 150, 110, 160])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9F7F1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D1C7B7")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#EAE3D9")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # Section 1: Ingested Empirical Indicators (Floor 4)
    elements.append(Paragraph("1. Ledger Quantities and Evidence Classification", section_style))
    indicators = data.get("indicators", [])
    if indicators:
        ind_rows = [
            [
                Paragraph("<b>Indicator</b>", bold_style),
                Paragraph("<b>Observed Value</b>", bold_style),
                Paragraph("<b>Unit</b>", bold_style),
                Paragraph("<b>As Of</b>", bold_style),
                Paragraph("<b>Quality</b>", bold_style),
                Paragraph("<b>Trace</b>", bold_style),
            ]
        ]
        for ind in indicators:
            val_str = (
                f"{ind.get('value'):,}"
                if isinstance(ind.get("value"), (int, float))
                else str(ind.get("value", "N/A"))
            )
            ind_rows.append(
                [
                    Paragraph(str(ind.get("definition_key", "")), body_style),
                    Paragraph(val_str, bold_style),
                    Paragraph(str(ind.get("unit", "")), body_style),
                    Paragraph(str(ind.get("as_of", "")), body_style),
                    Paragraph(str(ind.get("quality_status", "UNCLASSIFIED")), body_style),
                    Paragraph(
                        "<br/>".join(
                            escape(str(value))
                            for value in (
                                f"Ledger: {ind.get('quantity_id')}" if ind.get("quantity_id") else "",
                                f"Source: {ind.get('source_name')} ({ind.get('source_id')}) / version {ind.get('source_version_id')}"
                                if ind.get("source_version_id")
                                else "Provenance incomplete",
                                "Source versions: "
                                + ", ".join(
                                    f"{item.get('source_id')} / {item.get('source_version_id')}"
                                    for item in (ind.get("lineage_source_provenance") or [])
                                    if item.get("provenance_complete")
                                )
                                if any(
                                    item.get("provenance_complete")
                                    for item in (ind.get("lineage_source_provenance") or [])
                                )
                                else "",
                                f"Inputs: {', '.join(ind.get('parent_ids') or [])}"
                                if ind.get("parent_ids")
                                else "",
                            )
                            if value
                        ),
                        body_style,
                    ),
                ]
            )
        ind_table = Table(ind_rows, colWidths=[125, 75, 50, 70, 65, 145])
        ind_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A3A2F")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1C7B7")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1A3A2F")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        # Style header texts to white
        for c in range(5):
            ind_rows[0][c].style.textColor = colors.white
        elements.append(ind_table)
    else:
        elements.append(
            Paragraph("No empirical indicators registered for this territory.", body_style)
        )

    elements.append(Spacer(1, 14))

    # Section 2: Scenario Business Model & Financial Simulation (Floor 1)
    scenario: Optional[Dict[str, Any]] = data.get("scenario")
    if scenario:
        elements.append(
            Paragraph("2. Scenario Financial & Demand Simulation (Floor 1 Model)", section_style)
        )
        calc = scenario.get("calculations") or {}
        scen_table_data = [
            [
                Paragraph("<b>Scenario Name:</b>", body_style),
                Paragraph(str(scenario.get("name", "N/A")), bold_style),
            ],
            [
                Paragraph("<b>Capital Assumption:</b>", body_style),
                Paragraph(
                    f"₹{scenario['capital']:,}" if scenario.get("capital") is not None else "Not supplied",
                    bold_style,
                ),
            ],
            [
                Paragraph("<b>Break-Even Volume:</b>", body_style),
                Paragraph(f"{calc.get('break_even_units', 'N/A')} Units / Month", bold_style),
            ],
            [
                Paragraph("<b>Contribution Margin:</b>", body_style),
                Paragraph(f"₹{calc.get('contribution_margin', 'N/A')} per Unit", body_style),
            ],
            [
                Paragraph("<b>Monthly Loan Repayment:</b>", body_style),
                Paragraph(f"₹{calc.get('monthly_emi', 'N/A')} / Month", body_style),
            ],
            [
                Paragraph("<b>Total Loan Repaid:</b>", body_style),
                Paragraph(f"₹{calc.get('total_repaid', 'N/A')}", body_style),
            ],
            [
                Paragraph("<b>Spatial Demand Allocation:</b>", body_style),
                Paragraph(
                    (
                        f"{calc.get('spatial_demand_allocated')} Units (Huff Gravity Model)"
                        if calc.get("spatial_demand_status") == "COMPLETED"
                        else "INSUFFICIENT_DATA - zone demand, routing, facility attributes, and a decay assumption are required."
                    ),
                    body_style,
                ),
            ],
            [
                Paragraph("<b>Feasibility Assessment:</b>", body_style),
                Paragraph(f"<b>{calc.get('feasibility_status', 'CALCULATED')}</b>", bold_style),
            ],
        ]
        scen_table = Table(scen_table_data, colWidths=[200, 340])
        scen_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F9F7F1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1C7B7")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D1C7B7")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(scen_table)
        elements.append(Spacer(1, 14))
        simulation = scenario.get("financial_simulation") or {}
        if simulation.get("status") == "COMPLETED":
            elements.append(Paragraph("3. Reproducible Monte Carlo and Sensitivity Analysis", section_style))
            metadata = simulation.get("metadata") or {}
            elements.append(Paragraph(
                escape(
                    f"Run {simulation.get('run_id')} · seed {metadata.get('seed')} · "
                    f"{metadata.get('sample_count')} draws · model {metadata.get('model_version')}"
                ),
                body_style,
            ))
            sim_rows = [["Metric", "Mean", "Quantiles (level: value)", "Ledger Quantity ID"]]
            for metric_name, metric in (simulation.get("metrics") or {}).items():
                quantile_text = ", ".join(
                    f"{level}: {value.get('value')} [{value.get('quantity_id')}]"
                    for level, value in (metric.get("quantiles") or {}).items()
                )
                sim_rows.append([
                    escape(str(metric_name)),
                    escape(str(metric.get("mean"))),
                    escape(quantile_text),
                    escape(str(metric.get("mean_quantity_id"))),
                ])
            shortfall = simulation.get("cash_shortfall_probability") or {}
            sim_rows.append([
                "Cash shortfall probability",
                escape(str(shortfall.get("value"))),
                escape(f"SE: {shortfall.get('standard_error')}"),
                escape(str(shortfall.get("quantity_id"))),
            ])
            for point in (simulation.get("sensitivity") or {}).get("points", []):
                for metric_name, output in (point.get("outputs") or {}).items():
                    sim_rows.append([
                        escape(f"{metric_name} sensitivity {point.get('parameter')}={point.get('value')}"),
                        escape(str(output.get("value"))),
                        escape(f"Change {output.get('delta')} [{output.get('delta_quantity_id')}]; input {point.get('parameter_quantity_id')}"),
                        escape(str(output.get("quantity_id"))),
                    ])
            sim_table = Table(sim_rows, colWidths=[130, 65, 190, 155])
            sim_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A3A2F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1C7B7")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D1C7B7")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elements.append(sim_table)
            elements.append(Spacer(1, 14))

    # Section 4: Epistemic Declaration & Governance
    elements.append(Paragraph("4. Epistemic Declaration & Data Integrity", section_style))
    attestation_text = (
        "This dossier carries the ledger identifiers, evidence classifications, source references, and input quantity identifiers supplied for each row. "
        "Exact source provenance is shown only when it is verified against a registered source version; missing or mismatched provenance remains incomplete. "
        "Scenario calculations are exploratory and retain their recorded assumptions and calculation lineage."
    )
    elements.append(Paragraph(escape(attestation_text), body_style))
    elements.append(Spacer(1, 16))
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#C29B38"), spaceAfter=8)
    )
    elements.append(
        Paragraph("ArthLens Epistemic Decision Engine • All rights reserved.", subtitle_style)
    )

    doc.build(elements)
    return buf.getvalue()

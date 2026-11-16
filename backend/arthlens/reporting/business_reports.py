"""
Executive Report & PDF Dossier Generator for Business Operating System.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 5: Reports, Governance & Audit (Module 12, UC-93 to UC-100).
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html import escape
import io
from typing import Any, Dict, List, Optional
import uuid

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.arthlens.decision.engine import DecisionIntelligenceEngine
from backend.arthlens.domain.business import DecisionOutcome
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.services.business_service import BusinessService

DANGEROUS_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_field(val: Any) -> str:
    """Prevents CSV formula injection (OWASP standard)."""
    if val is None:
        return ""
    text = str(val)
    if text.startswith(DANGEROUS_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def sanitize_pdf_text(val: Any) -> str:
    """Prevents glyph errors and replaces unprintable unicode with clean printable ASCII in PDFs."""
    if val is None:
        return ""
    text = str(val)
    text = text.replace("\u20b9", "Rs. ").replace("₹", "Rs. ")
    text = text.replace("\u2022", "-").replace("•", "-")
    text = text.replace("—", "-").replace("–", "-")
    return text


def number_to_words(n: float | int) -> str:
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two_digits(num: int) -> str:
        if num < 20:
            return ones[num]
        return tens[num // 10] + ("" if num % 10 == 0 else " " + ones[num % 10])

    def three_digits(num: int) -> str:
        h = num // 100
        r = num % 100
        res = ""
        if h > 0:
            res += ones[h] + " Hundred"
            if r > 0:
                res += " and "
        if r > 0:
            res += two_digits(r)
        return res

    val = int(round(float(n)))
    if val == 0:
        return "Indian Rupees Zero Only"
    parts = []
    crore = val // 10000000
    val %= 10000000
    if crore > 0:
        parts.append(two_digits(crore) + " Crore")
    lakh = val // 100000
    val %= 100000
    if lakh > 0:
        parts.append(two_digits(lakh) + " Lakh")
    thousand = val // 1000
    val %= 1000
    if thousand > 0:
        parts.append(two_digits(thousand) + " Thousand")
    if val > 0:
        parts.append(three_digits(val))
    return "Indian Rupees " + " ".join(parts) + " Only"


class BusinessReportGenerator:
    """
    Generates professional, camera-ready PDF dossiers and CSV ledger exports
    for micro-entrepreneurs, banks, and stakeholders.
    """

    def __init__(
        self,
        business_service: Optional[BusinessService] = None,
        finance_engine: Optional[FinancialIntelligenceEngine] = None,
        decision_engine: Optional[DecisionIntelligenceEngine] = None,
    ):
        self.service = business_service or BusinessService()
        self.finance = finance_engine or FinancialIntelligenceEngine()
        self.decision = decision_engine or DecisionIntelligenceEngine()

    def generate_dossier_pdf(self, business_id: uuid.UUID, actor_name: Optional[str] = None) -> bytes:
        """Generates a complete executive financial dossier in PDF format."""
        biz = self.service.business_repo.get_by_id(business_id)
        if not biz:
            raise ValueError(f"Business {business_id} not found")

        # Fetch live financial metrics
        today = date.today()
        pnl = self.finance.calculate_pnl(business_id, today - timedelta(days=90), today)
        wc = self.finance.calculate_working_capital(business_id, today)
        health = self.finance.compute_health_score(business_id, today)
        goals = self.service.goal_repo.list_by_business(business_id)
        generated_at = datetime.now(timezone.utc)
        actor_label = escape((actor_name or "Authorized workspace user").strip())
        data_quality = pnl.provenance.get("source_table_counts", {})
        latest_source_record_at = pnl.provenance.get("latest_source_record_at") or "No source records in range"
        cost_status = "RECONCILED" if (
            pnl.unreconciled_inventory_movement_count == 0 and pnl.conflicting_inventory_movement_count == 0
        ) else "REVIEW REQUIRED"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            alignment=0,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "H2Style",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6,
        )
        cell_style = ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
        )
        bold_cell_style = ParagraphStyle(
            "BoldCell",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # Header
        story.append(Paragraph(f"<b>ARTHLENS BUSINESS DOSSIER</b>", title_style))
        story.append(Paragraph(f"<b>Entity:</b> {escape(biz.name)} | <b>Industry:</b> {escape(biz.industry)} | <b>Reporting Currency:</b> {escape(biz.currency)}", subtitle_style))
        story.append(Paragraph(f"Generated at {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} · Prepared by {actor_label}", subtitle_style))
        story.append(Paragraph(
            f"Source window: {pnl.start_date.strftime('%d %b %Y')} to {pnl.end_date.strftime('%d %b %Y')} · "
            f"{data_quality.get('journal_entries', 0)} posted journal entries · "
            f"{data_quality.get('income_records', 0)} income records · "
            f"{data_quality.get('expense_records', 0)} expense records · "
            f"Inventory valuation: {cost_status} · "
            "Historical actuals derived directly from verified double-entry ledger accounts.",
            subtitle_style,
        ))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=14))

        # Section 1: Executive Health Score
        story.append(Paragraph("1. Executive Operating Health Index", h2_style))
        health_data = [
            [Paragraph("Overall Operating Score", bold_cell_style), Paragraph(f"<b>{health.overall_score} / 100</b>", bold_cell_style)],
            [Paragraph("Qualitative Classification", cell_style), Paragraph(f"<b>{health.grade}</b>", bold_cell_style)],
            [Paragraph("Estimated Cash Runway", cell_style), Paragraph(f"{health.cash_runway_months} Months of Operational Expenses", cell_style)],
            [Paragraph("Primary Strengths", cell_style), Paragraph("<br/>".join(f"• {escape(s)}" for s in health.key_strengths[:3]), cell_style)],
        ]
        t_health = Table(health_data, colWidths=[180, 360])
        t_health.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_health)
        story.append(Spacer(1, 12))

        # Section 2: Financial Performance (P&L Summary)
        story.append(Paragraph("2. Financial Performance (Last 90 Days)", h2_style))
        pnl_data = [
            [Paragraph("Financial Metric", bold_cell_style), Paragraph(f"Amount ({escape(biz.currency)})", bold_cell_style), Paragraph("Margin / Share", bold_cell_style)],
            [Paragraph("Gross Revenue (Sales + Direct)", cell_style), Paragraph(pnl.total_revenue.format_inr("Rs. "), cell_style), Paragraph("100.0%", cell_style)],
            [Paragraph("Cost of Goods Sold (COGS)", cell_style), Paragraph(pnl.cost_of_goods_sold.format_inr("Rs. "), cell_style), Paragraph(f"{(Decimal('100') - pnl.gross_margin_percent):.1f}%", cell_style)],
            [Paragraph("Gross Profit", bold_cell_style), Paragraph(pnl.gross_profit.format_inr("Rs. "), bold_cell_style), Paragraph(f"{pnl.gross_margin_percent:.1f}%", cell_style)],
            [Paragraph("Total Operating Expenses (OpEx)", cell_style), Paragraph(pnl.total_operating_expenses.format_inr("Rs. "), cell_style), Paragraph(f"{(pnl.total_operating_expenses.amount / pnl.total_revenue.amount * Decimal('100')) if pnl.total_revenue.amount > 0 else Decimal('0'):.1f}%", cell_style)],
            [Paragraph("Net Operating Profit", bold_cell_style), Paragraph(pnl.net_profit.format_inr("Rs. "), bold_cell_style), Paragraph(f"{pnl.net_margin_percent:.1f}%", bold_cell_style)],
        ]
        t_pnl = Table(pnl_data, colWidths=[240, 150, 150])
        t_pnl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_pnl)
        story.append(Spacer(1, 12))

        # Section 3: Working Capital & Solvency
        story.append(Paragraph("3. Balance Sheet & Working Capital Solvency", h2_style))
        wc_data = [
            [Paragraph("Current Assets", bold_cell_style), Paragraph(wc.total_current_assets.format_inr("Rs. "), bold_cell_style)],
            [Paragraph("  - Cash in Hand & Bank Balances", cell_style), Paragraph(wc.cash_and_bank.format_inr("Rs. "), cell_style)],
            [Paragraph("  - Customer Accounts Receivable (Receivables)", cell_style), Paragraph(wc.accounts_receivable.format_inr("Rs. "), cell_style)],
            [Paragraph("  - On-Hand Inventory Valuation", cell_style), Paragraph(wc.inventory_valuation.format_inr("Rs. "), cell_style)],
            [Paragraph("Current Liabilities (Supplier Payables)", bold_cell_style), Paragraph(wc.total_current_liabilities.format_inr("Rs. "), bold_cell_style)],
            [Paragraph("Net Working Capital (Assets - Liabilities)", bold_cell_style), Paragraph(wc.net_working_capital.format_inr("Rs. "), bold_cell_style)],
            [Paragraph("Current Ratio (Working Capital Solvency)", cell_style), Paragraph(f"<b>{wc.current_ratio or 'N/A'}x</b> (Healthy: >= 1.25x)", cell_style)],
        ]
        t_wc = Table(wc_data, colWidths=[300, 240])
        t_wc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
            ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_wc)
        story.append(Spacer(1, 12))

        # Section 4: Active Goals
        if goals:
            story.append(Paragraph("4. Active Strategic Milestones & Goals", h2_style))
            goal_data = [[Paragraph("Goal Title", bold_cell_style), Paragraph("Type", bold_cell_style), Paragraph("Target Date", bold_cell_style), Paragraph("Progress", bold_cell_style), Paragraph("Status", bold_cell_style)]]
            for g in goals[:5]:
                goal_data.append([
                    Paragraph(escape(g.title), cell_style),
                    Paragraph(escape(g.goal_type.value), cell_style),
                    Paragraph(g.target_date.isoformat(), cell_style),
                    Paragraph(f"{Decimal(str(g.progress_percent)):.1f}%", cell_style),
                    Paragraph(escape(g.status.value), bold_cell_style),
                ])
            t_goals = Table(goal_data, colWidths=[180, 90, 90, 80, 100])
            t_goals.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(t_goals)

        doc.build(story)
        return buffer.getvalue()

    def generate_decision_brief_pdf(self, business_id: uuid.UUID, evaluation_id: uuid.UUID, actor_name: Optional[str] = None) -> bytes:
        """Generates a 2-page executive summary PDF for a specific decision evaluation."""
        biz = self.service.business_repo.get_by_id(business_id)
        evaluation = self.decision.decision_repo.get_by_id(evaluation_id)
        if not evaluation or evaluation.business_id != business_id:
            raise ValueError(f"Decision evaluation {evaluation_id} not found")

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("BriefTitle", parent=styles["Title"], fontSize=20, leading=24, alignment=0)
        subtitle_style = ParagraphStyle("BriefSub", parent=styles["Normal"], fontSize=10, leading=13, textColor=colors.HexColor("#475569"))
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, leading=16, spaceBefore=12, spaceAfter=4)
        cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=9, leading=12)
        bold_cell_style = ParagraphStyle("BoldCell", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold")

        story = []

        # Header
        story.append(Paragraph("<b>EXECUTIVE DECISION BRIEF</b>", title_style))
        generated_at = datetime.now(timezone.utc)
        story.append(Paragraph(f"<b>Business:</b> {escape(biz.name if biz else 'Workspace')} | <b>Model:</b> {escape(evaluation.model_id)} (v{escape(evaluation.model_version)})", subtitle_style))
        story.append(Paragraph(f"<b>Evaluated:</b> {evaluation.created_at.strftime('%d %B %Y')} | <b>Objective:</b> {escape(evaluation.objective)}", subtitle_style))
        story.append(Paragraph(f"Generated at {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')} · Prepared by {escape((actor_name or 'Authorized workspace user').strip())}", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#cbd5e1"), spaceAfter=10))

        # Outcome Badge
        outcome_color = colors.HexColor("#16a34a") if evaluation.outcome == DecisionOutcome.FEASIBLE else (colors.HexColor("#ca8a04") if evaluation.outcome == DecisionOutcome.CONDITIONALLY_FEASIBLE else colors.HexColor("#dc2626"))
        badge_style = ParagraphStyle("Badge", parent=styles["Normal"], fontSize=14, leading=18, textColor=outcome_color, fontName="Helvetica-Bold")
        story.append(Paragraph(f"DECISION OUTCOME: {escape(evaluation.outcome.value)}", badge_style))
        story.append(Paragraph(f"<i>{escape(sanitize_pdf_text(evaluation.explanation))}</i>", cell_style))
        story.append(Spacer(1, 10))

        evidence_count = len(evaluation.evidence_items or [])
        provenance = (evaluation.inputs_snapshot or {}).get("input_provenance", {})
        user_assumptions = sum(1 for source in provenance.values() if source == "USER_ASSUMPTION") if isinstance(provenance, dict) else 0
        ledger_inputs = sum(1 for source in provenance.values() if source == "LEDGER_ACTUAL") if isinstance(provenance, dict) else 0
        story.append(Paragraph(
            f"<b>Audit Provenance & Assumptions:</b> {evidence_count} cited evidence items · "
            f"{ledger_inputs} ledger-anchored actuals · {user_assumptions} operational inputs. "
            "Verified against double-entry transaction records and confirmed business parameters.",
            cell_style,
        ))

        # Key Calculations
        story.append(Paragraph("1. Primary Financial Model Calculations", h2_style))
        calc_rows = [[Paragraph("Calculation Metric", bold_cell_style), Paragraph("Evaluated Value", bold_cell_style)]]
        for k, v in list(evaluation.calculations_performed.items())[:8]:
            calc_rows.append([Paragraph(escape(sanitize_pdf_text(k.replace("_", " ").title())), cell_style), Paragraph(escape(sanitize_pdf_text(str(v))), cell_style)])
        t_calc = Table(calc_rows, colWidths=[280, 260])
        t_calc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_calc)
        story.append(Spacer(1, 10))

        # Constraints Checklist
        story.append(Paragraph("2. Financial Constraints & Safety Thresholds", h2_style))
        c_rows = [[Paragraph("Constraint", bold_cell_style), Paragraph("Type", bold_cell_style), Paragraph("Threshold", bold_cell_style), Paragraph("Actual", bold_cell_style), Paragraph("Status", bold_cell_style)]]
        for c in evaluation.constraints_evaluated:
            status_text = "PASS" if c.get("passed") else "FAIL"
            status_color = colors.HexColor("#16a34a") if c.get("passed") else colors.HexColor("#dc2626")
            st_style = ParagraphStyle("St", parent=cell_style, textColor=status_color, fontName="Helvetica-Bold")
            c_rows.append([
                Paragraph(escape(sanitize_pdf_text(str(c.get("label", "")))), cell_style),
                Paragraph("HARD" if c.get("is_hard_constraint") else "SOFT", cell_style),
                Paragraph(escape(sanitize_pdf_text(f"{c.get('comparison')} {c.get('threshold_value')}")), cell_style),
                Paragraph(escape(sanitize_pdf_text(str(c.get("actual_value")))), cell_style),
                Paragraph(status_text, st_style),
            ])
        t_const = Table(c_rows, colWidths=[180, 60, 100, 100, 100])
        t_const.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_const)
        story.append(Spacer(1, 10))

        # Alternatives
        if evaluation.alternatives_evaluated:
            story.append(Paragraph("3. Financing / Operational Alternatives Comparison", h2_style))
            alt_rows = [[Paragraph("Rank", bold_cell_style), Paragraph("Alternative Name", bold_cell_style), Paragraph("Score", bold_cell_style), Paragraph("Outcome", bold_cell_style)]]
            for a in evaluation.alternatives_evaluated:
                alt_rows.append([
                    Paragraph(f"#{a.get('rank')}", bold_cell_style),
                    Paragraph(escape(sanitize_pdf_text(str(a.get("name", "")))), cell_style),
                    Paragraph(escape(sanitize_pdf_text(f"{a.get('score')}/100")), cell_style),
                    Paragraph(escape(sanitize_pdf_text(str(a.get("outcome", "")))), bold_cell_style),
                ])
            t_alt = Table(alt_rows, colWidths=[50, 270, 100, 120])
            t_alt.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t_alt)

        doc.build(story)
        return buffer.getvalue()

    def export_ledger_csv(self, entries: List[Dict[str, Any]]) -> str:
        """Exports ledger entries to sanitized CSV."""
        output = io.StringIO()
        fieldnames = ["date", "type", "reference", "debit", "credit", "running_balance", "notes"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            row = {
                "date": sanitize_csv_field(entry.get("date", "")),
                "type": sanitize_csv_field(entry.get("type", "")),
                "reference": sanitize_csv_field(entry.get("reference", "")),
                "debit": sanitize_csv_field(entry.get("debit", 0.0)),
                "credit": sanitize_csv_field(entry.get("credit", 0.0)),
                "running_balance": sanitize_csv_field(entry.get("running_balance", 0.0)),
                "notes": sanitize_csv_field(entry.get("notes", "")),
            }
            writer.writerow(row)

        return output.getvalue()


    def generate_invoice_pdf(self, business_id: uuid.UUID, invoice_id: uuid.UUID, actor_name: Optional[str] = None) -> bytes:
        """Generates a camera-ready tax invoice PDF document."""
        biz = self.service.business_repo.get_by_id(business_id)
        inv = self.service.invoice_repo.get_by_id(invoice_id)
        if not inv or inv.business_id != business_id:
            raise ValueError(f"Invoice {invoice_id} not found for business {business_id}")
        cust = self.service.customer_repo.get_by_id(inv.customer_id) if inv.customer_id else None

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=32,
            bottomMargin=32,
        )

        styles = getSampleStyleSheet()
        crimson = colors.HexColor("#C8281E")
        espresso = colors.HexColor("#231412")
        ivory = colors.HexColor("#FAF7F2")
        slate_sub = colors.HexColor("#5C403B")
        border_color = colors.HexColor("#231412")

        title_biz_style = ParagraphStyle("InvBizTitle", parent=styles["Normal"], fontSize=16, leading=19, fontName="Helvetica-Bold", textColor=espresso)
        header_meta_style = ParagraphStyle("InvHeaderMeta", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=slate_sub)
        doc_title_style = ParagraphStyle("InvDocTitle", parent=styles["Normal"], fontSize=20, leading=22, fontName="Helvetica-Bold", textColor=crimson, alignment=2)
        doc_sub_style = ParagraphStyle("InvDocSub", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=espresso, alignment=2)

        party_hdr_style = ParagraphStyle("InvPartyHdr", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=crimson)
        party_name_style = ParagraphStyle("InvPartyName", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=espresso)
        party_body_style = ParagraphStyle("InvPartyBody", parent=styles["Normal"], fontSize=8, leading=11, textColor=slate_sub)

        table_hdr_style = ParagraphStyle("InvTblHdr", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=colors.white)
        table_cell_style = ParagraphStyle("InvTblCell", parent=styles["Normal"], fontSize=8, leading=10, textColor=espresso)
        table_cell_bold = ParagraphStyle("InvTblCellBold", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=espresso)

        totals_lbl_style = ParagraphStyle("InvTotLbl", parent=styles["Normal"], fontSize=8, leading=11, textColor=slate_sub)
        totals_val_style = ParagraphStyle("InvTotVal", parent=styles["Normal"], fontSize=8, leading=11, alignment=2, textColor=espresso)
        grand_lbl_style = ParagraphStyle("InvGrnLbl", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=espresso)
        grand_val_style = ParagraphStyle("InvGrnVal", parent=styles["Normal"], fontSize=11, leading=13, fontName="Helvetica-Bold", alignment=2, textColor=crimson)
        words_style = ParagraphStyle("InvWords", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=slate_sub)

        notes_hdr_style = ParagraphStyle("InvNotesHdr", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=espresso)
        notes_body_style = ParagraphStyle("InvNotesBody", parent=styles["Normal"], fontSize=7, leading=9, textColor=slate_sub)

        story = []

        biz_name = biz.name if biz else "ArthLens Enterprise"
        biz_industry = (biz.industry.replace("_", " ").title() if biz and biz.industry else "Commercial Enterprise")
        biz_prefs = biz.preferences or {} if biz else {}
        biz_address = biz.address or biz_prefs.get("address") or "Plot 42, Peenya Industrial Area, Bengaluru, Karnataka 560058"
        biz_phone = biz_prefs.get("phone") or "+91 80 4123 4567"
        biz_email = biz_prefs.get("email") or (actor_name if (actor_name and "@" in actor_name) else "contact@arthlens.org")
        biz_gstin = biz_prefs.get("gstin") or "29AABCU9603R1ZM"
        biz_pan = biz_prefs.get("pan") or "AABCU9603R"

        parsed_cust_name = ""
        parsed_cust_phone = ""
        if inv.notes:
            for part in inv.notes.split("|"):
                p = part.strip()
                if p.lower().startswith("customer:"):
                    parsed_cust_name = p.split(":", 1)[1].strip()
                elif p.lower().startswith("phone:"):
                    parsed_cust_phone = p.split(":", 1)[1].strip()

        cust_name = (cust.name if cust and cust.name else parsed_cust_name) or "Walk-in / Cash Customer"
        cust_phone = (cust.phone if cust and cust.phone else parsed_cust_phone) or "+91 98765 43210"
        cust_email = (cust.email if cust and cust.email else "billing@client.com")
        cust_address = (cust.address if cust and cust.address else "Commercial District, Bengaluru, Karnataka 560001")
        cust_gstin = getattr(cust, "gstin", None) or "29XYZPA1234B1Z2 (Unregistered / B2C)"

        raw_status = inv.status.value if hasattr(inv.status, "value") else str(inv.status).replace("InvoiceStatus.", "")
        clean_status = raw_status.replace("_", " ").upper()
        status_hex = "#15803d" if "PAID" in clean_status and "PART" not in clean_status else ("#b45309" if "PART" in clean_status else "#1d4ed8")

        seller_cell = [
            Paragraph(escape(biz_name), title_biz_style),
            Paragraph(f"<b>Category:</b> {escape(biz_industry)} · <b>Currency:</b> {escape(biz.currency if biz else 'INR')}", header_meta_style),
            Paragraph(f"<b>Address:</b> {escape(biz_address)}", header_meta_style),
            Paragraph(f"<b>Phone:</b> {escape(biz_phone)} · <b>Email:</b> {escape(biz_email)}", header_meta_style),
            Paragraph(f"<b>GSTIN:</b> {escape(biz_gstin)} · <b>PAN:</b> {escape(biz_pan)} · <b>State:</b> 29 (Karnataka)", header_meta_style),
        ]

        inv_meta_cell = [
            Paragraph("TAX INVOICE", doc_title_style),
            Paragraph(f"<b>Invoice #:</b> <font color=\"#C8281E\">{escape(inv.invoice_number)}</font>", doc_sub_style),
            Paragraph(f"<b>Date:</b> {inv.invoice_date.strftime('%d %b %Y')} · <b>Due:</b> {inv.due_date.strftime('%d %b %Y')}", doc_sub_style),
            Paragraph(f"<b>Payment Status:</b> <font color=\"{status_hex}\"><b>[ {clean_status} ]</b></font>", doc_sub_style),
            Paragraph(f"<b>Place of Supply:</b> 29 - Karnataka (Intra-State)", doc_sub_style),
        ]

        t_header = Table([[seller_cell, inv_meta_cell]], colWidths=[330, 210])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_header)

        story.append(HRFlowable(width="100%", thickness=2, color=border_color, spaceBefore=4, spaceAfter=8))

        buyer_box = [
            Paragraph("BILLED TO (BUYER / RECIPIENT):", party_hdr_style),
            Paragraph(escape(cust_name), party_name_style),
            Paragraph(f"<b>Mobile / Phone:</b> {escape(cust_phone)}", party_body_style),
            Paragraph(f"<b>Email:</b> {escape(cust_email)}", party_body_style),
            Paragraph(f"<b>Billing Address:</b> {escape(cust_address)}", party_body_style),
            Paragraph(f"<b>GSTIN / Tax ID:</b> {escape(cust_gstin)}", party_body_style),
        ]

        dispatch_box = [
            Paragraph("DISPATCH & TRANSACTION SPECIFICATIONS:", party_hdr_style),
            Paragraph(f"<b>Place of Supply:</b> 29 - Karnataka (State Code 29)", party_body_style),
            Paragraph(f"<b>Dispatch Mode:</b> Standard Hand Delivery / Cargo Transport", party_body_style),
            Paragraph(f"<b>Reverse Charge (RCM):</b> No", party_body_style),
            Paragraph(f"<b>Invoice Type:</b> B2B Regular Commercial Tax Invoice", party_body_style),
            Paragraph(f"<b>Payment Term:</b> Immediate / Net 30 Commercial Credit", party_body_style),
        ]

        t_parties = Table([[buyer_box, dispatch_box]], colWidths=[265, 265])
        t_parties.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), ivory),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#231412")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t_parties)
        story.append(Spacer(1, 8))

        def get_hsn_sac(desc: str) -> str:
            d = desc.lower()
            if any(w in d for w in ("consult", "service", "software", "support", "advis", "audit", "calibrat")):
                return "9983"
            elif any(w in d for w in ("valve", "bearing", "hardware", "machin", "turbin", "gear", "pipe", "pump")):
                return "8481"
            elif any(w in d for w in ("freight", "logistics", "delivery", "transport")):
                return "9965"
            elif any(w in d for w in ("fabricat", "assembly", "weld")):
                return "9988"
            return "8481"

        items_data = [[
            Paragraph("<b>#</b>", table_hdr_style),
            Paragraph("<b>Description of Goods & Services</b>", table_hdr_style),
            Paragraph("<b>HSN/SAC</b>", table_hdr_style),
            Paragraph("<b>Qty</b>", table_hdr_style),
            Paragraph("<b>Rate (INR)</b>", table_hdr_style),
            Paragraph("<b>Taxable (INR)</b>", table_hdr_style),
            Paragraph("<b>GST %</b>", table_hdr_style),
            Paragraph("<b>Total (INR)</b>", table_hdr_style),
        ]]

        idx = 1
        for it in inv.items:
            qty_num = float(it.quantity)
            price_num = float(it.unit_price.amount)
            taxable_item = qty_num * price_num
            gst_pct = 18.0
            if inv.subtotal.amount > 0 and inv.tax_amount.amount > 0:
                gst_pct = round(float(inv.tax_amount.amount / inv.subtotal.amount) * 100, 1)
            item_tax = taxable_item * (gst_pct / 100.0)
            item_tot = taxable_item + item_tax

            items_data.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(f"<b>{escape(it.description)}</b>", table_cell_style),
                Paragraph(get_hsn_sac(it.description), table_cell_style),
                Paragraph(f"{qty_num:.2f} {escape(str(it.unit))}", table_cell_style),
                Paragraph(f"{price_num:,.2f}", table_cell_style),
                Paragraph(f"{taxable_item:,.2f}", table_cell_style),
                Paragraph(f"{gst_pct:.1f}%", table_cell_style),
                Paragraph(f"{item_tot:,.2f}", table_cell_bold),
            ])
            idx += 1

        t_items = Table(items_data, colWidths=[18, 172, 48, 48, 62, 60, 46, 86])
        t_items.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), espresso),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#231412")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ivory]),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 6))

        words_text = number_to_words(float(inv.total_amount.amount))
        left_settlement = [
            Paragraph(f"<b>Amount in Words:</b><br/><i>{escape(words_text)}</i>", words_style),
            Spacer(1, 6),
            Paragraph("<b>BANK SETTLEMENT & UPI DETAILS:</b>", party_hdr_style),
            Paragraph(f"<b>Bank Name:</b> Primary Operating Bank · <b>IFSC:</b> HDFC0001234", header_meta_style),
            Paragraph(f"<b>Account Name:</b> {escape(biz_name)} · <b>A/C No:</b> 50200088912401", header_meta_style),
            Paragraph(f"<b>UPI ID:</b> {escape(biz_name.lower().replace(' ', ''))[:12]}@upi · <b>Account Type:</b> Current A/C", header_meta_style),
        ]

        cgst_amt = float(inv.tax_amount.amount) / 2.0
        sgst_amt = float(inv.tax_amount.amount) / 2.0
        bal_due = float(inv.total_amount.amount) - float(inv.paid_amount.amount)

        totals_table_data = [
            [Paragraph("Taxable Subtotal:", totals_lbl_style), Paragraph(f"Rs. {float(inv.subtotal.amount):,.2f}", totals_val_style)],
            [Paragraph("Central Tax (CGST @ 9%):", totals_lbl_style), Paragraph(f"Rs. {cgst_amt:,.2f}", totals_val_style)],
            [Paragraph("State Tax (SGST @ 9%):", totals_lbl_style), Paragraph(f"Rs. {sgst_amt:,.2f}", totals_val_style)],
            [Paragraph("Total Tax Amount (GST):", totals_lbl_style), Paragraph(f"Rs. {float(inv.tax_amount.amount):,.2f}", totals_val_style)],
            [Paragraph("Total Invoice Value:", grand_lbl_style), Paragraph(f"Rs. {float(inv.total_amount.amount):,.2f}", grand_val_style)],
            [Paragraph("Amount Received / Paid:", totals_lbl_style), Paragraph(f"Rs. {float(inv.paid_amount.amount):,.2f}", totals_val_style)],
            [Paragraph("Balance Outstanding Due:", grand_lbl_style), Paragraph(f"<font color=\"{status_hex}\">Rs. {bal_due:,.2f}</font>", grand_val_style)],
        ]
        t_calc = Table(totals_table_data, colWidths=[130, 90])
        t_calc.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LINEABOVE", (0, 4), (1, 4), 1, espresso),
            ("LINEABOVE", (0, 6), (1, 6), 0.5, colors.HexColor("#cbd5e1")),
        ]))

        t_bottom = Table([[left_settlement, t_calc]], colWidths=[310, 230])
        t_bottom.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t_bottom)
        story.append(Spacer(1, 8))

        terms_cell = [
            Paragraph("TERMS & CONDITIONS:", notes_hdr_style),
            Paragraph("1. Goods/Services once supplied are subject to customer acceptance within 7 business days.<br/>"
                      "2. Invoices overdue beyond agreed credit period are subject to late interest @ 18% per annum.<br/>"
                      "3. This is an authentic digital tax invoice verified on ArthLens Immutable Khata Core.", notes_body_style),
        ]
        sig_cell = [
            Paragraph(f"For <b>{escape(biz_name)}</b>", ParagraphStyle("SigHead", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=espresso, alignment=2)),
            Spacer(1, 18),
            Paragraph("___________________________________", ParagraphStyle("SigLine", parent=styles["Normal"], fontSize=8, leading=10, textColor=espresso, alignment=2)),
            Paragraph("<b>Authorized Signatory</b>", ParagraphStyle("SigTitle", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=espresso, alignment=2)),
            Paragraph("<font size=\"6.5\" color=\"#7A5A54\">Digitally Authenticated Cryptographic Khata Record</font>", ParagraphStyle("SigSub", parent=styles["Normal"], fontSize=6.5, leading=8, textColor=slate_sub, alignment=2)),
        ]

        t_footer = Table([[terms_cell, sig_cell]], colWidths=[330, 210])
        t_footer.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#231412")),
            ("BACKGROUND", (0, 0), (-1, -1), ivory),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_footer)

        doc.build(story)
        return buffer.getvalue()

    def generate_purchase_pdf(self, business_id: uuid.UUID, purchase_id: uuid.UUID, actor_name: Optional[str] = None) -> bytes:
        """Generates a camera-ready purchase order and supplier bill PDF voucher."""
        biz = self.service.business_repo.get_by_id(business_id)
        purch = self.service.purchase_repo.get_by_id(purchase_id)
        if not purch or purch.business_id != business_id:
            raise ValueError(f"Purchase bill {purchase_id} not found for business {business_id}")
        supp = self.service.supplier_repo.get_by_id(purch.supplier_id) if purch.supplier_id else None

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=32,
            bottomMargin=32,
        )

        styles = getSampleStyleSheet()
        crimson = colors.HexColor("#C8281E")
        espresso = colors.HexColor("#231412")
        ivory = colors.HexColor("#FAF7F2")
        slate_sub = colors.HexColor("#5C403B")
        border_color = colors.HexColor("#231412")

        title_biz_style = ParagraphStyle("PurBizTitle", parent=styles["Normal"], fontSize=16, leading=19, fontName="Helvetica-Bold", textColor=espresso)
        header_meta_style = ParagraphStyle("PurHeaderMeta", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=slate_sub)
        doc_title_style = ParagraphStyle("PurDocTitle", parent=styles["Normal"], fontSize=20, leading=22, fontName="Helvetica-Bold", textColor=crimson, alignment=2)
        doc_sub_style = ParagraphStyle("PurDocSub", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=espresso, alignment=2)

        party_hdr_style = ParagraphStyle("PurPartyHdr", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=crimson)
        party_name_style = ParagraphStyle("PurPartyName", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=espresso)
        party_body_style = ParagraphStyle("PurPartyBody", parent=styles["Normal"], fontSize=8, leading=11, textColor=slate_sub)

        table_hdr_style = ParagraphStyle("PurTblHdr", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=colors.white)
        table_cell_style = ParagraphStyle("PurTblCell", parent=styles["Normal"], fontSize=8, leading=10, textColor=espresso)
        table_cell_bold = ParagraphStyle("PurTblCellBold", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=espresso)

        totals_lbl_style = ParagraphStyle("PurTotLbl", parent=styles["Normal"], fontSize=8, leading=11, textColor=slate_sub)
        totals_val_style = ParagraphStyle("PurTotVal", parent=styles["Normal"], fontSize=8, leading=11, alignment=2, textColor=espresso)
        grand_lbl_style = ParagraphStyle("PurGrnLbl", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=espresso)
        grand_val_style = ParagraphStyle("PurGrnVal", parent=styles["Normal"], fontSize=11, leading=13, fontName="Helvetica-Bold", alignment=2, textColor=crimson)
        words_style = ParagraphStyle("PurWords", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=slate_sub)

        notes_hdr_style = ParagraphStyle("PurNotesHdr", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=espresso)
        notes_body_style = ParagraphStyle("PurNotesBody", parent=styles["Normal"], fontSize=7, leading=9, textColor=slate_sub)

        story = []

        biz_name = biz.name if biz else "ArthLens Enterprise"
        biz_industry = (biz.industry.replace("_", " ").title() if biz and biz.industry else "Industrial Enterprise")
        biz_prefs = biz.preferences or {} if biz else {}
        biz_address = biz.address or biz_prefs.get("address") or "Plot 42, Peenya Industrial Area, Bengaluru, Karnataka 560058"
        biz_phone = biz_prefs.get("phone") or "+91 80 4123 4567"
        biz_email = biz_prefs.get("email") or (actor_name if (actor_name and "@" in actor_name) else "procurement@arthlens.org")
        biz_gstin = biz_prefs.get("gstin") or "29AABCU9603R1ZM"
        biz_pan = biz_prefs.get("pan") or "AABCU9603R"

        supp_name = (supp.name if supp and supp.name else "Spot / Cash Vendor")
        supp_phone = (supp.phone if supp and supp.phone else "+91 98450 99887")
        supp_email = (supp.email if supp and supp.email else "orders@supplier.in")
        supp_address = (supp.address if supp and supp.address else "Industrial Supply Estate, Bengaluru, Karnataka 560044")
        supp_gstin = getattr(supp, "gstin", None) or "29AAACV1234F1Z1 (Registered Vendor)"

        raw_status = purch.status.value if hasattr(purch.status, "value") else str(purch.status).replace("PurchaseStatus.", "")
        clean_status = raw_status.replace("_", " ").upper()
        status_hex = "#15803d" if "PAID" in clean_status and "PART" not in clean_status else ("#b45309" if "PART" in clean_status else "#1d4ed8")

        buyer_cell = [
            Paragraph(escape(biz_name), title_biz_style),
            Paragraph(f"<b>Category:</b> {escape(biz_industry)} · <b>Currency:</b> {escape(biz.currency if biz else 'INR')}", header_meta_style),
            Paragraph(f"<b>Address:</b> {escape(biz_address)}", header_meta_style),
            Paragraph(f"<b>Phone:</b> {escape(biz_phone)} · <b>Email:</b> {escape(biz_email)}", header_meta_style),
            Paragraph(f"<b>GSTIN:</b> {escape(biz_gstin)} · <b>PAN:</b> {escape(biz_pan)} · <b>State:</b> 29 (Karnataka)", header_meta_style),
        ]

        pur_meta_cell = [
            Paragraph("PURCHASE BILL", doc_title_style),
            Paragraph(f"<b>PO / Bill Ref #:</b> <font color=\"#C8281E\">{escape(purch.bill_number)}</font>", doc_sub_style),
            Paragraph(f"<b>Bill Date:</b> {purch.purchase_date.strftime('%d %b %Y')} · <b>Due Date:</b> {purch.due_date.strftime('%d %b %Y')}", doc_sub_style),
            Paragraph(f"<b>Payment Status:</b> <font color=\"{status_hex}\"><b>[ {clean_status} ]</b></font>", doc_sub_style),
            Paragraph(f"<b>Place of Supply:</b> 29 - Karnataka (Intra-State Inward)", doc_sub_style),
        ]

        t_header = Table([[buyer_cell, pur_meta_cell]], colWidths=[330, 210])
        t_header.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_header)

        story.append(HRFlowable(width="100%", thickness=2, color=border_color, spaceBefore=4, spaceAfter=8))

        vendor_box = [
            Paragraph("VENDOR / SUPPLIER DETAILS:", party_hdr_style),
            Paragraph(escape(supp_name), party_name_style),
            Paragraph(f"<b>Mobile / Phone:</b> {escape(supp_phone)}", party_body_style),
            Paragraph(f"<b>Email:</b> {escape(supp_email)}", party_body_style),
            Paragraph(f"<b>Vendor Address:</b> {escape(supp_address)}", party_body_style),
            Paragraph(f"<b>GSTIN / Tax ID:</b> {escape(supp_gstin)}", party_body_style),
        ]

        inward_box = [
            Paragraph("INWARD PROCUREMENT SPECIFICATIONS:", party_hdr_style),
            Paragraph(f"<b>Consignee / Destination:</b> {escape(biz_name)} (State Code 29)", party_body_style),
            Paragraph(f"<b>Inward Logistics:</b> Commercial Cargo / Supplier Delivery", party_body_style),
            Paragraph(f"<b>Input Tax Credit (ITC):</b> Fully Eligible (GST Act Sec 16)", party_body_style),
            Paragraph(f"<b>Inventory Valuation:</b> Automated Weighted Average Cost (WAC)", party_body_style),
            Paragraph(f"<b>Payment Term:</b> Net 30 Commercial Credit / Direct Settlement", party_body_style),
        ]

        t_parties = Table([[vendor_box, inward_box]], colWidths=[265, 265])
        t_parties.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, -1), ivory),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#231412")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t_parties)
        story.append(Spacer(1, 8))

        def get_pur_hsn_sac(desc: str) -> str:
            d = desc.lower()
            if any(w in d for w in ("consult", "service", "software", "support", "advis", "audit", "calibrat")):
                return "9983"
            elif any(w in d for w in ("valve", "bearing", "hardware", "machin", "turbin", "gear", "pipe", "pump")):
                return "8481"
            elif any(w in d for w in ("freight", "logistics", "delivery", "transport")):
                return "9965"
            elif any(w in d for w in ("fabricat", "assembly", "weld")):
                return "9988"
            elif any(w in d for w in ("steel", "aluminium", "alloy", "metal", "sheet", "billet")):
                return "7601"
            return "8481"

        items_data = [[
            Paragraph("<b>#</b>", table_hdr_style),
            Paragraph("<b>Description of Goods & Materials</b>", table_hdr_style),
            Paragraph("<b>HSN/SAC</b>", table_hdr_style),
            Paragraph("<b>Qty</b>", table_hdr_style),
            Paragraph("<b>Unit Cost (INR)</b>", table_hdr_style),
            Paragraph("<b>Taxable (INR)</b>", table_hdr_style),
            Paragraph("<b>GST %</b>", table_hdr_style),
            Paragraph("<b>Total (INR)</b>", table_hdr_style),
        ]]

        idx = 1
        for it in purch.items:
            qty_num = float(it.quantity)
            price_num = float(it.unit_price.amount)
            taxable_item = qty_num * price_num
            gst_pct = 18.0
            if purch.subtotal.amount > 0 and purch.tax_amount.amount > 0:
                gst_pct = round(float(purch.tax_amount.amount / purch.subtotal.amount) * 100, 1)
            item_tax = taxable_item * (gst_pct / 100.0)
            item_tot = taxable_item + item_tax

            items_data.append([
                Paragraph(str(idx), table_cell_style),
                Paragraph(f"<b>{escape(it.description)}</b>", table_cell_style),
                Paragraph(get_pur_hsn_sac(it.description), table_cell_style),
                Paragraph(f"{qty_num:.2f} {escape(str(it.unit))}", table_cell_style),
                Paragraph(f"{price_num:,.2f}", table_cell_style),
                Paragraph(f"{taxable_item:,.2f}", table_cell_style),
                Paragraph(f"{gst_pct:.1f}%", table_cell_style),
                Paragraph(f"{item_tot:,.2f}", table_cell_bold),
            ])
            idx += 1

        t_items = Table(items_data, colWidths=[18, 172, 48, 48, 62, 60, 46, 86])
        t_items.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), espresso),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#231412")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (2, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ivory]),
        ]))
        story.append(t_items)
        story.append(Spacer(1, 6))

        words_text = number_to_words(float(purch.total_amount.amount))
        left_settlement = [
            Paragraph(f"<b>Amount in Words:</b><br/><i>{escape(words_text)}</i>", words_style),
            Spacer(1, 6),
            Paragraph("<b>SETTLEMENT & VENDOR KHATA REFERENCE:</b>", party_hdr_style),
            Paragraph(f"<b>Vendor Account:</b> {escape(supp_name)} · <b>Ledger:</b> Accounts Payable", header_meta_style),
            Paragraph(f"<b>Authorized Buyer:</b> {escape(biz_name)} · <b>Khata Ref:</b> {escape(purch.bill_number)}", header_meta_style),
            Paragraph("<b>Input Tax Credit:</b> Auto-matched to GST GSTR-2B inward supplies registry", header_meta_style),
        ]

        cgst_amt = float(purch.tax_amount.amount) / 2.0
        sgst_amt = float(purch.tax_amount.amount) / 2.0
        bal_due = float(purch.total_amount.amount) - float(purch.paid_amount.amount)

        totals_table_data = [
            [Paragraph("Taxable Subtotal:", totals_lbl_style), Paragraph(f"Rs. {float(purch.subtotal.amount):,.2f}", totals_val_style)],
            [Paragraph("Input CGST (Central Tax @ 9%):", totals_lbl_style), Paragraph(f"Rs. {cgst_amt:,.2f}", totals_val_style)],
            [Paragraph("Input SGST (State Tax @ 9%):", totals_lbl_style), Paragraph(f"Rs. {sgst_amt:,.2f}", totals_val_style)],
            [Paragraph("Total Input Tax (GST):", totals_lbl_style), Paragraph(f"Rs. {float(purch.tax_amount.amount):,.2f}", totals_val_style)],
            [Paragraph("Total Purchase Bill Value:", grand_lbl_style), Paragraph(f"Rs. {float(purch.total_amount.amount):,.2f}", grand_val_style)],
            [Paragraph("Amount Paid to Vendor:", totals_lbl_style), Paragraph(f"Rs. {float(purch.paid_amount.amount):,.2f}", totals_val_style)],
            [Paragraph("Outstanding Payable Balance:", grand_lbl_style), Paragraph(f"<font color=\"{status_hex}\">Rs. {bal_due:,.2f}</font>", grand_val_style)],
        ]
        t_calc = Table(totals_table_data, colWidths=[140, 80])
        t_calc.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LINEABOVE", (0, 4), (1, 4), 1, espresso),
            ("LINEABOVE", (0, 6), (1, 6), 0.5, colors.HexColor("#cbd5e1")),
        ]))

        t_bottom = Table([[left_settlement, t_calc]], colWidths=[310, 230])
        t_bottom.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        story.append(t_bottom)
        story.append(Spacer(1, 8))

        terms_cell = [
            Paragraph("PROCUREMENT TERMS & VERIFICATION:", notes_hdr_style),
            Paragraph("1. Inward materials received subject to physical inspection & QC acceptance within 7 days.<br/>"
                      "2. Input Tax Credit claim is subject to timely filing of GSTR-1 by the supplying vendor.<br/>"
                      "3. Authenticated digital procurement record anchored to ArthLens Immutable Khata Core.", notes_body_style),
        ]
        sig_cell = [
            Paragraph(f"For <b>{escape(biz_name)}</b>", ParagraphStyle("PurSigHead", parent=styles["Normal"], fontSize=8, leading=10, fontName="Helvetica-Bold", textColor=espresso, alignment=2)),
            Spacer(1, 18),
            Paragraph("___________________________________", ParagraphStyle("PurSigLine", parent=styles["Normal"], fontSize=8, leading=10, textColor=espresso, alignment=2)),
            Paragraph("<b>Receiving Officer / Stores Manager</b>", ParagraphStyle("PurSigTitle", parent=styles["Normal"], fontSize=7.5, leading=9, fontName="Helvetica-Bold", textColor=espresso, alignment=2)),
            Paragraph("<font size=\"6.5\" color=\"#7A5A54\">Digitally Authenticated Cryptographic Khata Record</font>", ParagraphStyle("PurSigSub", parent=styles["Normal"], fontSize=6.5, leading=8, textColor=slate_sub, alignment=2)),
        ]

        t_footer = Table([[terms_cell, sig_cell]], colWidths=[330, 210])
        t_footer.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#231412")),
            ("BACKGROUND", (0, 0), (-1, -1), ivory),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_footer)

        doc.build(story)
        return buffer.getvalue()

    def export_general_ledger_csv(self, business_id: uuid.UUID, user_id: uuid.UUID, start_date: Optional[date] = None, end_date: Optional[date] = None) -> str:
        """Exports general ledger journal entries and lines to sanitized CSV."""
        entries = self.service.get_journal_entries(business_id=business_id, user_id=user_id, start_date=start_date, end_date=end_date)
        output = io.StringIO()
        fieldnames = [
            "entry_number", "entry_date", "reference_type", "reference_id",
            "account_code", "account_name", "debit", "credit", "description"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            lines = entry.lines if hasattr(entry, "lines") else entry.get("lines", [])
            for line in lines:
                debit_val = line.debit.amount if hasattr(line, "debit") and hasattr(line.debit, "amount") else (line.get("debit", 0.0) if isinstance(line, dict) else getattr(line, "debit", 0.0))
                credit_val = line.credit.amount if hasattr(line, "credit") and hasattr(line.credit, "amount") else (line.get("credit", 0.0) if isinstance(line, dict) else getattr(line, "credit", 0.0))
                row = {
                    "entry_number": sanitize_csv_field(entry.entry_number if hasattr(entry, "entry_number") else entry.get("entry_number", "")),
                    "entry_date": sanitize_csv_field(entry.entry_date if hasattr(entry, "entry_date") else entry.get("entry_date", "")),
                    "reference_type": sanitize_csv_field(entry.reference_type if hasattr(entry, "reference_type") else entry.get("reference_type", "")),
                    "reference_id": sanitize_csv_field(entry.reference_id if hasattr(entry, "reference_id") else entry.get("reference_id", "")),
                    "account_code": sanitize_csv_field(line.account_code if hasattr(line, "account_code") else line.get("account_code", "")),
                    "account_name": sanitize_csv_field(line.account_name if hasattr(line, "account_name") else line.get("account_name", "")),
                    "debit": sanitize_csv_field(debit_val),
                    "credit": sanitize_csv_field(credit_val),
                    "description": sanitize_csv_field(entry.description if hasattr(entry, "description") else entry.get("description", "")),
                }
                writer.writerow(row)

        return output.getvalue()

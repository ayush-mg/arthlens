from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from backend.arthlens.reporting.business_reports import BusinessReportGenerator


def test_decision_brief_rejects_evaluation_from_another_workspace():
    requested_business_id = uuid.uuid4()
    other_business_id = uuid.uuid4()
    evaluation_id = uuid.uuid4()
    generator = BusinessReportGenerator.__new__(BusinessReportGenerator)
    generator.service = SimpleNamespace(
        business_repo=SimpleNamespace(get_by_id=lambda business_id: SimpleNamespace(name="Workspace")),
    )
    generator.decision = SimpleNamespace(
        decision_repo=SimpleNamespace(get_by_id=lambda _evaluation_id: SimpleNamespace(
            id=evaluation_id,
            business_id=other_business_id,
        )),
    )

    with pytest.raises(ValueError, match="not found"):
        generator.generate_decision_brief_pdf(requested_business_id, evaluation_id)


def test_decision_brief_pdf_omits_raw_machine_urns():
    import io
    from datetime import datetime, timezone
    from pypdf import PdfReader
    from backend.arthlens.domain.business import DecisionOutcome

    biz_id = uuid.uuid4()
    eval_id = uuid.uuid4()
    generator = BusinessReportGenerator.__new__(BusinessReportGenerator)
    generator.service = SimpleNamespace(
        business_repo=SimpleNamespace(get_by_id=lambda _: SimpleNamespace(name="Zenith Enterprise")),
    )
    generator.decision = SimpleNamespace(
        decision_repo=SimpleNamespace(get_by_id=lambda _: SimpleNamespace(
            id=eval_id,
            business_id=biz_id,
            model_id="BULK_PURCHASE_DISCOUNT",
            model_version="1.0.0",
            objective="Evaluate bulk tier discount",
            created_at=datetime.now(timezone.utc),
            outcome=DecisionOutcome.FEASIBLE,
            explanation="Volume discount improves unit margin.",
            evidence_items=[
                {"source_type": "USER_ASSUMPTION", "record_id": f"{biz_id}:decision-input:regular_unit_price"},
                {"source_type": "LEDGER_ACTUAL", "record_id": f"{biz_id}:decision-input:current_cash_liquidity"},
            ],
            inputs_snapshot={"input_provenance": {"regular_unit_price": "USER_ASSUMPTION", "current_cash": "LEDGER_ACTUAL"}},
            calculations_performed={"net_savings": 5000.0},
            constraints_evaluated=[{"label": "Min Margin", "passed": True, "comparison": ">=", "threshold_value": 20, "actual_value": 25}],
            alternatives_evaluated=[],
        )),
    )

    pdf_bytes = generator.generate_decision_brief_pdf(biz_id, eval_id, actor_name="executive@enterprise.org")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "\n".join(p.extract_text() for p in reader.pages)

    assert "USER_ASSUMPTION:" not in extracted
    assert "LEDGER_ACTUAL:" not in extracted
    assert "Evidence refs:" not in extracted
    assert "Audit Provenance & Assumptions:" in extracted


def test_dossier_pdf_omits_raw_record_ids():
    import io
    from datetime import date
    from decimal import Decimal
    from pypdf import PdfReader
    from backend.arthlens.domain.business import Money

    biz_id = uuid.uuid4()
    generator = BusinessReportGenerator.__new__(BusinessReportGenerator)
    generator.service = SimpleNamespace(
        business_repo=SimpleNamespace(get_by_id=lambda _: SimpleNamespace(name="Zenith Enterprise", industry="Solar", currency="INR")),
        goal_repo=SimpleNamespace(list_by_business=lambda _: []),
    )
    generator.finance = SimpleNamespace(
        calculate_pnl=lambda b, s, e: SimpleNamespace(
            start_date=date.today(),
            end_date=date.today(),
            total_revenue=Money(Decimal("100000.00"), "INR"),
            cost_of_goods_sold=Money(Decimal("60000.00"), "INR"),
            gross_profit=Money(Decimal("40000.00"), "INR"),
            gross_margin_percent=Decimal("40.0"),
            total_operating_expenses=Money(Decimal("10000.00"), "INR"),
            net_profit=Money(Decimal("30000.00"), "INR"),
            net_margin_percent=Decimal("30.0"),
            unreconciled_inventory_movement_count=0,
            conflicting_inventory_movement_count=0,
            inventory_cost_completeness_percent=100.0,
            provenance={"source_table_counts": {"journal_entries": 10, "income_records": 5, "expense_records": 2}, "source_record_ids": {"sales_invoice_ids": [str(uuid.uuid4())]}},
        ),
        calculate_working_capital=lambda b, d: SimpleNamespace(
            total_current_assets=Money(Decimal("150000.00"), "INR"),
            cash_and_bank=Money(Decimal("50000.00"), "INR"),
            accounts_receivable=Money(Decimal("50000.00"), "INR"),
            inventory_valuation=Money(Decimal("50000.00"), "INR"),
            total_current_liabilities=Money(Decimal("30000.00"), "INR"),
            net_working_capital=Money(Decimal("120000.00"), "INR"),
            current_ratio="5.0",
        ),
        compute_health_score=lambda b, d: SimpleNamespace(
            overall_score=95,
            grade="EXCELLENT",
            cash_runway_months=12.0,
            key_strengths=["Strong Liquidity"],
        ),
    )

    pdf_bytes = generator.generate_dossier_pdf(biz_id, actor_name="executive@enterprise.org")
    reader = PdfReader(io.BytesIO(pdf_bytes))
    extracted = "\n".join(p.extract_text() for p in reader.pages)

    assert "sales_invoice_ids:" not in extracted
    assert "Evidence references:" not in extracted
    assert "Historical actuals derived directly from verified double-entry" in extracted

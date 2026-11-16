"""
Deterministic Financial Intelligence Engine for ArthLens.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 3: Financial Understanding & Analytics (P&L, Cash Flow, Working Capital, Ageing, Break-even, Health Score).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
import uuid

from backend.arthlens.domain.business import (
    Customer,
    ExpenseCategory,
    ExpenseRecord,
    IncomeRecord,
    InventoryBalance,
    InvoiceStatus,
    Money,
    Payment,
    PaymentMethod,
    PaymentType,
    Purchase,
    PurchaseStatus,
    SalesInvoice,
    StandardAccount,
    Supplier,
)
from backend.arthlens.infra.business_repositories import (
    PostgresCustomerRepository,
    PostgresIncomeExpenseRepository,
    PostgresInventoryRepository,
    PostgresJournalEntryRepository,
    PostgresPaymentRepository,
    PostgresPurchaseRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)


@dataclass(frozen=True)
class ProfitAndLossStatement:
    business_id: uuid.UUID
    start_date: date
    end_date: date
    gross_sales: Money
    sales_returns: Money
    direct_income: Money
    total_revenue: Money
    cost_of_goods_sold: Money
    gross_profit: Money
    gross_margin_percent: Decimal
    operating_expenses: Dict[str, Money]
    total_operating_expenses: Money
    operating_profit_ebitda: Money
    operating_margin_percent: Decimal
    net_profit: Money
    net_margin_percent: Decimal
    data_quality_warnings: List[str] = field(default_factory=list)
    unreconciled_inventory_movement_count: int = 0
    conflicting_inventory_movement_count: int = 0
    inventory_cost_completeness_percent: Decimal = Decimal("100.00")
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": str(self.business_id),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "gross_sales": float(self.gross_sales.amount),
            "gross_sales_exact": f"{self.gross_sales.amount:.2f}",
            "formatted_gross_sales": self.gross_sales.format_inr(),
            "sales_returns": float(self.sales_returns.amount),
            "sales_returns_exact": f"{self.sales_returns.amount:.2f}",
            "formatted_sales_returns": self.sales_returns.format_inr(),
            "direct_income": float(self.direct_income.amount),
            "direct_income_exact": f"{self.direct_income.amount:.2f}",
            "formatted_direct_income": self.direct_income.format_inr(),
            "total_revenue": float(self.total_revenue.amount),
            "total_revenue_exact": f"{self.total_revenue.amount:.2f}",
            "formatted_total_revenue": self.total_revenue.format_inr(),
            "cost_of_goods_sold": float(self.cost_of_goods_sold.amount),
            "cost_of_goods_sold_exact": f"{self.cost_of_goods_sold.amount:.2f}",
            "formatted_cogs": self.cost_of_goods_sold.format_inr(),
            "gross_profit": float(self.gross_profit.amount),
            "gross_profit_exact": f"{self.gross_profit.amount:.2f}",
            "formatted_gross_profit": self.gross_profit.format_inr(),
            "gross_margin_percent": float(self.gross_margin_percent),
            "operating_expenses": {k: float(v.amount) for k, v in self.operating_expenses.items()},
            "operating_expenses_exact": {k: f"{v.amount:.2f}" for k, v in self.operating_expenses.items()},
            "formatted_operating_expenses": {k: v.format_inr() for k, v in self.operating_expenses.items()},
            "total_operating_expenses": float(self.total_operating_expenses.amount),
            "total_operating_expenses_exact": f"{self.total_operating_expenses.amount:.2f}",
            "formatted_total_operating_expenses": self.total_operating_expenses.format_inr(),
            "operating_profit_ebitda": float(self.operating_profit_ebitda.amount),
            "operating_profit_ebitda_exact": f"{self.operating_profit_ebitda.amount:.2f}",
            "formatted_operating_profit": self.operating_profit_ebitda.format_inr(),
            "operating_margin_percent": float(self.operating_margin_percent),
            "net_profit": float(self.net_profit.amount),
            "net_profit_exact": f"{self.net_profit.amount:.2f}",
            "formatted_net_profit": self.net_profit.format_inr(),
            "net_margin_percent": float(self.net_margin_percent),
            "currency": self.total_revenue.currency,
            "data_quality_warnings": self.data_quality_warnings,
            "data_quality": {
                "unreconciled_inventory_movement_count": self.unreconciled_inventory_movement_count,
                "conflicting_inventory_movement_count": self.conflicting_inventory_movement_count,
                "inventory_cost_completeness_percent": f"{self.inventory_cost_completeness_percent:.2f}",
            },
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class CashFlowStatement:
    business_id: uuid.UUID
    start_date: date
    end_date: date
    operating_cash_inflows: Money
    operating_cash_outflows: Money
    net_operating_cash_flow: Money
    investing_cash_outflows: Money
    net_investing_cash_flow: Money
    financing_cash_inflows: Money
    financing_cash_outflows: Money
    net_financing_cash_flow: Money
    net_change_in_cash: Money
    closing_cash_in_hand: Money
    closing_bank_balance: Money
    total_closing_liquidity: Money
    opening_cash_balance: Money

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": str(self.business_id),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "operating_cash_inflows": float(self.operating_cash_inflows.amount),
            "operating_cash_inflows_exact": f"{self.operating_cash_inflows.amount:.2f}",
            "operating_cash_outflows": float(self.operating_cash_outflows.amount),
            "operating_cash_outflows_exact": f"{self.operating_cash_outflows.amount:.2f}",
            "net_operating_cash_flow": float(self.net_operating_cash_flow.amount),
            "net_operating_cash_flow_exact": f"{self.net_operating_cash_flow.amount:.2f}",
            "investing_cash_outflows": float(self.investing_cash_outflows.amount),
            "investing_cash_outflows_exact": f"{self.investing_cash_outflows.amount:.2f}",
            "net_investing_cash_flow": float(self.net_investing_cash_flow.amount),
            "net_investing_cash_flow_exact": f"{self.net_investing_cash_flow.amount:.2f}",
            "financing_cash_inflows": float(self.financing_cash_inflows.amount),
            "financing_cash_inflows_exact": f"{self.financing_cash_inflows.amount:.2f}",
            "financing_cash_outflows": float(self.financing_cash_outflows.amount),
            "financing_cash_outflows_exact": f"{self.financing_cash_outflows.amount:.2f}",
            "net_financing_cash_flow": float(self.net_financing_cash_flow.amount),
            "net_financing_cash_flow_exact": f"{self.net_financing_cash_flow.amount:.2f}",
            "net_change_in_cash": float(self.net_change_in_cash.amount),
            "net_change_in_cash_exact": f"{self.net_change_in_cash.amount:.2f}",
            "opening_cash_balance": float(self.opening_cash_balance.amount),
            "opening_cash_balance_exact": f"{self.opening_cash_balance.amount:.2f}",
            "formatted_net_change_in_cash": self.net_change_in_cash.format_inr(),
            "closing_cash_in_hand": float(self.closing_cash_in_hand.amount),
            "closing_cash_in_hand_exact": f"{self.closing_cash_in_hand.amount:.2f}",
            "formatted_closing_cash_in_hand": self.closing_cash_in_hand.format_inr(),
            "closing_bank_balance": float(self.closing_bank_balance.amount),
            "closing_bank_balance_exact": f"{self.closing_bank_balance.amount:.2f}",
            "formatted_closing_bank_balance": self.closing_bank_balance.format_inr(),
            "total_closing_liquidity": float(self.total_closing_liquidity.amount),
            "total_closing_liquidity_exact": f"{self.total_closing_liquidity.amount:.2f}",
            "formatted_total_closing_liquidity": self.total_closing_liquidity.format_inr(),
        }


@dataclass(frozen=True)
class WorkingCapitalPosition:
    business_id: uuid.UUID
    as_of_date: date
    cash_and_bank: Money
    accounts_receivable: Money
    inventory_valuation: Money
    total_current_assets: Money
    accounts_payable: Money
    other_current_liabilities: Money
    total_current_liabilities: Money
    net_working_capital: Money
    current_ratio: Optional[float]
    quick_ratio: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": str(self.business_id),
            "as_of_date": self.as_of_date.isoformat(),
            "cash_and_bank": float(self.cash_and_bank.amount),
            "cash_and_bank_exact": f"{self.cash_and_bank.amount:.2f}",
            "accounts_receivable": float(self.accounts_receivable.amount),
            "accounts_receivable_exact": f"{self.accounts_receivable.amount:.2f}",
            "inventory_valuation": float(self.inventory_valuation.amount),
            "inventory_valuation_exact": f"{self.inventory_valuation.amount:.2f}",
            "total_current_assets": float(self.total_current_assets.amount),
            "total_current_assets_exact": f"{self.total_current_assets.amount:.2f}",
            "formatted_total_current_assets": self.total_current_assets.format_inr(),
            "accounts_payable": float(self.accounts_payable.amount),
            "accounts_payable_exact": f"{self.accounts_payable.amount:.2f}",
            "other_current_liabilities": float(self.other_current_liabilities.amount),
            "other_current_liabilities_exact": f"{self.other_current_liabilities.amount:.2f}",
            "total_current_liabilities": float(self.total_current_liabilities.amount),
            "total_current_liabilities_exact": f"{self.total_current_liabilities.amount:.2f}",
            "formatted_total_current_liabilities": self.total_current_liabilities.format_inr(),
            "net_working_capital": float(self.net_working_capital.amount),
            "net_working_capital_exact": f"{self.net_working_capital.amount:.2f}",
            "formatted_net_working_capital": self.net_working_capital.format_inr(),
            "current_ratio": self.current_ratio,
            "quick_ratio": self.quick_ratio,
        }


@dataclass(frozen=True)
class AgeingBucketSummary:
    bucket_0_30: Money
    bucket_31_60: Money
    bucket_61_90: Money
    bucket_90_plus: Money
    total_outstanding: Money
    total_overdue: Money
    average_days: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "0_30_days": float(self.bucket_0_30.amount),
            "0_30_days_exact": f"{self.bucket_0_30.amount:.2f}",
            "formatted_0_30": self.bucket_0_30.format_inr(),
            "31_60_days": float(self.bucket_31_60.amount),
            "31_60_days_exact": f"{self.bucket_31_60.amount:.2f}",
            "formatted_31_60": self.bucket_31_60.format_inr(),
            "61_90_days": float(self.bucket_61_90.amount),
            "61_90_days_exact": f"{self.bucket_61_90.amount:.2f}",
            "formatted_61_90": self.bucket_61_90.format_inr(),
            "90_plus_days": float(self.bucket_90_plus.amount),
            "90_plus_days_exact": f"{self.bucket_90_plus.amount:.2f}",
            "formatted_90_plus": self.bucket_90_plus.format_inr(),
            "total_outstanding": float(self.total_outstanding.amount),
            "total_outstanding_exact": f"{self.total_outstanding.amount:.2f}",
            "formatted_total_outstanding": self.total_outstanding.format_inr(),
            "total_overdue": float(self.total_overdue.amount),
            "total_overdue_exact": f"{self.total_overdue.amount:.2f}",
            "formatted_total_overdue": self.total_overdue.format_inr(),
            "average_days": self.average_days,
        }


@dataclass(frozen=True)
class BreakEvenAnalysis:
    business_id: uuid.UUID
    start_date: date
    end_date: date
    total_revenue: Money
    total_variable_costs: Money
    total_fixed_costs: Money
    contribution_margin: Money
    contribution_margin_ratio: float
    break_even_revenue: Optional[Money]
    margin_of_safety_percent: Optional[float]
    is_profitable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": str(self.business_id),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_revenue": float(self.total_revenue.amount),
            "total_revenue_exact": f"{self.total_revenue.amount:.2f}",
            "formatted_total_revenue": self.total_revenue.format_inr(),
            "total_variable_costs": float(self.total_variable_costs.amount),
            "total_variable_costs_exact": f"{self.total_variable_costs.amount:.2f}",
            "formatted_variable_costs": self.total_variable_costs.format_inr(),
            "total_fixed_costs": float(self.total_fixed_costs.amount),
            "total_fixed_costs_exact": f"{self.total_fixed_costs.amount:.2f}",
            "formatted_fixed_costs": self.total_fixed_costs.format_inr(),
            "contribution_margin": float(self.contribution_margin.amount),
            "contribution_margin_exact": f"{self.contribution_margin.amount:.2f}",
            "formatted_contribution_margin": self.contribution_margin.format_inr(),
            "contribution_margin_ratio": self.contribution_margin_ratio,
            "break_even_revenue": float(self.break_even_revenue.amount) if self.break_even_revenue else None,
            "break_even_revenue_exact": f"{self.break_even_revenue.amount:.2f}" if self.break_even_revenue else None,
            "formatted_break_even_revenue": self.break_even_revenue.format_inr() if self.break_even_revenue else "N/A",
            "margin_of_safety_percent": self.margin_of_safety_percent,
            "is_profitable": self.is_profitable,
        }


@dataclass(frozen=True)
class HealthScore:
    business_id: uuid.UUID
    as_of_date: date
    overall_score: int  # 0 to 100
    grade: str  # EXCELLENT, HEALTHY, NEEDS_ATTENTION, CRITICAL
    liquidity_score: int  # 0 to 20
    profitability_score: int  # 0 to 20
    solvency_score: int  # 0 to 20
    efficiency_score: int  # 0 to 20
    cash_runway_score: int  # 0 to 20
    cash_runway_months: float
    key_strengths: List[str]
    identified_risks: List[str]
    data_completeness_score: Decimal = Decimal("100.00")
    unreconciled_inventory_movement_count: int = 0
    conflicting_inventory_movement_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "business_id": str(self.business_id),
            "as_of_date": self.as_of_date.isoformat(),
            "overall_score": self.overall_score,
            "grade": self.grade,
            "pillars": {
                "liquidity": {"score": self.liquidity_score, "max": 20},
                "profitability": {"score": self.profitability_score, "max": 20},
                "solvency": {"score": self.solvency_score, "max": 20},
                "efficiency": {"score": self.efficiency_score, "max": 20},
                "cash_runway": {"score": self.cash_runway_score, "max": 20, "months": self.cash_runway_months},
            },
            "key_strengths": self.key_strengths,
            "identified_risks": self.identified_risks,
            "data_completeness_score": f"{self.data_completeness_score:.2f}",
            "unreconciled_inventory_movement_count": self.unreconciled_inventory_movement_count,
            "conflicting_inventory_movement_count": self.conflicting_inventory_movement_count,
        }


class FinancialIntelligenceEngine:
    """
    Deterministic Financial Intelligence Engine.
    Executes zero-hallucination accounting, cash flow, ageing, and solvency analysis
    directly from verified double-entry and transactional records.
    """

    def __init__(
        self,
        invoice_repo: Optional[PostgresSalesInvoiceRepository] = None,
        purchase_repo: Optional[PostgresPurchaseRepository] = None,
        customer_repo: Optional[PostgresCustomerRepository] = None,
        supplier_repo: Optional[PostgresSupplierRepository] = None,
        inventory_repo: Optional[PostgresInventoryRepository] = None,
        payment_repo: Optional[PostgresPaymentRepository] = None,
        income_expense_repo: Optional[PostgresIncomeExpenseRepository] = None,
        journal_repo: Optional[PostgresJournalEntryRepository] = None,
    ):
        self.invoice_repo = invoice_repo or PostgresSalesInvoiceRepository()
        self.purchase_repo = purchase_repo or PostgresPurchaseRepository()
        self.customer_repo = customer_repo or PostgresCustomerRepository()
        self.supplier_repo = supplier_repo or PostgresSupplierRepository()
        self.inventory_repo = inventory_repo or PostgresInventoryRepository()
        self.payment_repo = payment_repo or PostgresPaymentRepository()
        self.income_expense_repo = income_expense_repo or PostgresIncomeExpenseRepository()
        self.journal_repo = journal_repo or PostgresJournalEntryRepository()

    # ==========================================================================
    # 1. Profit & Loss Statement (UC-51)
    # ==========================================================================

    def calculate_pnl(
        self,
        business_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> ProfitAndLossStatement:
        """Computes P&L from dated journal postings, with source coverage warnings."""
        invoices = self.invoice_repo.list_by_business(business_id)
        period_invoices = [inv for inv in invoices if start_date <= inv.invoice_date <= end_date]
        entries = self.journal_repo.list_by_business(business_id, start_date=start_date, end_date=end_date)
        account_net: Dict[str, Decimal] = {}
        for entry in entries:
            if not getattr(entry, "is_posted", True):
                continue
            for line in entry.lines:
                account_net[line.account_code] = account_net.get(line.account_code, Decimal("0")) + line.credit.amount - line.debit.amount
        warnings: List[str] = []

        # Revenue, returns, and COGS are read from the posted ledger so cancellations
        # and returns affect the accounting date on which their journal was posted.
        gross_sales = Money(account_net.get(StandardAccount.SALES_REVENUE.value, Decimal("0")))
        sales_returns = Money(-account_net.get(StandardAccount.SALES_RETURNS.value, Decimal("0")))
        incomes = self.income_expense_repo.list_income(business_id, start_date=start_date, end_date=end_date)
        recorded_income = sum((inc.amount for inc in incomes), Money.zero())
        has_income_postings = any(
            line.account_code == StandardAccount.OTHER_INCOME.value
            for entry in entries
            for line in entry.lines
        )
        ledger_income = Money(account_net.get(StandardAccount.OTHER_INCOME.value, Decimal("0")))
        inventory_gains = Money(account_net.get(StandardAccount.INVENTORY_GAIN.value, Decimal("0")))
        if has_income_postings and ledger_income != recorded_income:
            warnings.append("Posted other-income journals do not reconcile to the income records for this period.")
        direct_income = (ledger_income if has_income_postings else recorded_income) + inventory_gains
        net_sales = gross_sales - sales_returns
        total_revenue = net_sales + direct_income

        cost_of_goods_sold = Money(-account_net.get(StandardAccount.COGS.value, Decimal("0")))
        gross_profit = net_sales - cost_of_goods_sold
        gross_margin_pct = (
            (gross_profit.amount / net_sales.amount * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if net_sales.amount > 0 else Decimal("0.00")
        )

        # Operating expenses by category
        expenses = self.income_expense_repo.list_expenses(business_id, start_date=start_date, end_date=end_date)
        category_totals: Dict[str, Money] = {}
        for exp in expenses:
            cat_name = exp.category.value
            category_totals[cat_name] = category_totals.get(cat_name, Money.zero()) + exp.amount

        ledger_opex = Money(
            -account_net.get(StandardAccount.OPERATING_EXPENSES.value, Decimal("0"))
            - account_net.get(StandardAccount.INVENTORY_LOSS.value, Decimal("0"))
        )
        record_opex = sum(category_totals.values(), Money.zero())
        has_expense_postings = any(
            line.account_code in (StandardAccount.OPERATING_EXPENSES.value, StandardAccount.INVENTORY_LOSS.value)
            for entry in entries
            for line in entry.lines
        )
        ledger_expense_records = Money(-account_net.get(StandardAccount.OPERATING_EXPENSES.value, Decimal("0")))
        total_opex = ledger_opex if has_expense_postings else record_opex
        if (
            any(line.account_code == StandardAccount.OPERATING_EXPENSES.value for entry in entries for line in entry.lines)
            and ledger_expense_records != record_opex
        ):
            warnings.append("Posted operating expense journals do not reconcile to the expense records for this period.")

        # Pre-cost-basis sales cannot be safely reversed or reconstructed from
        # today's stock average. Surface those legacy gaps in the report.
        period_invoice_ids = {str(inv.id) for inv in period_invoices}
        movement_rows = self.inventory_repo.list_movements(business_id)
        unresolved_cost_rows = [
            movement for movement in movement_rows
            if getattr(movement, "cost_reconciliation_status", "VERIFIED") != "VERIFIED"
        ]
        unreconciled_count = sum(
            1 for movement in movement_rows
            if getattr(movement, "cost_reconciliation_status", "VERIFIED") == "UNRECONCILED"
        )
        conflicting_count = sum(
            1 for movement in movement_rows
            if getattr(movement, "cost_reconciliation_status", "VERIFIED") == "CONFLICTING"
        )
        if unresolved_cost_rows:
            warnings.append(
                f"{len(unresolved_cost_rows)} inventory movements have unreconciled or conflicting cost status."
            )
        verified_count = len(movement_rows) - len(unresolved_cost_rows)
        completeness = (
            (Decimal(verified_count) / Decimal(len(movement_rows)) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if movement_rows else Decimal("100.00")
        )
        posted_cogs_refs = {
            str(getattr(entry, "reference_id"))
            for entry in entries
            if getattr(entry, "reference_type", None) == "INVOICE_COGS" and getattr(entry, "reference_id", None) is not None
        }
        for inv in period_invoices:
            product_quantities: Dict[uuid.UUID, Decimal] = {}
            for item in inv.items:
                if item.product_id:
                    product_quantities[item.product_id] = product_quantities.get(item.product_id, Decimal("0")) + item.quantity
            for product_id, expected_quantity in product_quantities.items():
                sale_rows = [
                    movement for movement in movement_rows
                    if movement.reference_id == str(inv.id)
                    and movement.product_id == product_id
                    and movement.movement_type.value == "SALE"
                ]
                if (
                    not sale_rows
                    or sum((movement.quantity for movement in sale_rows), Decimal("0")) != expected_quantity
                    or any(movement.cost_basis is None for movement in sale_rows)
                    or (
                        any(movement.cost_basis and movement.cost_basis > Money.zero() for movement in sale_rows)
                        and str(inv.id) not in posted_cogs_refs
                    )
                ):
                    warnings.append(
                        f"Invoice {inv.invoice_number} has inventory sales without captured sale-time cost; historical COGS may be incomplete."
                    )
                    break
        operating_profit = gross_profit + direct_income - total_opex
        operating_margin_pct = (
            (operating_profit.amount / total_revenue.amount * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_revenue.amount > 0 else Decimal("0.00")
        )

        net_profit = operating_profit
        net_margin_pct = (
            (net_profit.amount / total_revenue.amount * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if total_revenue.amount > 0 else Decimal("0.00")
        )

        period_movements = [
            movement for movement in movement_rows
            if start_date <= movement.created_at.date() <= end_date
        ]
        source_timestamps = [
            item.created_at
            for item in [*period_invoices, *incomes, *expenses, *entries, *period_movements]
            if getattr(item, "created_at", None) is not None
        ]
        provenance = {
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "calculated_at": datetime.now(timezone.utc).isoformat(),
            "latest_source_record_at": (
                max(source_timestamps, key=lambda value: value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)).isoformat()
                if source_timestamps else None
            ),
            "source_table_counts": {
                "sales_invoices": len(period_invoices),
                "journal_entries": sum(1 for entry in entries if getattr(entry, "is_posted", True)),
                "income_records": len(incomes),
                "expense_records": len(expenses),
                "inventory_movements_in_period": len(period_movements),
                "inventory_movements_total": len(movement_rows),
                "unreconciled_inventory_movements": unreconciled_count,
                "conflicting_inventory_movements": conflicting_count,
            },
            "formulas": {
                "net_sales": "posted_sales_revenue - posted_sales_returns",
                "total_revenue": "net_sales + posted_other_income + inventory_adjustment_gains",
                "cost_of_goods_sold": "-posted_COGS_account_net_balance; source invoice sale costs must have verified movement cost basis",
                "gross_profit": "net_sales - cost_of_goods_sold",
                "operating_expenses": "posted_operating_expenses + posted_inventory_shrinkage; source expense categories are reconciled to journal postings",
                "net_profit": "gross_profit + direct_income - operating_expenses",
            },
            "source_record_ids": {
                "sales_invoice_ids": [str(invoice.id) for invoice in period_invoices],
                "journal_entry_ids": [
                    str(entry_id)
                    for entry in entries
                    if getattr(entry, "is_posted", True)
                    and (entry_id := getattr(entry, "id", None)) is not None
                ],
                "income_record_ids": [str(item.id) for item in incomes],
                "expense_record_ids": [str(item.id) for item in expenses],
                "inventory_movement_ids": [str(item.id) for item in period_movements],
            },
            "data_quality_warnings": list(warnings),
            "inventory_cost_completeness_percent": f"{completeness:.2f}",
        }

        return ProfitAndLossStatement(
            business_id=business_id,
            start_date=start_date,
            end_date=end_date,
            gross_sales=gross_sales,
            sales_returns=sales_returns,
            direct_income=direct_income,
            total_revenue=total_revenue,
            cost_of_goods_sold=cost_of_goods_sold,
            gross_profit=gross_profit,
            gross_margin_percent=gross_margin_pct,
            operating_expenses=category_totals,
            total_operating_expenses=total_opex,
            operating_profit_ebitda=operating_profit,
            operating_margin_percent=operating_margin_pct,
            net_profit=net_profit,
            net_margin_percent=net_margin_pct,
            data_quality_warnings=warnings,
            unreconciled_inventory_movement_count=unreconciled_count,
            conflicting_inventory_movement_count=conflicting_count,
            inventory_cost_completeness_percent=completeness,
            provenance=provenance,
        )

    # ==========================================================================
    # 2. Cash Flow Statement (UC-52)
    # ==========================================================================

    def calculate_cash_flow(
        self,
        business_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> CashFlowStatement:
        """Derives operating, investing, and financing cash flows from transactional payments."""
        payments = self.payment_repo.list_by_business(business_id)
        period_payments = [p for p in payments if start_date <= p.payment_date <= end_date]

        incomes = self.income_expense_repo.list_income(business_id, start_date=start_date, end_date=end_date)
        expenses = self.income_expense_repo.list_expenses(business_id, start_date=start_date, end_date=end_date)

        # Operating inflows: customer payments + direct income
        operating_inflows = sum(
            (p.amount for p in period_payments if p.payment_type == PaymentType.RECEIVED and p.reference_type != "LOAN"),
            Money.zero(),
        ) + sum((inc.amount for inc in incomes), Money.zero())

        # Operating outflows: supplier payments for goods + opex expenses
        operating_outflows = sum(
            (p.amount for p in period_payments if p.payment_type == PaymentType.PAID and p.reference_type != "CAPEX"),
            Money.zero(),
        ) + sum((exp.amount for exp in expenses if exp.category != ExpenseCategory.CAPITAL), Money.zero())

        net_operating = operating_inflows - operating_outflows

        # Investing: capital expenses
        investing_outflows = sum(
            (exp.amount for exp in expenses if exp.category == ExpenseCategory.CAPITAL),
            Money.zero(),
        )
        net_investing = -investing_outflows

        # Financing: loans / equity
        financing_inflows = sum(
            (p.amount for p in period_payments if p.payment_type == PaymentType.RECEIVED and p.reference_type == "LOAN"),
            Money.zero(),
        )
        financing_outflows = sum(
            (p.amount for p in period_payments if p.payment_type == PaymentType.PAID and p.reference_type == "LOAN_REPAYMENT"),
            Money.zero(),
        )
        net_financing = financing_inflows - financing_outflows

        net_change = net_operating + net_investing + net_financing

        # Live cash and bank position
        all_payments = self.payment_repo.list_by_business(business_id)
        all_incomes = self.income_expense_repo.list_income(business_id)
        all_expenses = self.income_expense_repo.list_expenses(business_id)

        cash_in_hand = Decimal("0.00")
        bank_balance = Decimal("0.00")

        opening_cash = Decimal("0.00")
        opening_bank = Decimal("0.00")
        for p in all_payments:
            signed = p.amount.amount if p.payment_type == PaymentType.RECEIVED else -p.amount.amount
            if p.payment_date < start_date:
                if p.payment_method == PaymentMethod.CASH:
                    opening_cash += signed
                else:
                    opening_bank += signed
            if p.payment_date <= end_date:
                if p.payment_method == PaymentMethod.CASH:
                    cash_in_hand += signed
                else:
                    bank_balance += signed

        for inc in all_incomes:
            if inc.date < start_date:
                if inc.payment_method == PaymentMethod.CASH:
                    opening_cash += inc.amount.amount
                else:
                    opening_bank += inc.amount.amount
            if inc.date <= end_date:
                if inc.payment_method == PaymentMethod.CASH:
                    cash_in_hand += inc.amount.amount
                else:
                    bank_balance += inc.amount.amount

        for exp in all_expenses:
            if exp.date < start_date:
                if exp.payment_method == PaymentMethod.CASH:
                    opening_cash -= exp.amount.amount
                else:
                    opening_bank -= exp.amount.amount
            if exp.date <= end_date:
                if exp.payment_method == PaymentMethod.CASH:
                    cash_in_hand -= exp.amount.amount
                else:
                    bank_balance -= exp.amount.amount

        closing_cash = Money(cash_in_hand)
        closing_bank = Money(bank_balance)
        total_liq = closing_cash + closing_bank

        return CashFlowStatement(
            business_id=business_id,
            start_date=start_date,
            end_date=end_date,
            operating_cash_inflows=operating_inflows,
            operating_cash_outflows=operating_outflows,
            net_operating_cash_flow=net_operating,
            investing_cash_outflows=investing_outflows,
            net_investing_cash_flow=net_investing,
            financing_cash_inflows=financing_inflows,
            financing_cash_outflows=financing_outflows,
            net_financing_cash_flow=net_financing,
            net_change_in_cash=net_change,
            opening_cash_balance=Money(opening_cash + opening_bank),
            closing_cash_in_hand=closing_cash,
            closing_bank_balance=closing_bank,
            total_closing_liquidity=total_liq,
        )

    # ==========================================================================
    # 3. Working Capital & Ratios (UC-53)
    # ==========================================================================

    def calculate_working_capital(
        self,
        business_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> WorkingCapitalPosition:
        """Calculates current assets, liabilities, and working capital solvency ratios."""
        ref_date = as_of_date or date.today()

        # Cash & Bank
        cf = self.calculate_cash_flow(business_id, ref_date - timedelta(days=365), ref_date)
        cash_and_bank = cf.total_closing_liquidity

        # Receivables
        customers = self.customer_repo.list_by_business(business_id)
        receivables = sum((c.current_balance for c in customers if c.current_balance.is_positive()), Money.zero())

        # Inventory
        balances = self.inventory_repo.list_balances(business_id)
        inventory_val = sum((b.total_valuation for b in balances), Money.zero())

        total_assets = cash_and_bank + receivables + inventory_val

        # Payables
        suppliers = self.supplier_repo.list_by_business(business_id)
        payables = sum((s.current_balance for s in suppliers if s.current_balance.is_positive()), Money.zero())
        other_liabilities = Money.zero()
        total_liabilities = payables + other_liabilities

        net_working_capital = total_assets - total_liabilities

        curr_ratio = None
        if total_liabilities.amount > 0:
            curr_ratio = round(float(total_assets.amount / total_liabilities.amount), 2)

        quick_ratio = None
        if total_liabilities.amount > 0:
            quick_assets = cash_and_bank + receivables
            quick_ratio = round(float(quick_assets.amount / total_liabilities.amount), 2)

        return WorkingCapitalPosition(
            business_id=business_id,
            as_of_date=ref_date,
            cash_and_bank=cash_and_bank,
            accounts_receivable=receivables,
            inventory_valuation=inventory_val,
            total_current_assets=total_assets,
            accounts_payable=payables,
            other_current_liabilities=other_liabilities,
            total_current_liabilities=total_liabilities,
            net_working_capital=net_working_capital,
            current_ratio=curr_ratio,
            quick_ratio=quick_ratio,
        )

    # ==========================================================================
    # 4. Ageing Analysis: Receivables & Payables (UC-54)
    # ==========================================================================

    def calculate_receivables_ageing(
        self,
        business_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> AgeingBucketSummary:
        """Aggregates unpaid customer invoices into 0-30, 31-60, 61-90, and 90+ day overdue buckets."""
        ref_date = as_of_date or date.today()
        invoices = self.invoice_repo.list_by_business(business_id)
        unpaid = [inv for inv in invoices if inv.status in (InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE)]

        b0_30 = Decimal("0.00")
        b31_60 = Decimal("0.00")
        b61_90 = Decimal("0.00")
        b90_plus = Decimal("0.00")
        total_overdue = Decimal("0.00")
        weighted_days = Decimal("0.00")
        total_out = Decimal("0.00")

        for inv in unpaid:
            bal = inv.outstanding_balance.amount
            if bal <= 0:
                continue
            total_out += bal
            age_days = (ref_date - inv.due_date).days
            if age_days > 0:
                total_overdue += bal
                weighted_days += Decimal(str(age_days)) * bal

            if age_days <= 30:
                b0_30 += bal
            elif age_days <= 60:
                b31_60 += bal
            elif age_days <= 90:
                b61_90 += bal
            else:
                b90_plus += bal

        avg_days = float(weighted_days / total_out) if total_out > 0 else 0.0

        return AgeingBucketSummary(
            bucket_0_30=Money(b0_30),
            bucket_31_60=Money(b31_60),
            bucket_61_90=Money(b61_90),
            bucket_90_plus=Money(b90_plus),
            total_outstanding=Money(total_out),
            total_overdue=Money(total_overdue),
            average_days=round(avg_days, 1),
        )

    def calculate_payables_ageing(
        self,
        business_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> AgeingBucketSummary:
        """Aggregates unpaid supplier bills into ageing buckets."""
        ref_date = as_of_date or date.today()
        purchases = self.purchase_repo.list_by_business(business_id)
        unpaid = [p for p in purchases if p.status in (PurchaseStatus.PENDING, PurchaseStatus.PARTIALLY_PAID, PurchaseStatus.OVERDUE)]

        b0_30 = Decimal("0.00")
        b31_60 = Decimal("0.00")
        b61_90 = Decimal("0.00")
        b90_plus = Decimal("0.00")
        total_overdue = Decimal("0.00")
        weighted_days = Decimal("0.00")
        total_out = Decimal("0.00")

        for p in unpaid:
            bal = p.outstanding_balance.amount
            if bal <= 0:
                continue
            total_out += bal
            age_days = (ref_date - p.due_date).days
            if age_days > 0:
                total_overdue += bal
                weighted_days += Decimal(str(age_days)) * bal

            if age_days <= 30:
                b0_30 += bal
            elif age_days <= 60:
                b31_60 += bal
            elif age_days <= 90:
                b61_90 += bal
            else:
                b90_plus += bal

        avg_days = float(weighted_days / total_out) if total_out > 0 else 0.0

        return AgeingBucketSummary(
            bucket_0_30=Money(b0_30),
            bucket_31_60=Money(b31_60),
            bucket_61_90=Money(b61_90),
            bucket_90_plus=Money(b90_plus),
            total_outstanding=Money(total_out),
            total_overdue=Money(total_overdue),
            average_days=round(avg_days, 1),
        )

    # ==========================================================================
    # 5. Break-even Analysis (UC-56)
    # ==========================================================================

    def calculate_break_even(
        self,
        business_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> BreakEvenAnalysis:
        """Computes fixed vs variable costs, contribution margin, and break-even revenue."""
        pnl = self.calculate_pnl(business_id, start_date, end_date)
        total_rev = pnl.total_revenue
        var_costs = pnl.cost_of_goods_sold  # Primary variable costs
        fixed_costs = pnl.total_operating_expenses  # Operational overhead

        contribution_margin = total_rev - var_costs
        cm_ratio = 0.0
        if total_rev.amount > 0:
            cm_ratio = float(contribution_margin.amount / total_rev.amount)

        be_rev = None
        mos_pct = None
        if cm_ratio > 0:
            be_amt = (fixed_costs.amount / Decimal(str(cm_ratio))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            be_rev = Money(be_amt)
            if total_rev.amount > 0:
                mos = float((total_rev.amount - be_rev.amount) / total_rev.amount * Decimal("100"))
                mos_pct = round(mos, 2)

        is_profitable = pnl.net_profit.is_positive()

        return BreakEvenAnalysis(
            business_id=business_id,
            start_date=start_date,
            end_date=end_date,
            total_revenue=total_rev,
            total_variable_costs=var_costs,
            total_fixed_costs=fixed_costs,
            contribution_margin=contribution_margin,
            contribution_margin_ratio=round(cm_ratio, 4),
            break_even_revenue=be_rev,
            margin_of_safety_percent=mos_pct,
            is_profitable=is_profitable,
        )

    # ==========================================================================
    # 6. Business Health Score (UC-57 & UC-58)
    # ==========================================================================

    def compute_health_score(
        self,
        business_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> HealthScore:
        """Computes comprehensive 0-100 business health score across 5 essential operational pillars."""
        ref_date = as_of_date or date.today()
        wc = self.calculate_working_capital(business_id, ref_date)
        pnl = self.calculate_pnl(business_id, ref_date - timedelta(days=90), ref_date)
        ageing = self.calculate_receivables_ageing(business_id, ref_date)

        has_commercial_activity = (
            pnl.total_revenue.amount > 0
            or len(self.invoice_repo.list_by_business(business_id)) > 0
            or len(self.payment_repo.list_by_business(business_id)) > 0
            or pnl.total_operating_expenses.amount > 0
        )
        if not has_commercial_activity:
            return HealthScore(
                business_id=business_id,
                as_of_date=ref_date,
                overall_score=0,
                grade="NEEDS_ATTENTION",
                liquidity_score=0,
                profitability_score=0,
                solvency_score=0,
                efficiency_score=0,
                cash_runway_score=0,
                cash_runway_months=0.0,
                key_strengths=[],
                identified_risks=["Workspace is newly established with zero recorded commercial trading activity."],
                data_completeness_score=Decimal("100.00"),
                unreconciled_inventory_movement_count=0,
                conflicting_inventory_movement_count=0,
            )

        strengths: List[str] = []
        risks: List[str] = []

        # 1. Liquidity Pillar (0-20)
        c_ratio = wc.current_ratio or 0.0
        if c_ratio >= 1.5:
            liq_score = 20
            strengths.append(f"Strong liquidity buffer with current ratio of {c_ratio:.2f}")
        elif c_ratio >= 1.1:
            liq_score = 15
        elif c_ratio >= 0.8:
            liq_score = 10
            risks.append(f"Working capital ratio ({c_ratio:.2f}) is approaching danger threshold")
        else:
            liq_score = 5
            risks.append(f"Severely strained liquidity with current ratio of {c_ratio:.2f}")

        # 2. Profitability Pillar (0-20)
        margin = float(pnl.net_margin_percent)
        if margin >= 20.0:
            prof_score = 20
            strengths.append(f"High net profit margin ({margin:.1f}%)")
        elif margin >= 10.0:
            prof_score = 16
            strengths.append(f"Healthy operational profitability ({margin:.1f}%)")
        elif margin > 0.0:
            prof_score = 11
        else:
            prof_score = 4
            risks.append(f"Operating at net financial loss (margin: {margin:.1f}%)")

        # 3. Solvency Pillar (0-20)
        payables = wc.accounts_payable.amount
        receivables = wc.accounts_receivable.amount
        if payables == 0 or receivables >= payables:
            solv_score = 20
            strengths.append("Receivables comfortably exceed outstanding supplier payables")
        elif receivables >= payables * Decimal("0.70"):
            solv_score = 14
        else:
            solv_score = 8
            risks.append("Accounts payable substantially exceed customer receivables")

        # 4. Collection Efficiency Pillar (0-20)
        total_receivables = ageing.total_outstanding.amount
        overdue_90 = ageing.bucket_90_plus.amount
        if total_receivables == 0 or overdue_90 == 0:
            eff_score = 20
            strengths.append("Pristine customer collection cycle with zero long-term dues")
        elif overdue_90 <= total_receivables * Decimal("0.15"):
            eff_score = 15
        elif overdue_90 <= total_receivables * Decimal("0.35"):
            eff_score = 10
            risks.append(f"Elevated overdue receivables: ₹{Money(overdue_90).amount} over 90 days")
        else:
            eff_score = 5
            risks.append("Chronic debt collection delays: >35% of receivables exceed 90 days")

        # 5. Cash Runway Pillar (0-20)
        monthly_opex = float(pnl.total_operating_expenses.amount) / 3.0 if pnl.total_operating_expenses.amount > 0 else 1.0
        available_liquidity = float(wc.cash_and_bank.amount)
        runway_months = round(max(0.0, available_liquidity / monthly_opex), 1)

        if runway_months >= 6.0:
            runway_score = 20
            strengths.append(f"Substantial cash runway of {runway_months} months of operational expenses")
        elif runway_months >= 3.0:
            runway_score = 16
            strengths.append(f"Adequate cash runway of {runway_months} months")
        elif runway_months >= 1.0:
            runway_score = 10
            risks.append(f"Tight cash runway: only {runway_months} months of OpEx remaining")
        else:
            runway_score = 3
            risks.append(f"Critical liquidity emergency: cash runway is {runway_months} months")

        overall_score = liq_score + prof_score + solv_score + eff_score + runway_score

        if overall_score >= 80:
            grade = "EXCELLENT"
        elif overall_score >= 65:
            grade = "HEALTHY"
        elif overall_score >= 50:
            grade = "NEEDS_ATTENTION"
        else:
            grade = "CRITICAL"

        return HealthScore(
            business_id=business_id,
            as_of_date=ref_date,
            overall_score=overall_score,
            grade=grade,
            liquidity_score=liq_score,
            profitability_score=prof_score,
            solvency_score=solv_score,
            efficiency_score=eff_score,
            cash_runway_score=runway_score,
            cash_runway_months=runway_months,
            key_strengths=strengths,
            identified_risks=risks,
            data_completeness_score=pnl.inventory_cost_completeness_percent,
            unreconciled_inventory_movement_count=pnl.unreconciled_inventory_movement_count,
            conflicting_inventory_movement_count=pnl.conflicting_inventory_movement_count,
        )

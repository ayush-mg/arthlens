"""
Unit Tests for Deterministic Financial Intelligence Engine.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 3: Financial Understanding & Analytics (P&L, Cash Flow, Working Capital, Ageing, Break-even, Health Score).
"""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
import uuid
import pytest

from backend.arthlens.domain.business import (
    Customer,
    ExpenseCategory,
    ExpenseRecord,
    IncomeRecord,
    InventoryBalance,
    InventoryMovement,
    InvoiceStatus,
    Money,
    MovementType,
    Payment,
    PaymentMethod,
    PaymentType,
    Product,
    Purchase,
    PurchaseItem,
    PurchaseStatus,
    SalesInvoice,
    SalesInvoiceItem,
    StandardAccount,
    Supplier,
)
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine


class MockSalesInvoiceRepository:
    def __init__(self, invoices):
        self._invoices = invoices

    def list_by_business(self, business_id, customer_id=None):
        if customer_id:
            return [i for i in self._invoices if i.business_id == business_id and i.customer_id == customer_id]
        return [i for i in self._invoices if i.business_id == business_id]


class MockPurchaseRepository:
    def __init__(self, purchases):
        self._purchases = purchases

    def list_by_business(self, business_id, supplier_id=None):
        if supplier_id:
            return [p for p in self._purchases if p.business_id == business_id and p.supplier_id == supplier_id]
        return [p for p in self._purchases if p.business_id == business_id]


class MockCustomerRepository:
    def __init__(self, customers):
        self._customers = customers

    def list_by_business(self, business_id, include_archived=False):
        return [c for c in self._customers if c.business_id == business_id]


class MockSupplierRepository:
    def __init__(self, suppliers):
        self._suppliers = suppliers

    def list_by_business(self, business_id, include_archived=False):
        return [s for s in self._suppliers if s.business_id == business_id]


class MockInventoryRepository:
    def __init__(self, balances, movements=None):
        self._balances = balances
        self._movements = movements or []

    def get_balance(self, business_id, product_id):
        return next((b for b in self._balances if b.business_id == business_id and b.product_id == product_id), None)

    def list_balances(self, business_id):
        return [b for b in self._balances if b.business_id == business_id]

    def list_movements(self, business_id, product_id=None):
        return [
            movement for movement in self._movements
            if movement.business_id == business_id and (product_id is None or movement.product_id == product_id)
        ]


class MockPaymentRepository:
    def __init__(self, payments):
        self._payments = payments

    def list_by_business(self, business_id, party_id=None):
        if party_id:
            return [p for p in self._payments if p.business_id == business_id and p.party_id == party_id]
        return [p for p in self._payments if p.business_id == business_id]


class MockIncomeExpenseRepository:
    def __init__(self, incomes, expenses):
        self._incomes = incomes
        self._expenses = expenses

    def list_income(self, business_id, start_date=None, end_date=None):
        return [i for i in self._incomes if i.business_id == business_id]

    def list_expenses(self, business_id, start_date=None, end_date=None):
        return [e for e in self._expenses if e.business_id == business_id]


class MockJournalRepository:
    def __init__(self, lines, reference_id=None, reference_type="INVOICE_COGS"):
        self._lines = lines
        self._reference_id = reference_id
        self._reference_type = reference_type

    def list_by_business(self, business_id, start_date=None, end_date=None):
        return [SimpleNamespace(
            lines=self._lines,
            reference_id=self._reference_id,
            reference_type=self._reference_type,
            is_posted=True,
        )] if self._lines else []


def test_profit_and_loss_deterministic_calculation():
    """Verifies that P&L derives revenue, COGS, gross margin, OpEx, and net profit with exact decimal math."""
    biz_id = uuid.uuid4()
    prod_id = uuid.uuid4()

    # 1. Product balance: Unit cost = ₹300
    bal = InventoryBalance(
        id=uuid.uuid4(),
        business_id=biz_id,
        product_id=prod_id,
        quantity_on_hand=Decimal("50"),
        unit_cost=Money(300),
        total_valuation=Money(15000),
    )

    # 2. Sales Invoice: 10 units @ ₹500 = ₹5,000 + ₹250 tax = ₹5,250
    inv = SalesInvoice(
        id=uuid.uuid4(),
        business_id=biz_id,
        customer_id=uuid.uuid4(),
        invoice_number="INV-001",
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 15),
        subtotal=Money(5000),
        tax_amount=Money(250),
        total_amount=Money(5250),
        status=InvoiceStatus.PAID,
        items=[
            SalesInvoiceItem(
                id=uuid.uuid4(),
                invoice_id=uuid.uuid4(),
                product_id=prod_id,
                description="Engine Oil Filter",
                quantity=Decimal("10"),
                unit="pcs",
                unit_price=Money(500),
                total_price=Money(5000),
            )
        ],
    )

    # 3. Direct income: ₹750 (scrap/consulting)
    inc = IncomeRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category="Consulting",
        amount=Money(750),
        date=date(2026, 11, 5),
    )

    # 4. Expenses: Operating ₹600, Salaries ₹1,400 = Total ₹2,000
    exp1 = ExpenseRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category=ExpenseCategory.OPERATING,
        amount=Money(600),
        date=date(2026, 11, 2),
    )
    exp2 = ExpenseRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category=ExpenseCategory.SALARIES,
        amount=Money(1400),
        date=date(2026, 11, 3),
    )

    engine = FinancialIntelligenceEngine(
        invoice_repo=MockSalesInvoiceRepository([inv]),
        purchase_repo=MockPurchaseRepository([]),
        customer_repo=MockCustomerRepository([]),
        supplier_repo=MockSupplierRepository([]),
        inventory_repo=MockInventoryRepository([bal], [InventoryMovement(
            id=uuid.uuid4(),
            business_id=biz_id,
            product_id=prod_id,
            movement_type=MovementType.SALE,
            quantity=Decimal("10"),
            unit_price=Money(500),
            reference_id=str(inv.id),
            reason="Sale Invoice INV-001",
            balance_after=Decimal("40"),
            cost_basis=Money(300),
        )]),
        payment_repo=MockPaymentRepository([]),
        income_expense_repo=MockIncomeExpenseRepository([inc], [exp1, exp2]),
        journal_repo=MockJournalRepository([
            type("Line", (), {"account_code": StandardAccount.SALES_REVENUE.value, "debit": Money.zero(), "credit": Money(5000)})(),
            type("Line", (), {"account_code": StandardAccount.COGS.value, "debit": Money(3000), "credit": Money.zero()})(),
            type("Line", (), {"account_code": StandardAccount.OTHER_INCOME.value, "debit": Money.zero(), "credit": Money(750)})(),
            type("Line", (), {"account_code": StandardAccount.OPERATING_EXPENSES.value, "debit": Money(2000), "credit": Money.zero()})(),
        ], reference_id=inv.id),
    )

    pnl = engine.calculate_pnl(biz_id, date(2026, 11, 1), date(2026, 11, 30))

    # Tax is excluded from revenue: ₹5,000 net sales + ₹750 direct income.
    assert pnl.gross_sales == Money(5000)
    assert pnl.total_revenue == Money(5750)
    # COGS = 10 * 300 = 3000
    assert pnl.cost_of_goods_sold == Money(3000)
    # Gross profit uses net sales only; other income contributes below gross profit.
    assert pnl.gross_profit == Money(2000)
    # Gross Margin % = 2000 / 5000 * 100 = 40.00%
    assert pnl.gross_margin_percent == Decimal("40.00")
    # Operating Expenses = 2000
    assert pnl.total_operating_expenses == Money(2000)
    # Operating Profit / Net Profit = 2000 + 750 other income - 2000 expenses = 750
    assert pnl.net_profit == Money(750)
    # Net Margin % = 750 / 5750 * 100 = 13.04%
    assert pnl.net_margin_percent == Decimal("13.04")
    assert pnl.data_quality_warnings == []


def test_working_capital_and_solvency_ratios():
    """Verifies that Working Capital and Current/Quick Ratios match accounting invariants."""
    biz_id = uuid.uuid4()

    # Cash + Bank payments: +₹50,000 received, -₹20,000 paid = ₹30,000 closing liquidity
    p1 = Payment(
        id=uuid.uuid4(),
        business_id=biz_id,
        party_type=Customer,
        party_id=None,
        reference_type="INVOICE",
        reference_id=None,
        payment_type=PaymentType.RECEIVED,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Money(50000),
        payment_date=date.today(),
    )
    p2 = Payment(
        id=uuid.uuid4(),
        business_id=biz_id,
        party_type=Supplier,
        party_id=None,
        reference_type="PURCHASE",
        reference_id=None,
        payment_type=PaymentType.PAID,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Money(20000),
        payment_date=date.today(),
    )

    # Customer receivables: ₹20,000
    cust = Customer(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Reliable Traders",
        current_balance=Money(20000),
    )

    # Supplier payables: ₹25,000
    sup = Supplier(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Steel Mill Supply",
        current_balance=Money(25000),
    )

    # Inventory: ₹30,000
    bal = InventoryBalance(
        id=uuid.uuid4(),
        business_id=biz_id,
        product_id=uuid.uuid4(),
        quantity_on_hand=Decimal("100"),
        unit_cost=Money(300),
        total_valuation=Money(30000),
    )

    engine = FinancialIntelligenceEngine(
        invoice_repo=MockSalesInvoiceRepository([]),
        purchase_repo=MockPurchaseRepository([]),
        customer_repo=MockCustomerRepository([cust]),
        supplier_repo=MockSupplierRepository([sup]),
        inventory_repo=MockInventoryRepository([bal]),
        payment_repo=MockPaymentRepository([p1, p2]),
        income_expense_repo=MockIncomeExpenseRepository([], []),
    )

    wc = engine.calculate_working_capital(biz_id, date.today())

    # Current Assets = Cash (30k) + Receivables (20k) + Inventory (30k) = ₹80,000
    assert wc.total_current_assets == Money(80000)
    # Current Liabilities = Payables (25k) = ₹25,000
    assert wc.total_current_liabilities == Money(25000)
    # Net Working Capital = 80k - 25k = ₹55,000
    assert wc.net_working_capital == Money(55000)
    # Current Ratio = 80000 / 25000 = 3.20
    assert wc.current_ratio == 3.20
    # Quick Ratio = (30k + 20k) / 25000 = 2.00
    assert wc.quick_ratio == 2.00


def test_break_even_and_margin_of_safety():
    """Verifies break-even revenue calculation and margin of safety percentage."""
    biz_id = uuid.uuid4()
    prod_id = uuid.uuid4()

    # Unit cost = ₹200
    bal = InventoryBalance(
        id=uuid.uuid4(),
        business_id=biz_id,
        product_id=prod_id,
        quantity_on_hand=Decimal("100"),
        unit_cost=Money(200),
        total_valuation=Money(20000),
    )

    # Invoice: 50 units @ ₹400 = ₹20,000 revenue
    inv = SalesInvoice(
        id=uuid.uuid4(),
        business_id=biz_id,
        customer_id=uuid.uuid4(),
        invoice_number="INV-BE-01",
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 15),
        subtotal=Money(20000),
        total_amount=Money(20000),
        status=InvoiceStatus.PAID,
        items=[
            SalesInvoiceItem(
                id=uuid.uuid4(),
                invoice_id=uuid.uuid4(),
                product_id=prod_id,
                description="Product A",
                quantity=Decimal("50"),
                unit="pcs",
                unit_price=Money(400),
                total_price=Money(20000),
            )
        ],
    )

    # Fixed costs: ₹5,000 operating expense
    exp = ExpenseRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category=ExpenseCategory.ADMINISTRATIVE,
        amount=Money(5000),
        date=date(2026, 11, 2),
    )

    engine = FinancialIntelligenceEngine(
        invoice_repo=MockSalesInvoiceRepository([inv]),
        purchase_repo=MockPurchaseRepository([]),
        customer_repo=MockCustomerRepository([]),
        supplier_repo=MockSupplierRepository([]),
        inventory_repo=MockInventoryRepository([bal]),
        payment_repo=MockPaymentRepository([]),
        income_expense_repo=MockIncomeExpenseRepository([], [exp]),
        journal_repo=MockJournalRepository([
            type("Line", (), {"account_code": StandardAccount.SALES_REVENUE.value, "debit": Money.zero(), "credit": Money(20000)})(),
            type("Line", (), {"account_code": StandardAccount.COGS.value, "debit": Money(10000), "credit": Money.zero()})(),
            type("Line", (), {"account_code": StandardAccount.OPERATING_EXPENSES.value, "debit": Money(5000), "credit": Money.zero()})(),
        ], reference_id=inv.id),
    )

    be = engine.calculate_break_even(biz_id, date(2026, 11, 1), date(2026, 11, 30))

    # Revenue = 20,000
    # Variable cost (COGS) = 50 * 200 = 10,000
    # Contribution Margin = 20,000 - 10,000 = 10,000
    # CM Ratio = 10,000 / 20,000 = 0.50 (50%)
    assert be.contribution_margin == Money(10000)
    assert be.contribution_margin_ratio == 0.50

    # Fixed Costs = 5,000
    # Break-even Revenue = Fixed Costs / CM Ratio = 5,000 / 0.50 = ₹10,000
    assert be.break_even_revenue == Money(10000)
    # Margin of Safety % = (20,000 - 10,000) / 20,000 * 100 = 50.00%
    assert be.margin_of_safety_percent == 50.0
    assert be.is_profitable is True


def test_business_health_score_evaluation():
    """Verifies composite 0-100 business health score, grading, and strength/risk identification."""
    biz_id = uuid.uuid4()

    # Liquid funds: ₹100,000
    p = Payment(
        id=uuid.uuid4(),
        business_id=biz_id,
        party_type=Customer,
        party_id=None,
        reference_type="INVOICE",
        reference_id=None,
        payment_type=PaymentType.RECEIVED,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=Money(100000),
        payment_date=date.today(),
    )

    # Customer receivables: ₹40,000 with 0 overdue
    cust = Customer(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Prompt Customer",
        current_balance=Money(40000),
    )

    # Supplier payables: ₹20,000
    sup = Supplier(
        id=uuid.uuid4(),
        business_id=biz_id,
        name="Direct Supplier",
        current_balance=Money(20000),
    )

    # Sales invoice: ₹60,000 revenue
    inv = SalesInvoice(
        id=uuid.uuid4(),
        business_id=biz_id,
        customer_id=cust.id,
        invoice_number="INV-HS-01",
        invoice_date=date.today() - timedelta(days=10),
        due_date=date.today() + timedelta(days=20),
        subtotal=Money(60000),
        total_amount=Money(60000),
        status=InvoiceStatus.PAID,
    )

    # OpEx: ₹10,000
    exp = ExpenseRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category=ExpenseCategory.OPERATING,
        amount=Money(10000),
        date=date.today() - timedelta(days=5),
    )

    engine = FinancialIntelligenceEngine(
        invoice_repo=MockSalesInvoiceRepository([inv]),
        purchase_repo=MockPurchaseRepository([]),
        customer_repo=MockCustomerRepository([cust]),
        supplier_repo=MockSupplierRepository([sup]),
        inventory_repo=MockInventoryRepository([]),
        payment_repo=MockPaymentRepository([p]),
        income_expense_repo=MockIncomeExpenseRepository([], [exp]),
    )

    score = engine.compute_health_score(biz_id, date.today())

    # High liquidity, profitable, low debt, pristine collections, generous cash runway
    assert score.overall_score >= 80
    assert score.grade == "EXCELLENT"
    assert len(score.key_strengths) > 0
    assert score.cash_runway_months >= 6.0


def test_compute_health_score_new_workspace_returns_zero():
    biz_id = uuid.uuid4()
    engine = FinancialIntelligenceEngine(
        invoice_repo=MockSalesInvoiceRepository([]),
        purchase_repo=MockPurchaseRepository([]),
        customer_repo=MockCustomerRepository([]),
        supplier_repo=MockSupplierRepository([]),
        inventory_repo=MockInventoryRepository([]),
        payment_repo=MockPaymentRepository([]),
        income_expense_repo=MockIncomeExpenseRepository([], []),
        journal_repo=MockJournalRepository([]),
    )
    score = engine.compute_health_score(biz_id, date.today())
    assert score.overall_score == 0
    assert score.grade == "NEEDS_ATTENTION"
    assert score.cash_runway_months == 0.0
    assert score.liquidity_score == 0
    assert score.profitability_score == 0
    assert score.solvency_score == 0
    assert score.efficiency_score == 0
    assert score.cash_runway_score == 0
    assert len(score.key_strengths) == 0
    assert len(score.identified_risks) > 0

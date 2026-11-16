"""
Unit tests for ArthLens Business Operating System Domain Models & Value Objects.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest

from backend.arthlens.domain.business import (
    Business,
    BusinessRole,
    Customer,
    DateRange,
    ExpenseCategory,
    ExpenseRecord,
    Goal,
    GoalStatus,
    GoalType,
    IncomeRecord,
    InventoryBalance,
    InvoiceStatus,
    Money,
    Percentage,
    Product,
    Purchase,
    PurchaseItem,
    PurchaseStatus,
    SalesInvoice,
    SalesInvoiceItem,
    Supplier,
)


def test_money_arithmetic_and_rounding():
    m1 = Money(Decimal("100.50"))
    m2 = Money(Decimal("50.25"))

    # Addition
    assert (m1 + m2).amount == Decimal("150.75")
    # Subtraction
    assert (m1 - m2).amount == Decimal("50.25")
    # Multiplication
    assert (m1 * 2).amount == Decimal("201.00")
    # Division
    assert (m1 / 2).amount == Decimal("50.25")
    # Indian formatting
    m3 = Money(Decimal("1234567.89"))
    assert m3.format_inr() == "₹12,34,567.89"
    # Zero division error
    with pytest.raises(ZeroDivisionError):
        _ = m1 / 0


def test_percentage_calculation():
    pct = Percentage(Decimal("18.00"))  # 18% GST
    base = Money(Decimal("1000.00"))
    tax = pct.apply_to(base)
    assert tax.amount == Decimal("180.00")


def test_date_range_validation():
    d1 = date(2026, 4, 1)
    d2 = date(2027, 3, 31)
    dr = DateRange(d1, d2)
    assert dr.duration_days == 365
    assert dr.contains(date(2026, 6, 15)) is True
    assert dr.contains(date(2027, 5, 1)) is False

    with pytest.raises(ValueError):
        DateRange(d2, d1)


def test_customer_receivable_lifecycle():
    cid = uuid.uuid4()
    bid = uuid.uuid4()
    cust = Customer(
        id=cid,
        business_id=bid,
        name="Shree Ram Enterprises",
        credit_limit=Money(Decimal("50000.00")),
    )
    assert cust.current_balance == Money.zero()

    # Credit sale of 15,000
    cust.add_receivable(Money(Decimal("15000.00")))
    assert cust.current_balance == Money(Decimal("15000.00"))

    # Partial payment of 6,000
    cust.apply_payment(Money(Decimal("6000.00")))
    assert cust.current_balance == Money(Decimal("9000.00"))


def test_inventory_addition_and_weighted_average_cost():
    pid = uuid.uuid4()
    bid = uuid.uuid4()
    inv = InventoryBalance(
        id=uuid.uuid4(),
        business_id=bid,
        product_id=pid,
        quantity_on_hand=Decimal("0.00"),
        unit_cost=Money.zero(),
        total_valuation=Money.zero(),
    )

    # 1st batch: 100 units at 50/unit = 5,000
    inv.apply_addition(Decimal("100"), Money(Decimal("50.00")))
    assert inv.quantity_on_hand == Decimal("100")
    assert inv.total_valuation == Money(Decimal("5000.00"))
    assert inv.unit_cost == Money(Decimal("50.00"))

    # 2nd batch: 100 units at 70/unit = 7,000 -> total 12,000 / 200 units = 60/unit
    inv.apply_addition(Decimal("100"), Money(Decimal("70.00")))
    assert inv.quantity_on_hand == Decimal("200")
    assert inv.total_valuation == Money(Decimal("12000.00"))
    assert inv.unit_cost == Money(Decimal("60.00"))

    # Sale deduction: 50 units
    inv.apply_deduction(Decimal("50"))
    assert inv.quantity_on_hand == Decimal("150")
    assert inv.total_valuation == Money(Decimal("9000.00"))

    # Oversell deduction error without allow_negative
    with pytest.raises(ValueError):
        inv.apply_deduction(Decimal("200"))


def test_sales_invoice_calculation_and_payment():
    iid = uuid.uuid4()
    bid = uuid.uuid4()
    item1 = SalesInvoiceItem(
        id=uuid.uuid4(),
        invoice_id=iid,
        product_id=uuid.uuid4(),
        description="Premium Flour 25kg",
        quantity=Decimal("10"),
        unit="bag",
        unit_price=Money(Decimal("800.00")),
        discount_percent=Decimal("5.00"),  # 5% discount
    )
    item_total = item1.calculate_total()
    assert item_total == Money(Decimal("7600.00"))

    invoice = SalesInvoice(
        id=iid,
        business_id=bid,
        customer_id=uuid.uuid4(),
        invoice_number="INV-2026-001",
        invoice_date=date(2026, 11, 15),
        due_date=date(2026, 11, 30),
        subtotal=item_total,
        tax_amount=Money(Decimal("380.00")),  # 5% GST
        total_amount=Money(Decimal("7980.00")),
        items=[item1],
    )
    assert invoice.outstanding_balance == Money(Decimal("7980.00"))
    assert invoice.status == InvoiceStatus.DRAFT

    # Partial payment
    invoice.record_payment(Money(Decimal("3000.00")))
    assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    assert invoice.outstanding_balance == Money(Decimal("4980.00"))

    # Full payment
    invoice.record_payment(Money(Decimal("4980.00")))
    assert invoice.status == InvoiceStatus.PAID
    assert invoice.outstanding_balance == Money.zero()


def test_goal_progress():
    goal = Goal(
        id=uuid.uuid4(),
        business_id=uuid.uuid4(),
        goal_type=GoalType.REVENUE,
        title="Q3 Revenue Target",
        target_value=Decimal("1000000.00"),
        current_value=Decimal("450000.00"),
    )
    assert goal.progress_percent == Decimal("45.00")

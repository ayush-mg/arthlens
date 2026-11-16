"""
Integration tests for Business Operating System Repositories against PostgreSQL.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest

from backend.arthlens.domain.business import (
    Business,
    BusinessRole,
    Customer,
    DecisionEvaluation,
    DecisionOutcome,
    ExpenseCategory,
    ExpenseRecord,
    Goal,
    GoalStatus,
    GoalType,
    IncomeRecord,
    InventoryBalance,
    InventoryMovement,
    InvoiceStatus,
    Money,
    MovementType,
    PartyType,
    Payment,
    PaymentMethod,
    PaymentType,
    Product,
    Purchase,
    PurchaseItem,
    PurchaseStatus,
    SalesInvoice,
    SalesInvoiceItem,
    Supplier,
)
from backend.arthlens.infra.business_repositories import (
    PostgresBusinessRepository,
    PostgresCustomerRepository,
    PostgresDecisionEvaluationRepository,
    PostgresGoalRepository,
    PostgresIncomeExpenseRepository,
    PostgresInventoryRepository,
    PostgresPaymentRepository,
    PostgresProductRepository,
    PostgresPurchaseRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password


@pytest.fixture
def test_user():
    user_repo = PostgresUserRepository()
    unique_email = f"owner.{uuid.uuid4().hex[:8]}@arthlens.test"
    user_id = user_repo.save({
        "email": unique_email,
        "password_hash": hash_password("TestPassword123!"),
        "roles": ["ENTREPRENEUR"],
    })
    return uuid.UUID(user_id)


def test_business_and_membership_lifecycle(test_user):
    repo = PostgresBusinessRepository()
    biz_id = uuid.uuid4()
    biz = Business(
        id=biz_id,
        owner_id=test_user,
        name="Varanasi Silk Weavers Ltd",
        industry="Textiles & Handloom",
        address="Dashashwamedh Ghat Road, Varanasi",
    )
    created = repo.create(biz)
    assert created.id == biz_id

    # Retrieve by ID
    fetched = repo.get_by_id(biz_id)
    assert fetched is not None
    assert fetched.name == "Varanasi Silk Weavers Ltd"
    assert fetched.industry == "Textiles & Handloom"

    # List by user
    user_bizs = repo.list_by_user(test_user)
    assert any(b.id == biz_id for b in user_bizs)

    # Membership check
    membership = repo.get_membership(biz_id, test_user)
    assert membership is not None
    assert membership.role == BusinessRole.OWNER


def test_customer_supplier_and_khata_persistence(test_user):
    biz_repo = PostgresBusinessRepository()
    biz_id = uuid.uuid4()
    biz_repo.create(Business(id=biz_id, owner_id=test_user, name="Agro Mills", industry="Food Processing"))

    cust_repo = PostgresCustomerRepository()
    cid = uuid.uuid4()
    cust = Customer(
        id=cid,
        business_id=biz_id,
        name="Ganga Retail Mart",
        phone="9876543210",
        credit_limit=Money(Decimal("100000.00")),
        current_balance=Money(Decimal("25000.00")),
    )
    cust_repo.create(cust)

    fetched_cust = cust_repo.get_by_id(cid)
    assert fetched_cust is not None
    assert fetched_cust.name == "Ganga Retail Mart"
    assert fetched_cust.current_balance == Money(Decimal("25000.00"))

    # Update balance
    cust_repo.update_balance(cid, Money(Decimal("15000.00")))
    updated_cust = cust_repo.get_by_id(cid)
    assert updated_cust.current_balance == Money(Decimal("15000.00"))

    # Supplier
    supp_repo = PostgresSupplierRepository()
    sid = uuid.uuid4()
    supp = Supplier(
        id=sid,
        business_id=biz_id,
        name="Bhopal Grain Depot",
        phone="9123456780",
        current_balance=Money(Decimal("45000.00")),
    )
    supp_repo.create(supp)
    fetched_supp = supp_repo.get_by_id(sid)
    assert fetched_supp is not None
    assert fetched_supp.name == "Bhopal Grain Depot"
    assert fetched_supp.current_balance == Money(Decimal("45000.00"))


def test_product_and_inventory_stock_movements(test_user):
    biz_repo = PostgresBusinessRepository()
    biz_id = uuid.uuid4()
    biz_repo.create(Business(id=biz_id, owner_id=test_user, name="Spice Processing Unit", industry="Food Processing"))

    prod_repo = PostgresProductRepository()
    pid = uuid.uuid4()
    prod = Product(
        id=pid,
        business_id=biz_id,
        sku="SPICE-CHILLI-001",
        name="Organic Red Chilli Powder 1kg",
        category="Spices",
        unit="kg",
        purchase_price=Money(Decimal("180.00")),
        selling_price=Money(Decimal("260.00")),
        min_stock_alert=Decimal("50.00"),
    )
    prod_repo.create(prod)

    fetched_prod = prod_repo.get_by_id(pid)
    assert fetched_prod is not None
    assert fetched_prod.sku == "SPICE-CHILLI-001"

    inv_repo = PostgresInventoryRepository()
    bal = InventoryBalance(
        id=uuid.uuid4(),
        business_id=biz_id,
        product_id=pid,
        quantity_on_hand=Decimal("200.00"),
        unit_cost=Money(Decimal("180.00")),
        total_valuation=Money(Decimal("36000.00")),
    )
    inv_repo.save_balance(bal)

    fetched_bal = inv_repo.get_balance(biz_id, pid)
    assert fetched_bal is not None
    assert fetched_bal.quantity_on_hand == Decimal("200.0000")
    assert fetched_bal.total_valuation == Money(Decimal("36000.00"))

    # Movement audit
    mvt = InventoryMovement(
        id=uuid.uuid4(),
        business_id=biz_id,
        product_id=pid,
        movement_type=MovementType.OPENING,
        quantity=Decimal("200.00"),
        unit_price=Money(Decimal("180.00")),
        reference_id="BATCH-001",
        reason="Initial opening inventory",
        balance_after=Decimal("200.00"),
    )
    inv_repo.record_movement(mvt)

    mvts = inv_repo.list_movements(biz_id, pid)
    assert len(mvts) == 1
    assert mvts[0].movement_type == MovementType.OPENING


def test_sales_invoice_and_payment_flow(test_user):
    biz_repo = PostgresBusinessRepository()
    biz_id = uuid.uuid4()
    biz_repo.create(Business(id=biz_id, owner_id=test_user, name="Modern Bakery", industry="Food & Beverage"))

    cust_repo = PostgresCustomerRepository()
    cid = uuid.uuid4()
    cust_repo.create(Customer(id=cid, business_id=biz_id, name="City Cafe"))

    inv_repo = PostgresSalesInvoiceRepository()
    iid = uuid.uuid4()
    item = SalesInvoiceItem(
        id=uuid.uuid4(),
        invoice_id=iid,
        product_id=None,
        description="Daily Bread Delivery",
        quantity=Decimal("100"),
        unit="loaves",
        unit_price=Money(Decimal("35.00")),
        total_price=Money(Decimal("3500.00")),
    )
    invoice = SalesInvoice(
        id=iid,
        business_id=biz_id,
        customer_id=cid,
        invoice_number="INV-BAKE-001",
        invoice_date=date(2026, 11, 1),
        due_date=date(2026, 11, 15),
        subtotal=Money(Decimal("3500.00")),
        tax_amount=Money(Decimal("175.00")),
        total_amount=Money(Decimal("3675.00")),
        paid_amount=Money.zero(),
        status=InvoiceStatus.ISSUED,
        items=[item],
    )
    inv_repo.create(invoice)

    fetched_inv = inv_repo.get_by_id(iid)
    assert fetched_inv is not None
    assert fetched_inv.invoice_number == "INV-BAKE-001"
    assert len(fetched_inv.items) == 1
    assert fetched_inv.items[0].description == "Daily Bread Delivery"

    # Payment recording
    pay_repo = PostgresPaymentRepository()
    pid = uuid.uuid4()
    pay = Payment(
        id=pid,
        business_id=biz_id,
        party_type=PartyType.CUSTOMER,
        party_id=cid,
        reference_type="INVOICE",
        reference_id=iid,
        payment_type=PaymentType.RECEIVED,
        payment_method=PaymentMethod.UPI,
        amount=Money(Decimal("2000.00")),
        payment_date=date(2026, 11, 5),
        notes="Advance partial payment via UPI",
    )
    pay_repo.create(pay)

    payments = pay_repo.list_by_business(biz_id, cid)
    assert len(payments) == 1
    assert payments[0].amount == Money(Decimal("2000.00"))

    inv_repo.update_payment(iid, Money(Decimal("2000.00")), InvoiceStatus.PARTIALLY_PAID)
    updated_inv = inv_repo.get_by_id(iid)
    assert updated_inv.paid_amount == Money(Decimal("2000.00"))
    assert updated_inv.status == InvoiceStatus.PARTIALLY_PAID


def test_income_expenses_and_goals(test_user):
    biz_repo = PostgresBusinessRepository()
    biz_id = uuid.uuid4()
    biz_repo.create(Business(id=biz_id, owner_id=test_user, name="Solar Tech Solutions", industry="Energy"))

    ie_repo = PostgresIncomeExpenseRepository()
    # Income
    inc = IncomeRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category="Consulting Services",
        amount=Money(Decimal("75000.00")),
        date=date(2026, 11, 10),
        description="Rooftop solar design consultation",
    )
    ie_repo.create_income(inc)
    income_list = ie_repo.list_income(biz_id)
    assert len(income_list) == 1
    assert income_list[0].amount == Money(Decimal("75000.00"))

    # Expense
    exp = ExpenseRecord(
        id=uuid.uuid4(),
        business_id=biz_id,
        category=ExpenseCategory.UTILITIES,
        amount=Money(Decimal("12500.00")),
        date=date(2026, 11, 8),
        description="Office electricity bill",
    )
    ie_repo.create_expense(exp)
    expense_list = ie_repo.list_expenses(biz_id)
    assert len(expense_list) == 1
    assert expense_list[0].amount == Money(Decimal("12500.00"))

    # Goals
    goal_repo = PostgresGoalRepository()
    gid = uuid.uuid4()
    goal = Goal(
        id=gid,
        business_id=biz_id,
        goal_type=GoalType.PROFIT,
        title="Annual Net Profit Target",
        target_value=Decimal("500000.00"),
        current_value=Decimal("120000.00"),
        start_date=date(2026, 4, 1),
        target_date=date(2027, 3, 31),
    )
    goal_repo.create(goal)
    goals = goal_repo.list_by_business(biz_id)
    assert len(goals) == 1
    assert goals[0].title == "Annual Net Profit Target"
    assert goals[0].progress_percent == Decimal("24.00")

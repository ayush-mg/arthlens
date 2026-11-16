"""
Integration Tests for Transaction Integrity, Concurrency, Row Locks, and Idempotency (Mandate 5).

Validates:
1. Cross-business line-item validation fails with InvalidOperationError (cannot invoice another business's product).
2. Cross-business customer validation fails with InvalidOperationError (cannot invoice another business's customer).
3. Cross-business supplier validation fails with InvalidOperationError (cannot purchase from another business's supplier).
4. Payment idempotency key prevents duplicate payments (second call returns existing payment record).
5. Atomic invoice cancellation rolls back inventory quantity and customer balance in a single transaction.
6. Row-level locks (with_for_update) prevent overselling under concurrent deductions.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest

from backend.arthlens.domain.business import (
    Business,
    Customer,
    InventoryBalance,
    InvoiceStatus,
    Money,
    PaymentMethod,
    Product,
    Supplier,
)
from backend.arthlens.infra.business_repositories import (
    PostgresBusinessRepository,
    PostgresCustomerRepository,
    PostgresInventoryRepository,
    PostgresPaymentRepository,
    PostgresProductRepository,
    PostgresPurchaseRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.services.business_service import (
    BusinessService,
    FinancialPeriodClosedError,
    IdempotencyConflictError,
    InsufficientInventoryError,
    InvalidOperationError,
)


@pytest.fixture
def two_tenants():
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    cust_repo = PostgresCustomerRepository()
    sup_repo = PostgresSupplierRepository()
    prod_repo = PostgresProductRepository()
    inv_repo = PostgresInventoryRepository()

    # Business A
    u_a = user_repo.save({
        "email": f"concur_a_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    biz_a = Business(
        id=uuid.uuid4(),
        owner_id=u_a,
        name="Concur Biz A",
        industry="Retail",
        address="Noida, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz_a)

    cust_a = Customer(
        id=uuid.uuid4(),
        business_id=biz_a.id,
        name="Customer A",
        phone="9811100001",
        credit_limit=Money.from_float(100000.0),
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    cust_repo.create(cust_a)

    prod_a = Product(
        id=uuid.uuid4(),
        business_id=biz_a.id,
        sku=f"SKU-A-{uuid.uuid4().hex[:4]}",
        name="Product A",
        category="General",
        unit="pcs",
        selling_price=Money.from_float(100.0),
        purchase_price=Money.from_float(60.0),
    )
    prod_repo.create(prod_a)

    # Seed 50 units in stock for Product A
    inv_repo.save_balance(InventoryBalance(
        id=uuid.uuid4(),
        business_id=biz_a.id,
        product_id=prod_a.id,
        quantity_on_hand=Decimal("50.0"),
        unit_cost=Money.from_float(60.0),
        total_valuation=Money.from_float(3000.0),
    ))

    # Business B
    u_b = user_repo.save({
        "email": f"concur_b_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    biz_b = Business(
        id=uuid.uuid4(),
        owner_id=u_b,
        name="Concur Biz B",
        industry="Wholesale",
        address="Ghaziabad, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz_b)

    cust_b = Customer(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        name="Customer B",
        phone="9811100002",
        credit_limit=Money.from_float(100000.0),
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    cust_repo.create(cust_b)

    sup_b = Supplier(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        name="Supplier B",
        contact_person="Vendor B",
        phone="9811100003",
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    sup_repo.create(sup_b)

    prod_b = Product(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        sku=f"SKU-B-{uuid.uuid4().hex[:4]}",
        name="Product B",
        category="General",
        unit="pcs",
        selling_price=Money.from_float(200.0),
        purchase_price=Money.from_float(120.0),
    )
    prod_repo.create(prod_b)

    return {
        "biz_a": biz_a, "cust_a": cust_a, "prod_a": prod_a,
        "biz_b": biz_b, "cust_b": cust_b, "sup_b": sup_b, "prod_b": prod_b,
        "u_a": u_a, "u_b": u_b,
    }


def test_cross_business_line_item_validation(two_tenants):
    """Verifies that an invoice cannot reference a product belonging to another business."""
    svc = BusinessService()
    t = two_tenants

    # Business A attempts to create invoice with Business B's product
    with pytest.raises(InvalidOperationError) as exc_info:
        svc.create_sales_invoice(
            business_id=t["biz_a"].id,
            user_id=t["u_a"],
            customer_id=t["cust_a"].id,
            invoice_number="INV-A-CROSS-PROD",
            invoice_date=date.today(),
            due_date=date.today(),
            items=[{"product_id": t["prod_b"].id, "description": "Foreign Item", "quantity": 5.0, "unit_price": 200.0}],
        )
    assert "does not belong to authorized business" in str(exc_info.value)


def test_cross_business_customer_validation(two_tenants):
    """Verifies that an invoice cannot be billed to another business's customer."""
    svc = BusinessService()
    t = two_tenants

    with pytest.raises(InvalidOperationError) as exc_info:
        svc.create_sales_invoice(
            business_id=t["biz_a"].id,
            user_id=t["u_a"],
            customer_id=t["cust_b"].id,  # Customer B belongs to Biz B
            invoice_number="INV-A-CROSS-CUST",
            invoice_date=date.today(),
            due_date=date.today(),
            items=[{"product_id": t["prod_a"].id, "description": "Valid Item", "quantity": 2.0, "unit_price": 100.0}],
        )
    assert "does not belong to authorized business" in str(exc_info.value)


def test_cross_business_supplier_validation(two_tenants):
    """Verifies that a purchase cannot be recorded against another business's supplier."""
    svc = BusinessService()
    t = two_tenants

    with pytest.raises(InvalidOperationError) as exc_info:
        svc.create_purchase(
            business_id=t["biz_a"].id,
            user_id=t["u_a"],
            supplier_id=t["sup_b"].id,  # Supplier B belongs to Biz B
            bill_number="BILL-CROSS-SUP",
            purchase_date=date.today(),
            due_date=date.today(),
            items=[{"product_id": t["prod_a"].id, "description": "Raw Material", "quantity": 10.0, "unit_price": 60.0}],
        )
    assert "does not belong to authorized business" in str(exc_info.value)


def test_payment_idempotency_key_prevents_duplicate_payments(two_tenants):
    """Verifies that duplicate payment requests with the same idempotency_key return existing payment."""
    svc = BusinessService()
    t = two_tenants

    inv = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 10.0, "unit_price": 100.0}],
    )

    idem_key = f"pay_idem_{uuid.uuid4().hex}"

    # First payment attempt
    p1 = svc.record_invoice_payment(
        business_id=t["biz_a"].id,
        invoice_id=inv.id,
        user_id=t["u_a"],
        amount=500.0,
        payment_date=date.today(),
        payment_method=PaymentMethod.UPI,
        idempotency_key=idem_key,
    )
    assert p1.paid_amount == Money.from_float(500.0)

    # Second payment attempt with exact same idempotency key
    p2 = svc.record_invoice_payment(
        business_id=t["biz_a"].id,
        invoice_id=inv.id,
        user_id=t["u_a"],
        amount=500.0,
        payment_date=date.today(),
        payment_method=PaymentMethod.UPI,
        idempotency_key=idem_key,
    )

    # Must return the existing payment without deducting customer balance again
    assert p2.paid_amount == Money.from_float(500.0)

    # Verify customer balance only reflects one payment of 500
    cust = PostgresCustomerRepository().get_by_id(t["cust_a"].id)
    # Total invoice = 1000, paid = 500, balance = 500
    assert cust.current_balance == Money.from_float(500.0)


def test_atomic_invoice_cancellation_rolls_back_stock_and_ledger(two_tenants):
    """Verifies that cancelling an invoice atomically restores stock and reverses customer ledger."""
    svc = BusinessService()
    inv_repo = PostgresInventoryRepository()
    cust_repo = PostgresCustomerRepository()
    t = two_tenants

    # Stock before = 50.0
    bal_before = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id)
    assert bal_before.quantity_on_hand == Decimal("50.0")
    valuation_before = bal_before.total_valuation

    # Create invoice for 15 units (deducts 15, stock becomes 35, customer balance becomes 1500)
    inv = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 15.0, "unit_price": 100.0}],
    )

    bal_after_inv = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id)
    assert bal_after_inv.quantity_on_hand == Decimal("35.0")
    cust_after_inv = cust_repo.get_by_id(t["cust_a"].id)
    assert cust_after_inv.current_balance == Money.from_float(1500.0)

    # Cancel invoice
    cancelled_inv = svc.cancel_sales_invoice(
        business_id=t["biz_a"].id,
        invoice_id=inv.id,
        user_id=t["u_a"],
        reason="Customer cancellation request",
    )
    assert cancelled_inv.status.value == "CANCELLED"

    # Inventory must be atomically restored to 50.0
    bal_after_cancel = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id)
    assert bal_after_cancel.quantity_on_hand == Decimal("50.0")
    assert bal_after_cancel.total_valuation == valuation_before
    cancel_movements = [
        movement for movement in inv_repo.list_movements(t["biz_a"].id, t["prod_a"].id)
        if movement.reference_id == str(inv.id)
    ]
    assert all(movement.cost_basis == Money(60) for movement in cancel_movements)

    invoice_journals = [
        entry for entry in svc.journal_repo.list_by_business(t["biz_a"].id)
        if entry.reference_id == inv.id
    ]
    cogs_debits = sum(
        line.debit.amount for entry in invoice_journals for line in entry.lines
        if line.account_code == "5010"
    )
    cogs_credits = sum(
        line.credit.amount for entry in invoice_journals for line in entry.lines
        if line.account_code == "5010"
    )
    assert cogs_debits == cogs_credits
    pnl = FinancialIntelligenceEngine().calculate_pnl(t["biz_a"].id, date.today(), date.today())
    assert pnl.gross_sales == Money.zero()
    assert pnl.cost_of_goods_sold == Money.zero()

    # Customer balance must be reversed back to 0.0
    cust_after_cancel = cust_repo.get_by_id(t["cust_a"].id)
    assert cust_after_cancel.current_balance == Money.zero()


def test_paid_invoice_cannot_be_cancelled(two_tenants):
    svc = BusinessService()
    t = two_tenants
    invoice = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-PAID-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 2.0, "unit_price": 100.0}],
    )
    svc.record_invoice_payment(
        business_id=t["biz_a"].id,
        invoice_id=invoice.id,
        user_id=t["u_a"],
        amount=50.0,
        payment_date=date.today(),
        payment_method=PaymentMethod.UPI,
    )

    with pytest.raises(InvalidOperationError, match="paid or partially paid"):
        svc.cancel_sales_invoice(t["biz_a"].id, invoice.id, t["u_a"], "Customer paid part of invoice")


def test_cancelled_invoice_rejects_payment(two_tenants):
    svc = BusinessService()
    t = two_tenants
    invoice = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-CANCEL-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 2.0, "unit_price": 100.0}],
    )
    svc.cancel_sales_invoice(t["biz_a"].id, invoice.id, t["u_a"], "Entered in error")

    with pytest.raises(InvalidOperationError, match="cancelled invoice"):
        svc.record_invoice_payment(
            business_id=t["biz_a"].id,
            invoice_id=invoice.id,
            user_id=t["u_a"],
            amount=50.0,
            payment_date=date.today(),
            payment_method=PaymentMethod.UPI,
        )

def test_conflicting_idempotency_key_raises_conflict(two_tenants):
    """
    Mandate 5 & Item 10: Reusing an idempotency key with differing parameters
    must raise IdempotencyConflictError rather than silently returning wrong data.
    """
    svc = BusinessService()
    t = two_tenants

    # Invoice 1
    inv1 = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 5.0, "unit_price": 100.0}],
    )

    # Invoice 2
    inv2 = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 5.0, "unit_price": 100.0}],
    )

    idem_key = f"pay_shared_key_{uuid.uuid4().hex}"

    # Payment against Invoice 1 with 300
    svc.record_invoice_payment(
        business_id=t["biz_a"].id,
        invoice_id=inv1.id,
        user_id=t["u_a"],
        amount=300.0,
        payment_date=date.today(),
        payment_method=PaymentMethod.CASH,
        idempotency_key=idem_key,
    )

    # Attempt reuse of same idempotency key for Invoice 2 (conflict)
    with pytest.raises(IdempotencyConflictError) as exc_info:
        svc.record_invoice_payment(
            business_id=t["biz_a"].id,
            invoice_id=inv2.id,
            user_id=t["u_a"],
            amount=300.0,
            payment_date=date.today(),
            payment_method=PaymentMethod.CASH,
            idempotency_key=idem_key,
        )
    assert "conflicting parameters" in str(exc_info.value) or "conflict" in str(exc_info.value).lower()

    # Attempt reuse on Invoice 1 but with different amount 200 (conflict)
    with pytest.raises(IdempotencyConflictError):
        svc.record_invoice_payment(
            business_id=t["biz_a"].id,
            invoice_id=inv1.id,
            user_id=t["u_a"],
            amount=200.0,
            payment_date=date.today(),
            payment_method=PaymentMethod.CASH,
            idempotency_key=idem_key,
        )


def test_hard_closed_period_prevents_backdated_tampering(two_tenants):
    """
    Item 29: An accounting period in HARD_CLOSED status prevents
    backdated invoices, payments, or ledger postings.
    """
    from datetime import timedelta
    from backend.arthlens.domain.business import FinancialPeriodStatus
    svc = BusinessService()
    t = two_tenants

    last_month_start = date.today() - timedelta(days=60)
    last_month_end = date.today() - timedelta(days=31)

    # Create and close past period
    period = svc.create_financial_period(
        business_id=t["biz_a"].id,
        period_name="Locked Past Quarter",
        start_date=last_month_start,
        end_date=last_month_end,
        user_id=t["u_a"],
    )
    svc.close_financial_period(
        business_id=t["biz_a"].id,
        period_id=period.id,
        status=FinancialPeriodStatus.HARD_CLOSED,
        user_id=t["u_a"],
    )

    # Attempt backdated invoice into closed period
    with pytest.raises(FinancialPeriodClosedError) as exc_info:
        svc.create_sales_invoice(
            business_id=t["biz_a"].id,
            user_id=t["u_a"],
            customer_id=t["cust_a"].id,
            invoice_number=f"INV-BACK-{uuid.uuid4().hex[:4]}",
            invoice_date=last_month_start + timedelta(days=5),
            due_date=last_month_start + timedelta(days=10),
            items=[{"product_id": t["prod_a"].id, "description": "Backdated Item", "quantity": 1.0, "unit_price": 100.0}],
        )
    assert "locked/closed" in str(exc_info.value)


def test_general_ledger_trial_balance_is_balanced(two_tenants):
    """
    Item 28: Verifies that general ledger maintains balanced debits and credits across all events.
    """
    svc = BusinessService()
    t = two_tenants

    # Create invoice for 2000
    inv = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-TB-{uuid.uuid4().hex[:4]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 20.0, "unit_price": 100.0}],
    )

    # Record partial payment of 800
    svc.record_invoice_payment(
        business_id=t["biz_a"].id,
        invoice_id=inv.id,
        user_id=t["u_a"],
        amount=800.0,
        payment_date=date.today(),
        payment_method=PaymentMethod.BANK_TRANSFER,
    )

    # Record miscellaneous income of 500
    svc.create_income(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        category="Consulting",
        amount=500.0,
        record_date=date.today(),
        description="Design consultancy fee",
    )

    # Verify trial balance is balanced
    tb = svc.get_trial_balance(t["biz_a"].id, t["u_a"])
    assert tb["is_balanced"] is True
    assert tb["total_debits"] > 0
    assert abs(tb["total_debits"] - tb["total_credits"]) < 0.01


def test_sales_return_restores_stock_and_adjusts_khata(two_tenants):
    """
    Item 23: Sales return restores physical stock and adjusts customer balance.
    """
    svc = BusinessService()
    t = two_tenants
    inv_repo = PostgresInventoryRepository()
    cust_repo = PostgresCustomerRepository()

    # Create invoice for 10 units at 100
    inv = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"INV-RET-{uuid.uuid4().hex[:4]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Good", "quantity": 10.0, "unit_price": 100.0}],
    )

    stock_after_sale = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id).quantity_on_hand
    cust_bal_after_sale = cust_repo.get_by_id(t["cust_a"].id).current_balance

    # Return 4 units
    ret_res = svc.record_sales_return(
        business_id=t["biz_a"].id,
        invoice_id=inv.id,
        user_id=t["u_a"],
        items=[{"product_id": str(t["prod_a"].id), "quantity": 4.0, "unit_price": 100.0}],
        return_date=date.today(),
        reason="Defective box packaging",
    )
    assert ret_res["status"] == "PROCESSED"
    assert ret_res["total_returned"] == 400.0

    # Stock should increase by 4
    stock_after_return = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id).quantity_on_hand
    assert stock_after_return == stock_after_sale + Decimal("4.0")
    valuation_after_return = inv_repo.get_balance(t["biz_a"].id, t["prod_a"].id).total_valuation
    assert valuation_after_return == Money(2640)
    return_movements = [
        movement for movement in inv_repo.list_movements(t["biz_a"].id, t["prod_a"].id)
        if movement.reference_id == str(inv.id) and movement.reason.startswith("Sales Return:")
    ]
    assert return_movements[-1].cost_basis == Money(60)

    pnl = FinancialIntelligenceEngine().calculate_pnl(t["biz_a"].id, date.today(), date.today())
    assert pnl.gross_sales == Money(1000)
    assert pnl.total_revenue == Money(600)
    assert pnl.cost_of_goods_sold == Money(360)

    # Customer balance should decrease by 400
    cust_bal_after_return = cust_repo.get_by_id(t["cust_a"].id).current_balance
    assert cust_bal_after_return == cust_bal_after_sale - Money.from_float(400.0)


# ==============================================================================
# AUDIT ITEM 4: Concurrent PostgreSQL Race & Locking Verification Tests
# ==============================================================================

import concurrent.futures


def test_concurrent_stock_deductions_prevent_overselling(two_tenants):
    """
    Audit Item 4: High-concurrency race condition test on inventory.
    6 concurrent worker threads simultaneously attempt to invoice 5.0 units
    from a pool of only 20.0 units.
    Pessimistic row-level locks (with_for_update) MUST ensure exactly 4 succeed
    and 2 fail with InsufficientInventoryError, with final stock strictly 0.0.
    """
    svc = BusinessService()
    t = two_tenants
    inv_repo = PostgresInventoryRepository()
    prod_repo = PostgresProductRepository()

    # Create a fresh limited-stock product with exactly 20.0 units
    test_prod = Product(
        id=uuid.uuid4(),
        business_id=t["biz_a"].id,
        sku=f"LIMITED-{uuid.uuid4().hex[:6]}",
        name="Limited Edition Espresso Machine",
        category="Appliances",
        unit="units",
        selling_price=Money.from_float(500.0),
        purchase_price=Money.from_float(300.0),
    )
    prod_repo.create(test_prod)
    inv_repo.save_balance(InventoryBalance(
        id=uuid.uuid4(),
        business_id=t["biz_a"].id,
        product_id=test_prod.id,
        quantity_on_hand=Decimal("20.0"),
        unit_cost=Money.from_float(300.0),
        total_valuation=Money.from_float(6000.0),
    ))

    successes = []
    failures = []

    def attempt_invoice(thread_idx: int):
        thread_svc = BusinessService()
        try:
            inv = thread_svc.create_sales_invoice(
                business_id=t["biz_a"].id,
                user_id=t["u_a"],
                customer_id=t["cust_a"].id,
                invoice_number=f"RACE-INV-{thread_idx}-{uuid.uuid4().hex[:4]}",
                invoice_date=date.today(),
                due_date=date.today(),
                items=[{"product_id": test_prod.id, "description": "Unit", "quantity": 5.0, "unit_price": 500.0}],
            )
            return ("SUCCESS", inv.id)
        except InsufficientInventoryError as e:
            return ("FAILED", str(e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(attempt_invoice, i) for i in range(6)]
        for f in concurrent.futures.as_completed(futures):
            res_type, res_val = f.result()
            if res_type == "SUCCESS":
                successes.append(res_val)
            else:
                failures.append(res_val)

    # Exactly 4 invoices of 5 units should succeed (4 * 5 = 20)
    assert len(successes) == 4, f"Expected 4 successes, got {len(successes)}"
    # Exactly 2 requests must be rejected for insufficient inventory
    assert len(failures) == 2, f"Expected 2 failures, got {len(failures)}"

    # Final stock in PostgreSQL must be exactly 0.0 with ZERO overselling
    final_bal = inv_repo.get_balance(t["biz_a"].id, test_prod.id)
    assert final_bal.quantity_on_hand == Decimal("0.0"), f"Expected 0.0 on hand, got {final_bal.quantity_on_hand}"


def test_concurrent_payments_with_idempotency_are_race_safe(two_tenants):
    """
    Audit Item 4: High-concurrency race test on payments with identical idempotency key.
    8 concurrent worker threads simultaneously attempt to record the same payment.
    The database unique constraint and service transaction locking MUST guarantee
    exactly one payment row is created in PostgreSQL and the balance is credited once.
    """
    svc = BusinessService()
    t = two_tenants
    cust_repo = PostgresCustomerRepository()
    pay_repo = PostgresPaymentRepository()

    # Create an invoice for 1000.0
    inv = svc.create_sales_invoice(
        business_id=t["biz_a"].id,
        user_id=t["u_a"],
        customer_id=t["cust_a"].id,
        invoice_number=f"RACE-PAY-INV-{uuid.uuid4().hex[:6]}",
        invoice_date=date.today(),
        due_date=date.today(),
        items=[{"product_id": t["prod_a"].id, "description": "Item", "quantity": 10.0, "unit_price": 100.0}],
    )

    cust_bal_before = cust_repo.get_by_id(t["cust_a"].id).current_balance
    shared_idem_key = f"race_idem_{uuid.uuid4().hex}"

    def attempt_concurrent_payment(thread_idx: int):
        thread_svc = BusinessService()
        p = thread_svc.record_invoice_payment(
            business_id=t["biz_a"].id,
            invoice_id=inv.id,
            user_id=t["u_a"],
            amount=400.0,
            payment_date=date.today(),
            payment_method=PaymentMethod.UPI,
            idempotency_key=shared_idem_key,
        )
        return p.id

    payment_ids = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_concurrent_payment, i) for i in range(8)]
        for f in concurrent.futures.as_completed(futures):
            payment_ids.append(f.result())

    # All 8 threads must return the exact same Payment ID
    assert len(set(payment_ids)) == 1, f"Expected 1 unique payment ID across all 8 threads, got {set(payment_ids)}"

    # In database, exactly one payment record exists for this idempotency key
    with pay_repo.session_factory() as session:
        from backend.arthlens.infra.models import PaymentModel
        from sqlalchemy import select
        payments_in_db = session.execute(
            select(PaymentModel).where(
                PaymentModel.business_id == t["biz_a"].id,
                PaymentModel.idempotency_key == shared_idem_key,
            )
        ).scalars().all()
        assert len(payments_in_db) == 1, f"Expected 1 payment in DB, got {len(payments_in_db)}"

    # Customer balance must be credited exactly once (400.0 less than before)
    cust_bal_after = cust_repo.get_by_id(t["cust_a"].id).current_balance
    assert cust_bal_after == cust_bal_before - Money.from_float(400.0)


def test_concurrent_invoice_posting_and_customer_balance_updates(two_tenants):
    """
    Audit Item 4: High-concurrency race test on customer balance updates.
    5 concurrent threads create sales invoices for the same customer.
    Row-level locking on CustomerModel guarantees zero lost updates.
    """
    t = two_tenants
    cust_repo = PostgresCustomerRepository()
    inv_repo = PostgresInventoryRepository()
    prod_repo = PostgresProductRepository()

    # Fresh product with plenty of stock
    stock_prod = Product(
        id=uuid.uuid4(),
        business_id=t["biz_a"].id,
        sku=f"BULK-{uuid.uuid4().hex[:6]}",
        name="Bulk Commodity Sacks",
        category="Commodities",
        unit="sacks",
        selling_price=Money.from_float(100.0),
        purchase_price=Money.from_float(50.0),
    )
    prod_repo.create(stock_prod)
    inv_repo.save_balance(InventoryBalance(
        id=uuid.uuid4(),
        business_id=t["biz_a"].id,
        product_id=stock_prod.id,
        quantity_on_hand=Decimal("100.0"),
        unit_cost=Money.from_float(50.0),
        total_valuation=Money.from_float(5000.0),
    ))

    cust_bal_before = cust_repo.get_by_id(t["cust_a"].id).current_balance

    def post_invoice(idx: int):
        thread_svc = BusinessService()
        inv = thread_svc.create_sales_invoice(
            business_id=t["biz_a"].id,
            user_id=t["u_a"],
            customer_id=t["cust_a"].id,
            invoice_number=f"CONCUR-POST-{idx}-{uuid.uuid4().hex[:4]}",
            invoice_date=date.today(),
            due_date=date.today(),
            items=[{"product_id": stock_prod.id, "description": "Sack", "quantity": 2.0, "unit_price": 100.0}],
        )
        return inv.total_amount.amount

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        amounts = list(executor.map(post_invoice, range(5)))

    # 5 invoices * 200.0 = 1000.0
    total_posted = sum(amounts)
    assert total_posted == Decimal("1000.00")

    # Customer balance in PostgreSQL must reflect exactly the sum with ZERO lost updates
    cust_bal_after = cust_repo.get_by_id(t["cust_a"].id).current_balance
    expected_balance = cust_bal_before + Money(Decimal("1000.00"), "INR")
    assert cust_bal_after == expected_balance, f"Expected {expected_balance}, got {cust_bal_after}"

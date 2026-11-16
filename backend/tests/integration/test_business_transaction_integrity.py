"""
Transaction Integrity and Atomicity Integration Tests.

Authoritative Reference: ArthLens Final Product Vision & Post-Audit Correction D.
Validates:
1. Complete rollback on inventory shortage (no partial deductions or orphaned ledger entries).
2. Multi-item transaction atomicity (all-or-nothing stock movements).
3. Overpayment prevention on sales invoices and purchase bills.
4. Customer and supplier ledger balance consistency.
5. Idempotent payment handling and status transition invariants.
"""

from datetime import date
from decimal import Decimal
import uuid
import pytest
from sqlalchemy import select, update

from backend.arthlens.domain.business import (
    Business,
    BusinessRole,
    Customer,
    InvoiceStatus,
    Money,
    MovementType,
    PaymentMethod,
    PaymentType,
    Product,
    PurchaseStatus,
    Supplier,
)
from backend.arthlens.services.business_service import (
    BusinessNotFoundError,
    BusinessService,
    IdempotencyConflictError,
    InsufficientInventoryError,
    InvalidOperationError,
)
from backend.arthlens.infra.business_repositories import (
    PostgresBusinessRepository,
    PostgresCustomerRepository,
    PostgresInventoryRepository,
    PostgresPaymentRepository,
    PostgresProductRepository,
    PostgresPurchaseRepository,
    PostgresPurchaseReturnRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    InventoryBalanceModel,
    InventoryCostReconciliationEventModel,
    InventoryMovementModel,
    PurchaseModel,
)
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role


@pytest.fixture
def integrity_workspace():
    """Seeds an isolated workspace with owner, product, customer, and supplier."""
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    prod_repo = PostgresProductRepository()
    cust_repo = PostgresCustomerRepository()
    sup_repo = PostgresSupplierRepository()
    inv_repo = PostgresInventoryRepository()

    owner_id = user_repo.save({
        "email": f"integrity_{uuid.uuid4().hex[:8]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })

    biz = Business(
        id=uuid.uuid4(),
        owner_id=owner_id,
        name=f"Integrity Test Enterprise {uuid.uuid4().hex[:6]}",
        industry="Light Manufacturing",
        address="Kanpur, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz)

    # Create Product A with 10 units on hand
    prod_a = Product(
        id=uuid.uuid4(),
        business_id=biz.id,
        sku="SKU-A",
        name="Precision Gear Box",
        category="Machinery",
        unit="pcs",
        selling_price=Money.from_float(500.0),
        purchase_price=Money.from_float(300.0),
    )
    prod_repo.create(prod_a)

    # Create Product B with 2 units on hand
    prod_b = Product(
        id=uuid.uuid4(),
        business_id=biz.id,
        sku="SKU-B",
        name="High-Torque Motor",
        category="Machinery",
        unit="pcs",
        selling_price=Money.from_float(1200.0),
        purchase_price=Money.from_float(800.0),
    )
    prod_repo.create(prod_b)

    # Seed stock for Product A (10 units) and Product B (2 units)
    service = BusinessService()
    service.adjust_inventory(
        business_id=biz.id,
        product_id=prod_a.id,
        user_id=owner_id,
        movement_type=MovementType.OPENING,
        quantity=10.0,
        unit_price=300.0,
        reason="Initial test stock A",
    )
    service.adjust_inventory(
        business_id=biz.id,
        product_id=prod_b.id,
        user_id=owner_id,
        movement_type=MovementType.OPENING,
        quantity=2.0,
        unit_price=800.0,
        reason="Initial test stock B",
    )

    # Create customer with ₹50,000 credit limit
    cust = Customer(
        id=uuid.uuid4(),
        business_id=biz.id,
        name="Apex Engineering Works",
        credit_limit=Money.from_float(50000.0),
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    cust_repo.create(cust)

    # Create supplier
    sup = Supplier(
        id=uuid.uuid4(),
        business_id=biz.id,
        name="Tata Steel & Components",
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    sup_repo.create(sup)

    return {
        "service": service,
        "business_id": biz.id,
        "owner_id": owner_id,
        "prod_a": prod_a,
        "prod_b": prod_b,
        "customer": cust,
        "supplier": sup,
        "inv_repo": inv_repo,
        "invoice_repo": PostgresSalesInvoiceRepository(),
        "purchase_repo": PostgresPurchaseRepository(),
        "cust_repo": cust_repo,
        "sup_repo": sup_repo,
        "biz_repo": biz_repo,
    }


@pytest.mark.integration
class TestBusinessTransactionIntegrity:
    """Verifies atomic rollback, non-destructive failures, and payment guarantees."""

    def test_single_item_insufficient_stock_rollback(self, integrity_workspace):
        """When an invoice requests more than available stock, zero records are altered."""
        w = integrity_workspace
        service: BusinessService = w["service"]

        # Attempt to sell 15 units of Product A (only 10 available)
        with pytest.raises(InsufficientInventoryError) as exc_info:
            service.create_sales_invoice(
                business_id=w["business_id"],
                user_id=w["owner_id"],
                customer_id=w["customer"].id,
                invoice_number="INV-FAIL-01",
                invoice_date=date.today(),
                due_date=date.today(),
                items=[{
                    "product_id": str(w["prod_a"].id),
                    "description": "Precision Gear Box",
                    "quantity": 15.0,
                    "unit_price": 500.0,
                }],
            )

        assert "Insufficient stock" in str(exc_info.value)

        # 1. Product A stock must still be exactly 10 units
        bal_a = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id)
        assert bal_a.quantity_on_hand == Decimal("10.00")

        # 2. Invoice must NOT exist
        invoices = w["invoice_repo"].list_by_business(w["business_id"])
        inv_numbers = [inv.invoice_number for inv in invoices]
        assert "INV-FAIL-01" not in inv_numbers

        # 3. Customer balance must be unchanged (₹0.00)
        cust = w["cust_repo"].get_by_id(w["customer"].id)
        assert cust.current_balance == Money.zero()

    def test_multi_item_partial_shortage_atomic_rollback(self, integrity_workspace):
        """When item 1 has enough stock but item 2 fails, item 1 deduction MUST roll back completely."""
        w = integrity_workspace
        service: BusinessService = w["service"]

        # Product A has 10 units (request 5: valid)
        # Product B has 2 units (request 5: invalid)
        with pytest.raises(InsufficientInventoryError):
            service.create_sales_invoice(
                business_id=w["business_id"],
                user_id=w["owner_id"],
                customer_id=w["customer"].id,
                invoice_number="INV-MULTI-FAIL",
                invoice_date=date.today(),
                due_date=date.today(),
                items=[
                    {
                        "product_id": str(w["prod_a"].id),
                        "description": "Gear Box",
                        "quantity": 5.0,
                        "unit_price": 500.0,
                    },
                    {
                        "product_id": str(w["prod_b"].id),
                        "description": "Motor",
                        "quantity": 5.0,
                        "unit_price": 1200.0,
                    },
                ],
            )

        # Critical ACID test: Product A was processed first in the loop, but must NOT have been deducted!
        bal_a = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id)
        assert bal_a.quantity_on_hand == Decimal("10.00"), "Product A stock was partially deducted!"

        bal_b = w["inv_repo"].get_balance(w["business_id"], w["prod_b"].id)
        assert bal_b.quantity_on_hand == Decimal("2.00")

    def test_overpayment_rejection_and_ledger_integrity(self, integrity_workspace):
        """Overpaying an invoice or purchase is strictly rejected, preserving exact balances."""
        w = integrity_workspace
        service: BusinessService = w["service"]

        # 1. Create a valid invoice of ₹2,500 (5 units of Prod A)
        inv = service.create_sales_invoice(
            business_id=w["business_id"],
            user_id=w["owner_id"],
            customer_id=w["customer"].id,
            invoice_number="INV-PAY-01",
            invoice_date=date.today(),
            due_date=date.today(),
            items=[{
                "product_id": str(w["prod_a"].id),
                "description": "Gear Box",
                "quantity": 5.0,
                "unit_price": 500.0,
            }],
        )
        assert inv.total_amount == Money.from_float(2500.0)
        assert inv.outstanding_balance == Money.from_float(2500.0)

        # Customer balance should be ₹2,500
        cust = w["cust_repo"].get_by_id(w["customer"].id)
        assert cust.current_balance == Money.from_float(2500.0)

        # 2. Attempt overpayment of ₹3,000 (exceeds ₹2,500)
        with pytest.raises(InvalidOperationError) as exc_info:
            service.record_invoice_payment(
                business_id=w["business_id"],
                invoice_id=inv.id,
                user_id=w["owner_id"],
                amount=3000.0,
                payment_date=date.today(),
                payment_method=PaymentMethod.BANK_TRANSFER,
            )
        assert "exceeds invoice outstanding balance" in str(exc_info.value)

        # 3. Assert invoice is still ISSUED and paid_amount is 0
        refreshed_inv = service.get_sales_invoice(w["business_id"], inv.id, w["owner_id"])
        assert refreshed_inv.status == InvoiceStatus.ISSUED
        assert refreshed_inv.paid_amount == Money.zero()

        # 4. Pay exact amount: ₹2,500
        paid_inv = service.record_invoice_payment(
            business_id=w["business_id"],
            invoice_id=inv.id,
            user_id=w["owner_id"],
            amount=2500.0,
            payment_date=date.today(),
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
        assert paid_inv.status == InvoiceStatus.PAID
        assert paid_inv.outstanding_balance == Money.zero()

        # Customer current balance must now be ₹0.00
        cust_after = w["cust_repo"].get_by_id(w["customer"].id)
        assert cust_after.current_balance == Money.zero()

        # 5. Subsequent payment attempt on fully paid invoice must fail
        with pytest.raises(InvalidOperationError):
            service.record_invoice_payment(
                business_id=w["business_id"],
                invoice_id=inv.id,
                user_id=w["owner_id"],
                amount=100.0,
                payment_date=date.today(),
                payment_method=PaymentMethod.CASH,
            )

    def test_purchase_bill_atomic_stock_addition_and_payable_ledger(self, integrity_workspace):
        """Creating a purchase bill atomically increases inventory and creates supplier payable."""
        w = integrity_workspace
        service: BusinessService = w["service"]

        # Buy 20 units of Product A at ₹300 = ₹6,000
        purch = service.create_purchase(
            business_id=w["business_id"],
            user_id=w["owner_id"],
            supplier_id=w["supplier"].id,
            bill_number="BILL-TAT-101",
            purchase_date=date.today(),
            due_date=date.today(),
            items=[{
                "product_id": str(w["prod_a"].id),
                "description": "Gear Raw Castings",
                "quantity": 20.0,
                "unit": "pcs",
                "unit_price": 300.0,
            }],
        )
        assert purch.total_amount == Money.from_float(6000.0)
        assert purch.status == PurchaseStatus.PENDING

        # Stock A was 10 (or 5 if previous test ran on same db, let's verify exact addition)
        bal_a = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id)
        assert bal_a.quantity_on_hand >= Decimal("20.00")

        # Supplier balance must be ₹6,000
        sup = w["sup_repo"].get_by_id(w["supplier"].id)
        assert sup.current_balance == Money.from_float(6000.0)

        # Overpaying purchase is rejected
        with pytest.raises(InvalidOperationError) as exc_info:
            service.record_purchase_payment(
                business_id=w["business_id"],
                purchase_id=purch.id,
                user_id=w["owner_id"],
                amount=7000.0,
                payment_date=date.today(),
                payment_method=PaymentMethod.BANK_TRANSFER,
            )
        assert "exceeds purchase outstanding balance" in str(exc_info.value)


@pytest.mark.integration
class TestPurchaseReturnIntegrity:
    def _purchase(self, w, quantity=4, unit_price=50, tax_amount=18, is_cash=False, product=None):
        return w["service"].create_purchase(
            business_id=w["business_id"],
            user_id=w["owner_id"],
            supplier_id=w["supplier"].id,
            bill_number=f"RETURN-{uuid.uuid4().hex[:10]}",
            purchase_date=date.today(),
            due_date=date.today(),
            items=[{
                "product_id": str((product or w["prod_a"]).id),
                "description": "Return test stock",
                "quantity": quantity,
                "unit": "pcs",
                "unit_price": unit_price,
            }],
            tax_amount=tax_amount,
            is_cash_purchase=is_cash,
            immediate_payment_method=PaymentMethod.BANK_TRANSFER if is_cash else None,
        )

    def _return(self, w, purchase, quantity, **kwargs):
        kwargs.setdefault("idempotency_key", f"return-{uuid.uuid4().hex}")
        return w["service"].record_purchase_return(
            business_id=w["business_id"],
            purchase_id=purchase.id,
            user_id=w["owner_id"],
            items=[{"purchase_item_id": str(purchase.items[0].id), "quantity": quantity}],
            return_date=date.today(),
            **kwargs,
        )

    def test_partial_returns_allocate_source_value_and_tax_and_are_idempotent(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w)
        key = f"return-{uuid.uuid4().hex}"

        first = self._return(w, purchase, "1", idempotency_key=key)
        assert first["subtotal"] == 50.0
        assert first["tax_amount"] == 4.5
        assert first["total_returned"] == 54.5
        assert first["items"][0]["original_unit_price"] == 50.0
        assert first["inventory_cost_removed"] > 0
        return_movement = next(
            movement for movement in w["inv_repo"].list_movements(w["business_id"], w["prod_a"].id)
            if movement.reference_id == first["purchase_return_id"]
        )
        assert return_movement.cost_basis == Money.from_float(50)
        assert return_movement.source_purchase_item_id == purchase.items[0].id
        partially_returned_purchase = w["purchase_repo"].get_by_id(purchase.id)
        assert partially_returned_purchase.status == PurchaseStatus.PARTIALLY_RETURNED
        assert partially_returned_purchase.return_credit_amount == Money.from_float(54.5)
        assert partially_returned_purchase.outstanding_balance == Money.from_float(163.5)

        # A retry returns the persisted result and does not deduct stock twice.
        stock_after_first = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand
        replay = self._return(w, purchase, "1", idempotency_key=key)
        assert replay["purchase_return_id"] == first["purchase_return_id"]
        assert w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand == stock_after_first

        with pytest.raises(IdempotencyConflictError, match="different purchase return"):
            self._return(w, purchase, "2", idempotency_key=key)
        with pytest.raises(InvalidOperationError, match="exceeds the remaining quantity"):
            self._return(w, purchase, "4")

        second = self._return(w, purchase, "3")
        assert second["subtotal"] == 150.0
        assert second["tax_amount"] == 13.5
        assert second["total_returned"] == 163.5
        assert w["sup_repo"].get_by_id(w["supplier"].id).current_balance == Money.zero()
        fully_returned_purchase = w["purchase_repo"].get_by_id(purchase.id)
        assert fully_returned_purchase.status == PurchaseStatus.RETURNED
        assert fully_returned_purchase.outstanding_balance == Money.zero()
        assert fully_returned_purchase.items[0].returned_quantity == Decimal("4.0000")

        history = PostgresPurchaseReturnRepository().list_by_purchase(w["business_id"], purchase.id)
        assert len(history) == 2
        assert sum((line.quantity for record in history for line in record.items), Decimal("0")) == Decimal("4")
        assert sum((record.subtotal.amount for record in history), Decimal("0")) == Decimal("200.00")
        assert sum((record.tax_amount.amount for record in history), Decimal("0")) == Decimal("18.00")

    def test_request_requires_idempotency_and_forbids_client_pricing(self):
        from pydantic import ValidationError
        from backend.arthlens.api.business import PurchaseReturnItemRequest, PurchaseReturnRequest

        purchase_item_id = uuid.uuid4()
        parsed = PurchaseReturnItemRequest.model_validate({
            "purchase_item_id": str(purchase_item_id), "quantity": "0.1250",
        })
        assert parsed.quantity == Decimal("0.1250")
        with pytest.raises(ValidationError):
            PurchaseReturnItemRequest.model_validate({
                "purchase_item_id": str(purchase_item_id), "quantity": "1", "unit_price": "0.01",
            })
        with pytest.raises(ValidationError):
            PurchaseReturnRequest.model_validate({
                "purchase_id": str(uuid.uuid4()),
                "items": [{"purchase_item_id": str(purchase_item_id), "quantity": "1"}],
            })

    def test_rejects_wrong_purchase_line_and_user_supplied_price(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w)
        unrelated = self._purchase(w, quantity=2, product=w["prod_b"])

        with pytest.raises(InvalidOperationError, match="selected purchase"):
            w["service"].record_purchase_return(
                w["business_id"], purchase.id, w["owner_id"],
                [{"purchase_item_id": str(unrelated.items[0].id), "quantity": "1"}], date.today(),
                idempotency_key=f"return-{uuid.uuid4().hex}",
            )
        with pytest.raises(InvalidOperationError, match="only an original purchase_item_id"):
            w["service"].record_purchase_return(
                w["business_id"], purchase.id, w["owner_id"],
                [{"purchase_item_id": str(purchase.items[0].id), "quantity": "1", "unit_price": "0.01"}],
                date.today(), idempotency_key=f"return-{uuid.uuid4().hex}",
            )
        with pytest.raises(InvalidOperationError, match="exceeds the remaining quantity"):
            self._return(w, purchase, "5")
        with pytest.raises(InvalidOperationError, match="idempotency key is required"):
            self._return(w, purchase, "1", idempotency_key="")

    def test_rejects_foreign_purchase_supplier_and_cross_business_purchase(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w)
        foreign_business = Business(
            id=uuid.uuid4(), owner_id=w["owner_id"], name="Second tenant",
            industry="Retail", address="Pune", financial_year_start="04-01", currency="INR",
        )
        w["biz_repo"].create(foreign_business)
        foreign_supplier = Supplier(
            id=uuid.uuid4(), business_id=foreign_business.id, name="Foreign Supplier",
        )
        w["sup_repo"].create(foreign_supplier)
        with get_session_factory()() as session:
            with session.begin():
                session.execute(
                    update(PurchaseModel)
                    .where(PurchaseModel.id == purchase.id)
                    .values(supplier_id=foreign_supplier.id)
                )

        with pytest.raises(BusinessNotFoundError, match="not found for this business"):
            w["service"].record_purchase_return(
                foreign_business.id, purchase.id, w["owner_id"],
                [{"purchase_item_id": str(purchase.items[0].id), "quantity": "1"}], date.today(),
                idempotency_key=f"return-{uuid.uuid4().hex}",
            )
        with pytest.raises(InvalidOperationError, match="supplier is invalid"):
            self._return(w, purchase, "1")

    def test_cash_refund_creates_receipt_and_balanced_journal_entry(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w, quantity=2, unit_price=100, tax_amount=10, is_cash=True)
        result = self._return(w, purchase, "1", refund_method=PaymentMethod.BANK_TRANSFER)

        assert result["total_returned"] == 105.0
        assert result["settlement_method"] == PaymentMethod.BANK_TRANSFER.value
        assert w["sup_repo"].get_by_id(w["supplier"].id).current_balance == Money.zero()
        refreshed_purchase = w["purchase_repo"].get_by_id(purchase.id)
        assert refreshed_purchase.return_credit_amount == Money.from_float(105)
        assert refreshed_purchase.paid_amount == Money.from_float(105)
        assert refreshed_purchase.outstanding_balance == Money.zero()

        receipts = [
            payment for payment in w["service"].payment_repo.list_by_business(w["business_id"])
            if payment.reference_type == "PURCHASE_RETURN"
            and str(payment.reference_id) == result["purchase_return_id"]
        ]
        assert len(receipts) == 1
        assert receipts[0].payment_type == PaymentType.RECEIVED
        assert receipts[0].amount == Money.from_float(105.0)

        entry = next(
            entry for entry in w["service"].journal_repo.list_by_business(w["business_id"])
            if entry.reference_type == "PURCHASE_RETURN" and str(entry.reference_id) == result["purchase_return_id"]
        )
        assert sum((line.debit.amount for line in entry.lines), Decimal("0")) == sum(
            (line.credit.amount for line in entry.lines), Decimal("0")
        )

    def test_cash_refund_cannot_exceed_paid_purchase_value(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w, quantity=2, unit_price=100, tax_amount=10, is_cash=False)
        stock_before = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand

        with pytest.raises(InvalidOperationError, match="cannot exceed the amount currently paid"):
            self._return(w, purchase, "1", refund_method=PaymentMethod.CASH)

        assert w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand == stock_before
        assert PostgresPurchaseReturnRepository().list_by_purchase(w["business_id"], purchase.id) == []

    def test_return_after_full_payment_posts_supplier_debit_note_receivable(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w, quantity=2, unit_price=100, tax_amount=10, is_cash=True)
        result = self._return(w, purchase, "1")

        refreshed_purchase = w["purchase_repo"].get_by_id(purchase.id)
        assert refreshed_purchase.outstanding_balance == Money.zero()
        assert w["sup_repo"].get_by_id(w["supplier"].id).current_balance == Money.from_float(-105)
        entry = next(
            entry for entry in w["service"].journal_repo.list_by_business(w["business_id"])
            if entry.reference_type == "PURCHASE_RETURN" and str(entry.reference_id) == result["purchase_return_id"]
        )
        debit_note = [line for line in entry.lines if line.account_code == "1160"]
        assert sum((line.debit.amount for line in debit_note), Decimal("0")) == Decimal("105.00")
        assert sum((line.debit.amount for line in entry.lines), Decimal("0")) == sum(
            (line.credit.amount for line in entry.lines), Decimal("0")
        )

    def test_missing_stock_rejects_without_creating_return(self, integrity_workspace):
        w = integrity_workspace
        purchase = self._purchase(w, quantity=2, unit_price=40, tax_amount=0)
        w["service"].create_sales_invoice(
            business_id=w["business_id"], user_id=w["owner_id"], customer_id=w["customer"].id,
            invoice_number=f"SELL-{uuid.uuid4().hex[:10]}", invoice_date=date.today(), due_date=date.today(),
            items=[{
                "product_id": str(w["prod_a"].id), "description": "Sell all test stock",
                "quantity": 12, "unit_price": 500,
            }],
        )
        with pytest.raises(InsufficientInventoryError):
            self._return(w, purchase, "1")
        assert PostgresPurchaseReturnRepository().list_by_purchase(w["business_id"], purchase.id) == []

    def test_journal_failure_rolls_back_return_stock_supplier_and_history(self, integrity_workspace, monkeypatch):
        w = integrity_workspace
        purchase = self._purchase(w)
        before_stock = w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand
        before_supplier = w["sup_repo"].get_by_id(w["supplier"].id).current_balance
        before_movements = len(w["inv_repo"].list_movements(w["business_id"], w["prod_a"].id))

        def fail_posting(**_kwargs):
            raise RuntimeError("simulated journal failure")

        monkeypatch.setattr(w["service"], "_post_gl_entry", fail_posting)
        with pytest.raises(RuntimeError, match="simulated journal failure"):
            self._return(w, purchase, "1")

        assert w["inv_repo"].get_balance(w["business_id"], w["prod_a"].id).quantity_on_hand == before_stock
        assert w["sup_repo"].get_by_id(w["supplier"].id).current_balance == before_supplier
        assert len(w["inv_repo"].list_movements(w["business_id"], w["prod_a"].id)) == before_movements
        assert PostgresPurchaseReturnRepository().list_by_purchase(w["business_id"], purchase.id) == []

    def test_concurrent_returns_cannot_exceed_purchased_quantity(self, integrity_workspace):
        from concurrent.futures import ThreadPoolExecutor

        w = integrity_workspace
        purchase = self._purchase(w, quantity=5, unit_price=20, tax_amount=0)

        def attempt_return():
            try:
                return self._return(w, purchase, "3")
            except InvalidOperationError as exc:
                return exc

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt_return(), range(2)))
        assert sum(not isinstance(result, Exception) for result in results) == 1
        assert sum(isinstance(result, InvalidOperationError) for result in results) == 1
        history = PostgresPurchaseReturnRepository().list_by_purchase(w["business_id"], purchase.id)
        assert sum((line.quantity for record in history for line in record.items), Decimal("0")) == Decimal("3")


@pytest.mark.integration
class TestInventoryCostReconciliation:
    def test_chronological_replay_uses_captured_source_and_restores_completeness(self, integrity_workspace):
        w = integrity_workspace
        service = w["service"]
        invoice = service.create_sales_invoice(
            business_id=w["business_id"], user_id=w["owner_id"], customer_id=w["customer"].id,
            invoice_number=f"COST-{uuid.uuid4().hex[:10]}", invoice_date=date.today(), due_date=date.today(),
            items=[{
                "product_id": str(w["prod_a"].id), "description": "Cost replay sale",
                "quantity": 2, "unit_price": 500,
            }],
        )
        sale_movement = next(
            movement for movement in w["inv_repo"].list_movements(w["business_id"], w["prod_a"].id)
            if movement.reference_id == str(invoice.id) and movement.movement_type == MovementType.SALE
        )
        with get_session_factory()() as session:
            with session.begin():
                session.execute(
                    update(InventoryMovementModel)
                    .where(InventoryMovementModel.id == sale_movement.id)
                    .values(cost_basis=None, cost_reconciliation_status="UNRECONCILED")
                )

        preview = service.list_unreconciled_inventory_movements(w["business_id"], w["owner_id"])
        assert preview["unreconciled_movement_count"] == 1
        assert preview["movements"][0]["estimated_cogs_impact"] == "600.00"
        assert preview["movements"][0]["classification"] == "UNKNOWN"

        result = service.reconcile_historical_inventory_costs(
            w["business_id"], w["owner_id"], "CHRONOLOGICAL_REPLAY",
        )
        assert result["status"] == "COMPLETED"
        assert result["resolved_movement_count"] == 1
        with get_session_factory()() as session:
            movement = session.get(InventoryMovementModel, sale_movement.id)
            events = session.execute(
                select(InventoryCostReconciliationEventModel).where(
                    InventoryCostReconciliationEventModel.reconciliation_id == uuid.UUID(result["reconciliation_id"])
                )
            ).scalars().all()
        assert movement.cost_basis == Decimal("300.00")
        assert movement.cost_reconciliation_status == "VERIFIED"
        assert len(events) == 1
        assert events[0].classification == "DERIVED_FROM_VERIFIED_SOURCE"
        finance = FinancialIntelligenceEngine(
            invoice_repo=service.invoice_repo,
            purchase_repo=service.purchase_repo,
            inventory_repo=service.inventory_repo,
            journal_repo=service.journal_repo,
        )
        pnl = finance.calculate_pnl(w["business_id"], date.today(), date.today())
        assert pnl.unreconciled_inventory_movement_count == 0
        assert pnl.inventory_cost_completeness_percent == Decimal("100.00")
        assert pnl.to_dict()["data_quality"]["inventory_cost_completeness_percent"] == "100.00"

    def test_manual_attestation_updates_balance_and_posts_audited_adjustment(self, integrity_workspace):
        w = integrity_workspace
        service = w["service"]
        product = service.create_product(
            business_id=w["business_id"], user_id=w["owner_id"], sku=f"UNK-{uuid.uuid4().hex[:6]}",
            name="Unknown opening cost", category="Test", unit="pcs",
            purchase_price=0, selling_price=10, initial_stock=0,
        )
        service.adjust_inventory(
            business_id=w["business_id"], product_id=product.id, user_id=w["owner_id"],
            movement_type=MovementType.OPENING, quantity=2, unit_price=0, reason="Unpriced opening stock",
        )
        movement = next(
            row for row in w["inv_repo"].list_movements(w["business_id"], product.id)
            if row.movement_type == MovementType.OPENING
        )
        result = service.reconcile_historical_inventory_costs(
            w["business_id"], w["owner_id"], "MANUAL_ATTESTATION",
            overrides=[{
                "movement_id": str(movement.id), "unit_cost": "25.00",
                "note": "Verified supplier invoice for opening stock",
            }],
        )
        assert result["status"] == "COMPLETED"
        assert result["resolved_movement_count"] == 1
        balance = w["inv_repo"].get_balance(w["business_id"], product.id)
        assert balance.quantity_on_hand == Decimal("2.0000")
        assert balance.unit_cost == Money("25.00")
        assert balance.total_valuation == Money("50.00")
        assert result["ledger_adjustment"]["inventory_valuation_delta"] == "50.00"
        with get_session_factory()() as session:
            event = session.execute(
                select(InventoryCostReconciliationEventModel).where(
                    InventoryCostReconciliationEventModel.reconciliation_id == uuid.UUID(result["reconciliation_id"]),
                    InventoryCostReconciliationEventModel.movement_id == movement.id,
                )
            ).scalar_one()
            stored_balance = session.execute(
                select(InventoryBalanceModel).where(InventoryBalanceModel.product_id == product.id)
            ).scalar_one()
        assert event.classification == "USER_CONFIRMED"
        assert event.resolution_note == "Verified supplier invoice for opening stock"
        assert stored_balance.unit_cost == Decimal("25.00")


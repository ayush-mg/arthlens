"""
Business Operating System Application Services.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 2: Business Operations Services and Core Domain Orchestration.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
import uuid

from backend.arthlens.domain.business import (
    ACCOUNT_NAMES,
    FinancialPeriod,
    FinancialPeriodStatus,
    JournalEntry,
    JournalEntryLine,
    StandardAccount,
    Business,
    BusinessMembership,
    BusinessRole,
    Customer,
    DateRange,
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
    Percentage,
    Product,
    Purchase,
    PurchaseItem,
    PurchaseReturn,
    PurchaseReturnItem,
    PurchaseStatus,
    SalesInvoice,
    SalesInvoiceItem,
    Supplier,
)
from backend.arthlens.infra.business_repositories import (
    PostgresFinancialPeriodRepository,
    PostgresJournalEntryRepository,
    PostgresBusinessRepository,
    PostgresCustomerRepository,
    PostgresDecisionEvaluationRepository,
    PostgresGoalRepository,
    PostgresIncomeExpenseRepository,
    PostgresInventoryRepository,
    PostgresPaymentRepository,
    PostgresProductRepository,
    PostgresPurchaseRepository,
    PostgresPurchaseReturnRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.services.inventory_cost_service import InventoryCostService
from sqlalchemy import delete, select
from backend.arthlens.infra.models import (
    JournalEntryModel,
    JournalEntryLineModel,
    SalesInvoiceModel,
    SalesInvoiceItemModel,
    PurchaseModel,
    PurchaseItemModel,
    InventoryMovementModel,
)


class BusinessNotFoundError(Exception):
    """Raised when a requested business workspace does not exist."""
    pass


class UnauthorizedBusinessAccessError(Exception):
    """Raised when a user does not have permission for the business workspace."""
    pass


class CreditLimitExceededError(Exception):
    """Raised when a credit transaction would violate the customer's credit limit."""
    pass


class InsufficientInventoryError(Exception):
    """Raised when attempting to deduct more stock than is available on hand."""
    pass


class InvalidOperationError(Exception):
    """Raised when a requested business operation violates domain invariants."""
    pass


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused with conflicting parameters."""
    pass


class FinancialPeriodClosedError(Exception):
    """Raised when an operation is attempted in a closed or locked financial period."""
    pass


class BusinessService:
    """
    Central orchestration service for the ArthLens Business Operating System.
    Enforces multi-tenant isolation, role checks, and transactional invariants across all 12 modules.
    """

    def __init__(
        self,
        business_repo: Optional[PostgresBusinessRepository] = None,
        customer_repo: Optional[PostgresCustomerRepository] = None,
        supplier_repo: Optional[PostgresSupplierRepository] = None,
        product_repo: Optional[PostgresProductRepository] = None,
        inventory_repo: Optional[PostgresInventoryRepository] = None,
        invoice_repo: Optional[PostgresSalesInvoiceRepository] = None,
        purchase_repo: Optional[PostgresPurchaseRepository] = None,
        purchase_return_repo: Optional[PostgresPurchaseReturnRepository] = None,
        payment_repo: Optional[PostgresPaymentRepository] = None,
        income_expense_repo: Optional[PostgresIncomeExpenseRepository] = None,
        goal_repo: Optional[PostgresGoalRepository] = None,
        decision_repo: Optional[PostgresDecisionEvaluationRepository] = None,
        session_factory=None,
    ):
        self.business_repo = business_repo or PostgresBusinessRepository()
        self.customer_repo = customer_repo or PostgresCustomerRepository()
        self.supplier_repo = supplier_repo or PostgresSupplierRepository()
        self.product_repo = product_repo or PostgresProductRepository()
        self.inventory_repo = inventory_repo or PostgresInventoryRepository()
        self.invoice_repo = invoice_repo or PostgresSalesInvoiceRepository()
        self.purchase_repo = purchase_repo or PostgresPurchaseRepository()
        self.purchase_return_repo = purchase_return_repo or PostgresPurchaseReturnRepository()
        self.payment_repo = payment_repo or PostgresPaymentRepository()
        self.income_expense_repo = income_expense_repo or PostgresIncomeExpenseRepository()
        self.goal_repo = goal_repo or PostgresGoalRepository()
        self.decision_repo = decision_repo or PostgresDecisionEvaluationRepository()
        self.session_factory = session_factory or getattr(self.business_repo, "session_factory", None) or get_session_factory()
        self.journal_repo = PostgresJournalEntryRepository(self.session_factory)
        self.period_repo = PostgresFinancialPeriodRepository(self.session_factory)
        self.inventory_cost_service = InventoryCostService(self.session_factory)

    # ==========================================================================
    # Authorization & Tenant Verification
    # ==========================================================================

    def verify_access(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        required_roles: Optional[List[BusinessRole]] = None,
    ) -> BusinessMembership:
        """Verifies user membership and role in the requested business workspace."""
        membership = self.business_repo.get_membership(business_id, user_id)
        if not membership or not membership.is_active:
            raise UnauthorizedBusinessAccessError(f"User {user_id} does not have access to business {business_id}")

        role_matches = membership.role in (required_roles or [])
        if membership.role == BusinessRole.ADMIN and required_roles:
            role_matches = True
        if required_roles and not role_matches:
            raise UnauthorizedBusinessAccessError(
                f"User role {membership.role.value} does not have sufficient permission (required: {[r.value for r in required_roles]})"
            )
        return membership
    def _post_gl_entry(
        self,
        business_id: uuid.UUID,
        entry_date: date,
        reference_type: str,
        description: str,
        lines_data: List[Tuple[str, str, Money, Money]],  # (code, name, debit, credit)
        reference_id: Optional[uuid.UUID] = None,
        session: Optional[Any] = None,
    ) -> JournalEntry:
        """Records an authoritative balanced double-entry General Ledger transaction."""
        if self.period_repo.is_date_locked(business_id, entry_date, session=session):
            raise FinancialPeriodClosedError(
                f"Cannot record financial event on {entry_date}: accounting period is locked/closed."
            )
        entry_id = uuid.uuid4()
        entry_number = self.journal_repo.get_next_entry_number(business_id, session=session)
        lines: List[JournalEntryLine] = []
        for code, name, debit, credit in lines_data:
            if debit > Money.zero() or credit > Money.zero():
                lines.append(
                    JournalEntryLine(
                        id=uuid.uuid4(),
                        journal_entry_id=entry_id,
                        account_code=code,
                        account_name=name,
                        debit=debit,
                        credit=credit,
                        notes=description,
                    )
                )
        entry = JournalEntry(
            id=entry_id,
            business_id=business_id,
            entry_number=entry_number,
            entry_date=entry_date,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            lines=lines,
            is_posted=True,
        )
        return self.journal_repo.create(entry, session=session)

    def _invoice_inventory_costs(
        self,
        business_id: uuid.UUID,
        invoice: SalesInvoice,
        session: Any,
    ) -> Dict[uuid.UUID, Tuple[Decimal, Money]]:
        """Return sale-time quantity and cost by product, failing on legacy gaps."""
        expected: Dict[uuid.UUID, Decimal] = {}
        for item in invoice.items:
            if item.product_id:
                expected[item.product_id] = expected.get(item.product_id, Decimal("0")) + item.quantity

        sale_rows = [
            movement
            for movement in self.inventory_repo.list_movements(business_id, session=session)
            if movement.reference_id == str(invoice.id) and movement.movement_type == MovementType.SALE
        ]
        result: Dict[uuid.UUID, Tuple[Decimal, Money]] = {}
        for product_id, expected_qty in expected.items():
            rows = [movement for movement in sale_rows if movement.product_id == product_id]
            if not rows or sum((row.quantity for row in rows), Decimal("0")) != expected_qty:
                raise InvalidOperationError(
                    f"Sale-time inventory cost is unavailable for product {product_id} on invoice {invoice.invoice_number}."
                )
            if any(row.cost_basis is None for row in rows):
                raise InvalidOperationError(
                    f"Invoice {invoice.invoice_number} predates captured inventory cost. Its inventory cost must be reconciled before reversal."
                )
            cost = sum((row.cost_basis * row.quantity for row in rows), Money.zero())
            result[product_id] = (expected_qty, cost)
        return result

        return membership

    # ==========================================================================
    # 1. Multi-Business Workspaces (UC-01 to UC-08)
    # ==========================================================================

    def create_business(
        self,
        owner_id: uuid.UUID,
        name: str,
        industry: str,
        address: str = "",
        financial_year_start: str = "04-01",
        currency: str = "INR",
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Business:
        business = Business(
            id=uuid.uuid4(),
            owner_id=owner_id,
            name=name.strip(),
            industry=industry.strip(),
            address=address.strip(),
            financial_year_start=financial_year_start,
            currency=currency.upper(),
            preferences=preferences or {},
        )
        return self.business_repo.create(business)

    def get_business(self, business_id: uuid.UUID, user_id: uuid.UUID) -> Business:
        self.verify_access(business_id, user_id)
        biz = self.business_repo.get_by_id(business_id)
        if not biz:
            raise BusinessNotFoundError(f"Business {business_id} not found")
        return biz

    def list_user_businesses(self, user_id: uuid.UUID) -> List[Business]:
        return self.business_repo.list_by_user(user_id)

    def update_business(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        address: Optional[str] = None,
        financial_year_start: Optional[str] = None,
        currency: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Business:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        biz = self.business_repo.get_by_id(business_id)
        if not biz:
            raise BusinessNotFoundError(f"Business {business_id} not found")

        if name is not None:
            biz.name = name.strip()
        if industry is not None:
            biz.industry = industry.strip()
        if address is not None:
            biz.address = address.strip()
        if financial_year_start is not None:
            biz.financial_year_start = financial_year_start
        if currency is not None:
            biz.currency = currency.upper()
        if preferences is not None:
            biz.preferences.update(preferences)

        return self.business_repo.update(biz)

    def set_business_archived(self, business_id: uuid.UUID, user_id: uuid.UUID, is_archived: bool) -> None:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER])
        self.business_repo.set_archived(business_id, is_archived)

    def delete_business(self, business_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER])
        self.business_repo.delete(business_id)

    def add_member(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: BusinessRole,
    ) -> BusinessMembership:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER])
        if role == BusinessRole.OWNER:
            raise InvalidOperationError("A workspace owner cannot be assigned through member management.")
        existing = self.business_repo.get_membership(business_id, target_user_id)
        if existing and existing.role == BusinessRole.OWNER:
            raise InvalidOperationError("The workspace owner's role cannot be changed.")
        membership = BusinessMembership(
            id=uuid.uuid4(),
            business_id=business_id,
            user_id=target_user_id,
            role=role,
        )
        saved = self.business_repo.add_member(membership)
        from backend.arthlens.security.audit import get_audit_service

        get_audit_service().record_event(
            actor=user_id,
            action="BUSINESS_MEMBER_ACTIVATED",
            target=f"business_member:{business_id}:{target_user_id}",
            payload={"role": saved.role.value},
        )
        return saved

    def list_members(self, business_id: uuid.UUID, user_id: uuid.UUID) -> List[BusinessMembership]:
        self.verify_access(business_id, user_id)
        return self.business_repo.list_members(business_id)

    def remove_member(self, business_id: uuid.UUID, user_id: uuid.UUID, target_user_id: uuid.UUID) -> bool:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER])
        target = self.business_repo.get_membership(business_id, target_user_id)
        if target and target.role == BusinessRole.OWNER:
            raise InvalidOperationError("The workspace owner membership cannot be removed.")
        changed = self.business_repo.remove_member(business_id, target_user_id)
        if changed:
            from backend.arthlens.security.audit import get_audit_service

            get_audit_service().record_event(
                actor=user_id,
                action="BUSINESS_MEMBER_DEACTIVATED",
                target=f"business_member:{business_id}:{target_user_id}",
                payload={},
            )
        return changed

    def update_member_role(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        target_user_id: uuid.UUID,
        role: BusinessRole,
    ) -> BusinessMembership:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER])
        if role == BusinessRole.OWNER:
            raise InvalidOperationError("The workspace owner role cannot be assigned to another member.")
        target = self.business_repo.get_membership(business_id, target_user_id)
        if target is None or not target.is_active:
            raise BusinessNotFoundError("The active workspace membership was not found.")
        if target.role == BusinessRole.OWNER:
            raise InvalidOperationError("The workspace owner's role cannot be changed.")
        old_role = target.role
        updated = self.business_repo.update_member_role(business_id, target_user_id, role)
        if updated is None:
            raise BusinessNotFoundError("The active workspace membership was not found.")
        from backend.arthlens.security.audit import get_audit_service

        get_audit_service().record_event(
            actor=user_id,
            action="BUSINESS_MEMBER_ROLE_UPDATED",
            target=f"business_member:{business_id}:{target_user_id}",
            payload={"old_role": old_role.value, "new_role": updated.role.value},
        )
        return updated

    # ==========================================================================
    # 2. Khata & Parties: Customers & Suppliers (UC-09 to UC-18)
    # ==========================================================================

    def create_customer(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        phone: str = "",
        email: str = "",
        address: str = "",
        credit_limit: float = 0.0,
        opening_balance: float = 0.0,
    ) -> Customer:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        open_bal = Money.from_decimal(opening_balance)
        cust = Customer(
            id=uuid.uuid4(),
            business_id=business_id,
            name=name.strip(),
            phone=phone.strip(),
            email=email.strip(),
            address=address.strip(),
            credit_limit=Money.from_decimal(credit_limit),
            opening_balance=open_bal,
            current_balance=open_bal,
        )
        return self.customer_repo.create(cust)

    def get_customer(self, business_id: uuid.UUID, customer_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Customer:
        if user_id is not None:
            self.verify_access(business_id, user_id)
        cust = self.customer_repo.get_by_id(customer_id)
        if not cust or cust.business_id != business_id:
            raise InvalidOperationError(f"Customer {customer_id} does not belong to authorized business {business_id}")
        return cust

    def list_customers(self, business_id: uuid.UUID, user_id: uuid.UUID, include_archived: bool = False) -> List[Customer]:
        self.verify_access(business_id, user_id)
        return self.customer_repo.list_by_business(business_id, include_archived=include_archived)

    def update_customer(
        self,
        business_id: uuid.UUID,
        customer_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        credit_limit: Optional[float] = None,
    ) -> Customer:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        cust = self.get_customer(business_id, customer_id, user_id)
        if name is not None:
            cust.name = name.strip()
        if phone is not None:
            cust.phone = phone.strip()
        if email is not None:
            cust.email = email.strip()
        if address is not None:
            cust.address = address.strip()
        if credit_limit is not None:
            cust.credit_limit = Money.from_decimal(credit_limit)
        return self.customer_repo.update(cust)

    def get_customer_ledger(self, business_id: uuid.UUID, customer_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Calculates running transaction statement and outstanding receivables for a customer."""
        cust = self.get_customer(business_id, customer_id, user_id)
        invoices = self.invoice_repo.list_by_business(business_id, customer_id=customer_id)
        payments = self.payment_repo.list_by_business(business_id, party_id=customer_id)

        entries = []
        # Opening balance entry
        if not cust.opening_balance.is_zero():
            opening_debit = cust.opening_balance if cust.opening_balance.is_positive() else Money.zero()
            opening_credit = -cust.opening_balance if cust.opening_balance.amount < 0 else Money.zero()
            entries.append({
                "date": cust.created_at.date().isoformat(),
                "type": "OPENING_BALANCE",
                "reference": "OPENING",
                "debit": float(opening_debit.amount),
                "debit_exact": f"{opening_debit.amount:.2f}",
                "credit": float(opening_credit.amount),
                "credit_exact": f"{opening_credit.amount:.2f}",
                "notes": "Opening Receivables Balance",
            })

        for inv in invoices:
            entries.append({
                "date": inv.invoice_date.isoformat(),
                "type": "INVOICE",
                "reference": inv.invoice_number,
                "debit": float(inv.total_amount.amount),
                "debit_exact": f"{inv.total_amount.amount:.2f}",
                "credit": 0.0,
                "credit_exact": "0.00",
                "credit_exact": "0.00",
                "status": inv.status.value,
                "notes": inv.notes,
            })

        for p in payments:
            entries.append({
                "date": p.payment_date.isoformat(),
                "type": "PAYMENT",
                "reference": str(p.reference_id or p.id),
                "debit": 0.0,
                "debit_exact": "0.00",
                "credit": float(p.amount.amount),
                "credit_exact": f"{p.amount.amount:.2f}",
                "payment_method": p.payment_method.value,
                "notes": p.notes,
            })

        entries.sort(key=lambda x: x["date"])
        running_bal = Decimal("0.00")
        for e in entries:
            running_bal += Decimal(e["debit_exact"]) - Decimal(e["credit_exact"])
            e["running_balance"] = float(running_bal)
            e["running_balance_exact"] = f"{running_bal:.2f}"

        return {
            "customer_id": str(cust.id),
            "customer_name": cust.name,
            "credit_limit": float(cust.credit_limit.amount),
            "credit_limit_exact": f"{cust.credit_limit.amount:.2f}",
            "current_balance": float(cust.current_balance.amount),
            "current_balance_exact": f"{cust.current_balance.amount:.2f}",
            "formatted_balance": cust.current_balance.format_inr(),
            "entries": entries,
        }

    def create_supplier(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        contact_person: str = "",
        phone: str = "",
        email: str = "",
        address: str = "",
        opening_balance: float = 0.0,
    ) -> Supplier:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        open_bal = Money.from_decimal(opening_balance)
        sup = Supplier(
            id=uuid.uuid4(),
            business_id=business_id,
            name=name.strip(),
            contact_person=contact_person.strip(),
            phone=phone.strip(),
            email=email.strip(),
            address=address.strip(),
            opening_balance=open_bal,
            current_balance=open_bal,
        )
        return self.supplier_repo.create(sup)

    def get_supplier(self, business_id: uuid.UUID, supplier_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Supplier:
        if user_id is not None:
            self.verify_access(business_id, user_id)
        sup = self.supplier_repo.get_by_id(supplier_id)
        if not sup or sup.business_id != business_id:
            raise InvalidOperationError(f"Supplier {supplier_id} does not belong to authorized business {business_id}")
        return sup

    def list_suppliers(self, business_id: uuid.UUID, user_id: uuid.UUID, include_archived: bool = False) -> List[Supplier]:
        self.verify_access(business_id, user_id)
        return self.supplier_repo.list_by_business(business_id, include_archived=include_archived)

    def get_supplier_ledger(self, business_id: uuid.UUID, supplier_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Calculates running transaction statement and outstanding payables for a supplier."""
        sup = self.get_supplier(business_id, supplier_id, user_id)
        purchases = self.purchase_repo.list_by_business(business_id, supplier_id=supplier_id)
        payments = self.payment_repo.list_by_business(business_id, party_id=supplier_id)

        entries = []
        if not sup.opening_balance.is_zero():
            opening_credit = sup.opening_balance if sup.opening_balance.is_positive() else Money.zero()
            opening_debit = -sup.opening_balance if sup.opening_balance.amount < 0 else Money.zero()
            entries.append({
                "date": sup.created_at.date().isoformat(),
                "type": "OPENING_BALANCE",
                "reference": "OPENING",
                "credit": float(opening_credit.amount),
                "credit_exact": f"{opening_credit.amount:.2f}",
                "debit": float(opening_debit.amount),
                "debit_exact": f"{opening_debit.amount:.2f}",
                "notes": "Opening Payables Balance",
            })

        for p in purchases:
            entries.append({
                "date": p.purchase_date.isoformat(),
                "type": "PURCHASE_BILL",
                "reference": p.bill_number,
                "credit": float(p.total_amount.amount),
                "credit_exact": f"{p.total_amount.amount:.2f}",
                "debit": 0.0,
                "debit_exact": "0.00",
                "status": p.status.value,
                "notes": "",
            })

        for pm in payments:
            entries.append({
                "date": pm.payment_date.isoformat(),
                "type": "PAYMENT",
                "reference": str(pm.reference_id or pm.id),
                "credit": 0.0,
                "credit_exact": "0.00",
                "debit": float(pm.amount.amount),
                "debit_exact": f"{pm.amount.amount:.2f}",
                "payment_method": pm.payment_method.value,
                "notes": pm.notes,
            })

        entries.sort(key=lambda x: x["date"])
        running_bal = Decimal("0.00")
        for e in entries:
            running_bal += Decimal(e["credit_exact"]) - Decimal(e["debit_exact"])
            e["running_balance"] = float(running_bal)
            e["running_balance_exact"] = f"{running_bal:.2f}"

        return {
            "supplier_id": str(sup.id),
            "supplier_name": sup.name,
            "current_balance": float(sup.current_balance.amount),
            "current_balance_exact": f"{sup.current_balance.amount:.2f}",
            "formatted_balance": sup.current_balance.format_inr(),
            "entries": entries,
        }

    def update_supplier(
        self,
        business_id: uuid.UUID,
        supplier_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Supplier:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        sup = self.get_supplier(business_id, supplier_id, user_id)
        if name is not None:
            sup.name = name.strip()
        if contact_person is not None:
            sup.contact_person = contact_person.strip()
        if phone is not None:
            sup.phone = phone.strip()
        if email is not None:
            sup.email = email.strip()
        if address is not None:
            sup.address = address.strip()
        return self.supplier_repo.update(sup)

    # ==========================================================================
    # 3. Product Catalog & Inventory Management (UC-35 to UC-42)
    # ==========================================================================

    def create_product(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        sku: str,
        name: str,
        category: str,
        unit: str,
        purchase_price: float,
        selling_price: float,
        min_stock_alert: float = 0.0,
        initial_stock: float = 0.0,
    ) -> Product:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        prod = Product(
            id=uuid.uuid4(),
            business_id=business_id,
            sku=sku.strip(),
            name=name.strip(),
            category=category.strip(),
            unit=unit.strip(),
            purchase_price=Money.from_decimal(purchase_price),
            selling_price=Money.from_decimal(selling_price),
            min_stock_alert=Decimal(str(min_stock_alert)),
        )
        saved_prod = self.product_repo.create(prod)

        # Initialize inventory balance record
        init_qty = Decimal(str(initial_stock))
        init_cost = Money.from_decimal(purchase_price)
        bal = InventoryBalance(
            id=uuid.uuid4(),
            business_id=business_id,
            product_id=saved_prod.id,
            quantity_on_hand=init_qty,
            unit_cost=init_cost,
            total_valuation=init_cost * init_qty if init_qty > 0 else Money.zero(),
        )
        self.inventory_repo.save_balance(bal)

        if init_qty > 0:
            mov = InventoryMovement(
                id=uuid.uuid4(),
                business_id=business_id,
                product_id=saved_prod.id,
                movement_type=MovementType.OPENING,
                quantity=init_qty,
                unit_price=init_cost,
                reference_id="INIT",
                reason="Initial inventory opening stock",
                balance_after=init_qty,
                cost_basis=init_cost,
            )
            self.inventory_repo.record_movement(mov)

        return saved_prod

    def get_product(self, business_id: uuid.UUID, product_id: uuid.UUID, user_id: uuid.UUID) -> Product:
        self.verify_access(business_id, user_id)
        prod = self.product_repo.get_by_id(product_id)
        if not prod or prod.business_id != business_id:
            raise InvalidOperationError(f"Product {product_id} does not belong to authorized business {business_id}")
        return prod

    def update_product(
        self,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        name: Optional[str] = None,
        category: Optional[str] = None,
        unit: Optional[str] = None,
        purchase_price: Optional[float] = None,
        selling_price: Optional[float] = None,
        min_stock_alert: Optional[float] = None,
        is_active: Optional[bool] = None,
    ) -> Product:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        prod = self.get_product(business_id, product_id, user_id)
        if name is not None:
            prod.name = name.strip()
        if category is not None:
            prod.category = category.strip()
        if unit is not None:
            prod.unit = unit.strip()
        if purchase_price is not None:
            prod.purchase_price = Money.from_decimal(purchase_price)
        if selling_price is not None:
            prod.selling_price = Money.from_decimal(selling_price)
        if min_stock_alert is not None:
            prod.min_stock_alert = Decimal(str(min_stock_alert))
        if is_active is not None:
            prod.is_active = is_active
        return self.product_repo.update(prod)

    def list_products(self, business_id: uuid.UUID, user_id: uuid.UUID, active_only: bool = False) -> List[Product]:
        self.verify_access(business_id, user_id)
        return self.product_repo.list_by_business(business_id, active_only=active_only)

    def adjust_inventory(
        self,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        movement_type: MovementType,
        quantity: float,
        unit_price: float,
        reason: str,
        reference_id: str = "MANUAL",
    ) -> InventoryBalance:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        qty = Decimal(str(quantity))
        if qty <= 0:
            raise InvalidOperationError("Adjustment quantity must be strictly positive")

        u_price = Money.from_decimal(unit_price)
        val_delta = u_price * qty

        with self.session_factory() as session:
            with session.begin():
                bal = self.inventory_repo.get_balance(business_id, product_id, session=session, for_update=True)
                if not bal:
                    bal = InventoryBalance(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        product_id=product_id,
                        quantity_on_hand=Decimal("0.00"),
                        unit_cost=Money.zero(),
                        total_valuation=Money.zero(),
                    )

                if movement_type in (MovementType.PURCHASE, MovementType.RETURN, MovementType.OPENING, MovementType.ADJUSTMENT) and qty > 0:
                    movement_cost_basis = u_price
                    bal.apply_addition(qty, u_price)
                    saved_bal = self.inventory_repo.save_balance(bal, session=session)
                    # GL posting for inventory addition/gain
                    if val_delta > Money.zero():
                        self._post_gl_entry(
                            business_id=business_id,
                            entry_date=date.today(),
                            reference_type="INVENTORY_ADJUSTMENT",
                            description=f"Inventory Adjustment: {reason}",
                            lines_data=[
                                (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], val_delta, Money.zero()),
                                (StandardAccount.INVENTORY_GAIN.value, ACCOUNT_NAMES[StandardAccount.INVENTORY_GAIN.value], Money.zero(), val_delta),
                            ],
                            reference_id=product_id,
                            session=session,
                        )
                else:
                    if bal.quantity_on_hand < qty:
                        raise InsufficientInventoryError(
                            f"Insufficient stock on hand: requested {qty}, available {bal.quantity_on_hand}"
                        )
                    movement_cost_basis = bal.unit_cost
                    bal.apply_deduction(qty)
                    saved_bal = self.inventory_repo.save_balance(bal, session=session)
                    # GL posting for inventory shrinkage/loss
                    if val_delta > Money.zero():
                        self._post_gl_entry(
                            business_id=business_id,
                            entry_date=date.today(),
                            reference_type="INVENTORY_ADJUSTMENT",
                            description=f"Inventory Adjustment: {reason}",
                            lines_data=[
                                (StandardAccount.INVENTORY_LOSS.value, ACCOUNT_NAMES[StandardAccount.INVENTORY_LOSS.value], val_delta, Money.zero()),
                                (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], Money.zero(), val_delta),
                            ],
                            reference_id=product_id,
                            session=session,
                        )

                mov = InventoryMovement(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    product_id=product_id,
                    movement_type=movement_type,
                    quantity=qty,
                    unit_price=u_price,
                    reference_id=reference_id,
                    reason=reason,
                    balance_after=saved_bal.quantity_on_hand,
                    cost_basis=movement_cost_basis,
                )
                self.inventory_repo.record_movement(mov, session=session)
                return saved_bal

    def list_inventory_balances(
        self,
        business_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        low_stock_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if user_id is not None:
            self.verify_access(business_id, user_id)
        balances = self.inventory_repo.list_balances(business_id)
        products = {p.id: p for p in self.product_repo.list_by_business(business_id)}

        result = []
        for b in balances:
            prod = products.get(b.product_id)
            if not prod:
                continue
            is_low = b.quantity_on_hand <= prod.min_stock_alert
            if low_stock_only and not is_low:
                continue
            result.append({
                "product_id": str(b.product_id),
                "sku": prod.sku,
                "name": prod.name,
                "category": prod.category,
                "unit": prod.unit,
                "quantity_on_hand": float(b.quantity_on_hand),
                "unit_cost": float(b.unit_cost.amount),
                "unit_cost_exact": f"{b.unit_cost.amount:.2f}",
                "total_valuation": float(b.total_valuation.amount),
                "total_valuation_exact": f"{b.total_valuation.amount:.2f}",
                "currency": b.total_valuation.currency,
                "min_stock_alert": float(prod.min_stock_alert),
                "is_low_stock": is_low,
                "last_movement_at": b.last_movement_at.isoformat(),
            })
        return result

    def list_inventory_movements(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        product_id: Optional[uuid.UUID] = None,
    ) -> List[InventoryMovement]:
        self.verify_access(business_id, user_id)
        return self.inventory_repo.list_movements(business_id, product_id=product_id)

    def list_unreconciled_inventory_movements(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        self.verify_access(business_id, user_id)
        return self.inventory_cost_service.list_unreconciled_inventory_movements(business_id)

    def reconcile_historical_inventory_costs(
        self,
        business_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        mode: str,
        overrides: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.verify_access(
            business_id,
            actor_user_id,
            [BusinessRole.OWNER, BusinessRole.ACCOUNTANT],
        )
        return self.inventory_cost_service.reconcile_historical_inventory_costs(
            business_id,
            actor_user_id,
            mode,
            overrides,
            post_journal_entry=self._post_gl_entry,
        )

    def list_inventory_cost_reconciliation_history(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        self.verify_access(business_id, user_id)
        return self.inventory_cost_service.list_history(business_id)

    # ==========================================================================
    # 4. Sales & Invoicing (UC-19 to UC-26)
    # ==========================================================================

    def create_sales_invoice(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        customer_id: Optional[uuid.UUID],
        invoice_number: str,
        invoice_date: date,
        due_date: date,
        items: List[Dict[str, Any]],
        tax_amount: float = 0.0,
        discount_amount: float = 0.0,
        notes: str = "",
        is_cash_sale: bool = False,
        immediate_payment_method: Optional[PaymentMethod] = None,
    ) -> SalesInvoice:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])

        if not items:
            raise InvalidOperationError("Sales invoice must contain at least one line item")

        invoice_id = uuid.uuid4()
        line_items: List[SalesInvoiceItem] = []
        subtotal = Money.zero()

        existing_prods = self.product_repo.list_by_business(business_id)
        prod_by_name = {p.name.strip().lower(): p for p in existing_prods}

        for it in items:
            p_id = uuid.UUID(str(it["product_id"])) if it.get("product_id") else None
            desc = it.get("description", "").strip()
            if not p_id and desc and desc.lower() in prod_by_name:
                p_id = prod_by_name[desc.lower()].id
            if p_id:
                prod = self.product_repo.get_by_id(p_id)
                if not prod or prod.business_id != business_id:
                    raise InvalidOperationError(f"Product {p_id} does not belong to authorized business {business_id}")
            qty = Decimal(str(it["quantity"]))
            u_price = Money.from_decimal(it["unit_price"])
            disc_pct = Decimal(str(it.get("discount_percent", 0.0)))
            item_entity = SalesInvoiceItem(
                id=uuid.uuid4(),
                invoice_id=invoice_id,
                product_id=p_id,
                description=it["description"].strip(),
                quantity=qty,
                unit=it.get("unit", "pcs"),
                unit_price=u_price,
                discount_percent=disc_pct,
            )
            item_total = item_entity.calculate_total()
            subtotal = subtotal + item_total
            line_items.append(item_entity)

        t_amt = Money.from_decimal(tax_amount)
        d_amt = Money.from_decimal(discount_amount)
        total_amt = subtotal + t_amt - d_amt

        # Check customer belongs to business and credit limit if credit sale
        customer = None
        if customer_id:
            customer = self.get_customer(business_id, customer_id, user_id)
            if not customer or customer.business_id != business_id:
                raise InvalidOperationError(f"Customer {customer_id} does not belong to authorized business {business_id}")
            if not is_cash_sale and customer.credit_limit.is_positive():
                new_bal = customer.current_balance + total_amt
                if new_bal > customer.credit_limit:
                    raise CreditLimitExceededError(
                        f"Invoice total ₹{total_amt.amount} exceeds customer credit limit ₹{customer.credit_limit.amount} (current dues: ₹{customer.current_balance.amount})"
                    )

        with self.session_factory() as session:
            with session.begin():
                # Deduct stock for inventory-tracked products
                cogs_amount = Money.zero()
                for line in line_items:
                    if line.product_id:
                        bal = self.inventory_repo.get_balance(business_id, line.product_id, session=session, for_update=True)
                        if not bal:
                            raise InsufficientInventoryError(
                                f"No inventory recorded for '{line.description}'; units must be purchased or initialized before sale."
                            )
                        if bal.quantity_on_hand < line.quantity:
                            raise InsufficientInventoryError(
                                f"Insufficient stock (units on hand) for '{line.description}': requested {line.quantity}, available {bal.quantity_on_hand}. Please record an inward purchase bill or adjust inventory first."
                            )
                        sale_cost = bal.unit_cost
                        cogs_amount = cogs_amount + (sale_cost * line.quantity)
                        bal.apply_deduction(line.quantity)
                        self.inventory_repo.save_balance(bal, session=session)
                        mov = InventoryMovement(
                            id=uuid.uuid4(),
                            business_id=business_id,
                            product_id=line.product_id,
                            movement_type=MovementType.SALE,
                            quantity=line.quantity,
                            unit_price=line.unit_price,
                            reference_id=str(invoice_id),
                            reason=f"Sale Invoice {invoice_number}",
                            balance_after=bal.quantity_on_hand,
                            cost_basis=sale_cost,
                        )
                        self.inventory_repo.record_movement(mov, session=session)

                inv = SalesInvoice(
                    id=invoice_id,
                    business_id=business_id,
                    customer_id=customer_id,
                    invoice_number=invoice_number.strip(),
                    invoice_date=invoice_date,
                    due_date=due_date,
                    subtotal=subtotal,
                    tax_amount=t_amt,
                    discount_amount=d_amt,
                    total_amount=total_amt,
                    paid_amount=total_amt if is_cash_sale else Money.zero(),
                    status=InvoiceStatus.PAID if is_cash_sale else InvoiceStatus.ISSUED,
                    notes=notes.strip(),
                    items=line_items,
                )
                saved_inv = self.invoice_repo.create(inv, session=session)

                # Update customer balance with row locking or record cash payment
                if is_cash_sale:
                    pay = Payment(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        party_type=PartyType.CUSTOMER,
                        party_id=customer_id,
                        reference_type="INVOICE",
                        reference_id=invoice_id,
                        payment_type=PaymentType.RECEIVED,
                        payment_method=immediate_payment_method or PaymentMethod.CASH,
                        amount=total_amt,
                        payment_date=invoice_date,
                        notes=f"Cash payment for invoice {invoice_number}",
                    )
                    self.payment_repo.create(pay, session=session)
                elif customer_id:
                    cust_locked = self.customer_repo.get_by_id(customer_id, session=session, for_update=True)
                    if cust_locked:
                        if cust_locked.credit_limit.is_positive():
                            new_bal = cust_locked.current_balance + total_amt
                            if new_bal > cust_locked.credit_limit:
                                raise CreditLimitExceededError(
                                    f"Invoice total ₹{total_amt.amount} exceeds customer credit limit ₹{cust_locked.credit_limit.amount} (current dues: ₹{cust_locked.current_balance.amount})"
                                )
                        cust_locked.add_receivable(total_amt)
                        self.customer_repo.update_balance(cust_locked.id, cust_locked.current_balance, session=session)

                # Post Double-Entry General Ledger Journal Entry for Sales Revenue & Tax
                net_revenue = subtotal - d_amt
                debit_account = StandardAccount.CASH.value if is_cash_sale else StandardAccount.ACCOUNTS_RECEIVABLE.value
                gl_lines = [
                    (debit_account, ACCOUNT_NAMES[debit_account], total_amt, Money.zero()),
                    (StandardAccount.SALES_REVENUE.value, ACCOUNT_NAMES[StandardAccount.SALES_REVENUE.value], Money.zero(), net_revenue),
                ]
                if t_amt > Money.zero():
                    gl_lines.append((StandardAccount.OUTPUT_TAX.value, ACCOUNT_NAMES[StandardAccount.OUTPUT_TAX.value], Money.zero(), t_amt))

                if cogs_amount > Money.zero():
                    self._post_gl_entry(
                        business_id=business_id,
                        entry_date=invoice_date,
                        reference_type="INVOICE_COGS",
                        description=f"Cost of goods sold for Invoice {invoice_number}",
                        lines_data=[
                            (StandardAccount.COGS.value, ACCOUNT_NAMES[StandardAccount.COGS.value], cogs_amount, Money.zero()),
                            (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], Money.zero(), cogs_amount),
                        ],
                        reference_id=invoice_id,
                        session=session,
                    )

                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=invoice_date,
                    reference_type="INVOICE",
                    description=f"Sales Invoice {invoice_number}",
                    lines_data=gl_lines,
                    reference_id=invoice_id,
                    session=session,
                )

        return saved_inv

    def get_sales_invoice(self, business_id: uuid.UUID, invoice_id: uuid.UUID, user_id: uuid.UUID) -> SalesInvoice:
        self.verify_access(business_id, user_id)
        inv = self.invoice_repo.get_by_id(invoice_id)
        if not inv or inv.business_id != business_id:
            raise InvalidOperationError(f"Invoice {invoice_id} does not belong to authorized business {business_id}")
        return inv

    def list_sales_invoices(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        customer_id: Optional[uuid.UUID] = None,
    ) -> List[SalesInvoice]:
        self.verify_access(business_id, user_id)
        return self.invoice_repo.list_by_business(business_id, customer_id=customer_id)

    def record_invoice_payment(
        self,
        business_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: PaymentMethod,
        notes: str = "",
        idempotency_key: Optional[str] = None,
    ) -> SalesInvoice:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        pay_money = Money.from_decimal(amount)
        if pay_money <= Money.zero():
            raise InvalidOperationError("Payment amount must be strictly positive")

        with self.session_factory() as session:
            with session.begin():
                # Lock invoice row to prevent concurrent overpayment race conditions
                inv = self.invoice_repo.get_by_id(invoice_id, session=session, for_update=True)
                if not inv or inv.business_id != business_id:
                    raise InvalidOperationError(f"Sales invoice {invoice_id} not found for business {business_id}")

                # Idempotency check inside locked transaction
                if inv.status == InvoiceStatus.CANCELLED:
                    raise InvalidOperationError("Cannot record payment against a cancelled invoice")
                if idempotency_key:
                    existing = self.payment_repo.find_by_idempotency_key(business_id, idempotency_key, session=session)
                    if existing:
                        # Verify parameters match existing payment record
                        if (
                            str(existing.reference_id) == str(invoice_id)
                            and existing.amount == pay_money
                            and existing.payment_type == PaymentType.RECEIVED
                        ):
                            return inv
                        raise IdempotencyConflictError(
                            f"Idempotency key '{idempotency_key}' was previously used for a conflicting payment."
                        )

                if pay_money > inv.outstanding_balance:
                    raise InvalidOperationError(
                        f"Payment amount ₹{pay_money.amount} exceeds invoice outstanding balance ₹{inv.outstanding_balance.amount}"
                    )

                inv.record_payment(pay_money)
                self.invoice_repo.update_payment(inv.id, inv.paid_amount, inv.status, session=session)

                # Record payment transaction
                pay = Payment(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    party_type=PartyType.CUSTOMER,
                    party_id=inv.customer_id,
                    reference_type="INVOICE",
                    reference_id=inv.id,
                    payment_type=PaymentType.RECEIVED,
                    payment_method=payment_method,
                    amount=pay_money,
                    payment_date=payment_date,
                    idempotency_key=idempotency_key,
                    notes=notes or f"Payment against Invoice {inv.invoice_number}",
                )
                self.payment_repo.create(pay, session=session)

                # Update customer balance with locking
                if inv.customer_id:
                    cust = self.customer_repo.get_by_id(inv.customer_id, session=session, for_update=True)
                    if cust:
                        cust.apply_payment(pay_money)
                        self.customer_repo.update_balance(cust.id, cust.current_balance, session=session)

                # Post GL Journal Entry for payment receipt
                gl_acc = StandardAccount.BANK.value if payment_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI, PaymentMethod.CHEQUE) else StandardAccount.CASH.value
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=payment_date,
                    reference_type="PAYMENT",
                    description=f"Payment received for Invoice {inv.invoice_number}",
                    lines_data=[
                        (gl_acc, ACCOUNT_NAMES[gl_acc], pay_money, Money.zero()),
                        (StandardAccount.ACCOUNTS_RECEIVABLE.value, ACCOUNT_NAMES[StandardAccount.ACCOUNTS_RECEIVABLE.value], Money.zero(), pay_money),
                    ],
                    reference_id=inv.id,
                    session=session,
                )

        return inv

    def cancel_sales_invoice(self, business_id: uuid.UUID, invoice_id: uuid.UUID, user_id: uuid.UUID, reason: str) -> SalesInvoice:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        with self.session_factory() as session:
            with session.begin():
                inv = self.invoice_repo.get_by_id(invoice_id, session=session, for_update=True)
                if not inv or inv.business_id != business_id:
                    raise InvalidOperationError(f"Sales invoice {invoice_id} not found for business {business_id}")
                if inv.status == InvoiceStatus.CANCELLED:
                    raise InvalidOperationError("Invoice is already cancelled")
                if inv.paid_amount > Money.zero():
                    raise InvalidOperationError(
                        "A paid or partially paid invoice cannot be cancelled; record a refund or sales return."
                    )

                inventory_costs = self._invoice_inventory_costs(business_id, inv, session)
                cancellation_cogs = Money.zero()
                for item in inv.items:
                    if not item.product_id:
                        continue
                    total_qty, total_cost = inventory_costs[item.product_id]
                    unit_cost = total_cost / total_qty
                    bal = self.inventory_repo.get_balance(business_id, item.product_id, session=session, for_update=True)
                    if not bal:
                        raise InvalidOperationError(
                            f"Inventory balance is missing for product {item.product_id}; invoice cancellation was not applied."
                        )
                    bal.apply_addition(item.quantity, unit_cost)
                    self.inventory_repo.save_balance(bal, session=session)
                    cancellation_cogs = cancellation_cogs + (unit_cost * item.quantity)
                    mov = InventoryMovement(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        product_id=item.product_id,
                        movement_type=MovementType.RETURN,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        reference_id=str(invoice_id),
                        reason=f"Invoice cancellation: {reason}",
                        balance_after=bal.quantity_on_hand,
                        cost_basis=unit_cost,
                    )
                    self.inventory_repo.record_movement(mov, session=session)

                # Reverse customer balance with lock
                if inv.customer_id and inv.outstanding_balance.is_positive():
                    cust = self.customer_repo.get_by_id(inv.customer_id, session=session, for_update=True)
                    if cust:
                        cust.apply_payment(inv.outstanding_balance)
                        self.customer_repo.update_balance(cust.id, cust.current_balance, session=session)

                # Reverse the original receivable, revenue and tax posting. Keep
                # this as a separate immutable journal entry for auditability.
                sales_revenue = inv.subtotal - inv.discount_amount
                reversal_lines = [
                    (
                        StandardAccount.SALES_REVENUE.value,
                        ACCOUNT_NAMES[StandardAccount.SALES_REVENUE.value],
                        sales_revenue,
                        Money.zero(),
                    ),
                    (
                        StandardAccount.ACCOUNTS_RECEIVABLE.value,
                        ACCOUNT_NAMES[StandardAccount.ACCOUNTS_RECEIVABLE.value],
                        Money.zero(),
                        inv.total_amount,
                    ),
                ]
                if inv.tax_amount > Money.zero():
                    reversal_lines.append(
                        (
                            StandardAccount.OUTPUT_TAX.value,
                            ACCOUNT_NAMES[StandardAccount.OUTPUT_TAX.value],
                            inv.tax_amount,
                            Money.zero(),
                        )
                    )
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=date.today(),
                    reference_type="INVOICE_CANCELLATION",
                    description=f"Cancellation of Sales Invoice {inv.invoice_number}: {reason}",
                    lines_data=reversal_lines,
                    reference_id=inv.id,
                    session=session,
                )

                if cancellation_cogs > Money.zero():
                    self._post_gl_entry(
                        business_id=business_id,
                        entry_date=date.today(),
                        reference_type="INVOICE_CANCELLATION_COGS",
                        description=f"Cost reversal for cancellation of Invoice {inv.invoice_number}: {reason}",
                        lines_data=[
                            (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], cancellation_cogs, Money.zero()),
                            (StandardAccount.COGS.value, ACCOUNT_NAMES[StandardAccount.COGS.value], Money.zero(), cancellation_cogs),
                        ],
                        reference_id=inv.id,
                        session=session,
                    )

                self.invoice_repo.update_status(inv.id, InvoiceStatus.CANCELLED, session=session)
                inv.status = InvoiceStatus.CANCELLED
                return inv

    def update_sales_invoice(
        self,
        business_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        customer_id: Optional[uuid.UUID],
        invoice_date: date,
        due_date: Optional[date],
        items: List[Dict[str, Any]],
        tax_amount: float = 0.0,
        notes: str = "",
    ) -> SalesInvoice:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        with self.session_factory() as session:
            with session.begin():
                inv = self.invoice_repo.get_by_id(invoice_id, session=session, for_update=True)
                if not inv or inv.business_id != business_id:
                    raise InvalidOperationError(f"Sales invoice {invoice_id} not found for business {business_id}")
                if inv.paid_amount > Money.zero():
                    raise InvalidOperationError("A paid or partially paid invoice cannot be edited; delete payments first.")
                if inv.status == InvoiceStatus.CANCELLED:
                    raise InvalidOperationError("A cancelled invoice cannot be edited.")

                for old_item in inv.items:
                    if old_item.product_id:
                        bal = self.inventory_repo.get_balance(business_id, old_item.product_id, session=session, for_update=True)
                        if bal:
                            bal.apply_addition(old_item.quantity, bal.unit_cost)
                            self.inventory_repo.save_balance(bal, session=session)

                if inv.customer_id and inv.outstanding_balance.is_positive():
                    old_cust = self.customer_repo.get_by_id(inv.customer_id, session=session, for_update=True)
                    if old_cust:
                        old_cust.apply_payment(inv.outstanding_balance)
                        self.customer_repo.update_balance(old_cust.id, old_cust.current_balance, session=session)

                session.execute(delete(SalesInvoiceItemModel).where(SalesInvoiceItemModel.invoice_id == invoice_id))

                existing_prods = self.product_repo.list_by_business(business_id)
                prod_by_name = {p.name.strip().lower(): p for p in existing_prods}

                subtotal = Money.zero()
                for it in items:
                    p_id = uuid.UUID(str(it["product_id"])) if it.get("product_id") else None
                    desc = it.get("description", "").strip()
                    if not p_id and desc and desc.lower() in prod_by_name:
                        p_id = prod_by_name[desc.lower()].id
                    qty = Decimal(str(it["quantity"]))
                    u_price = Money.from_decimal(it["unit_price"])
                    t_price = u_price * qty
                    subtotal = subtotal + t_price
                    item_model = SalesInvoiceItemModel(
                        id=uuid.uuid4(),
                        invoice_id=invoice_id,
                        product_id=p_id,
                        description=it["description"].strip(),
                        quantity=qty,
                        unit=it.get("unit", "pcs"),
                        unit_price=u_price.amount,
                        discount_percent=Decimal(str(it.get("discount_percent", 0.0))),
                        total_price=t_price.amount,
                    )
                    session.add(item_model)
                    if p_id:
                        bal = self.inventory_repo.get_balance(business_id, p_id, session=session, for_update=True)
                        if bal:
                            if bal.quantity_on_hand < qty:
                                raise InsufficientInventoryError(
                                    f"Insufficient stock (units on hand) for '{it.get('description', 'item')}': requested {qty}, available {bal.quantity_on_hand}. Please record an inward purchase bill or adjust inventory first."
                                )
                            bal.apply_deduction(qty)
                            self.inventory_repo.save_balance(bal, session=session)

                tax = Money.from_decimal(tax_amount)
                total = subtotal + tax

                inv_model = session.get(SalesInvoiceModel, invoice_id)
                inv_model.customer_id = customer_id
                inv_model.invoice_date = invoice_date
                inv_model.due_date = due_date
                inv_model.subtotal = subtotal.amount
                inv_model.tax_amount = tax.amount
                inv_model.total_amount = total.amount
                inv_model.notes = notes
                session.flush()

                if customer_id:
                    new_cust = self.customer_repo.get_by_id(customer_id, session=session, for_update=True)
                    if new_cust:
                        new_cust.current_balance = new_cust.current_balance + total
                        self.customer_repo.update_balance(new_cust.id, new_cust.current_balance, session=session)

                return self.invoice_repo.get_by_id(invoice_id, session=session)

    def delete_sales_invoice(self, business_id: uuid.UUID, invoice_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        with self.session_factory() as session:
            with session.begin():
                inv = self.invoice_repo.get_by_id(invoice_id, session=session, for_update=True)
                if not inv or inv.business_id != business_id:
                    raise InvalidOperationError(f"Sales invoice {invoice_id} not found for business {business_id}")
                if inv.paid_amount > Money.zero():
                    raise InvalidOperationError("A paid or partially paid invoice cannot be deleted; reverse payments first.")

                if inv.status != InvoiceStatus.CANCELLED:
                    for item in inv.items:
                        if not item.product_id:
                            continue
                        bal = self.inventory_repo.get_balance(business_id, item.product_id, session=session, for_update=True)
                        if bal:
                            bal.apply_addition(item.quantity, bal.unit_cost)
                            self.inventory_repo.save_balance(bal, session=session)

                    if inv.customer_id and inv.outstanding_balance.is_positive():
                        cust = self.customer_repo.get_by_id(inv.customer_id, session=session, for_update=True)
                        if cust:
                            cust.apply_payment(inv.outstanding_balance)
                            self.customer_repo.update_balance(cust.id, cust.current_balance, session=session)

                session.execute(
                    delete(JournalEntryLineModel).where(
                        JournalEntryLineModel.journal_entry_id.in_(
                            select(JournalEntryModel.id).where(
                                JournalEntryModel.business_id == business_id,
                                JournalEntryModel.reference_id == invoice_id,
                            )
                        )
                    )
                )
                session.execute(
                    delete(JournalEntryModel).where(
                        JournalEntryModel.business_id == business_id,
                        JournalEntryModel.reference_id == invoice_id,
                    )
                )

                self.invoice_repo.delete(invoice_id, session=session)

    # ==========================================================================
    # 5. Purchases & Payables (UC-27 to UC-34)
    # ==========================================================================

    def create_purchase(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID],
        bill_number: str,
        purchase_date: date,
        due_date: date,
        items: List[Dict[str, Any]],
        tax_amount: float = 0.0,
        is_cash_purchase: bool = False,
        immediate_payment_method: Optional[PaymentMethod] = None,
    ) -> Purchase:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])

        if not items:
            raise InvalidOperationError("Purchase bill must contain at least one line item")

        if supplier_id:
            supp = self.supplier_repo.get_by_id(supplier_id)
            if not supp or supp.business_id != business_id:
                raise InvalidOperationError(f"Supplier {supplier_id} does not belong to authorized business {business_id}")

        purchase_id = uuid.uuid4()
        line_items: List[PurchaseItem] = []
        subtotal = Money.zero()

        existing_prods = self.product_repo.list_by_business(business_id)
        prod_by_name = {p.name.strip().lower(): p for p in existing_prods}

        for it in items:
            p_id = uuid.UUID(str(it["product_id"])) if it.get("product_id") else None
            desc = it.get("description", "").strip()
            qty = Decimal(str(it["quantity"]))
            u_price = Money.from_decimal(it["unit_price"])
            if not p_id and desc:
                if desc.lower() in prod_by_name:
                    p_id = prod_by_name[desc.lower()].id
                else:
                    auto_sku = f"SKU-{desc[:3].upper()}-{str(uuid.uuid4())[:4].upper()}"
                    new_prod = Product(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        sku=auto_sku,
                        name=desc,
                        category="RAW_MATERIALS",
                        unit_of_measure=it.get("unit", "pcs"),
                        selling_price_amount=Money.from_decimal(float(it["unit_price"]) * 1.3),
                        purchase_price_amount=u_price,
                        current_stock=0.0,
                        weighted_average_cost=u_price,
                        reorder_level=0.0,
                        tax_rate_pct=18.0,
                        is_active=True,
                        created_at=datetime.utcnow(),
                    )
                    created_prod = self.product_repo.create(new_prod)
                    prod_by_name[desc.lower()] = created_prod
                    p_id = created_prod.id
            if p_id:
                prod = self.product_repo.get_by_id(p_id)
                if not prod or prod.business_id != business_id:
                    raise InvalidOperationError(f"Product {p_id} does not belong to authorized business {business_id}")
            item_entity = PurchaseItem(
                id=uuid.uuid4(),
                purchase_id=purchase_id,
                product_id=p_id,
                description=it["description"].strip(),
                quantity=qty,
                unit=it.get("unit", "pcs"),
                unit_price=u_price,
            )
            item_total = item_entity.calculate_total()
            subtotal = subtotal + item_total
            line_items.append(item_entity)

        t_amt = Money.from_decimal(tax_amount)
        total_amt = subtotal + t_amt

        with self.session_factory() as session:
            with session.begin():
                purch = Purchase(
                    id=purchase_id,
                    business_id=business_id,
                    supplier_id=supplier_id,
                    bill_number=bill_number.strip(),
                    purchase_date=purchase_date,
                    due_date=due_date,
                    subtotal=subtotal,
                    tax_amount=t_amt,
                    total_amount=total_amt,
                    paid_amount=total_amt if is_cash_purchase else Money.zero(),
                    status=PurchaseStatus.PAID if is_cash_purchase else PurchaseStatus.PENDING,
                    items=line_items,
                )
                # Persist purchase lines before movements because each movement
                # now keeps a foreign key to its exact source purchase item.
                saved_purch = self.purchase_repo.create(purch, session=session)

                # Add inventory with weighted average cost calculation
                for line in line_items:
                    if line.product_id:
                        bal = self.inventory_repo.get_balance(business_id, line.product_id, session=session, for_update=True)
                        if not bal:
                            bal = InventoryBalance(
                                id=uuid.uuid4(),
                                business_id=business_id,
                                product_id=line.product_id,
                                quantity_on_hand=Decimal("0.00"),
                                unit_cost=line.unit_price,
                                total_valuation=Money.zero(),
                            )
                        bal.apply_addition(line.quantity, line.unit_price)
                        self.inventory_repo.save_balance(bal, session=session)

                        mov = InventoryMovement(
                            id=uuid.uuid4(),
                            business_id=business_id,
                            product_id=line.product_id,
                            movement_type=MovementType.PURCHASE,
                            quantity=line.quantity,
                            unit_price=line.unit_price,
                            reference_id=str(purchase_id),
                            reason=f"Purchase Bill {bill_number}",
                            balance_after=bal.quantity_on_hand,
                            cost_basis=line.unit_price,
                            source_purchase_item_id=line.id,
                        )
                        self.inventory_repo.record_movement(mov, session=session)

                # Update supplier balance with row locking or record cash payment
                if is_cash_purchase:
                    pay = Payment(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        party_type=PartyType.SUPPLIER,
                        party_id=supplier_id,
                        reference_type="PURCHASE",
                        reference_id=purchase_id,
                        payment_type=PaymentType.PAID,
                        payment_method=immediate_payment_method or PaymentMethod.CASH,
                        amount=total_amt,
                        payment_date=purchase_date,
                        notes=f"Cash payment for purchase {bill_number}",
                    )
                    self.payment_repo.create(pay, session=session)
                elif supplier_id:
                    sup = self.supplier_repo.get_by_id(supplier_id, session=session, for_update=True)
                    if sup:
                        sup.add_payable(total_amt)
                        self.supplier_repo.update_balance(sup.id, sup.current_balance, session=session)

                # Post GL Journal Entry for Purchase
                credit_acc = StandardAccount.CASH.value if is_cash_purchase else StandardAccount.ACCOUNTS_PAYABLE.value
                gl_lines = [
                    (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], subtotal, Money.zero()),
                ]
                if t_amt > Money.zero():
                    gl_lines.append((StandardAccount.INPUT_TAX.value, ACCOUNT_NAMES[StandardAccount.INPUT_TAX.value], t_amt, Money.zero()))
                gl_lines.append((credit_acc, ACCOUNT_NAMES[credit_acc], Money.zero(), total_amt))

                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=purchase_date,
                    reference_type="PURCHASE",
                    description=f"Purchase Bill {bill_number}",
                    lines_data=gl_lines,
                    reference_id=purchase_id,
                    session=session,
                )

        return saved_purch

    def get_purchase(self, business_id: uuid.UUID, purchase_id: uuid.UUID, user_id: uuid.UUID) -> Purchase:
        self.verify_access(business_id, user_id)
        p = self.purchase_repo.get_by_id(purchase_id)
        if not p or p.business_id != business_id:
            raise InvalidOperationError(f"Purchase bill {purchase_id} does not belong to authorized business {business_id}")
        return p

    def list_purchases(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID] = None,
    ) -> List[Purchase]:
        self.verify_access(business_id, user_id)
        return self.purchase_repo.list_by_business(business_id, supplier_id=supplier_id)

    def record_purchase_payment(
        self,
        business_id: uuid.UUID,
        purchase_id: uuid.UUID,
        user_id: uuid.UUID,
        amount: float,
        payment_date: date,
        payment_method: PaymentMethod,
        notes: str = "",
        idempotency_key: Optional[str] = None,
    ) -> Purchase:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        pay_money = Money.from_decimal(amount)
        if pay_money <= Money.zero():
            raise InvalidOperationError("Payment amount must be strictly positive")

        with self.session_factory() as session:
            with session.begin():
                purch = self.purchase_repo.get_by_id(purchase_id, session=session, for_update=True)
                if not purch or purch.business_id != business_id:
                    raise InvalidOperationError(f"Purchase {purchase_id} not found for business {business_id}")

                # Idempotency check inside locked transaction
                if idempotency_key:
                    existing = self.payment_repo.find_by_idempotency_key(business_id, idempotency_key, session=session)
                    if existing:
                        if (
                            str(existing.reference_id) == str(purchase_id)
                            and existing.amount == pay_money
                            and existing.payment_type == PaymentType.PAID
                        ):
                            return purch
                        raise IdempotencyConflictError(
                            f"Idempotency key '{idempotency_key}' was previously used for a conflicting payment."
                        )

                if pay_money > purch.outstanding_balance:
                    raise InvalidOperationError(
                        f"Payment amount ₹{pay_money.amount} exceeds purchase outstanding balance ₹{purch.outstanding_balance.amount}"
                    )

                purch.record_payment(pay_money)
                self.purchase_repo.update_payment(purch.id, purch.paid_amount, purch.status, session=session)

                # Record payment transaction
                pay = Payment(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    party_type=PartyType.SUPPLIER,
                    party_id=purch.supplier_id,
                    reference_type="PURCHASE",
                    reference_id=purch.id,
                    payment_type=PaymentType.PAID,
                    payment_method=payment_method,
                    amount=pay_money,
                    payment_date=payment_date,
                    idempotency_key=idempotency_key,
                    notes=notes or f"Payment against Bill {purch.bill_number}",
                )
                self.payment_repo.create(pay, session=session)

                # Update supplier balance with row locking
                if purch.supplier_id:
                    sup = self.supplier_repo.get_by_id(purch.supplier_id, session=session, for_update=True)
                    if sup:
                        sup.apply_payment(pay_money)
                        self.supplier_repo.update_balance(sup.id, sup.current_balance, session=session)

                # Post GL Journal Entry for purchase payment
                gl_acc = StandardAccount.BANK.value if payment_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI, PaymentMethod.CHEQUE) else StandardAccount.CASH.value
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=payment_date,
                    reference_type="PAYMENT",
                    description=f"Payment made for Bill {purch.bill_number}",
                    lines_data=[
                        (StandardAccount.ACCOUNTS_PAYABLE.value, ACCOUNT_NAMES[StandardAccount.ACCOUNTS_PAYABLE.value], pay_money, Money.zero()),
                        (gl_acc, ACCOUNT_NAMES[gl_acc], Money.zero(), pay_money),
                    ],
                    reference_id=purch.id,
                    session=session,
                )

        return purch

    def update_purchase(
        self,
        business_id: uuid.UUID,
        purchase_id: uuid.UUID,
        user_id: uuid.UUID,
        supplier_id: Optional[uuid.UUID],
        bill_number: Optional[str],
        purchase_date: date,
        due_date: date,
        items: List[Dict[str, Any]],
        tax_amount: float = 0.0,
    ) -> Purchase:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        if not items:
            raise InvalidOperationError("Purchase bill must contain at least one line item")

        with self.session_factory() as session:
            with session.begin():
                purch = self.purchase_repo.get_by_id(purchase_id, session=session, for_update=True)
                if not purch or purch.business_id != business_id:
                    raise InvalidOperationError(f"Purchase bill {purchase_id} not found for business {business_id}")
                if purch.paid_amount > Money.zero():
                    raise InvalidOperationError("A paid or partially paid purchase cannot be edited; reverse payments first.")
                if purch.return_credit_amount > Money.zero():
                    raise InvalidOperationError("A purchase with returns cannot be edited; reverse returns first.")
                if purch.status == PurchaseStatus.CANCELLED:
                    raise InvalidOperationError("A cancelled purchase cannot be edited.")

                if supplier_id:
                    supp = self.supplier_repo.get_by_id(supplier_id, session=session)
                    if not supp or supp.business_id != business_id:
                        raise InvalidOperationError(f"Supplier {supplier_id} does not belong to authorized business {business_id}")

                for old_item in purch.items:
                    if old_item.product_id:
                        bal = self.inventory_repo.get_balance(business_id, old_item.product_id, session=session, for_update=True)
                        if bal:
                            if bal.quantity_on_hand < old_item.quantity:
                                raise InvalidOperationError(f"Cannot edit purchase: stock for product {old_item.description} has already been consumed or sold (Available: {bal.quantity_on_hand}, required to reverse: {old_item.quantity}).")
                            bal.apply_deduction(old_item.quantity)
                            self.inventory_repo.save_balance(bal, session=session)

                if purch.supplier_id:
                    old_sup = self.supplier_repo.get_by_id(purch.supplier_id, session=session, for_update=True)
                    if old_sup:
                        old_sup.apply_payment(purch.total_amount)
                        self.supplier_repo.update_balance(old_sup.id, old_sup.current_balance, session=session)

                session.execute(delete(InventoryMovementModel).where(InventoryMovementModel.reference_id == str(purchase_id)))
                session.execute(delete(PurchaseItemModel).where(PurchaseItemModel.purchase_id == purchase_id))

                existing_prods = self.product_repo.list_by_business(business_id)
                prod_by_name = {p.name.strip().lower(): p for p in existing_prods}

                subtotal = Money.zero()
                final_bill_number = bill_number.strip() if bill_number else purch.bill_number

                for it in items:
                    p_id = uuid.UUID(str(it["product_id"])) if it.get("product_id") else None
                    desc = it.get("description", "").strip()
                    qty = Decimal(str(it["quantity"]))
                    u_price = Money.from_decimal(it["unit_price"])
                    if not p_id and desc:
                        if desc.lower() in prod_by_name:
                            p_id = prod_by_name[desc.lower()].id
                        else:
                            auto_sku = f"SKU-{desc[:3].upper()}-{str(uuid.uuid4())[:4].upper()}"
                            new_prod = Product(
                                id=uuid.uuid4(),
                                business_id=business_id,
                                sku=auto_sku,
                                name=desc,
                                category="RAW_MATERIALS",
                                unit_of_measure=it.get("unit", "pcs"),
                                selling_price_amount=Money.from_decimal(float(it["unit_price"]) * 1.3),
                                purchase_price_amount=u_price,
                                current_stock=0.0,
                                weighted_average_cost=u_price,
                                reorder_level=0.0,
                                tax_rate_pct=18.0,
                                is_active=True,
                                created_at=datetime.utcnow(),
                            )
                            created_prod = self.product_repo.create(new_prod)
                            prod_by_name[desc.lower()] = created_prod
                            p_id = created_prod.id
                    if p_id:
                        prod = self.product_repo.get_by_id(p_id)
                        if not prod or prod.business_id != business_id:
                            raise InvalidOperationError(f"Product {p_id} does not belong to authorized business {business_id}")
                    item_total = u_price * qty
                    subtotal = subtotal + item_total

                    item_id = uuid.uuid4()
                    item_model = PurchaseItemModel(
                        id=item_id,
                        purchase_id=purchase_id,
                        product_id=p_id,
                        description=it["description"].strip(),
                        quantity=qty,
                        unit=it.get("unit", "pcs"),
                        unit_price=u_price.amount,
                        total_price=item_total.amount,
                    )
                    session.add(item_model)
                    session.flush()

                    if p_id:
                        bal = self.inventory_repo.get_balance(business_id, p_id, session=session, for_update=True)
                        if not bal:
                            bal = InventoryBalance(
                                id=uuid.uuid4(),
                                business_id=business_id,
                                product_id=p_id,
                                quantity_on_hand=Decimal("0.00"),
                                unit_cost=u_price,
                                total_valuation=Money.zero(),
                            )
                        bal.apply_addition(qty, u_price)
                        self.inventory_repo.save_balance(bal, session=session)

                        mov = InventoryMovement(
                            id=uuid.uuid4(),
                            business_id=business_id,
                            product_id=p_id,
                            movement_type=MovementType.PURCHASE,
                            quantity=qty,
                            unit_price=u_price,
                            reference_id=str(purchase_id),
                            reason=f"Purchase Bill {final_bill_number}",
                            balance_after=bal.quantity_on_hand,
                            cost_basis=u_price,
                            source_purchase_item_id=item_id,
                        )
                        self.inventory_repo.record_movement(mov, session=session)

                t_amt = Money.from_decimal(tax_amount)
                total_amt = subtotal + t_amt

                purch_model = session.get(PurchaseModel, purchase_id)
                purch_model.supplier_id = supplier_id
                purch_model.bill_number = final_bill_number
                purch_model.purchase_date = purchase_date
                purch_model.due_date = due_date
                purch_model.subtotal = subtotal.amount
                purch_model.tax_amount = t_amt.amount
                purch_model.total_amount = total_amt.amount
                session.flush()

                if supplier_id:
                    new_sup = self.supplier_repo.get_by_id(supplier_id, session=session, for_update=True)
                    if new_sup:
                        new_sup.add_payable(total_amt)
                        self.supplier_repo.update_balance(new_sup.id, new_sup.current_balance, session=session)

                session.execute(
                    delete(JournalEntryLineModel).where(
                        JournalEntryLineModel.journal_entry_id.in_(
                            select(JournalEntryModel.id).where(
                                JournalEntryModel.business_id == business_id,
                                JournalEntryModel.reference_id == purchase_id,
                            )
                        )
                    )
                )
                session.execute(
                    delete(JournalEntryModel).where(
                        JournalEntryModel.business_id == business_id,
                        JournalEntryModel.reference_id == purchase_id,
                    )
                )

                credit_acc = StandardAccount.ACCOUNTS_PAYABLE.value
                gl_lines = [
                    (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], subtotal, Money.zero()),
                ]
                if t_amt > Money.zero():
                    gl_lines.append((StandardAccount.INPUT_TAX.value, ACCOUNT_NAMES[StandardAccount.INPUT_TAX.value], t_amt, Money.zero()))
                gl_lines.append((credit_acc, ACCOUNT_NAMES[credit_acc], Money.zero(), total_amt))

                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=purchase_date,
                    reference_type="PURCHASE",
                    description=f"Purchase Bill {final_bill_number}",
                    lines_data=gl_lines,
                    reference_id=purchase_id,
                    session=session,
                )

                return self.purchase_repo.get_by_id(purchase_id, session=session)

    def delete_purchase(self, business_id: uuid.UUID, purchase_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        with self.session_factory() as session:
            with session.begin():
                purch = self.purchase_repo.get_by_id(purchase_id, session=session, for_update=True)
                if not purch or purch.business_id != business_id:
                    raise InvalidOperationError(f"Purchase bill {purchase_id} not found for business {business_id}")
                if purch.paid_amount > Money.zero():
                    raise InvalidOperationError("A paid or partially paid purchase cannot be deleted; reverse payments first.")
                if purch.return_credit_amount > Money.zero():
                    raise InvalidOperationError("A purchase with returns cannot be deleted; reverse returns first.")

                if purch.status != PurchaseStatus.CANCELLED:
                    for item in purch.items:
                        if not item.product_id:
                            continue
                        bal = self.inventory_repo.get_balance(business_id, item.product_id, session=session, for_update=True)
                        if bal:
                            if bal.quantity_on_hand < item.quantity:
                                raise InvalidOperationError(f"Cannot delete purchase: stock for product {item.description} has already been consumed or sold (Available: {bal.quantity_on_hand}, required to reverse: {item.quantity}).")
                            bal.apply_deduction(item.quantity)
                            self.inventory_repo.save_balance(bal, session=session)

                    if purch.supplier_id and purch.outstanding_balance.is_positive():
                        sup = self.supplier_repo.get_by_id(purch.supplier_id, session=session, for_update=True)
                        if sup:
                            sup.apply_payment(purch.outstanding_balance)
                            self.supplier_repo.update_balance(sup.id, sup.current_balance, session=session)

                session.execute(delete(InventoryMovementModel).where(InventoryMovementModel.reference_id == str(purchase_id)))

                session.execute(
                    delete(JournalEntryLineModel).where(
                        JournalEntryLineModel.journal_entry_id.in_(
                            select(JournalEntryModel.id).where(
                                JournalEntryModel.business_id == business_id,
                                JournalEntryModel.reference_id == purchase_id,
                            )
                        )
                    )
                )
                session.execute(
                    delete(JournalEntryModel).where(
                        JournalEntryModel.business_id == business_id,
                        JournalEntryModel.reference_id == purchase_id,
                    )
                )

                self.purchase_repo.delete(purchase_id, session=session)

    # ==========================================================================
    # 6. Income, Expenses & Cash Tracking (UC-43 to UC-50)
    # ==========================================================================

    def create_income(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        category: str,
        amount: float,
        record_date: date,
        description: str = "",
        payment_method: PaymentMethod = PaymentMethod.CASH,
    ) -> IncomeRecord:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        inc_money = Money.from_decimal(amount)
        with self.session_factory() as session:
            with session.begin():
                rec = IncomeRecord(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    category=category.strip(),
                    amount=inc_money,
                    date=record_date,
                    description=description.strip(),
                    payment_method=payment_method,
                )
                saved_inc = self.income_expense_repo.create_income(rec, session=session)
                gl_acc = StandardAccount.BANK.value if payment_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI, PaymentMethod.CHEQUE) else StandardAccount.CASH.value
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=record_date,
                    reference_type="INCOME",
                    description=f"Income: {category} - {description}",
                    lines_data=[
                        (gl_acc, ACCOUNT_NAMES[gl_acc], inc_money, Money.zero()),
                        (StandardAccount.OTHER_INCOME.value, ACCOUNT_NAMES[StandardAccount.OTHER_INCOME.value], Money.zero(), inc_money),
                    ],
                    reference_id=rec.id,
                    session=session,
                )
                return saved_inc

    def list_income(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[IncomeRecord]:
        self.verify_access(business_id, user_id)
        return self.income_expense_repo.list_income(business_id, start_date=start_date, end_date=end_date)

    def create_expense(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        category: ExpenseCategory,
        amount: float,
        record_date: date,
        description: str = "",
        payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER,
        is_recurring: bool = False,
    ) -> ExpenseRecord:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        exp_money = Money.from_decimal(amount)
        with self.session_factory() as session:
            with session.begin():
                rec = ExpenseRecord(
                    id=uuid.uuid4(),
                    business_id=business_id,
                    category=category,
                    amount=exp_money,
                    date=record_date,
                    description=description.strip(),
                    payment_method=payment_method,
                    is_recurring=is_recurring,
                )
                saved_exp = self.income_expense_repo.create_expense(rec, session=session)
                gl_acc = StandardAccount.BANK.value if payment_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI, PaymentMethod.CHEQUE) else StandardAccount.CASH.value
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=record_date,
                    reference_type="EXPENSE",
                    description=f"Expense: {category.value} - {description}",
                    lines_data=[
                        (StandardAccount.OPERATING_EXPENSES.value, ACCOUNT_NAMES[StandardAccount.OPERATING_EXPENSES.value], exp_money, Money.zero()),
                        (gl_acc, ACCOUNT_NAMES[gl_acc], Money.zero(), exp_money),
                    ],
                    reference_id=rec.id,
                    session=session,
                )
                return saved_exp

    def list_expenses(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[ExpenseRecord]:
        self.verify_access(business_id, user_id)
        return self.income_expense_repo.list_expenses(business_id, start_date=start_date, end_date=end_date)

    def get_cash_position(self, business_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Calculates live cash-in-hand and bank balances across all transactions."""
        if user_id is not None:
            self.verify_access(business_id, user_id)
        payments = self.payment_repo.list_by_business(business_id)
        incomes = self.income_expense_repo.list_income(business_id)
        expenses = self.income_expense_repo.list_expenses(business_id)

        cash_in_hand = Decimal("0.00")
        bank_balance = Decimal("0.00")

        # Process payment inflows and outflows
        for p in payments:
            amt = p.amount.amount
            if p.payment_method == PaymentMethod.CASH:
                if p.payment_type == PaymentType.RECEIVED:
                    cash_in_hand += amt
                else:
                    cash_in_hand -= amt
            else:  # UPI, BANK_TRANSFER, CHEQUE
                if p.payment_type == PaymentType.RECEIVED:
                    bank_balance += amt
                else:
                    bank_balance -= amt

        # Process direct income
        for inc in incomes:
            amt = inc.amount.amount
            if inc.payment_method == PaymentMethod.CASH:
                cash_in_hand += amt
            else:
                bank_balance += amt

        # Process direct expenses
        for exp in expenses:
            amt = exp.amount.amount
            if exp.payment_method == PaymentMethod.CASH:
                cash_in_hand -= amt
            else:
                bank_balance -= amt

        total_liquidity = cash_in_hand + bank_balance
        invoices = self.invoice_repo.list_by_business(business_id)
        invoice_receivables = sum(
            (inv.outstanding_balance for inv in invoices
             if inv.status not in (InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT) and inv.outstanding_balance.is_positive()),
            Money.zero(),
        )
        customer_receivables = sum(
            (customer.current_balance for customer in self.customer_repo.list_by_business(business_id)
             if customer.current_balance.is_positive()),
            Money.zero(),
        )
        receivables = max(invoice_receivables, customer_receivables)

        purchases = self.purchase_repo.list_by_business(business_id)
        purchase_payables = sum(
            (purch.outstanding_balance for purch in purchases
             if purch.status != PurchaseStatus.CANCELLED and purch.outstanding_balance.is_positive()),
            Money.zero(),
        )
        supplier_payables = sum(
            (supplier.current_balance for supplier in self.supplier_repo.list_by_business(business_id)
             if supplier.current_balance.is_positive()),
            Money.zero(),
        )
        payables = max(purchase_payables, supplier_payables)
        net_liquid_working_capital = Money(total_liquidity) + receivables - payables
        return {
            "cash_in_hand": float(cash_in_hand),
            "cash_on_hand": float(cash_in_hand),
            "cash_on_hand_exact": f"{cash_in_hand:.2f}",
            "formatted_cash_in_hand": Money(cash_in_hand).format_inr(),
            "bank_balance": float(bank_balance),
            "bank_balance_exact": f"{bank_balance:.2f}",
            "formatted_bank_balance": Money(bank_balance).format_inr(),
            "total_liquidity": float(total_liquidity),
            "total_liquidity_exact": f"{total_liquidity:.2f}",
            "total_liquid_cash": float(total_liquidity),
            "total_liquid_cash_exact": f"{total_liquidity:.2f}",
            "total_receivables": float(receivables.amount),
            "total_receivables_exact": f"{receivables.amount:.2f}",
            "total_payables": float(payables.amount),
            "total_payables_exact": f"{payables.amount:.2f}",
            "net_liquid_working_capital": float(net_liquid_working_capital.amount),
            "net_liquid_working_capital_exact": f"{net_liquid_working_capital.amount:.2f}",
            "formatted_total_liquidity": Money(total_liquidity).format_inr(),
        }

    # ==========================================================================
    # 7. Goals, Budgets & Forward Planning (UC-75 to UC-82)
    # ==========================================================================

    def create_goal(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        goal_type: GoalType,
        title: str,
        target_value: float,
        target_date: date,
        start_date: Optional[date] = None,
        plan_details: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        goal_start = start_date or date.today()
        if target_date < goal_start:
            raise InvalidOperationError("Goal target date must be on or after its start date.")
        normalized_plan_details = dict(plan_details or {})
        if goal_type == GoalType.DEBT_REDUCTION and "baseline_debt_total" not in normalized_plan_details:
            suppliers = self.supplier_repo.list_by_business(business_id)
            normalized_plan_details["baseline_debt_total"] = f"{sum((supplier.current_balance.amount for supplier in suppliers), Decimal('0.00')):.2f}"
            normalized_plan_details["baseline_debt_scope"] = "supplier_payables_only"
        goal = Goal(
            id=uuid.uuid4(),
            business_id=business_id,
            goal_type=goal_type,
            title=title.strip(),
            target_value=Decimal(str(target_value)),
            current_value=Decimal("0.00"),
            start_date=goal_start,
            target_date=target_date,
            status=GoalStatus.ACTIVE,
            plan_details=normalized_plan_details,
        )
        saved_goal = self.goal_repo.create(goal)
        return saved_goal

    def list_goals(self, business_id: uuid.UUID, user_id: uuid.UUID) -> List[Goal]:
        self.verify_access(business_id, user_id)
        return self.goal_repo.list_by_business(business_id)

    def get_goal(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID) -> Goal:
        self.verify_access(business_id, user_id)
        goal = self.goal_repo.get_by_id(business_id, goal_id)
        if goal is None:
            raise BusinessNotFoundError("Goal was not found in this workspace.")
        return goal

    def update_goal(
        self,
        business_id: uuid.UUID,
        goal_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        goal_type: Optional[GoalType] = None,
        title: Optional[str] = None,
        target_value: Optional[Decimal] = None,
        start_date: Optional[date] = None,
        target_date: Optional[date] = None,
        plan_details: Optional[Dict[str, Any]] = None,
    ) -> Goal:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        goal = self.goal_repo.get_by_id(business_id, goal_id)
        if goal is None:
            raise BusinessNotFoundError("Goal was not found in this workspace.")
        if goal.status in {GoalStatus.CANCELLED, GoalStatus.MISSED}:
            raise InvalidOperationError("A cancelled or missed goal cannot be edited.")
        if goal_type is not None:
            goal.goal_type = goal_type
        if title is not None:
            cleaned = title.strip()
            if not cleaned:
                raise InvalidOperationError("Goal title cannot be empty.")
            goal.title = cleaned
        if target_value is not None:
            value = Decimal(str(target_value))
            if not value.is_finite() or value <= 0:
                raise InvalidOperationError("Goal target value must be a positive finite amount.")
            goal.target_value = value.quantize(Decimal("0.01"))
        if start_date is not None:
            goal.start_date = start_date
        if target_date is not None:
            goal.target_date = target_date
        if goal.target_date < goal.start_date:
            raise InvalidOperationError("Goal target date must be on or after its start date.")
        if plan_details is not None:
            goal.plan_details = dict(plan_details)
        updated = self.goal_repo.update(goal)
        if updated is None:
            raise BusinessNotFoundError("Goal was not found in this workspace.")
        return updated

    def cancel_goal(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID) -> Goal:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        goal = self.goal_repo.get_by_id(business_id, goal_id)
        if goal is None:
            raise BusinessNotFoundError("Goal was not found in this workspace.")
        if goal.status == GoalStatus.ACHIEVED:
            raise InvalidOperationError("An achieved goal cannot be cancelled.")
        if goal.status != GoalStatus.CANCELLED:
            goal.status = GoalStatus.CANCELLED
            updated = self.goal_repo.update(goal)
            if updated is None:
                raise BusinessNotFoundError("Goal was not found in this workspace.")
            return updated
        return goal

    def recalculate_goal_progress(self, business_id: uuid.UUID, goal_id: uuid.UUID, user_id: uuid.UUID) -> Goal:
        """Derives live current progress toward a goal directly from transactional truth."""
        self.verify_access(business_id, user_id)
        goals = self.goal_repo.list_by_business(business_id)
        target_goal = next((g for g in goals if g.id == goal_id), None)
        if not target_goal:
            raise InvalidOperationError(f"Goal {goal_id} does not belong to authorized business {business_id}")

        if target_goal.goal_type == GoalType.REVENUE:
            invoices = self.invoice_repo.list_by_business(business_id)
            total_rev = sum((inv.total_amount.amount for inv in invoices if inv.status != InvoiceStatus.CANCELLED), Decimal("0.00"))
            incomes = self.income_expense_repo.list_income(business_id)
            total_rev += sum((inc.amount.amount for inc in incomes), Decimal("0.00"))
            current_val = total_rev
        elif target_goal.goal_type == GoalType.CASH_RESERVE:
            pos = self.get_cash_position(business_id, user_id)
            current_val = Decimal(str(pos["total_liquidity"]))
        elif target_goal.goal_type == GoalType.DEBT_REDUCTION:
            suppliers = self.supplier_repo.list_by_business(business_id)
            total_debt = sum((s.current_balance.amount for s in suppliers), Decimal("0.00"))
            current_val = max(Decimal("0.00"), target_goal.target_value - total_debt)
        else:
            current_val = target_goal.current_value

        new_status = target_goal.status
        if target_goal.status != GoalStatus.CANCELLED:
            if current_val >= target_goal.target_value:
                new_status = GoalStatus.ACHIEVED
            elif target_goal.target_date < date.today():
                new_status = GoalStatus.MISSED

        self.goal_repo.update_progress(target_goal.id, current_val, new_status)
        target_goal.current_value = current_val
        target_goal.status = new_status
        return target_goal

    # ==========================================================================
    # 11. Sales & Purchase Returns (Credit Notes & Debit Notes)
    # ==========================================================================

    def record_sales_return(
        self,
        business_id: uuid.UUID,
        invoice_id: uuid.UUID,
        user_id: uuid.UUID,
        items: List[Dict[str, Any]],
        return_date: date,
        reason: str = "Customer return",
        refund_method: Optional[PaymentMethod] = None,
    ) -> Dict[str, Any]:
        """Processes sales return, restores stock, credits customer khata, and posts balanced GL entries."""
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.MANAGER])
        with self.session_factory() as session:
            with session.begin():
                inv = self.invoice_repo.get_by_id(invoice_id, session=session, for_update=True)
                if not inv or inv.business_id != business_id:
                    raise InvalidOperationError(f"Invoice {invoice_id} not found")
                if inv.status == InvoiceStatus.CANCELLED:
                    raise InvalidOperationError("Cannot return items against a cancelled invoice")

                inventory_costs = self._invoice_inventory_costs(business_id, inv, session)
                movements = self.inventory_repo.list_movements(business_id, session=session)
                prior_returned: Dict[uuid.UUID, Decimal] = {}
                for movement in movements:
                    if (
                        movement.reference_id == str(invoice_id)
                        and movement.movement_type == MovementType.RETURN
                        and movement.reason.startswith("Sales Return:")
                    ):
                        prior_returned[movement.product_id] = prior_returned.get(movement.product_id, Decimal("0")) + movement.quantity

                total_return_subtotal = Money.zero()
                returned_cogs = Money.zero()
                for it in items:
                    if not it.get("product_id"):
                        raise InvalidOperationError("Sales returns require a product ID from the original invoice.")
                    p_id = uuid.UUID(str(it["product_id"]))
                    qty = Decimal(str(it["quantity"]))
                    if qty <= 0:
                        raise InvalidOperationError("Return quantity must be strictly positive")
                    u_price = Money.from_decimal(it["unit_price"])
                    if p_id not in inventory_costs:
                        raise InvalidOperationError(f"Product {p_id} was not sold on invoice {inv.invoice_number}")
                    sold_qty, sold_cost = inventory_costs[p_id]
                    already_returned = prior_returned.get(p_id, Decimal("0"))
                    if already_returned + qty > sold_qty:
                        raise InvalidOperationError(
                            f"Return quantity for product {p_id} exceeds the unreturned invoice quantity {sold_qty - already_returned}."
                        )

                    matching_lines = [item for item in inv.items if item.product_id == p_id]
                    listed_qty = sum((item.quantity for item in matching_lines), Decimal("0"))
                    listed_unit_price = Money(
                        sum((item.unit_price.amount * item.quantity for item in matching_lines), Decimal("0")) / listed_qty
                    )
                    if u_price != listed_unit_price:
                        raise InvalidOperationError(
                            f"Return price for product {p_id} must match the original invoice unit price {listed_unit_price.amount}."
                        )
                    line_subtotal = sum((item.total_price for item in matching_lines), Money.zero())
                    net_unit_value = line_subtotal / listed_qty
                    total_return_subtotal = total_return_subtotal + (net_unit_value * qty)

                    unit_cost = sold_cost / sold_qty
                    bal = self.inventory_repo.get_balance(business_id, p_id, session=session, for_update=True)
                    if not bal:
                        raise InvalidOperationError(f"Inventory balance is missing for product {p_id}")
                    bal.apply_addition(qty, unit_cost)
                    self.inventory_repo.save_balance(bal, session=session)
                    cost = unit_cost * qty
                    returned_cogs = returned_cogs + cost
                    prior_returned[p_id] = already_returned + qty
                    mov = InventoryMovement(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        product_id=p_id,
                        movement_type=MovementType.RETURN,
                        quantity=qty,
                        unit_price=u_price,
                        reference_id=str(invoice_id),
                        reason=f"Sales Return: {reason}",
                        balance_after=bal.quantity_on_hand,
                        cost_basis=unit_cost,
                    )
                    self.inventory_repo.record_movement(mov, session=session)

                invoice_discount_share = (
                    inv.discount_amount * (total_return_subtotal.amount / inv.subtotal.amount)
                    if inv.subtotal > Money.zero()
                    else Money.zero()
                )
                return_net = total_return_subtotal - invoice_discount_share
                tax_base = inv.subtotal - inv.discount_amount
                return_tax = inv.tax_amount * (return_net.amount / tax_base.amount) if tax_base > Money.zero() else Money.zero()
                total_return = return_net + return_tax

                # Customer khata adjustment or immediate refund
                if refund_method:
                    pay = Payment(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        party_type=PartyType.CUSTOMER,
                        party_id=inv.customer_id,
                        reference_type="INVOICE_RETURN",
                        reference_id=invoice_id,
                        payment_type=PaymentType.PAID,
                        payment_method=refund_method,
                        amount=total_return,
                        payment_date=return_date,
                        notes=f"Refund for return on Invoice {inv.invoice_number}",
                    )
                    self.payment_repo.create(pay, session=session)
                    gl_acc = StandardAccount.BANK.value if refund_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI) else StandardAccount.CASH.value
                    credit_account = gl_acc
                elif inv.customer_id:
                    cust = self.customer_repo.get_by_id(inv.customer_id, session=session, for_update=True)
                    if cust:
                        cust.apply_payment(total_return)
                        self.customer_repo.update_balance(cust.id, cust.current_balance, session=session)
                    credit_account = StandardAccount.ACCOUNTS_RECEIVABLE.value
                else:
                    credit_account = StandardAccount.CASH.value

                # Post GL Journal Entry for Sales Return
                return_lines = [
                    (StandardAccount.SALES_RETURNS.value, ACCOUNT_NAMES[StandardAccount.SALES_RETURNS.value], return_net, Money.zero()),
                    (credit_account, ACCOUNT_NAMES[credit_account], Money.zero(), total_return),
                ]
                if return_tax > Money.zero():
                    return_lines.append(
                        (StandardAccount.OUTPUT_TAX.value, ACCOUNT_NAMES[StandardAccount.OUTPUT_TAX.value], return_tax, Money.zero())
                    )
                self._post_gl_entry(
                    business_id=business_id,
                    entry_date=return_date,
                    reference_type="RETURN",
                    description=f"Sales Return on Invoice {inv.invoice_number}: {reason}",
                    lines_data=return_lines,
                    reference_id=invoice_id,
                    session=session,
                )

                if returned_cogs > Money.zero():
                    self._post_gl_entry(
                        business_id=business_id,
                        entry_date=return_date,
                        reference_type="INVOICE_RETURN_COGS",
                        description=f"Cost reversal for sales return on Invoice {inv.invoice_number}: {reason}",
                        lines_data=[
                            (StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], returned_cogs, Money.zero()),
                            (StandardAccount.COGS.value, ACCOUNT_NAMES[StandardAccount.COGS.value], Money.zero(), returned_cogs),
                        ],
                        reference_id=invoice_id,
                        session=session,
                    )

                return {
                    "invoice_id": str(invoice_id),
                    "total_returned": float(total_return.amount),
                    "total_returned_exact": f"{total_return.amount:.2f}",
                    "items_count": len(items),
                    "status": "PROCESSED",
                }

    def record_purchase_return(
        self,
        business_id: uuid.UUID,
        purchase_id: uuid.UUID,
        user_id: uuid.UUID,
        items: List[Dict[str, Any]],
        return_date: date,
        reason: str = "Supplier return",
        refund_method: Optional[PaymentMethod] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return stock only against original bill lines and settle its recorded value."""
        self.verify_access(
            business_id,
            user_id,
            [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT],
        )
        if not items:
            raise InvalidOperationError("A purchase return must include at least one original purchase line.")
        try:
            settlement_method = PaymentMethod(refund_method) if refund_method else None
        except ValueError as exc:
            raise InvalidOperationError("Unsupported supplier refund method.") from exc

        normalized_items: List[Tuple[uuid.UUID, Decimal]] = []
        seen_item_ids = set()
        for item in items:
            if "unit_price" in item or "product_id" in item:
                raise InvalidOperationError(
                    "Purchase returns accept only an original purchase_item_id and quantity; prices and products come from the source bill."
                )
            try:
                purchase_item_id = uuid.UUID(str(item["purchase_item_id"]))
                quantity = Decimal(str(item["quantity"]))
            except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
                raise InvalidOperationError("Each return line requires a valid purchase_item_id and quantity.") from exc
            if not quantity.is_finite() or quantity <= 0:
                raise InvalidOperationError("Return quantity must be a finite positive amount.")
            if quantity != quantity.quantize(Decimal("0.0001")):
                raise InvalidOperationError("Return quantity cannot have more than four decimal places.")
            if purchase_item_id in seen_item_ids:
                raise InvalidOperationError("A purchase line may appear only once in a return request.")
            seen_item_ids.add(purchase_item_id)
            normalized_items.append((purchase_item_id, quantity))

        reason = (reason or "Supplier return").strip()
        key = idempotency_key.strip() if idempotency_key else ""
        if not key:
            raise InvalidOperationError("A purchase return idempotency key is required.")
        if len(key) > 128:
            raise InvalidOperationError("Purchase return idempotency keys cannot exceed 128 characters.")

        def _result(return_record: PurchaseReturn, purchase: Optional[Purchase] = None) -> Dict[str, Any]:
            response = {
                "purchase_id": str(return_record.purchase_id),
                "purchase_return_id": str(return_record.id),
                "return_date": return_record.return_date.isoformat(),
                "subtotal": float(return_record.subtotal.amount),
                "subtotal_exact": f"{return_record.subtotal.amount:.2f}",
                "tax_amount": float(return_record.tax_amount.amount),
                "tax_amount_exact": f"{return_record.tax_amount.amount:.2f}",
                "total_returned": float(return_record.total_amount.amount),
                "total_returned_exact": f"{return_record.total_amount.amount:.2f}",
                "inventory_cost_removed": float(sum(
                    (line.inventory_cost_removed.amount for line in return_record.items), Decimal("0.00")
                )),
                "inventory_cost_removed_exact": f"{sum((line.inventory_cost_removed.amount for line in return_record.items), Decimal('0.00')):.2f}",
                "currency": return_record.total_amount.currency,
                "settlement_method": return_record.refund_method.value if return_record.refund_method else "SUPPLIER_CREDIT",
                "items": [
                    {
                        "purchase_item_id": str(line.purchase_item_id),
                        "product_id": str(line.product_id),
                        "quantity": str(line.quantity),
                        "original_unit_price": float(line.original_unit_price.amount),
                        "original_unit_price_exact": f"{line.original_unit_price.amount:.2f}",
                        "subtotal": float(line.pretax_amount.amount),
                        "subtotal_exact": f"{line.pretax_amount.amount:.2f}",
                        "tax_amount": float(line.tax_amount.amount),
                        "tax_amount_exact": f"{line.tax_amount.amount:.2f}",
                        "inventory_cost_removed": float(line.inventory_cost_removed.amount),
                        "inventory_cost_removed_exact": f"{line.inventory_cost_removed.amount:.2f}",
                    }
                    for line in return_record.items
                ],
                "items_count": len(return_record.items),
                "status": "PROCESSED",
            }
            if purchase is not None:
                response["purchase_status"] = purchase.status.value
                response["purchase_outstanding_balance"] = float(purchase.outstanding_balance.amount)
                response["purchase_outstanding_balance_exact"] = f"{purchase.outstanding_balance.amount:.2f}"
            return response

        with self.session_factory() as session:
            with session.begin():
                purch = self.purchase_repo.get_by_id(purchase_id, session=session, for_update=True)
                if not purch or purch.business_id != business_id:
                    raise BusinessNotFoundError(f"Purchase {purchase_id} not found for this business.")

                if key:
                    previous = self.purchase_return_repo.get_by_idempotency_key(business_id, key, session=session)
                    if previous:
                        same_request = (
                            previous.purchase_id == purchase_id
                            and previous.return_date == return_date
                            and previous.reason == reason
                            and previous.refund_method == settlement_method
                            and {line.purchase_item_id: line.quantity for line in previous.items}
                            == dict(normalized_items)
                        )
                        if same_request:
                            return _result(previous, purch)
                        raise IdempotencyConflictError(
                            f"Idempotency key '{key}' was already used for a different purchase return."
                        )

                if purch.status == PurchaseStatus.CANCELLED:
                    raise InvalidOperationError("A cancelled purchase cannot be returned.")
                if return_date < purch.purchase_date:
                    raise InvalidOperationError("Return date cannot be earlier than the original purchase date.")
                if not purch.supplier_id:
                    raise InvalidOperationError("The original purchase has no supplier and cannot be returned.")
                supplier = self.supplier_repo.get_by_id(purch.supplier_id, session=session, for_update=True)
                if not supplier or supplier.business_id != business_id:
                    raise InvalidOperationError("The original purchase supplier is invalid for this business.")
                if not self.period_repo.is_date_open(business_id, return_date, session=session):
                    raise FinancialPeriodClosedError(
                        f"Cannot return purchase on {return_date}: the financial period is not open."
                    )

                source_lines = {line.id: line for line in purch.items}
                prior_returns = self.purchase_return_repo.list_by_purchase(business_id, purchase_id, session=session)
                returned_quantity: Dict[uuid.UUID, Decimal] = {}
                returned_line_subtotal: Dict[uuid.UUID, Decimal] = {}
                prior_subtotal = Decimal("0.00")
                prior_tax = Decimal("0.00")
                for previous_return in prior_returns:
                    prior_subtotal += previous_return.subtotal.amount
                    prior_tax += previous_return.tax_amount.amount
                    for previous_line in previous_return.items:
                        returned_quantity[previous_line.purchase_item_id] = (
                            returned_quantity.get(previous_line.purchase_item_id, Decimal("0")) + previous_line.quantity
                        )
                        returned_line_subtotal[previous_line.purchase_item_id] = (
                            returned_line_subtotal.get(previous_line.purchase_item_id, Decimal("0.00"))
                            + previous_line.pretax_amount.amount
                        )

                # The legacy route keyed returns only by purchase/product. Its line allocation,
                # tax and return price cannot be recovered safely, so fail closed for those bills.
                legacy_returns = [
                    movement
                    for movement in self.inventory_repo.list_movements(business_id, session=session)
                    if movement.reference_id == str(purchase_id)
                    and movement.movement_type == MovementType.RETURN
                    and movement.reason.startswith("Purchase Return:")
                ]
                legacy_products = {movement.product_id for movement in legacy_returns}
                requested_legacy_product = any(
                    source_lines[line_id].product_id in legacy_products
                    for line_id, _ in normalized_items
                    if line_id in source_lines
                )
                if requested_legacy_product:
                    raise InvalidOperationError(
                        "This bill has legacy returns without original-line allocation. Reconcile that return history before returning more stock."
                    )

                pending: List[Dict[str, Any]] = []
                for purchase_item_id, quantity in normalized_items:
                    source = source_lines.get(purchase_item_id)
                    if not source:
                        raise InvalidOperationError("A return line must reference an item on the selected purchase.")
                    if source.product_id is None:
                        raise InvalidOperationError(
                            "Only product-linked purchase lines can be returned through the inventory return workflow."
                        )
                    product = self.product_repo.get_by_id(source.product_id)
                    if not product or product.business_id != business_id:
                        raise InvalidOperationError("The original purchase line product is invalid for this business.")
                    if source.quantity <= 0:
                        raise InvalidOperationError("The original purchase line has an invalid quantity and cannot be returned.")

                    previously_returned = returned_quantity.get(purchase_item_id, Decimal("0"))
                    remaining = source.quantity - previously_returned
                    if quantity > remaining:
                        raise InvalidOperationError(
                            f"Return quantity {quantity} exceeds the remaining quantity {remaining} on purchase line {purchase_item_id}."
                        )

                    cumulative_quantity = previously_returned + quantity
                    if cumulative_quantity == source.quantity:
                        cumulative_subtotal_target = source.total_price.amount
                    else:
                        cumulative_subtotal_target = (
                            source.total_price.amount * cumulative_quantity / source.quantity
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    line_subtotal = cumulative_subtotal_target - returned_line_subtotal.get(
                        purchase_item_id, Decimal("0.00")
                    )
                    if line_subtotal < 0:
                        raise InvalidOperationError("Prior return allocations exceed the source purchase line value.")
                    pending.append({
                        "source": source,
                        "product": product,
                        "quantity": quantity,
                        "subtotal": Money(line_subtotal),
                    })

                return_subtotal = sum((row["subtotal"] for row in pending), Money.zero())
                payable_before_return = purch.outstanding_balance
                cumulative_return_subtotal = prior_subtotal + return_subtotal.amount
                if purch.subtotal.amount <= 0:
                    if purch.tax_amount > Money.zero():
                        raise InvalidOperationError("Purchase tax cannot be allocated because the source subtotal is zero.")
                    cumulative_tax_target = Decimal("0.00")
                elif cumulative_return_subtotal >= purch.subtotal.amount:
                    cumulative_tax_target = purch.tax_amount.amount
                else:
                    cumulative_tax_target = (
                        purch.tax_amount.amount * cumulative_return_subtotal / purch.subtotal.amount
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                return_tax_amount = min(
                    max(Decimal("0.00"), cumulative_tax_target - prior_tax),
                    max(Decimal("0.00"), purch.tax_amount.amount - prior_tax),
                )
                total_return = return_subtotal + Money(return_tax_amount)
                if settlement_method is not None and total_return > purch.paid_amount:
                    raise InvalidOperationError(
                        "A cash refund cannot exceed the amount currently paid on the original purchase; use supplier credit for the unpaid portion."
                    )

                tax_remaining = return_tax_amount
                for index, row in enumerate(pending):
                    if index == len(pending) - 1:
                        allocated_tax = tax_remaining
                    elif return_subtotal > Money.zero():
                        allocated_tax = (
                            return_tax_amount * row["subtotal"].amount / return_subtotal.amount
                        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        allocated_tax = min(max(Decimal("0.00"), allocated_tax), tax_remaining)
                    else:
                        allocated_tax = Decimal("0.00")
                    row["tax"] = Money(allocated_tax)
                    tax_remaining -= allocated_tax

                return_id = uuid.uuid4()
                returned_lines: List[PurchaseReturnItem] = []
                total_inventory_cost = Money.zero()
                for row in pending:
                    source = row["source"]
                    product_id = source.product_id
                    quantity = row["quantity"]
                    balance = self.inventory_repo.get_balance(
                        business_id, product_id, session=session, for_update=True
                    )
                    if not balance:
                        raise InsufficientInventoryError(f"Inventory balance is missing for product {product_id}.")
                    if balance.quantity_on_hand < quantity:
                        raise InsufficientInventoryError(
                            f"Cannot return {quantity}: only {balance.quantity_on_hand} units are currently available."
                        )

                    valuation_before = balance.total_valuation
                    balance.apply_deduction(quantity)
                    inventory_cost_removed = valuation_before - balance.total_valuation
                    if inventory_cost_removed < Money.zero():
                        raise InvalidOperationError("Inventory valuation increased during a stock return.")
                    self.inventory_repo.save_balance(balance, session=session)
                    self.inventory_repo.record_movement(
                        InventoryMovement(
                            id=uuid.uuid4(),
                            business_id=business_id,
                            product_id=product_id,
                            movement_type=MovementType.RETURN,
                            quantity=quantity,
                            unit_price=source.unit_price,
                            # The movement audit records the original billed unit
                            # cost; the return line separately preserves the actual
                            # weighted-average inventory value removed for GL posting.
                            cost_basis=source.unit_price,
                            source_purchase_item_id=source.id,
                            reference_id=str(return_id),
                            reason=f"Purchase Return {purch.bill_number}: {reason}",
                            balance_after=balance.quantity_on_hand,
                        ),
                        session=session,
                    )
                    total_inventory_cost = total_inventory_cost + inventory_cost_removed
                    returned_lines.append(PurchaseReturnItem(
                        id=uuid.uuid4(),
                        purchase_return_id=return_id,
                        purchase_item_id=source.id,
                        product_id=product_id,
                        quantity=quantity,
                        original_unit_price=source.unit_price,
                        pretax_amount=row["subtotal"],
                        tax_amount=row["tax"],
                        inventory_cost_removed=inventory_cost_removed,
                    ))

                return_tax = Money(return_tax_amount)
                total_return = return_subtotal + return_tax
                return_record = PurchaseReturn(
                    id=return_id,
                    business_id=business_id,
                    purchase_id=purchase_id,
                    supplier_id=supplier.id,
                    return_date=return_date,
                    reason=reason,
                    refund_method=settlement_method,
                    subtotal=return_subtotal,
                    tax_amount=return_tax,
                    total_amount=total_return,
                    created_by=user_id,
                    idempotency_key=key,
                    items=returned_lines,
                )
                self.purchase_return_repo.create(return_record, session=session)

                # Every return reduces the bill. A cash refund also reduces the
                # net amount already paid; a supplier credit stays as a debit note.
                new_return_credit_amount = purch.return_credit_amount + total_return
                new_paid_amount = (
                    purch.paid_amount - total_return
                    if settlement_method is not None else purch.paid_amount
                )
                returned_this_request = {row["source"].id: row["quantity"] for row in pending}
                returnable_lines = [line for line in purch.items if line.product_id is not None]
                fully_returned = bool(returnable_lines) and all(
                    returned_quantity.get(line.id, Decimal("0"))
                    + returned_this_request.get(line.id, Decimal("0"))
                    >= line.quantity
                    for line in returnable_lines
                )
                purchase_return_status = PurchaseStatus.RETURNED if fully_returned else PurchaseStatus.PARTIALLY_RETURNED
                self.purchase_repo.update_return_state(
                    purch.id,
                    new_paid_amount,
                    new_return_credit_amount,
                    purchase_return_status,
                    session=session,
                )
                purch.paid_amount = new_paid_amount
                purch.return_credit_amount = new_return_credit_amount
                purch.status = purchase_return_status

                if settlement_method and total_return > Money.zero():
                    self.payment_repo.create(Payment(
                        id=uuid.uuid4(),
                        business_id=business_id,
                        party_type=PartyType.SUPPLIER,
                        party_id=supplier.id,
                        reference_type="PURCHASE_RETURN",
                        reference_id=return_id,
                        payment_type=PaymentType.RECEIVED,
                        payment_method=settlement_method,
                        amount=total_return,
                        payment_date=return_date,
                        idempotency_key=f"purchase-return:{key}" if key else None,
                        notes=f"Refund received for return on Bill {purch.bill_number}",
                    ), session=session)
                    settlement_account = (
                        StandardAccount.BANK.value
                        if settlement_method in (PaymentMethod.BANK_TRANSFER, PaymentMethod.UPI, PaymentMethod.CHEQUE)
                        else StandardAccount.CASH.value
                    )
                else:
                    settlement_account = StandardAccount.ACCOUNTS_PAYABLE.value
                    if total_return > Money.zero():
                        supplier.apply_payment(total_return)
                        self.supplier_repo.update_balance(supplier.id, supplier.current_balance, session=session)

                # The source supplier value and current WAC can differ. Post the actual
                # inventory value removed and route the difference through inventory gain/loss.
                variance = return_subtotal - total_inventory_cost
                gl_lines: List[Tuple[str, str, Money, Money]] = []
                if settlement_method and total_return > Money.zero():
                    gl_lines.append((settlement_account, ACCOUNT_NAMES[settlement_account], total_return, Money.zero()))
                elif total_return > Money.zero():
                    payable_reduction = min(total_return, payable_before_return)
                    debit_note_receivable = total_return - payable_reduction
                    if payable_reduction > Money.zero():
                        gl_lines.append((
                            StandardAccount.ACCOUNTS_PAYABLE.value,
                            ACCOUNT_NAMES[StandardAccount.ACCOUNTS_PAYABLE.value],
                            payable_reduction,
                            Money.zero(),
                        ))
                    if debit_note_receivable > Money.zero():
                        account = StandardAccount.SUPPLIER_DEBIT_NOTE_RECEIVABLE.value
                        gl_lines.append((account, ACCOUNT_NAMES[account], debit_note_receivable, Money.zero()))
                if total_inventory_cost > Money.zero():
                    gl_lines.append((StandardAccount.INVENTORY.value, ACCOUNT_NAMES[StandardAccount.INVENTORY.value], Money.zero(), total_inventory_cost))
                if return_tax > Money.zero():
                    gl_lines.append((StandardAccount.INPUT_TAX.value, ACCOUNT_NAMES[StandardAccount.INPUT_TAX.value], Money.zero(), return_tax))
                if variance > Money.zero():
                    gl_lines.append((StandardAccount.INVENTORY_GAIN.value, ACCOUNT_NAMES[StandardAccount.INVENTORY_GAIN.value], Money.zero(), variance))
                elif variance < Money.zero():
                    gl_lines.append((StandardAccount.INVENTORY_LOSS.value, ACCOUNT_NAMES[StandardAccount.INVENTORY_LOSS.value], -variance, Money.zero()))
                if gl_lines:
                    self._post_gl_entry(
                        business_id=business_id,
                        entry_date=return_date,
                        reference_type="PURCHASE_RETURN",
                        description=f"Purchase Return on Bill {purch.bill_number}: {reason}",
                        lines_data=gl_lines,
                        reference_id=return_id,
                        session=session,
                    )

                from backend.arthlens.security.audit import get_audit_service

                get_audit_service().record_event(
                    actor=user_id,
                    action="PURCHASE_RETURN_POSTED",
                    target=f"purchase_return:{return_id}",
                    payload={
                        "business_id": str(business_id),
                        "purchase_id": str(purchase_id),
                        "supplier_id": str(supplier.id),
                        "return_date": return_date.isoformat(),
                        "subtotal": str(return_subtotal.amount),
                        "tax_amount": str(return_tax.amount),
                        "total_amount": str(total_return.amount),
                        "inventory_cost_removed": str(total_inventory_cost.amount),
                        "settlement_method": settlement_method.value if settlement_method else "SUPPLIER_CREDIT",
                        "purchase_item_ids": [str(line.purchase_item_id) for line in returned_lines],
                    },
                    session=session,
                )
                return _result(return_record, purch)

    def list_purchase_returns(
        self,
        business_id: uuid.UUID,
        purchase_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        self.verify_access(business_id, user_id)
        purchase = self.purchase_repo.get_by_id(purchase_id)
        if not purchase or purchase.business_id != business_id:
            raise InvalidOperationError(f"Purchase {purchase_id} not found for this business.")
        return [
            {
                "purchase_id": str(record.purchase_id),
                "purchase_return_id": str(record.id),
                "return_date": record.return_date.isoformat(),
                "reason": record.reason,
                "subtotal": float(record.subtotal.amount),
                "subtotal_exact": f"{record.subtotal.amount:.2f}",
                "tax_amount": float(record.tax_amount.amount),
                "tax_amount_exact": f"{record.tax_amount.amount:.2f}",
                "total_returned": float(record.total_amount.amount),
                "total_returned_exact": f"{record.total_amount.amount:.2f}",
                "currency": record.total_amount.currency,
                "settlement_method": record.refund_method.value if record.refund_method else "SUPPLIER_CREDIT",
                "items": [
                    {
                        "purchase_item_id": str(line.purchase_item_id),
                        "product_id": str(line.product_id),
                        "quantity": str(line.quantity),
                        "original_unit_price": float(line.original_unit_price.amount),
                        "original_unit_price_exact": f"{line.original_unit_price.amount:.2f}",
                        "subtotal": float(line.pretax_amount.amount),
                        "subtotal_exact": f"{line.pretax_amount.amount:.2f}",
                        "tax_amount": float(line.tax_amount.amount),
                        "tax_amount_exact": f"{line.tax_amount.amount:.2f}",
                        "inventory_cost_removed": float(line.inventory_cost_removed.amount),
                        "inventory_cost_removed_exact": f"{line.inventory_cost_removed.amount:.2f}",
                    }
                    for line in record.items
                ],
            }
            for record in self.purchase_return_repo.list_by_purchase(business_id, purchase_id)
        ]

    # ==========================================================================
    # 12. Financial Periods (Soft and Hard Closing)
    # ==========================================================================

    def create_financial_period(
        self,
        business_id: uuid.UUID,
        period_name: str,
        start_date: date,
        end_date: date,
        user_id: uuid.UUID,
    ) -> FinancialPeriod:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.ACCOUNTANT])
        period = FinancialPeriod(
            id=uuid.uuid4(),
            business_id=business_id,
            period_name=period_name.strip(),
            start_date=start_date,
            end_date=end_date,
            status=FinancialPeriodStatus.OPEN,
        )
        return self.period_repo.create(period)

    def close_financial_period(
        self,
        business_id: uuid.UUID,
        period_id: uuid.UUID,
        status: FinancialPeriodStatus,
        user_id: uuid.UUID,
    ) -> None:
        self.verify_access(business_id, user_id, [BusinessRole.OWNER, BusinessRole.ACCOUNTANT])
        period = self.period_repo.get_by_id(period_id)
        if not period or period.business_id != business_id:
            raise InvalidOperationError(f"Financial period {period_id} not found")
        self.period_repo.update_status(period_id, status, closed_by=user_id)

    def list_financial_periods(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[FinancialPeriod]:
        self.verify_access(business_id, user_id)
        return self.period_repo.list_by_business(business_id)

    # ==========================================================================
    # 13. Double-Entry General Ledger Reporting & Trial Balance
    # ==========================================================================

    def get_journal_entries(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_code: Optional[str] = None,
    ) -> List[JournalEntry]:
        self.verify_access(business_id, user_id)
        return self.journal_repo.list_by_business(
            business_id, start_date=start_date, end_date=end_date, account_code=account_code
        )

    def get_trial_balance(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        as_of_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        self.verify_access(business_id, user_id)
        return self.journal_repo.get_trial_balance(business_id, as_of_date=as_of_date)

    def get_account_ledger(
        self,
        business_id: uuid.UUID,
        account_code: str,
        user_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        self.verify_access(business_id, user_id)
        entries = self.journal_repo.list_by_business(
            business_id, start_date=start_date, end_date=end_date, account_code=account_code
        )
        postings = []
        running_debit = Decimal("0.00")
        running_credit = Decimal("0.00")

        for e in entries:
            for l in e.lines:
                if l.account_code == account_code:
                    running_debit += l.debit.amount
                    running_credit += l.credit.amount
                    postings.append({
                        "entry_id": str(e.id),
                        "entry_number": e.entry_number,
                        "entry_date": e.entry_date.isoformat(),
                        "reference_type": e.reference_type,
                        "description": e.description,
                        "debit": float(l.debit.amount),
                        "debit_exact": f"{l.debit.amount:.2f}",
                        "credit": float(l.credit.amount),
                        "credit_exact": f"{l.credit.amount:.2f}",
                        "cumulative_net": float(running_debit - running_credit),
                        "cumulative_net_exact": f"{running_debit - running_credit:.2f}",
                    })

        acc_name = ACCOUNT_NAMES.get(account_code, f"Account {account_code}")
        return {
            "business_id": str(business_id),
            "account_code": account_code,
            "account_name": acc_name,
            "total_debits": float(running_debit),
            "total_debits_exact": f"{running_debit:.2f}",
            "total_credits": float(running_credit),
            "total_credits_exact": f"{running_credit:.2f}",
            "net_balance": float(running_debit - running_credit),
            "net_balance_exact": f"{running_debit - running_credit:.2f}",
            "postings": postings,
        }

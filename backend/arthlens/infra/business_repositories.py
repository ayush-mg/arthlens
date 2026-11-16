from __future__ import annotations

"""
PostgreSQL Repository Implementations for Business Operating System.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 1: Domain & Infrastructure (Multi-Tenant Repositories & Data Access).
"""


import uuid
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from backend.arthlens.domain.business import (
    FinancialPeriod,
    FinancialPeriodStatus,
    JournalEntry,
    JournalEntryLine,
    Business,
    BusinessMembership,
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
    PurchaseReturn,
    PurchaseReturnItem,
    PurchaseStatus,
    SalesInvoice,
    SalesInvoiceItem,
    Supplier,
)
from backend.arthlens.infra.database import get_session_factory
from backend.arthlens.infra.models import (
    AgentSessionModel,
    AgentTurnModel,
    BusinessMembershipModel,
    BusinessModel,
    CustomerModel,
    DecisionEvaluationModel,
    ExpenseRecordModel,
    GoalModel,
    IncomeRecordModel,
    InventoryBalanceModel,
    InventoryCostReconciliationEventModel,
    InventoryCostReconciliationModel,
    InventoryMovementModel,
    FinancialPeriodModel,
    JournalEntryLineModel,
    JournalEntryModel,
    PaymentModel,
    ProductModel,
    PurchaseReturnItemModel,
    PurchaseReturnModel,
    PurchaseItemModel,
    PurchaseModel,
    SalesInvoiceItemModel,
    SalesInvoiceModel,
    SupplierModel,
)


class PostgresBusinessRepository:
    """Manages multi-business workspaces and user role memberships."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, business: Business) -> Business:
        with self.session_factory() as session:
            model = BusinessModel(
                id=business.id,
                owner_id=business.owner_id,
                name=business.name,
                industry=business.industry,
                address=business.address,
                financial_year_start=business.financial_year_start,
                currency=business.currency,
                preferences=business.preferences,
                is_archived=business.is_archived,
                created_at=business.created_at,
                updated_at=business.updated_at,
            )
            session.add(model)
            session.flush()
            # Automatically add owner membership
            owner_membership = BusinessMembershipModel(
                id=uuid.uuid4(),
                business_id=business.id,
                user_id=business.owner_id,
                role=BusinessRole.OWNER.value,
            )
            session.add(owner_membership)
            session.commit()
            return business

    def get_by_id(self, business_id: uuid.UUID) -> Optional[Business]:
        with self.session_factory() as session:
            model = session.get(BusinessModel, business_id)
            if not model:
                return None
            return Business(
                id=model.id,
                owner_id=model.owner_id,
                name=model.name,
                industry=model.industry,
                address=model.address,
                financial_year_start=model.financial_year_start,
                currency=model.currency,
                preferences=dict(model.preferences or {}),
                is_archived=model.is_archived,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )

    def list_by_user(self, user_id: uuid.UUID) -> List[Business]:
        with self.session_factory() as session:
            stmt = (
                select(BusinessModel)
                .join(BusinessMembershipModel, BusinessMembershipModel.business_id == BusinessModel.id)
                .where(
                    BusinessMembershipModel.user_id == user_id,
                    BusinessMembershipModel.is_active == True,
                )
                .order_by(BusinessModel.created_at.desc())
            )
            rows = session.execute(stmt).scalars().all()
            return [
                Business(
                    id=m.id,
                    owner_id=m.owner_id,
                    name=m.name,
                    industry=m.industry,
                    address=m.address,
                    financial_year_start=m.financial_year_start,
                    currency=m.currency,
                    preferences=dict(m.preferences or {}),
                    is_archived=m.is_archived,
                    created_at=m.created_at,
                    updated_at=m.updated_at,
                )
                for m in rows
            ]

    def add_member(self, membership: BusinessMembership) -> BusinessMembership:
        with self.session_factory() as session:
            role = membership.role.value if isinstance(membership.role, BusinessRole) else str(membership.role)
            stmt = select(BusinessMembershipModel).where(
                BusinessMembershipModel.business_id == membership.business_id,
                BusinessMembershipModel.user_id == membership.user_id,
            )
            model = session.execute(stmt).scalars().first()
            if model:
                model.role = role
                model.is_active = True
            else:
                model = BusinessMembershipModel(
                    id=membership.id,
                    business_id=membership.business_id,
                    user_id=membership.user_id,
                    role=role,
                    is_active=True,
                )
                session.add(model)
            session.commit()
            return BusinessMembership(
                id=model.id,
                business_id=model.business_id,
                user_id=model.user_id,
                role=BusinessRole(model.role),
                created_at=model.created_at,
                is_active=model.is_active,
            )

    def get_membership(self, business_id: uuid.UUID, user_id: uuid.UUID) -> Optional[BusinessMembership]:
        with self.session_factory() as session:
            stmt = select(BusinessMembershipModel).where(
                BusinessMembershipModel.business_id == business_id,
                BusinessMembershipModel.user_id == user_id,
            )
            m = session.execute(stmt).scalars().first()
            if not m:
                return None
            return BusinessMembership(
                id=m.id,
                business_id=m.business_id,
                user_id=m.user_id,
                role=BusinessRole(m.role),
                created_at=m.created_at,
                is_active=m.is_active,
            )

    def list_members(self, business_id: uuid.UUID) -> List[BusinessMembership]:
        with self.session_factory() as session:
            stmt = select(BusinessMembershipModel).where(BusinessMembershipModel.business_id == business_id)
            rows = session.execute(stmt).scalars().all()
            return [
                BusinessMembership(
                    id=m.id,
                    business_id=m.business_id,
                    user_id=m.user_id,
                    role=BusinessRole(m.role),
                    created_at=m.created_at,
                    is_active=m.is_active,
                )
                for m in rows
            ]

    def remove_member(self, business_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        with self.session_factory() as session:
            stmt = select(BusinessMembershipModel).where(
                BusinessMembershipModel.business_id == business_id,
                BusinessMembershipModel.user_id == user_id,
            )
            membership = session.execute(stmt).scalars().first()
            if membership is None or not membership.is_active:
                return False
            membership.is_active = False
            session.commit()
            return True

    def update_member_role(
        self,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        role: BusinessRole,
    ) -> Optional[BusinessMembership]:
        with self.session_factory() as session:
            stmt = select(BusinessMembershipModel).where(
                BusinessMembershipModel.business_id == business_id,
                BusinessMembershipModel.user_id == user_id,
                BusinessMembershipModel.is_active == True,
            ).with_for_update()
            model = session.execute(stmt).scalars().first()
            if model is None:
                return None
            model.role = role.value
            session.commit()
            return BusinessMembership(
                id=model.id,
                business_id=model.business_id,
                user_id=model.user_id,
                role=BusinessRole(model.role),
                created_at=model.created_at,
                is_active=model.is_active,
            )

    def update(self, business: Business) -> Business:
        with self.session_factory() as session:
            m = session.get(BusinessModel, business.id)
            if m:
                m.name = business.name
                m.industry = business.industry
                m.address = business.address
                m.financial_year_start = business.financial_year_start
                m.currency = business.currency
                m.preferences = business.preferences
                m.is_archived = business.is_archived
                m.updated_at = datetime.now(timezone.utc)
                session.commit()
            return business

    def set_archived(self, business_id: uuid.UUID, is_archived: bool) -> None:
        with self.session_factory() as session:
            m = session.get(BusinessModel, business_id)
            if m:
                m.is_archived = is_archived
                m.updated_at = datetime.now(timezone.utc)
                session.commit()

    def delete(self, business_id: uuid.UUID) -> None:
        with self.session_factory() as session:
            recon_ids = select(InventoryCostReconciliationModel.id).where(
                InventoryCostReconciliationModel.business_id == business_id
            )
            session.execute(
                delete(InventoryCostReconciliationEventModel).where(
                    InventoryCostReconciliationEventModel.reconciliation_id.in_(recon_ids)
                )
            )
            session.execute(
                delete(InventoryCostReconciliationModel).where(
                    InventoryCostReconciliationModel.business_id == business_id
                )
            )
            return_ids = select(PurchaseReturnModel.id).where(
                PurchaseReturnModel.business_id == business_id
            )
            session.execute(
                delete(PurchaseReturnItemModel).where(
                    PurchaseReturnItemModel.purchase_return_id.in_(return_ids)
                )
            )
            session.execute(
                delete(PurchaseReturnModel).where(
                    PurchaseReturnModel.business_id == business_id
                )
            )
            m = session.get(BusinessModel, business_id)
            if m:
                session.delete(m)
                session.commit()


class PostgresCustomerRepository:
    """Manages customers and outstanding credit balances."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, customer: Customer) -> Customer:
        with self.session_factory() as session:
            model = CustomerModel(
                id=customer.id,
                business_id=customer.business_id,
                name=customer.name,
                phone=customer.phone,
                email=customer.email,
                address=customer.address,
                credit_limit=customer.credit_limit.amount,
                opening_balance=customer.opening_balance.amount,
                current_balance=customer.current_balance.amount,
                is_archived=customer.is_archived,
                created_at=customer.created_at,
            )
            session.add(model)
            session.commit()
            return customer

    def get_by_id(
        self,
        customer_id: uuid.UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> Optional[Customer]:
        if session is not None:
            stmt = select(CustomerModel).where(CustomerModel.id == customer_id)
            if for_update:
                stmt = stmt.with_for_update()
            model = session.execute(stmt).scalars().first()
            if not model:
                return None
            return Customer(
                id=model.id,
                business_id=model.business_id,
                name=model.name,
                phone=model.phone,
                email=model.email,
                address=model.address,
                credit_limit=Money(model.credit_limit),
                opening_balance=Money(model.opening_balance),
                current_balance=Money(model.current_balance),
                is_archived=model.is_archived,
                created_at=model.created_at,
            )
        with self.session_factory() as s:
            return self.get_by_id(customer_id, session=s, for_update=for_update)

    def list_by_business(self, business_id: uuid.UUID, include_archived: bool = False) -> List[Customer]:
        with self.session_factory() as session:
            stmt = select(CustomerModel).where(CustomerModel.business_id == business_id)
            if not include_archived:
                stmt = stmt.where(CustomerModel.is_archived == False)
            stmt = stmt.order_by(CustomerModel.name.asc())
            rows = session.execute(stmt).scalars().all()
            return [
                Customer(
                    id=m.id,
                    business_id=m.business_id,
                    name=m.name,
                    phone=m.phone,
                    email=m.email,
                    address=m.address,
                    credit_limit=Money(m.credit_limit),
                    opening_balance=Money(m.opening_balance),
                    current_balance=Money(m.current_balance),
                    is_archived=m.is_archived,
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def update_balance(self, customer_id: uuid.UUID, new_balance: Money, session: Optional[Session] = None) -> None:
        if session is not None:
            model = session.get(CustomerModel, customer_id)
            if model:
                model.current_balance = new_balance.amount
                session.flush()
            return
        with self.session_factory() as s:
            self.update_balance(customer_id, new_balance, session=s)
            s.commit()

    def update(self, customer: Customer) -> Customer:
        with self.session_factory() as session:
            model = session.get(CustomerModel, customer.id)
            if model:
                model.name = customer.name
                model.phone = customer.phone
                model.email = customer.email
                model.address = customer.address
                model.credit_limit = customer.credit_limit.amount
                model.is_archived = customer.is_archived
                session.commit()
            return customer

    def set_archived(self, customer_id: uuid.UUID, is_archived: bool) -> None:
        with self.session_factory() as session:
            model = session.get(CustomerModel, customer_id)
            if model:
                model.is_archived = is_archived
                session.commit()


class PostgresSupplierRepository:
    """Manages suppliers and outstanding payables balances."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, supplier: Supplier) -> Supplier:
        with self.session_factory() as session:
            model = SupplierModel(
                id=supplier.id,
                business_id=supplier.business_id,
                name=supplier.name,
                contact_person=supplier.contact_person,
                phone=supplier.phone,
                email=supplier.email,
                address=supplier.address,
                opening_balance=supplier.opening_balance.amount,
                current_balance=supplier.current_balance.amount,
                is_archived=supplier.is_archived,
                created_at=supplier.created_at,
            )
            session.add(model)
            session.commit()
            return supplier

    def get_by_id(
        self,
        supplier_id: uuid.UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> Optional[Supplier]:
        def _op(s: Session) -> Optional[Supplier]:
            if for_update:
                stmt = select(SupplierModel).where(SupplierModel.id == supplier_id).with_for_update()
                model = s.execute(stmt).scalar_one_or_none()
            else:
                model = s.get(SupplierModel, supplier_id)
            if not model:
                return None
            return Supplier(
                id=model.id,
                business_id=model.business_id,
                name=model.name,
                contact_person=model.contact_person,
                phone=model.phone,
                email=model.email,
                address=model.address,
                opening_balance=Money(model.opening_balance),
                current_balance=Money(model.current_balance),
                is_archived=model.is_archived,
                created_at=model.created_at,
            )

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def list_by_business(self, business_id: uuid.UUID, include_archived: bool = False) -> List[Supplier]:
        with self.session_factory() as session:
            stmt = select(SupplierModel).where(SupplierModel.business_id == business_id)
            if not include_archived:
                stmt = stmt.where(SupplierModel.is_archived == False)
            stmt = stmt.order_by(SupplierModel.name.asc())
            rows = session.execute(stmt).scalars().all()
            return [
                Supplier(
                    id=m.id,
                    business_id=m.business_id,
                    name=m.name,
                    contact_person=m.contact_person,
                    phone=m.phone,
                    email=m.email,
                    address=m.address,
                    opening_balance=Money(m.opening_balance),
                    current_balance=Money(m.current_balance),
                    is_archived=m.is_archived,
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def update_balance(self, supplier_id: uuid.UUID, new_balance: Money, session: Optional[Session] = None) -> None:
        if session is not None:
            model = session.get(SupplierModel, supplier_id)
            if model:
                model.current_balance = new_balance.amount
                session.flush()
            return
        with self.session_factory() as s:
            self.update_balance(supplier_id, new_balance, session=s)
            s.commit()

    def update(self, supplier: Supplier) -> Supplier:
        with self.session_factory() as session:
            model = session.get(SupplierModel, supplier.id)
            if model:
                model.name = supplier.name
                model.contact_person = supplier.contact_person
                model.phone = supplier.phone
                model.email = supplier.email
                model.address = supplier.address
                model.is_archived = supplier.is_archived
                session.commit()
            return supplier

    def set_archived(self, supplier_id: uuid.UUID, is_archived: bool) -> None:
        with self.session_factory() as session:
            model = session.get(SupplierModel, supplier_id)
            if model:
                model.is_archived = is_archived
                session.commit()


class PostgresProductRepository:
    """Manages product catalog and pricing."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, product: Product) -> Product:
        with self.session_factory() as session:
            model = ProductModel(
                id=product.id,
                business_id=product.business_id,
                sku=product.sku,
                name=product.name,
                category=product.category,
                unit=product.unit,
                purchase_price=product.purchase_price.amount,
                selling_price=product.selling_price.amount,
                min_stock_alert=product.min_stock_alert,
                is_active=product.is_active,
                created_at=product.created_at,
            )
            session.add(model)
            session.commit()
            return product

    def get_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        with self.session_factory() as session:
            model = session.get(ProductModel, product_id)
            if not model:
                return None
            return Product(
                id=model.id,
                business_id=model.business_id,
                sku=model.sku,
                name=model.name,
                category=model.category,
                unit=model.unit,
                purchase_price=Money(model.purchase_price),
                selling_price=Money(model.selling_price),
                min_stock_alert=Decimal(str(model.min_stock_alert)),
                is_active=model.is_active,
                created_at=model.created_at,
            )

    def list_by_business(self, business_id: uuid.UUID, active_only: bool = False) -> List[Product]:
        with self.session_factory() as session:
            stmt = select(ProductModel).where(ProductModel.business_id == business_id)
            if active_only:
                stmt = stmt.where(ProductModel.is_active == True)
            stmt = stmt.order_by(ProductModel.name.asc())
            rows = session.execute(stmt).scalars().all()
            return [
                Product(
                    id=m.id,
                    business_id=m.business_id,
                    sku=m.sku,
                    name=m.name,
                    category=m.category,
                    unit=m.unit,
                    purchase_price=Money(m.purchase_price),
                    selling_price=Money(m.selling_price),
                    min_stock_alert=Decimal(str(m.min_stock_alert)),
                    is_active=m.is_active,
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def update(self, product: Product) -> Product:
        with self.session_factory() as session:
            model = session.get(ProductModel, product.id)
            if model:
                model.sku = product.sku
                model.name = product.name
                model.category = product.category
                model.unit = product.unit
                model.purchase_price = product.purchase_price.amount
                model.selling_price = product.selling_price.amount
                model.min_stock_alert = product.min_stock_alert
                model.is_active = product.is_active
                session.commit()
            return product

    def set_active(self, product_id: uuid.UUID, is_active: bool) -> None:
        with self.session_factory() as session:
            model = session.get(ProductModel, product_id)
            if model:
                model.is_active = is_active
                session.commit()


class PostgresInventoryRepository:
    """Manages physical stock levels, valuations, and movement ledger."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def get_balance(
        self,
        business_id: uuid.UUID,
        product_id: uuid.UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> Optional[InventoryBalance]:
        if session is not None:
            stmt = select(InventoryBalanceModel).where(
                InventoryBalanceModel.business_id == business_id,
                InventoryBalanceModel.product_id == product_id,
            )
            if for_update:
                stmt = stmt.with_for_update()
            m = session.execute(stmt).scalars().first()
            if not m:
                return None
            return InventoryBalance(
                id=m.id,
                business_id=m.business_id,
                product_id=m.product_id,
                quantity_on_hand=Decimal(str(m.quantity_on_hand)),
                unit_cost=Money(m.unit_cost),
                total_valuation=Money(m.total_valuation),
                last_movement_at=m.last_movement_at,
            )
        with self.session_factory() as s:
            return self.get_balance(business_id, product_id, session=s, for_update=for_update)

    def save_balance(self, balance: InventoryBalance, session: Optional[Session] = None) -> InventoryBalance:
        if session is not None:
            model = session.get(InventoryBalanceModel, balance.id)
            if not model:
                model = InventoryBalanceModel(
                    id=balance.id,
                    business_id=balance.business_id,
                    product_id=balance.product_id,
                    quantity_on_hand=balance.quantity_on_hand,
                    unit_cost=balance.unit_cost.amount,
                    total_valuation=balance.total_valuation.amount,
                    last_movement_at=balance.last_movement_at,
                )
                session.add(model)
            else:
                model.quantity_on_hand = balance.quantity_on_hand
                model.unit_cost = balance.unit_cost.amount
                model.total_valuation = balance.total_valuation.amount
                model.last_movement_at = balance.last_movement_at
            session.flush()
            return balance
        with self.session_factory() as s:
            res = self.save_balance(balance, session=s)
            s.commit()
            return res

    def record_movement(self, movement: InventoryMovement, session: Optional[Session] = None) -> InventoryMovement:
        if session is not None:
            reconciliation_status = movement.cost_reconciliation_status
            if movement.cost_basis is None or (
                movement.cost_basis == Money.zero()
                and movement.movement_type in (
                    MovementType.SALE,
                    MovementType.RETURN,
                    MovementType.OPENING,
                    MovementType.ADJUSTMENT,
                )
            ):
                reconciliation_status = "UNRECONCILED"
            model = InventoryMovementModel(
                id=movement.id,
                business_id=movement.business_id,
                product_id=movement.product_id,
                movement_type=movement.movement_type.value if isinstance(movement.movement_type, MovementType) else str(movement.movement_type),
                quantity=movement.quantity,
                unit_price=movement.unit_price.amount,
                cost_basis=movement.cost_basis.amount if movement.cost_basis else None,
                source_purchase_item_id=movement.source_purchase_item_id,
                cost_reconciliation_status=reconciliation_status,
                reconciled_at=movement.reconciled_at,
                reconciled_by_user_id=movement.reconciled_by_user_id,
                reconciliation_note=movement.reconciliation_note,
                reference_id=movement.reference_id,
                reason=movement.reason,
                balance_after=movement.balance_after,
                created_at=movement.created_at,
            )
            session.add(model)
            session.flush()
            return movement
        with self.session_factory() as s:
            res = self.record_movement(movement, session=s)
            s.commit()
            return res

    def list_balances(self, business_id: uuid.UUID) -> List[InventoryBalance]:
        with self.session_factory() as session:
            stmt = select(InventoryBalanceModel).where(InventoryBalanceModel.business_id == business_id)
            rows = session.execute(stmt).scalars().all()
            return [
                InventoryBalance(
                    id=m.id,
                    business_id=m.business_id,
                    product_id=m.product_id,
                    quantity_on_hand=Decimal(str(m.quantity_on_hand)),
                    unit_cost=Money(m.unit_cost),
                    total_valuation=Money(m.total_valuation),
                    last_movement_at=m.last_movement_at,
                )
                for m in rows
            ]

    def list_movements(
        self,
        business_id: uuid.UUID,
        product_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None,
    ) -> List[InventoryMovement]:
        def _list(session: Session) -> List[InventoryMovement]:
            stmt = select(InventoryMovementModel).where(InventoryMovementModel.business_id == business_id)
            if product_id:
                stmt = stmt.where(InventoryMovementModel.product_id == product_id)
            stmt = stmt.order_by(InventoryMovementModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                InventoryMovement(
                    id=m.id,
                    business_id=m.business_id,
                    product_id=m.product_id,
                    movement_type=MovementType(m.movement_type),
                    quantity=Decimal(str(m.quantity)),
                    unit_price=Money(m.unit_price),
                    cost_basis=Money(m.cost_basis) if m.cost_basis is not None else None,
                    source_purchase_item_id=m.source_purchase_item_id,
                    cost_reconciliation_status=m.cost_reconciliation_status,
                    reconciled_at=m.reconciled_at,
                    reconciled_by_user_id=m.reconciled_by_user_id,
                    reconciliation_note=m.reconciliation_note,
                    reference_id=m.reference_id,
                    reason=m.reason,
                    balance_after=Decimal(str(m.balance_after)),
                    created_at=m.created_at,
                )
                for m in rows
            ]

        if session is not None:
            return _list(session)
        with self.session_factory() as db_session:
            return _list(db_session)


class PostgresSalesInvoiceRepository:
    """Manages sales invoices and line item persistence."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, invoice: SalesInvoice, session: Optional[Session] = None) -> SalesInvoice:
        if session is not None:
            inv_model = SalesInvoiceModel(
                id=invoice.id,
                business_id=invoice.business_id,
                customer_id=invoice.customer_id,
                invoice_number=invoice.invoice_number,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                subtotal=invoice.subtotal.amount,
                tax_amount=invoice.tax_amount.amount,
                discount_amount=invoice.discount_amount.amount,
                total_amount=invoice.total_amount.amount,
                paid_amount=invoice.paid_amount.amount,
                status=invoice.status.value if isinstance(invoice.status, InvoiceStatus) else str(invoice.status),
                notes=invoice.notes,
                created_at=invoice.created_at,
            )
            session.add(inv_model)
            session.flush()
            for item in invoice.items:
                item_model = SalesInvoiceItemModel(
                    id=item.id,
                    invoice_id=invoice.id,
                    product_id=item.product_id,
                    description=item.description,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price.amount,
                    discount_percent=item.discount_percent,
                    total_price=item.total_price.amount,
                )
                session.add(item_model)
            session.flush()
            return invoice
        with self.session_factory() as s:
            res = self.create(invoice, session=s)
            s.commit()
            return res

    def get_by_id(
        self,
        invoice_id: uuid.UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> Optional[SalesInvoice]:
        if session is not None:
            stmt = select(SalesInvoiceModel).where(SalesInvoiceModel.id == invoice_id)
            if for_update:
                stmt = stmt.with_for_update()
            inv = session.execute(stmt).scalars().first()
            if not inv:
                return None
            item_stmt = select(SalesInvoiceItemModel).where(SalesInvoiceItemModel.invoice_id == invoice_id)
            items = session.execute(item_stmt).scalars().all()
            return SalesInvoice(
                id=inv.id,
                business_id=inv.business_id,
                customer_id=inv.customer_id,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                subtotal=Money(inv.subtotal),
                tax_amount=Money(inv.tax_amount),
                discount_amount=Money(inv.discount_amount),
                total_amount=Money(inv.total_amount),
                paid_amount=Money(inv.paid_amount),
                status=InvoiceStatus(inv.status),
                notes=inv.notes,
                items=[
                    SalesInvoiceItem(
                        id=it.id,
                        invoice_id=it.invoice_id,
                        product_id=it.product_id,
                        description=it.description,
                        quantity=Decimal(str(it.quantity)),
                        unit=it.unit,
                        unit_price=Money(it.unit_price),
                        discount_percent=Decimal(str(it.discount_percent)),
                        total_price=Money(it.total_price),
                    )
                    for it in items
                ],
                created_at=inv.created_at,
            )
        with self.session_factory() as s:
            return self.get_by_id(invoice_id, session=s, for_update=for_update)

    def list_by_business(self, business_id: uuid.UUID, customer_id: Optional[uuid.UUID] = None) -> List[SalesInvoice]:
        with self.session_factory() as session:
            stmt = select(SalesInvoiceModel).where(SalesInvoiceModel.business_id == business_id)
            if customer_id:
                stmt = stmt.where(SalesInvoiceModel.customer_id == customer_id)
            stmt = stmt.order_by(SalesInvoiceModel.invoice_date.desc())
            rows = session.execute(stmt).scalars().all()
            if not rows:
                return []
            inv_ids = [m.id for m in rows]
            item_stmt = select(SalesInvoiceItemModel).where(SalesInvoiceItemModel.invoice_id.in_(inv_ids))
            all_items = session.execute(item_stmt).scalars().all()
            items_by_inv = {}
            for it in all_items:
                items_by_inv.setdefault(it.invoice_id, []).append(
                    SalesInvoiceItem(
                        id=it.id,
                        invoice_id=it.invoice_id,
                        product_id=it.product_id,
                        description=it.description,
                        quantity=Decimal(str(it.quantity)),
                        unit=it.unit,
                        unit_price=Money(it.unit_price),
                        discount_percent=Decimal(str(it.discount_percent)),
                        total_price=Money(it.total_price),
                    )
                )
            return [
                SalesInvoice(
                    id=m.id,
                    business_id=m.business_id,
                    customer_id=m.customer_id,
                    invoice_number=m.invoice_number,
                    invoice_date=m.invoice_date,
                    due_date=m.due_date,
                    subtotal=Money(m.subtotal),
                    tax_amount=Money(m.tax_amount),
                    discount_amount=Money(m.discount_amount),
                    total_amount=Money(m.total_amount),
                    paid_amount=Money(m.paid_amount),
                    status=InvoiceStatus(m.status),
                    notes=m.notes,
                    items=items_by_inv.get(m.id, []),
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def update_payment(self, invoice_id: uuid.UUID, paid_amount: Money, status: InvoiceStatus, session: Optional[Session] = None) -> None:
        if session is not None:
            inv = session.get(SalesInvoiceModel, invoice_id)
            if inv:
                inv.paid_amount = paid_amount.amount
                inv.status = status.value
                session.flush()
            return
        with self.session_factory() as s:
            self.update_payment(invoice_id, paid_amount, status, session=s)
            s.commit()

    def update_status(self, invoice_id: uuid.UUID, status: InvoiceStatus, session: Optional[Session] = None) -> None:
        if session is not None:
            inv = session.get(SalesInvoiceModel, invoice_id)
            if inv:
                inv.status = status.value
                session.flush()
            return
        with self.session_factory() as s:
            self.update_status(invoice_id, status, session=s)
            s.commit()

    def delete(self, invoice_id: uuid.UUID, session: Optional[Session] = None) -> bool:
        if session is not None:
            session.execute(delete(SalesInvoiceItemModel).where(SalesInvoiceItemModel.invoice_id == invoice_id))
            result = session.execute(delete(SalesInvoiceModel).where(SalesInvoiceModel.id == invoice_id))
            session.flush()
            return result.rowcount > 0
        with self.session_factory() as s:
            with s.begin():
                return self.delete(invoice_id, session=s)


class PostgresPurchaseRepository:
    """Manages supplier procurement bills and line items."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, purchase: Purchase, session: Optional[Session] = None) -> Purchase:
        if session is not None:
            model = PurchaseModel(
                id=purchase.id,
                business_id=purchase.business_id,
                supplier_id=purchase.supplier_id,
                bill_number=purchase.bill_number,
                purchase_date=purchase.purchase_date,
                due_date=purchase.due_date,
                subtotal=purchase.subtotal.amount,
                tax_amount=purchase.tax_amount.amount,
                total_amount=purchase.total_amount.amount,
                paid_amount=purchase.paid_amount.amount,
                return_credit_amount=purchase.return_credit_amount.amount,
                status=purchase.status.value if isinstance(purchase.status, PurchaseStatus) else str(purchase.status),
                created_at=purchase.created_at,
            )
            session.add(model)
            session.flush()
            for it in purchase.items:
                item_model = PurchaseItemModel(
                    id=it.id,
                    purchase_id=purchase.id,
                    product_id=it.product_id,
                    description=it.description,
                    quantity=it.quantity,
                    unit=it.unit,
                    unit_price=it.unit_price.amount,
                    total_price=it.total_price.amount,
                )
                session.add(item_model)
            session.flush()
            return purchase
        with self.session_factory() as s:
            res = self.create(purchase, session=s)
            s.commit()
            return res

    def get_by_id(
        self,
        purchase_id: uuid.UUID,
        session: Optional[Session] = None,
        for_update: bool = False,
    ) -> Optional[Purchase]:
        if session is not None:
            stmt = select(PurchaseModel).where(PurchaseModel.id == purchase_id)
            if for_update:
                stmt = stmt.with_for_update()
            p = session.execute(stmt).scalars().first()
            if not p:
                return None
            item_stmt = select(PurchaseItemModel).where(PurchaseItemModel.purchase_id == purchase_id)
            if for_update:
                item_stmt = item_stmt.with_for_update()
            items = session.execute(item_stmt).scalars().all()
            returned_rows = session.execute(
                select(
                    PurchaseReturnItemModel.purchase_item_id,
                    func.sum(PurchaseReturnItemModel.quantity),
                )
                .join(PurchaseReturnModel, PurchaseReturnModel.id == PurchaseReturnItemModel.purchase_return_id)
                .where(PurchaseReturnModel.purchase_id == purchase_id)
                .group_by(PurchaseReturnItemModel.purchase_item_id)
            ).all()
            returned_quantities = {item_id: Decimal(str(quantity)) for item_id, quantity in returned_rows}
            return Purchase(
                id=p.id,
                business_id=p.business_id,
                supplier_id=p.supplier_id,
                bill_number=p.bill_number,
                purchase_date=p.purchase_date,
                due_date=p.due_date,
                subtotal=Money(p.subtotal),
                tax_amount=Money(p.tax_amount),
                total_amount=Money(p.total_amount),
                paid_amount=Money(p.paid_amount),
                return_credit_amount=Money(p.return_credit_amount),
                status=PurchaseStatus(p.status),
                items=[
                    PurchaseItem(
                        id=it.id,
                        purchase_id=it.purchase_id,
                        product_id=it.product_id,
                        description=it.description,
                        quantity=Decimal(str(it.quantity)),
                        unit=it.unit,
                        unit_price=Money(it.unit_price),
                        total_price=Money(it.total_price),
                        returned_quantity=returned_quantities.get(it.id, Decimal("0.0000")),
                    )
                    for it in items
                ],
                created_at=p.created_at,
            )
        with self.session_factory() as s:
            return self.get_by_id(purchase_id, session=s, for_update=for_update)

    def list_by_business(self, business_id: uuid.UUID, supplier_id: Optional[uuid.UUID] = None) -> List[Purchase]:
        with self.session_factory() as session:
            stmt = select(PurchaseModel).where(PurchaseModel.business_id == business_id)
            if supplier_id:
                stmt = stmt.where(PurchaseModel.supplier_id == supplier_id)
            stmt = stmt.order_by(PurchaseModel.purchase_date.desc())
            rows = session.execute(stmt).scalars().all()
            if not rows:
                return []
            pur_ids = [m.id for m in rows]
            item_stmt = select(PurchaseItemModel).where(PurchaseItemModel.purchase_id.in_(pur_ids))
            all_items = session.execute(item_stmt).scalars().all()
            returned_rows = session.execute(
                select(
                    PurchaseReturnItemModel.purchase_item_id,
                    func.sum(PurchaseReturnItemModel.quantity),
                )
                .join(PurchaseReturnModel, PurchaseReturnModel.id == PurchaseReturnItemModel.purchase_return_id)
                .where(PurchaseReturnModel.purchase_id.in_(pur_ids))
                .group_by(PurchaseReturnItemModel.purchase_item_id)
            ).all()
            returned_quantities = {item_id: Decimal(str(quantity)) for item_id, quantity in returned_rows}
            items_by_pur = {}
            for it in all_items:
                items_by_pur.setdefault(it.purchase_id, []).append(
                    PurchaseItem(
                        id=it.id,
                        purchase_id=it.purchase_id,
                        product_id=it.product_id,
                        description=it.description,
                        quantity=Decimal(str(it.quantity)),
                        unit=it.unit,
                        unit_price=Money(it.unit_price),
                        total_price=Money(it.total_price),
                        returned_quantity=returned_quantities.get(it.id, Decimal("0.0000")),
                    )
                )
            return [
                Purchase(
                    id=m.id,
                    business_id=m.business_id,
                    supplier_id=m.supplier_id,
                    bill_number=m.bill_number,
                    purchase_date=m.purchase_date,
                    due_date=m.due_date,
                    subtotal=Money(m.subtotal),
                    tax_amount=Money(m.tax_amount),
                    total_amount=Money(m.total_amount),
                    paid_amount=Money(m.paid_amount),
                    return_credit_amount=Money(m.return_credit_amount),
                    status=PurchaseStatus(m.status),
                    items=items_by_pur.get(m.id, []),
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def update_payment(self, purchase_id: uuid.UUID, paid_amount: Money, status: PurchaseStatus, session: Optional[Session] = None) -> None:
        if session is not None:
            p = session.get(PurchaseModel, purchase_id)
            if p:
                p.paid_amount = paid_amount.amount
                p.status = status.value
                session.flush()
            return
        with self.session_factory() as s:
            self.update_payment(purchase_id, paid_amount, status, session=s)
            s.commit()

    def update_status(self, purchase_id: uuid.UUID, status: PurchaseStatus) -> None:
        with self.session_factory() as session:
            p = session.get(PurchaseModel, purchase_id)
            if p:
                p.status = status.value
                session.commit()

    def update_return_state(
        self,
        purchase_id: uuid.UUID,
        paid_amount: Money,
        return_credit_amount: Money,
        status: PurchaseStatus,
        session: Session,
    ) -> None:
        purchase_model = session.get(PurchaseModel, purchase_id)
        if not purchase_model:
            raise ValueError(f"Purchase {purchase_id} disappeared during return posting")
        purchase_model.paid_amount = paid_amount.amount
        purchase_model.return_credit_amount = return_credit_amount.amount
        purchase_model.status = status.value
        session.flush()

    def delete(self, purchase_id: uuid.UUID, session: Optional[Session] = None) -> bool:
        if session is not None:
            session.execute(delete(PurchaseItemModel).where(PurchaseItemModel.purchase_id == purchase_id))
            result = session.execute(delete(PurchaseModel).where(PurchaseModel.id == purchase_id))
            session.flush()
            return result.rowcount > 0
        with self.session_factory() as s:
            with s.begin():
                return self.delete(purchase_id, session=s)


class PostgresPurchaseReturnRepository:
    """Persists immutable supplier returns and line-level source allocations."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    @staticmethod
    def _to_domain(header: PurchaseReturnModel, items: List[PurchaseReturnItemModel]) -> PurchaseReturn:
        return PurchaseReturn(
            id=header.id,
            business_id=header.business_id,
            purchase_id=header.purchase_id,
            supplier_id=header.supplier_id,
            return_date=header.return_date,
            reason=header.reason,
            refund_method=PaymentMethod(header.refund_method) if header.refund_method else None,
            subtotal=Money(header.subtotal),
            tax_amount=Money(header.tax_amount),
            total_amount=Money(header.total_amount),
            created_by=header.created_by,
            idempotency_key=header.idempotency_key,
            items=[
                PurchaseReturnItem(
                    id=item.id,
                    purchase_return_id=item.purchase_return_id,
                    purchase_item_id=item.purchase_item_id,
                    product_id=item.product_id,
                    quantity=Decimal(str(item.quantity)),
                    original_unit_price=Money(item.original_unit_price),
                    pretax_amount=Money(item.pretax_amount),
                    tax_amount=Money(item.tax_amount),
                    inventory_cost_removed=Money(item.inventory_cost_removed),
                )
                for item in items
            ],
            created_at=header.created_at,
        )

    def create(self, purchase_return: PurchaseReturn, session: Optional[Session] = None) -> PurchaseReturn:
        if session is None:
            with self.session_factory() as db_session:
                with db_session.begin():
                    return self.create(purchase_return, session=db_session)

        header = PurchaseReturnModel(
            id=purchase_return.id,
            business_id=purchase_return.business_id,
            purchase_id=purchase_return.purchase_id,
            supplier_id=purchase_return.supplier_id,
            return_date=purchase_return.return_date,
            reason=purchase_return.reason,
            refund_method=purchase_return.refund_method.value if purchase_return.refund_method else None,
            subtotal=purchase_return.subtotal.amount,
            tax_amount=purchase_return.tax_amount.amount,
            total_amount=purchase_return.total_amount.amount,
            created_by=purchase_return.created_by,
            idempotency_key=purchase_return.idempotency_key,
            created_at=purchase_return.created_at,
        )
        session.add(header)
        session.flush()
        for item in purchase_return.items:
            session.add(PurchaseReturnItemModel(
                id=item.id,
                purchase_return_id=purchase_return.id,
                purchase_item_id=item.purchase_item_id,
                product_id=item.product_id,
                quantity=item.quantity,
                original_unit_price=item.original_unit_price.amount,
                pretax_amount=item.pretax_amount.amount,
                tax_amount=item.tax_amount.amount,
                inventory_cost_removed=item.inventory_cost_removed.amount,
            ))
        session.flush()
        return purchase_return

    def get_by_idempotency_key(
        self,
        business_id: uuid.UUID,
        idempotency_key: str,
        session: Session,
    ) -> Optional[PurchaseReturn]:
        header = session.execute(
            select(PurchaseReturnModel).where(
                PurchaseReturnModel.business_id == business_id,
                PurchaseReturnModel.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if not header:
            return None
        items = session.execute(
            select(PurchaseReturnItemModel)
            .where(PurchaseReturnItemModel.purchase_return_id == header.id)
            .order_by(PurchaseReturnItemModel.id)
        ).scalars().all()
        return self._to_domain(header, items)

    def list_by_purchase(
        self,
        business_id: uuid.UUID,
        purchase_id: uuid.UUID,
        session: Optional[Session] = None,
    ) -> List[PurchaseReturn]:
        def _list(db_session: Session) -> List[PurchaseReturn]:
            headers = db_session.execute(
                select(PurchaseReturnModel)
                .where(
                    PurchaseReturnModel.business_id == business_id,
                    PurchaseReturnModel.purchase_id == purchase_id,
                )
                .order_by(PurchaseReturnModel.return_date, PurchaseReturnModel.created_at, PurchaseReturnModel.id)
            ).scalars().all()
            if not headers:
                return []
            ids = [header.id for header in headers]
            items = db_session.execute(
                select(PurchaseReturnItemModel)
                .where(PurchaseReturnItemModel.purchase_return_id.in_(ids))
                .order_by(PurchaseReturnItemModel.id)
            ).scalars().all()
            by_return: Dict[uuid.UUID, List[PurchaseReturnItemModel]] = {}
            for item in items:
                by_return.setdefault(item.purchase_return_id, []).append(item)
            return [self._to_domain(header, by_return.get(header.id, [])) for header in headers]

        if session is not None:
            return _list(session)
        with self.session_factory() as db_session:
            return _list(db_session)


class PostgresPaymentRepository:
    """Manages cash/bank/UPI payment transaction records."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, payment: Payment, session: Optional[Session] = None) -> Payment:
        if session is not None:
            model = PaymentModel(
                id=payment.id,
                business_id=payment.business_id,
                party_type=payment.party_type.value if isinstance(payment.party_type, PartyType) else str(payment.party_type),
                party_id=payment.party_id,
                reference_type=payment.reference_type,
                reference_id=payment.reference_id,
                payment_type=payment.payment_type.value if isinstance(payment.payment_type, PaymentType) else str(payment.payment_type),
                payment_method=payment.payment_method.value if isinstance(payment.payment_method, PaymentMethod) else str(payment.payment_method),
                amount=payment.amount.amount,
                payment_date=payment.payment_date,
                idempotency_key=payment.idempotency_key,
                notes=payment.notes,
                created_at=payment.created_at,
            )
            session.add(model)
            session.flush()
            return payment
        with self.session_factory() as s:
            res = self.create(payment, session=s)
            s.commit()
            return res

    def list_by_business(self, business_id: uuid.UUID, party_id: Optional[uuid.UUID] = None) -> List[Payment]:
        with self.session_factory() as session:
            stmt = select(PaymentModel).where(PaymentModel.business_id == business_id)
            if party_id:
                stmt = stmt.where(PaymentModel.party_id == party_id)
            stmt = stmt.order_by(PaymentModel.payment_date.desc(), PaymentModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                Payment(
                    id=m.id,
                    business_id=m.business_id,
                    party_type=PartyType(m.party_type),
                    party_id=m.party_id,
                    reference_type=m.reference_type,
                    reference_id=m.reference_id,
                    payment_type=PaymentType(m.payment_type),
                    payment_method=PaymentMethod(m.payment_method),
                    amount=Money(m.amount),
                    payment_date=m.payment_date,
                    idempotency_key=m.idempotency_key,
                    notes=m.notes,
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def find_by_idempotency_key(
        self,
        business_id: uuid.UUID,
        idempotency_key: str,
        session: Optional[Session] = None,
    ) -> Optional[Payment]:
        if session is not None:
            stmt = select(PaymentModel).where(
                PaymentModel.business_id == business_id,
                PaymentModel.idempotency_key == idempotency_key,
            )
            m = session.execute(stmt).scalars().first()
            if not m:
                return None
            return Payment(
                id=m.id,
                business_id=m.business_id,
                party_type=PartyType(m.party_type),
                party_id=m.party_id,
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                payment_type=PaymentType(m.payment_type),
                payment_method=PaymentMethod(m.payment_method),
                amount=Money(m.amount),
                payment_date=m.payment_date,
                idempotency_key=m.idempotency_key,
                notes=m.notes,
                created_at=m.created_at,
            )
        with self.session_factory() as s:
            return self.find_by_idempotency_key(business_id, idempotency_key, session=s)


class PostgresIncomeExpenseRepository:
    """Manages direct income receipts and operational expenditure records."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create_income(self, record: IncomeRecord, session: Optional[Session] = None) -> IncomeRecord:
        def _op(s: Session) -> IncomeRecord:
            model = IncomeRecordModel(
                id=record.id,
                business_id=record.business_id,
                category=record.category,
                amount=record.amount.amount,
                date=record.date,
                description=record.description,
                payment_method=record.payment_method.value if isinstance(record.payment_method, PaymentMethod) else str(record.payment_method),
                created_at=record.created_at,
            )
            s.add(model)
            s.flush()
            return record

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            with s.begin():
                return _op(s)

    def list_income(self, business_id: uuid.UUID, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[IncomeRecord]:
        with self.session_factory() as session:
            stmt = select(IncomeRecordModel).where(IncomeRecordModel.business_id == business_id)
            if start_date:
                stmt = stmt.where(IncomeRecordModel.date >= start_date)
            if end_date:
                stmt = stmt.where(IncomeRecordModel.date <= end_date)
            stmt = stmt.order_by(IncomeRecordModel.date.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                IncomeRecord(
                    id=m.id,
                    business_id=m.business_id,
                    category=m.category,
                    amount=Money(m.amount),
                    date=m.date,
                    description=m.description,
                    payment_method=PaymentMethod(m.payment_method),
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def create_expense(self, record: ExpenseRecord, session: Optional[Session] = None) -> ExpenseRecord:
        def _op(s: Session) -> ExpenseRecord:
            model = ExpenseRecordModel(
                id=record.id,
                business_id=record.business_id,
                category=record.category.value if isinstance(record.category, ExpenseCategory) else str(record.category),
                amount=record.amount.amount,
                date=record.date,
                description=record.description,
                payment_method=record.payment_method.value if isinstance(record.payment_method, PaymentMethod) else str(record.payment_method),
                is_recurring=record.is_recurring,
                created_at=record.created_at,
            )
            s.add(model)
            s.flush()
            return record

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            with s.begin():
                return _op(s)

    def list_expenses(self, business_id: uuid.UUID, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[ExpenseRecord]:
        with self.session_factory() as session:
            stmt = select(ExpenseRecordModel).where(ExpenseRecordModel.business_id == business_id)
            if start_date:
                stmt = stmt.where(ExpenseRecordModel.date >= start_date)
            if end_date:
                stmt = stmt.where(ExpenseRecordModel.date <= end_date)
            stmt = stmt.order_by(ExpenseRecordModel.date.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                ExpenseRecord(
                    id=m.id,
                    business_id=m.business_id,
                    category=ExpenseCategory(m.category) if m.category in ExpenseCategory.__members__ else ExpenseCategory.OTHER,
                    amount=Money(m.amount),
                    date=m.date,
                    description=m.description,
                    payment_method=PaymentMethod(m.payment_method),
                    is_recurring=m.is_recurring,
                    created_at=m.created_at,
                )
                for m in rows
            ]


class PostgresGoalRepository:
    """Manages milestone growth targets and planning records."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, goal: Goal) -> Goal:
        with self.session_factory() as session:
            model = GoalModel(
                id=goal.id,
                business_id=goal.business_id,
                goal_type=goal.goal_type.value if isinstance(goal.goal_type, GoalType) else str(goal.goal_type),
                title=goal.title,
                target_value=goal.target_value,
                current_value=goal.current_value,
                start_date=goal.start_date,
                target_date=goal.target_date,
                status=goal.status.value if isinstance(goal.status, GoalStatus) else str(goal.status),
                plan_details=goal.plan_details,
                created_at=goal.created_at,
            )
            session.add(model)
            session.commit()
            return goal

    def list_by_business(self, business_id: uuid.UUID) -> List[Goal]:
        with self.session_factory() as session:
            stmt = select(GoalModel).where(GoalModel.business_id == business_id).order_by(GoalModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                Goal(
                    id=m.id,
                    business_id=m.business_id,
                    goal_type=GoalType(m.goal_type),
                    title=m.title,
                    target_value=Decimal(str(m.target_value)),
                    current_value=Decimal(str(m.current_value)),
                    start_date=m.start_date,
                    target_date=m.target_date,
                    status=GoalStatus(m.status),
                    plan_details=dict(m.plan_details or {}),
                    created_at=m.created_at,
                )
                for m in rows
            ]

    def get_by_id(self, business_id: uuid.UUID, goal_id: uuid.UUID) -> Optional[Goal]:
        with self.session_factory() as session:
            model = session.scalar(select(GoalModel).where(
                GoalModel.id == goal_id, GoalModel.business_id == business_id,
            ))
            if model is None:
                return None
            return Goal(
                id=model.id, business_id=model.business_id, goal_type=GoalType(model.goal_type),
                title=model.title, target_value=Decimal(str(model.target_value)),
                current_value=Decimal(str(model.current_value)), start_date=model.start_date,
                target_date=model.target_date, status=GoalStatus(model.status),
                plan_details=dict(model.plan_details or {}), created_at=model.created_at,
            )

    def update(self, goal: Goal) -> Optional[Goal]:
        with self.session_factory() as session:
            model = session.scalar(select(GoalModel).where(
                GoalModel.id == goal.id, GoalModel.business_id == goal.business_id,
            ).with_for_update())
            if model is None:
                return None
            model.goal_type = goal.goal_type.value
            model.title = goal.title
            model.target_value = goal.target_value
            model.start_date = goal.start_date
            model.target_date = goal.target_date
            model.status = goal.status.value
            model.plan_details = goal.plan_details
            session.commit()
            return Goal(
                id=model.id, business_id=model.business_id, goal_type=GoalType(model.goal_type),
                title=model.title, target_value=Decimal(str(model.target_value)),
                current_value=Decimal(str(model.current_value)), start_date=model.start_date,
                target_date=model.target_date, status=GoalStatus(model.status),
                plan_details=dict(model.plan_details or {}), created_at=model.created_at,
            )

    def update_progress(self, goal_id: uuid.UUID, current_value: Decimal, status: GoalStatus) -> None:
        with self.session_factory() as session:
            g = session.get(GoalModel, goal_id)
            if g:
                g.current_value = current_value
                g.status = status.value
                session.commit()


class PostgresDecisionEvaluationRepository:
    """Manages persisted decision graph evaluations and audit histories."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def save(self, evaluation: DecisionEvaluation) -> DecisionEvaluation:
        with self.session_factory() as session:
            version_number = 1
            if evaluation.parent_decision_id is not None:
                parent = session.scalar(select(DecisionEvaluationModel).where(
                    DecisionEvaluationModel.id == evaluation.parent_decision_id,
                    DecisionEvaluationModel.business_id == evaluation.business_id,
                ))
                if parent is None:
                    raise ValueError("Parent decision was not found in this workspace.")
                version_number = parent.version_number + 1
            model = DecisionEvaluationModel(
                id=evaluation.id,
                business_id=evaluation.business_id,
                version_number=version_number,
                parent_decision_id=evaluation.parent_decision_id,
                model_id=evaluation.model_id,
                model_version=evaluation.model_version,
                objective=evaluation.objective,
                inputs_snapshot=evaluation.inputs_snapshot,
                constraints_evaluated=evaluation.constraints_evaluated,
                calculations_performed=evaluation.calculations_performed,
                alternatives_evaluated=evaluation.alternatives_evaluated,
                outcome=evaluation.outcome.value if isinstance(evaluation.outcome, DecisionOutcome) else str(evaluation.outcome),
                explanation=evaluation.explanation,
                causal_graph=evaluation.causal_graph,
                evidence_items=evaluation.evidence_items,
                created_at=evaluation.created_at,
            )
            session.add(model)
            session.commit()
            return replace(evaluation, version_number=version_number)

    def get_by_id(self, evaluation_id: uuid.UUID) -> Optional[DecisionEvaluation]:
        with self.session_factory() as session:
            m = session.get(DecisionEvaluationModel, evaluation_id)
            if not m:
                return None
            return DecisionEvaluation(
                id=m.id,
                business_id=m.business_id,
                model_id=m.model_id,
                model_version=m.model_version,
                objective=m.objective,
                inputs_snapshot=dict(m.inputs_snapshot or {}),
                constraints_evaluated=list(m.constraints_evaluated or []),
                calculations_performed=dict(m.calculations_performed or {}),
                alternatives_evaluated=list(m.alternatives_evaluated or []),
                outcome=DecisionOutcome(m.outcome),
                explanation=m.explanation,
                created_at=m.created_at,
                version_number=m.version_number,
                parent_decision_id=m.parent_decision_id,
                causal_graph=dict(m.causal_graph or {}),
                evidence_items=list(m.evidence_items or []),
            )

    def list_by_business(self, business_id: uuid.UUID) -> List[DecisionEvaluation]:
        with self.session_factory() as session:
            stmt = select(DecisionEvaluationModel).where(DecisionEvaluationModel.business_id == business_id).order_by(DecisionEvaluationModel.created_at.desc())
            rows = session.execute(stmt).scalars().all()
            return [
                DecisionEvaluation(
                    id=m.id,
                    business_id=m.business_id,
                    model_id=m.model_id,
                    model_version=m.model_version,
                    objective=m.objective,
                    inputs_snapshot=dict(m.inputs_snapshot or {}),
                    constraints_evaluated=list(m.constraints_evaluated or []),
                    calculations_performed=dict(m.calculations_performed or {}),
                    alternatives_evaluated=list(m.alternatives_evaluated or []),
                    outcome=DecisionOutcome(m.outcome),
                    explanation=m.explanation,
                    created_at=m.created_at,
                    version_number=m.version_number,
                    parent_decision_id=m.parent_decision_id,
                    causal_graph=dict(m.causal_graph or {}),
                    evidence_items=list(m.evidence_items or []),
                )
                for m in rows
            ]

    def list_versions(self, business_id: uuid.UUID, decision_id: uuid.UUID) -> List[DecisionEvaluation]:
        with self.session_factory() as session:
            decision = session.scalar(select(DecisionEvaluationModel).where(
                DecisionEvaluationModel.id == decision_id,
                DecisionEvaluationModel.business_id == business_id,
            ))
            if decision is None:
                return []
            root_id = decision.parent_decision_id or decision.id
            # Follow parent pointers to the root, while tenant-scoping every lookup.
            while decision.parent_decision_id is not None:
                parent = session.scalar(select(DecisionEvaluationModel).where(
                    DecisionEvaluationModel.id == decision.parent_decision_id,
                    DecisionEvaluationModel.business_id == business_id,
                ))
                if parent is None:
                    break
                decision = parent
                root_id = decision.id
            candidates = session.scalars(select(DecisionEvaluationModel).where(
                DecisionEvaluationModel.business_id == business_id,
            ).order_by(DecisionEvaluationModel.version_number.asc())).all()
            ids = {root_id}
            rows = []
            changed = True
            while changed:
                changed = False
                for row in candidates:
                    if row.id in ids or row.parent_decision_id in ids:
                        if row.id not in ids:
                            ids.add(row.id)
                            changed = True
                        if row not in rows:
                            rows.append(row)
            return [DecisionEvaluation(
                id=m.id, business_id=m.business_id, model_id=m.model_id, model_version=m.model_version,
                objective=m.objective, inputs_snapshot=dict(m.inputs_snapshot or {}),
                constraints_evaluated=list(m.constraints_evaluated or []),
                calculations_performed=dict(m.calculations_performed or {}),
                alternatives_evaluated=list(m.alternatives_evaluated or []), outcome=DecisionOutcome(m.outcome),
                explanation=m.explanation, created_at=m.created_at, version_number=m.version_number,
                parent_decision_id=m.parent_decision_id, causal_graph=dict(m.causal_graph or {}),
                evidence_items=list(m.evidence_items or []),
            ) for m in rows]

class PostgresAgentSessionRepository:
    """Manages durable multi-turn agent sessions and conversation turns in PostgreSQL."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def get_or_create_session(
        self,
        session_id: uuid.UUID,
        business_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None,
    ) -> AgentSessionModel:
        if user_id is None:
            raise PermissionError("Authenticated user identity is required for agent sessions.")
        if session is not None:
            model = session.get(AgentSessionModel, session_id)
            if not model:
                model = AgentSessionModel(
                    id=session_id,
                    business_id=business_id,
                    user_id=user_id,
                    status="ACTIVE",
                )
                session.add(model)
                session.flush()
            elif (
                str(model.business_id) != str(business_id)
                or model.user_id is None
                or str(model.user_id) != str(user_id)
            ):
                raise PermissionError("Agent session does not belong to the authenticated user and business.")
            return model
        with self.session_factory() as s:
            res = self.get_or_create_session(session_id, business_id, user_id, session=s)
            s.commit()
            return res

    def get_session(
        self,
        session_id: uuid.UUID,
        session: Optional[Session] = None,
    ) -> Optional[AgentSessionModel]:
        if session is not None:
            return session.get(AgentSessionModel, session_id)
        with self.session_factory() as s:
            return self.get_session(session_id, session=s)

    def verify_session_ownership(
        self,
        session_id: uuid.UUID,
        business_id: uuid.UUID,
        user_id: Optional[Any] = None,
        must_exist: bool = True,
    ) -> bool:
        if not user_id:
            return False
        sess = self.get_session(session_id)
        if not sess:
            return not must_exist
        if str(sess.business_id) != str(business_id):
            return False
        if sess.user_id is None or str(sess.user_id) != str(user_id):
            return False
        return True

    def save_turn(
        self,
        session_id: uuid.UUID,
        business_id: uuid.UUID,
        turn_number: int,
        user_query: str,
        intent: str,
        extracted_parameters: Dict[str, Any],
        data_gaps: List[str],
        follow_up_questions: List[str],
        plan_steps: List[Dict[str, Any]],
        decision_outcome: Optional[str],
        synthesis: str,
        planning_attribution: Dict[str, Any],
        synthesis_attribution: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        session: Optional[Session] = None,
    ) -> AgentTurnModel:
        if user_id is None:
            raise PermissionError("Authenticated user identity is required to save agent turns.")
        if session is not None:
            self.get_or_create_session(session_id, business_id, user_id, session=session)
            turn = AgentTurnModel(
                id=uuid.uuid4(),
                session_id=session_id,
                turn_number=turn_number,
                user_query=user_query,
                intent=intent,
                extracted_parameters=extracted_parameters,
                data_gaps=data_gaps,
                follow_up_questions=follow_up_questions,
                plan_steps=plan_steps,
                decision_outcome=decision_outcome,
                synthesis=synthesis,
                planning_attribution=planning_attribution,
                synthesis_attribution=synthesis_attribution,
            )
            session.add(turn)
            sess = session.get(AgentSessionModel, session_id)
            if sess:
                sess.updated_at = datetime.now(timezone.utc)
            session.flush()
            return turn
        with self.session_factory() as s:
            res = self.save_turn(
                session_id=session_id,
                business_id=business_id,
                turn_number=turn_number,
                user_query=user_query,
                intent=intent,
                extracted_parameters=extracted_parameters,
                data_gaps=data_gaps,
                follow_up_questions=follow_up_questions,
                plan_steps=plan_steps,
                decision_outcome=decision_outcome,
                synthesis=synthesis,
                planning_attribution=planning_attribution,
                synthesis_attribution=synthesis_attribution,
                user_id=user_id,
                session=s,
            )
            s.commit()
            return res

    def get_turns(
        self,
        session_id: uuid.UUID,
        business_id: uuid.UUID,
        user_id: Any,
    ) -> List[Dict[str, Any]]:
        with self.session_factory() as session:
            sess = session.get(AgentSessionModel, session_id)
            if (
                user_id is None
                or not sess
                or str(sess.business_id) != str(business_id)
                or sess.user_id is None
                or str(sess.user_id) != str(user_id)
            ):
                return []
            stmt = (
                select(AgentTurnModel)
                .where(AgentTurnModel.session_id == session_id)
                .order_by(AgentTurnModel.turn_number.asc())
            )
            rows = session.execute(stmt).scalars().all()
            return [
                {
                    "turn_number": m.turn_number,
                    "query": m.user_query,
                    "intent": m.intent,
                    "extracted_parameters": m.extracted_parameters,
                    "data_gaps": m.data_gaps,
                    "follow_up_questions": m.follow_up_questions,
                    "plan_steps": m.plan_steps,
                    "decision_outcome": m.decision_outcome,
                    "synthesis": m.synthesis,
                    "planning_attribution": m.planning_attribution,
                    "synthesis_attribution": m.synthesis_attribution,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in rows
            ]

# ==============================================================================
# 11. General Ledger & Financial Periods Repositories
# ==============================================================================

class PostgresFinancialPeriodRepository:
    """Manages accounting periods and locks in PostgreSQL."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def create(self, period: FinancialPeriod, session: Optional[Session] = None) -> FinancialPeriod:
        def _op(s: Session) -> FinancialPeriod:
            model = FinancialPeriodModel(
                id=period.id,
                business_id=period.business_id,
                period_name=period.period_name,
                start_date=period.start_date,
                end_date=period.end_date,
                status=period.status.value,
                closed_at=period.closed_at,
                closed_by=period.closed_by,
                created_at=period.created_at,
            )
            s.add(model)
            s.flush()
            return period
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            with s.begin():
                return _op(s)

    def list_by_business(self, business_id: uuid.UUID, session: Optional[Session] = None) -> List[FinancialPeriod]:
        def _op(s: Session) -> List[FinancialPeriod]:
            stmt = select(FinancialPeriodModel).where(FinancialPeriodModel.business_id == business_id).order_by(FinancialPeriodModel.start_date.desc())
            models = s.execute(stmt).scalars().all()
            return [
                FinancialPeriod(
                    id=m.id,
                    business_id=m.business_id,
                    period_name=m.period_name,
                    start_date=m.start_date,
                    end_date=m.end_date,
                    status=FinancialPeriodStatus(m.status),
                    closed_at=m.closed_at,
                    closed_by=m.closed_by,
                    created_at=m.created_at,
                )
                for m in models
            ]
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def get_by_id(self, period_id: uuid.UUID, session: Optional[Session] = None) -> Optional[FinancialPeriod]:
        def _op(s: Session) -> Optional[FinancialPeriod]:
            m = s.get(FinancialPeriodModel, period_id)
            if not m:
                return None
            return FinancialPeriod(
                id=m.id,
                business_id=m.business_id,
                period_name=m.period_name,
                start_date=m.start_date,
                end_date=m.end_date,
                status=FinancialPeriodStatus(m.status),
                closed_at=m.closed_at,
                closed_by=m.closed_by,
                created_at=m.created_at,
            )
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def update_status(
        self,
        period_id: uuid.UUID,
        status: FinancialPeriodStatus,
        closed_by: Optional[uuid.UUID] = None,
        session: Optional[Session] = None,
    ) -> None:
        def _op(s: Session) -> None:
            m = s.get(FinancialPeriodModel, period_id)
            if m:
                m.status = status.value
                if status == FinancialPeriodStatus.HARD_CLOSED:
                    m.closed_at = datetime.now(timezone.utc)
                    m.closed_by = closed_by
                elif status == FinancialPeriodStatus.OPEN:
                    m.closed_at = None
                    m.closed_by = None
                s.flush()
        if session is not None:
            _op(session)
            return
        with self.session_factory() as s:
            with s.begin():
                _op(s)

    def is_date_locked(self, business_id: uuid.UUID, check_date: date, session: Optional[Session] = None) -> bool:
        def _op(s: Session) -> bool:
            stmt = select(FinancialPeriodModel).where(
                FinancialPeriodModel.business_id == business_id,
                FinancialPeriodModel.status == FinancialPeriodStatus.HARD_CLOSED.value,
                FinancialPeriodModel.start_date <= check_date,
                FinancialPeriodModel.end_date >= check_date,
            )
            return s.execute(stmt).scalars().first() is not None
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def is_date_open(self, business_id: uuid.UUID, check_date: date, session: Optional[Session] = None) -> bool:
        """Return false when a covering period is soft- or hard-closed."""
        def _op(s: Session) -> bool:
            stmt = select(FinancialPeriodModel).where(
                FinancialPeriodModel.business_id == business_id,
                FinancialPeriodModel.status != FinancialPeriodStatus.OPEN.value,
                FinancialPeriodModel.start_date <= check_date,
                FinancialPeriodModel.end_date >= check_date,
            )
            return s.execute(stmt).scalars().first() is None
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)


class PostgresJournalEntryRepository:
    """Manages double-entry journal entries and lines in PostgreSQL."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()

    def get_next_entry_number(self, business_id: uuid.UUID, session: Optional[Session] = None) -> str:
        def _op(s: Session) -> str:
            year = datetime.now(timezone.utc).year
            stmt = (
                select(func.count(JournalEntryModel.id))
                .where(JournalEntryModel.business_id == business_id)
            )
            count = s.execute(stmt).scalar() or 0
            return f"JE-{year}-{count + 1:04d}"
        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def create(self, entry: JournalEntry, session: Optional[Session] = None) -> JournalEntry:
        entry.validate_balance()

        def _op(s: Session) -> JournalEntry:
            model = JournalEntryModel(
                id=entry.id,
                business_id=entry.business_id,
                entry_number=entry.entry_number,
                entry_date=entry.entry_date,
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                description=entry.description,
                is_posted=entry.is_posted,
                created_at=entry.created_at,
            )
            s.add(model)
            s.flush()
            for line in entry.lines:
                line_model = JournalEntryLineModel(
                    id=line.id,
                    journal_entry_id=entry.id,
                    account_code=line.account_code,
                    account_name=line.account_name,
                    debit=line.debit.amount,
                    credit=line.credit.amount,
                    notes=line.notes,
                )
                s.add(line_model)
            s.flush()
            return entry

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            with s.begin():
                return _op(s)

    def list_by_business(
        self,
        business_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_code: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> List[JournalEntry]:
        def _op(s: Session) -> List[JournalEntry]:
            stmt = (
                select(JournalEntryModel)
                .where(JournalEntryModel.business_id == business_id)
            )
            if start_date:
                stmt = stmt.where(JournalEntryModel.entry_date >= start_date)
            if end_date:
                stmt = stmt.where(JournalEntryModel.entry_date <= end_date)
            stmt = stmt.order_by(JournalEntryModel.entry_date.desc(), JournalEntryModel.entry_number.desc())
            entry_models = s.execute(stmt).scalars().all()

            results: List[JournalEntry] = []
            for em in entry_models:
                lines_stmt = select(JournalEntryLineModel).where(JournalEntryLineModel.journal_entry_id == em.id)
                if account_code:
                    lines_stmt = lines_stmt.where(JournalEntryLineModel.account_code == account_code)
                line_models = s.execute(lines_stmt).scalars().all()
                if account_code and not line_models:
                    continue
                lines = [
                    JournalEntryLine(
                        id=lm.id,
                        journal_entry_id=lm.journal_entry_id,
                        account_code=lm.account_code,
                        account_name=lm.account_name,
                        debit=Money.from_decimal(lm.debit),
                        credit=Money.from_decimal(lm.credit),
                        notes=lm.notes,
                    )
                    for lm in line_models
                ]
                results.append(
                    JournalEntry(
                        id=em.id,
                        business_id=em.business_id,
                        entry_number=em.entry_number,
                        entry_date=em.entry_date,
                        reference_type=em.reference_type,
                        reference_id=em.reference_id,
                        description=em.description,
                        lines=lines,
                        is_posted=em.is_posted,
                        created_at=em.created_at,
                    )
                )
            return results

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

    def get_trial_balance(
        self,
        business_id: uuid.UUID,
        as_of_date: Optional[date] = None,
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        as_date = as_of_date or date.today()

        def _op(s: Session) -> Dict[str, Any]:
            stmt = (
                select(
                    JournalEntryLineModel.account_code,
                    JournalEntryLineModel.account_name,
                    func.sum(JournalEntryLineModel.debit).label("total_debit"),
                    func.sum(JournalEntryLineModel.credit).label("total_credit"),
                )
                .join(JournalEntryModel, JournalEntryLineModel.journal_entry_id == JournalEntryModel.id)
                .where(
                    JournalEntryModel.business_id == business_id,
                    JournalEntryModel.entry_date <= as_date,
                )
                .group_by(JournalEntryLineModel.account_code, JournalEntryLineModel.account_name)
                .order_by(JournalEntryLineModel.account_code.asc())
            )
            rows = s.execute(stmt).all()
            accounts = []
            grand_debit = Decimal("0.00")
            grand_credit = Decimal("0.00")

            for r in rows:
                d = Decimal(str(r.total_debit or 0))
                c = Decimal(str(r.total_credit or 0))
                grand_debit += d
                grand_credit += c
                accounts.append({
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "total_debit": float(d),
                    "total_debit_exact": f"{d:.2f}",
                    "total_credit": float(c),
                    "total_credit_exact": f"{c:.2f}",
                    "net_balance": float(d - c),
                    "net_balance_exact": f"{d - c:.2f}",
                })

            return {
                "business_id": str(business_id),
                "as_of_date": as_date.isoformat(),
                "accounts": accounts,
                "total_debits": float(grand_debit),
                "total_debits_exact": f"{grand_debit:.2f}",
                "total_credits": float(grand_credit),
                "total_credits_exact": f"{grand_credit:.2f}",
                "is_balanced": abs(grand_debit - grand_credit) < Decimal("0.01"),
            }

        if session is not None:
            return _op(session)
        with self.session_factory() as s:
            return _op(s)

"""
SQLAlchemy ORM Models for ArthLens Database Schema.

Authoritative Reference: ArthLens Build Handbook v1.0 (Part 9.1, 9.2).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import uuid

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from backend.arthlens.infra.database import Base

# ==============================================================================
# 1. Users, Roles, and Permissions (Handbook 9.1)
# ==============================================================================

class UserModel(Base):
    """User accounts and usage quota tracking."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False)
    password_hash = Column(Text, nullable=False)
    email_verified = Column(Boolean, nullable=False, server_default="false")
    google_sub = Column(String(255), nullable=True, unique=True, index=True)
    auth_provider = Column(String(32), nullable=False, server_default="local")
    two_factor_enabled = Column(Boolean, nullable=False, server_default="true")
    quota_counters = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        Index("ix_users_email", "email", unique=True),
    )

    roles = relationship("RoleModel", secondary="user_roles", back_populates="users")


class AuthOtpChallengeModel(Base):
    """Short-lived, single-use email OTP challenge; only a keyed hash is stored."""
    __tablename__ = "auth_otp_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    email = Column(String(320), nullable=False, index=True)
    purpose = Column(String(32), nullable=False)
    code_hash = Column(String(255), nullable=False)
    attempts = Column(Integer, nullable=False, server_default="0")
    max_attempts = Column(Integer, nullable=False, server_default="5")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("purpose IN ('REGISTER_VERIFY','LOGIN_2FA')", name="check_auth_otp_purpose"),
        CheckConstraint("attempts >= 0 AND max_attempts BETWEEN 1 AND 10", name="check_auth_otp_attempts"),
        Index("ix_auth_otp_challenges_active_email_purpose", "email", "purpose", "created_at"),
    )


class RoleModel(Base):
    """System and domain roles."""
    __tablename__ = "roles"

    id = Column(Text, primary_key=True)  # ENTREPRENEUR, STEWARD, ADMIN, etc.
    description = Column(Text, nullable=True)

    users = relationship("UserModel", secondary="user_roles", back_populates="roles")


class UserRoleModel(Base):
    """Association table linking users and assigned roles."""
    __tablename__ = "user_roles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(Text, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


# ==============================================================================
# Historical Compatibility Layer (Re-exported from historical_models)
# ==============================================================================
from backend.arthlens.infra.historical_models import (
    SourceModel,
    SourceVersionModel,
    SourceRecordModel,
    GeoUnitModel,
    FacilityModel,
    RoadNodeModel,
    RoadEdgeModel,
    QuantityModel,
    PolicyDocumentModel,
    PolicyRuleModel,
    PolicyEvaluationModel,
    BusinessProfileModel,
    ScenarioModel,
    SimulationRunModel,
    ScenarioComparisonModel,
    AgentRunModel,
    AgentRunStepModel,
    RunEventModel,
    JobModel,
    ApprovalModel,
    TaskModel,
)


# ==============================================================================
# 2. System Audit, Session Revocation, and Distributed Rate Limiting
# ==============================================================================

class AuditEventModel(Base):
    """Append-only audit trail for sensitive administrative operations."""
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor = Column(UUID(as_uuid=True), nullable=True)
    action = Column(Text, nullable=False)
    target = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, server_default="{}")
    prev_hash = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class RevokedTokenModel(Base):
    """Revoked JWT IDs (session invalidation upon logout)."""
    __tablename__ = "revoked_tokens"

    jti = Column(Text, primary_key=True)
    revoked_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)


class RateLimitModel(Base):
    """Concurrency-safe distributed rate limit buckets."""
    __tablename__ = "rate_limits"

    key = Column(Text, primary_key=True)
    count = Column(Integer, nullable=False, server_default="1")
    reset_at = Column(DateTime(timezone=True), nullable=False, index=True)


# ==============================================================================
# 7. Business Operating System & Decision Intelligence Models (Handbook v2.0)
# ==============================================================================

class BusinessModel(Base):
    """Business Operating System workspace source-of-truth."""
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    industry = Column(Text, nullable=False)
    address = Column(Text, nullable=False, server_default="")
    financial_year_start = Column(Text, nullable=False, server_default="04-01")
    currency = Column(Text, nullable=False, server_default="INR")
    preferences = Column(JSONB, nullable=False, server_default="{}")
    is_archived = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BusinessMembershipModel(Base):
    """RBAC membership linking users to business workspaces with role."""
    __tablename__ = "business_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("business_id", "user_id", name="uq_business_user_membership"),
        CheckConstraint("role IN ('OWNER', 'ADMIN', 'MANAGER', 'ACCOUNTANT', 'ANALYST', 'VIEWER')", name="check_membership_role"),
    )


class CustomerModel(Base):
    """Customer entity with credit limit and balance tracking."""
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=False, server_default="")
    email = Column(Text, nullable=False, server_default="")
    address = Column(Text, nullable=False, server_default="")
    credit_limit = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    opening_balance = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    current_balance = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    is_archived = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SupplierModel(Base):
    """Vendor/supplier entity with payables tracking."""
    __tablename__ = "suppliers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(Text, nullable=False)
    contact_person = Column(Text, nullable=False, server_default="")
    phone = Column(Text, nullable=False, server_default="")
    email = Column(Text, nullable=False, server_default="")
    address = Column(Text, nullable=False, server_default="")
    opening_balance = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    current_balance = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    is_archived = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ProductModel(Base):
    """Goods or services sold by the business."""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    unit = Column(Text, nullable=False, server_default="pcs")
    purchase_price = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    selling_price = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    min_stock_alert = Column(Numeric(14, 4), nullable=False, server_default="0.00")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_business_product_sku"),
    )


class InventoryBalanceModel(Base):
    """Current stock on hand and valuation per product."""
    __tablename__ = "inventory_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity_on_hand = Column(Numeric(14, 4), nullable=False, server_default="0.00")
    unit_cost = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    total_valuation = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    last_movement_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("business_id", "product_id", name="uq_business_inventory_product"),
    )


class InventoryMovementModel(Base):
    """Immutable audit trail for physical inventory changes."""
    __tablename__ = "inventory_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    movement_type = Column(Text, nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit_price = Column(Numeric(14, 2), nullable=False)
    cost_basis = Column(Numeric(14, 2), nullable=True)
    source_purchase_item_id = Column(UUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="SET NULL"), nullable=True)
    cost_reconciliation_status = Column(Text, nullable=False, server_default="VERIFIED")
    reconciled_at = Column(DateTime(timezone=True), nullable=True)
    reconciled_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reconciliation_note = Column(Text, nullable=True)
    reference_id = Column(Text, nullable=False, server_default="")
    reason = Column(Text, nullable=False, server_default="")
    balance_after = Column(Numeric(14, 4), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "cost_reconciliation_status IN ('VERIFIED', 'UNRECONCILED', 'ESTIMATED', 'CONFLICTING')",
            name="check_inventory_cost_reconciliation_status",
        ),
    )


class InventoryCostReconciliationModel(Base):
    """Immutable inventory-cost reconciliation run header."""
    __tablename__ = "inventory_cost_reconciliations"
    __table_args__ = (
        Index("ix_inventory_cost_reconciliations_business_created", "business_id", "created_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False)
    mode = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    summary = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InventoryCostReconciliationEventModel(Base):
    """Append-only evidence for a confirmed inventory movement cost resolution."""
    __tablename__ = "inventory_cost_reconciliation_events"
    __table_args__ = (
        Index("ix_inventory_cost_reconciliation_events_run_product", "reconciliation_id", "product_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reconciliation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("inventory_cost_reconciliations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_id = Column(UUID(as_uuid=True), ForeignKey("inventory_movements.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    classification = Column(Text, nullable=False)
    prior_cost_basis = Column(Numeric(14, 2), nullable=True)
    resolved_cost_basis = Column(Numeric(14, 2), nullable=True)
    source_evidence = Column(JSONB, nullable=False, server_default="{}")
    resolution_note = Column(Text, nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SalesInvoiceModel(Base):
    """Customer sales invoice header."""
    __tablename__ = "sales_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    invoice_number = Column(Text, nullable=False)
    invoice_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    tax_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    discount_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    total_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    paid_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    status = Column(Text, nullable=False, server_default="DRAFT")
    notes = Column(Text, nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("business_id", "invoice_number", name="uq_business_invoice_number"),
    )


class SalesInvoiceItemModel(Base):
    """Line item on customer sales invoice."""
    __tablename__ = "sales_invoice_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit = Column(Text, nullable=False, server_default="pcs")
    unit_price = Column(Numeric(14, 2), nullable=False)
    discount_percent = Column(Numeric(6, 2), nullable=False, server_default="0.00")
    total_price = Column(Numeric(14, 2), nullable=False)


class PurchaseModel(Base):
    """Supplier purchase/bill header."""
    __tablename__ = "purchases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    bill_number = Column(Text, nullable=False)
    purchase_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    tax_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    total_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    paid_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    return_credit_amount = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    status = Column(Text, nullable=False, server_default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("business_id", "bill_number", name="uq_business_purchase_bill_number"),
        CheckConstraint("return_credit_amount >= 0", name="check_purchase_return_credit_nonnegative"),
    )


class PurchaseItemModel(Base):
    """Line item on supplier purchase bill."""
    __tablename__ = "purchase_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_id = Column(UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    unit = Column(Text, nullable=False, server_default="pcs")
    unit_price = Column(Numeric(14, 2), nullable=False)
    total_price = Column(Numeric(14, 2), nullable=False)


class PurchaseReturnModel(Base):
    """Durable posted supplier return linked to its source purchase."""
    __tablename__ = "purchase_returns"
    __table_args__ = (
        UniqueConstraint("business_id", "idempotency_key", name="uq_purchase_returns_business_idempotency"),
        Index("ix_purchase_returns_business_purchase", "business_id", "purchase_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False)
    purchase_id = Column(UUID(as_uuid=True), ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False)
    return_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    refund_method = Column(Text, nullable=True)
    subtotal = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    idempotency_key = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PurchaseReturnItemModel(Base):
    """Immutable allocation from one purchase line to one supplier return."""
    __tablename__ = "purchase_return_items"
    __table_args__ = (
        UniqueConstraint("purchase_return_id", "purchase_item_id", name="uq_purchase_return_item_line"),
        CheckConstraint("quantity > 0", name="check_purchase_return_item_positive_quantity"),
        CheckConstraint("original_unit_price >= 0", name="check_purchase_return_item_nonnegative_price"),
        CheckConstraint("pretax_amount >= 0", name="check_purchase_return_item_nonnegative_pretax"),
        CheckConstraint("tax_amount >= 0", name="check_purchase_return_item_nonnegative_tax"),
        CheckConstraint("inventory_cost_removed >= 0", name="check_purchase_return_item_nonnegative_cost"),
        Index("ix_purchase_return_items_purchase_item", "purchase_item_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_return_id = Column(UUID(as_uuid=True), ForeignKey("purchase_returns.id", ondelete="RESTRICT"), nullable=False)
    purchase_item_id = Column(UUID(as_uuid=True), ForeignKey("purchase_items.id", ondelete="RESTRICT"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Numeric(14, 4), nullable=False)
    original_unit_price = Column(Numeric(14, 2), nullable=False)
    pretax_amount = Column(Numeric(14, 2), nullable=False)
    tax_amount = Column(Numeric(14, 2), nullable=False)
    inventory_cost_removed = Column(Numeric(14, 2), nullable=False)


class PaymentModel(Base):
    """Financial payment inflow or outflow."""
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("business_id", "idempotency_key", name="uq_payments_business_idempotency"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    party_type = Column(Text, nullable=False)  # CUSTOMER, SUPPLIER, OTHER
    party_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    reference_type = Column(Text, nullable=False)  # INVOICE, PURCHASE, ON_ACCOUNT, EXPENSE, INCOME
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    payment_type = Column(Text, nullable=False)  # RECEIVED, PAID
    payment_method = Column(Text, nullable=False)  # CASH, UPI, BANK_TRANSFER, CHEQUE, CREDIT
    amount = Column(Numeric(14, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    idempotency_key = Column(Text, nullable=True, index=True)
    notes = Column(Text, nullable=False, server_default="")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class IncomeRecordModel(Base):
    """Direct or miscellaneous revenue entry."""
    __tablename__ = "income_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    payment_method = Column(Text, nullable=False, server_default="CASH")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ExpenseRecordModel(Base):
    """Business operating expenditure."""
    __tablename__ = "expense_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(Text, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    date = Column(Date, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    payment_method = Column(Text, nullable=False, server_default="BANK_TRANSFER")
    is_recurring = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GoalModel(Base):
    """Targeted business objective and tracker."""
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    target_value = Column(Numeric(14, 2), nullable=False)
    current_value = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    status = Column(Text, nullable=False, server_default="ACTIVE")
    plan_details = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GoalMilestoneModel(Base):
    """Dated intermediate target for a business goal."""
    __tablename__ = "goal_milestones"
    __table_args__ = (UniqueConstraint("goal_id", "target_date", name="uq_goal_milestone_date"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    target_date = Column(Date, nullable=False)
    target_value = Column(Numeric(14, 2), nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ActionPlanModel(Base):
    """Tenant scoped action plan connected to a goal."""
    __tablename__ = "goal_action_plans"
    __table_args__ = (CheckConstraint("status IN ('ACTIVE','COMPLETED','CANCELLED')", name="check_goal_action_plan_status"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    status = Column(Text, nullable=False, server_default="ACTIVE")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ActionTaskModel(Base):
    """Assigned work item with expected financial impact and lifecycle state."""
    __tablename__ = "goal_action_tasks"
    __table_args__ = (
        CheckConstraint("status IN ('TODO','IN_PROGRESS','COMPLETED','BLOCKED')", name="check_goal_action_task_status"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="check_goal_action_task_priority"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("goal_action_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    assigned_member_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = Column(SmallInteger, nullable=False, server_default="3")
    status = Column(Text, nullable=False, server_default="TODO")
    due_date = Column(Date, nullable=True)
    expected_financial_impact = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class GoalProgressSnapshotModel(Base):
    """Immutable daily goal result with evidence and explanation payload."""
    __tablename__ = "goal_progress_snapshots"
    __table_args__ = (
        CheckConstraint("status IN ('ON_TRACK','AT_RISK','BEHIND','ACHIEVED')", name="check_goal_progress_snapshot_status"),
        Index("ix_goal_progress_snapshot_goal_date", "goal_id", "as_of_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    as_of_date = Column(Date, nullable=False)
    planned_value = Column(Numeric(14, 2), nullable=False)
    actual_value = Column(Numeric(14, 2), nullable=False)
    deviation_value = Column(Numeric(14, 2), nullable=False)
    status = Column(Text, nullable=False)
    explanation = Column(JSONB, nullable=False, server_default="{}")
    evidence_items = Column(JSONB, nullable=False, server_default="[]")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DecisionEvaluationModel(Base):
    """Persisted decision graph evaluation run."""
    __tablename__ = "decision_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False, server_default="1")
    parent_decision_id = Column(UUID(as_uuid=True), ForeignKey("decision_evaluations.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id = Column(Text, nullable=False, index=True)
    model_version = Column(Text, nullable=False)
    objective = Column(Text, nullable=False)
    inputs_snapshot = Column(JSONB, nullable=False, server_default="{}")
    constraints_evaluated = Column(JSONB, nullable=False, server_default="[]")
    calculations_performed = Column(JSONB, nullable=False, server_default="{}")
    alternatives_evaluated = Column(JSONB, nullable=False, server_default="[]")
    outcome = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False, server_default="")
    causal_graph = Column(JSONB, nullable=False, server_default="{}")
    evidence_items = Column(JSONB, nullable=False, server_default="[]")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BusinessScenarioModel(Base):
    """Tenant scoped scenario workspace with an immutable version history."""
    __tablename__ = "business_scenarios"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_business_scenarios_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=False, server_default="")
    current_version = Column(Integer, nullable=False, server_default="1")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class BusinessScenarioVersionModel(Base):
    """Immutable assumptions and derived case outputs for one scenario revision."""
    __tablename__ = "business_scenario_versions"
    __table_args__ = (UniqueConstraint("scenario_id", "version_number", name="uq_business_scenario_version"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("business_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    assumptions = Column(JSONB, nullable=False)
    baseline_snapshot_hash = Column(Text, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class BusinessSimulationRunModel(Base):
    """Reproducible Monte Carlo run linked to an immutable scenario version."""
    __tablename__ = "business_simulation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_version_id = Column(UUID(as_uuid=True), ForeignKey("business_scenario_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    random_seed = Column(Numeric(20, 0), nullable=False)
    iterations = Column(Integer, nullable=False)
    distribution_config = Column(JSONB, nullable=False)
    baseline_snapshot_hash = Column(Text, nullable=False)
    model_version = Column(Text, nullable=False)
    result = Column(JSONB, nullable=False)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("random_seed = TRUNC(random_seed) AND random_seed >= 0 AND random_seed <= 18446744073709551615", name="check_business_simulation_seed_range"),
        CheckConstraint("iterations >= 1 AND iterations <= 100000", name="check_business_simulation_iterations"),
    )


class AgentSessionModel(Base):
    """Durable multi-turn agent conversation session for a business workspace."""
    __tablename__ = "agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(Text, nullable=False, server_default="ACTIVE")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentTurnModel(Base):
    """Individual interaction turn within a persistent agent session."""
    __tablename__ = "agent_session_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    user_query = Column(Text, nullable=False)
    intent = Column(Text, nullable=False)
    extracted_parameters = Column(JSONB, nullable=False, server_default="{}")
    data_gaps = Column(JSONB, nullable=False, server_default="[]")
    follow_up_questions = Column(JSONB, nullable=False, server_default="[]")
    plan_steps = Column(JSONB, nullable=False, server_default="[]")
    decision_outcome = Column(Text, nullable=True)
    synthesis = Column(Text, nullable=False)
    planning_attribution = Column(JSONB, nullable=False, server_default="{}")
    synthesis_attribution = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AgentProposedActionModel(Base):
    """Agent action preview persisted until an authorized user confirms or rejects it."""
    __tablename__ = "agent_proposed_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING_CONFIRMATION','CONFIRMED','REJECTED')",
            name="check_agent_proposed_action_status",
        ),
        CheckConstraint(
            "action_type IN ('CREATE_GOAL','CREATE_TASK','GENERATE_REPORT')",
            name="check_agent_proposed_action_type",
        ),
        Index("ix_agent_proposed_actions_session_status", "session_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(Text, nullable=False, server_default="PENDING_CONFIRMATION")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    result = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

class FinancialPeriodModel(Base):
    """Financial accounting period with soft/hard closing controls."""
    __tablename__ = "financial_periods"
    __table_args__ = (
        UniqueConstraint("business_id", "period_name", name="uq_business_period_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    period_name = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Text, nullable=False, server_default="OPEN")  # OPEN, SOFT_CLOSED, HARD_CLOSED
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JournalEntryModel(Base):
    """Authoritative double-entry general ledger journal header."""
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("business_id", "entry_number", name="uq_journal_entry_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_number = Column(Text, nullable=False)
    entry_date = Column(Date, nullable=False)
    reference_type = Column(Text, nullable=False)
    reference_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    description = Column(Text, nullable=False)
    is_posted = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class JournalEntryLineModel(Base):
    """Individual debit or credit posting in a balanced journal entry."""
    __tablename__ = "journal_entry_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_code = Column(Text, nullable=False, index=True)
    account_name = Column(Text, nullable=False)
    debit = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    credit = Column(Numeric(14, 2), nullable=False, server_default="0.00")
    notes = Column(Text, nullable=False, server_default="")

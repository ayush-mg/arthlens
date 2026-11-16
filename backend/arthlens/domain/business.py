"""
ArthLens Business Operating System Domain Models & Value Objects.

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 1: Domain and Infrastructure (OOM, Invariant Enforcement, Value Objects).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid


# ==============================================================================
# 1. Enums
# ==============================================================================

class BusinessRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    ACCOUNTANT = "ACCOUNTANT"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class PurchaseStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    RETURNED = "RETURNED"
    CANCELLED = "CANCELLED"


class MovementType(str, Enum):
    OPENING = "OPENING"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"


class PartyType(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"
    OTHER = "OTHER"


class PaymentType(str, Enum):
    RECEIVED = "RECEIVED"
    PAID = "PAID"


class PaymentMethod(str, Enum):
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    CREDIT = "CREDIT"


class ExpenseCategory(str, Enum):
    OPERATING = "OPERATING"
    ADMINISTRATIVE = "ADMINISTRATIVE"
    MARKETING = "MARKETING"
    UTILITIES = "UTILITIES"
    SALARIES = "SALARIES"
    CAPITAL = "CAPITAL"
    INTEREST = "INTEREST"
    OTHER = "OTHER"


class GoalType(str, Enum):
    REVENUE = "REVENUE"
    PROFIT = "PROFIT"
    DEBT_REDUCTION = "DEBT_REDUCTION"
    CASH_RESERVE = "CASH_RESERVE"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    EXPANSION = "EXPANSION"


class GoalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ON_TRACK = "ON_TRACK"
    BEHIND = "BEHIND"
    ACHIEVED = "ACHIEVED"
    AT_RISK = "AT_RISK"
    MISSED = "MISSED"
    CANCELLED = "CANCELLED"


class DecisionOutcome(str, Enum):
    FEASIBLE = "FEASIBLE"
    CONDITIONALLY_FEASIBLE = "CONDITIONALLY_FEASIBLE"
    NOT_FEASIBLE = "NOT_FEASIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    CONTRADICTORY_INFORMATION = "CONTRADICTORY_INFORMATION"
    VERIFIED = "VERIFIED"
    INFORMATIONAL = "INFORMATIONAL"


# ==============================================================================
# 2. Value Objects
# ==============================================================================

@dataclass(frozen=True)
class Money:
    """
    Immutable decimal-safe monetary representation.
    Guarantees two decimal places and exact mathematical rounding.
    """
    amount: Decimal
    currency: str = "INR"

    def __post_init__(self):
        dec = Decimal(str(self.amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", dec)

    @classmethod
    def from_float(cls, val: float, currency: str = "INR") -> Money:
        return cls(Decimal(str(val)), currency)

    @classmethod
    def from_decimal(cls, val: Any, currency: str = "INR") -> Money:
        return cls(Decimal(str(val)), currency)

    @classmethod
    def zero(cls, currency: str = "INR") -> Money:
        return cls(Decimal("0.00"), currency)

    def __add__(self, other: Any) -> Money:
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
            return Money(self.amount + other.amount, self.currency)
        return Money(self.amount + Decimal(str(other)), self.currency)

    def __sub__(self, other: Any) -> Money:
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
            return Money(self.amount - other.amount, self.currency)
        return Money(self.amount - Decimal(str(other)), self.currency)

    def __mul__(self, factor: Any) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __truediv__(self, divisor: Any) -> Money:
        div = Decimal(str(divisor))
        if div == 0:
            raise ZeroDivisionError("Cannot divide Money by zero")
        return Money(self.amount / div, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __lt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount < other.amount
        return self.amount < Decimal(str(other))

    def __le__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount <= other.amount
        return self.amount <= Decimal(str(other))

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount > other.amount
        return self.amount > Decimal(str(other))

    def __ge__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount >= other.amount
        return self.amount >= Decimal(str(other))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        try:
            return self.amount == Decimal(str(other))
        except Exception:
            return False

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_zero(self) -> bool:
        return self.amount == 0

    def format_inr(self, symbol: str = "₹") -> str:
        """Indian numbering format: ₹12,34,567.89"""
        s = f"{abs(self.amount):.2f}"
        integer_part, decimal_part = s.split(".")
        if len(integer_part) > 3:
            last_three = integer_part[-3:]
            remaining = integer_part[:-3]
            groups = []
            while remaining:
                groups.append(remaining[-2:])
                remaining = remaining[:-2]
            groups.reverse()
            formatted = ",".join(groups) + "," + last_three
        else:
            formatted = integer_part
        sign = "-" if self.amount < 0 else ""
        return f"{sign}{symbol}{formatted}.{decimal_part}"

    def to_float(self) -> float:
        return float(self.amount)


@dataclass(frozen=True)
class Percentage:
    """Immutable percentage representation (e.g. 18.0 for 18%)."""
    value: Decimal

    def __post_init__(self):
        dec = Decimal(str(self.value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        object.__setattr__(self, "value", dec)

    @property
    def decimal_factor(self) -> Decimal:
        return self.value / Decimal("100")

    def apply_to(self, money: Money) -> Money:
        return Money(money.amount * self.decimal_factor, money.currency)


@dataclass(frozen=True)
class DateRange:
    """Immutable date span for financial reporting and planning."""
    start_date: date
    end_date: date

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})")

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def contains(self, d: date) -> bool:
        return self.start_date <= d <= self.end_date


# ==============================================================================
# 3. Domain Entities
# ==============================================================================

@dataclass
class Business:
    """Primary tenant boundary entity."""
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    industry: str
    address: str = ""
    financial_year_start: str = "04-01"
    currency: str = "INR"
    preferences: Dict[str, Any] = field(default_factory=dict)
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def archive(self) -> None:
        self.is_archived = True
        self.updated_at = datetime.now(timezone.utc)

    def unarchive(self) -> None:
        self.is_archived = False
        self.updated_at = datetime.now(timezone.utc)


@dataclass
class BusinessMembership:
    """Role-based user association with a specific business workspace."""
    id: uuid.UUID
    business_id: uuid.UUID
    user_id: uuid.UUID
    role: BusinessRole
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class Customer:
    """Customer entity with running credit ledger balance."""
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    credit_limit: Money = field(default_factory=Money.zero)
    opening_balance: Money = field(default_factory=Money.zero)
    current_balance: Money = field(default_factory=Money.zero)  # Positive = customer owes us
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_receivable(self, amount: Money) -> None:
        self.current_balance = self.current_balance + amount

    def apply_payment(self, amount: Money) -> None:
        self.current_balance = self.current_balance - amount


@dataclass
class Supplier:
    """Supplier entity with running payable ledger balance."""
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    opening_balance: Money = field(default_factory=Money.zero)
    current_balance: Money = field(default_factory=Money.zero)  # Positive = we owe supplier
    is_archived: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_payable(self, amount: Money) -> None:
        self.current_balance = self.current_balance + amount

    def apply_payment(self, amount: Money) -> None:
        self.current_balance = self.current_balance - amount


@dataclass
class Product:
    """Inventory item definition."""
    id: uuid.UUID
    business_id: uuid.UUID
    sku: str
    name: str
    category: str
    unit: str  # e.g., kg, pcs, box, litre
    purchase_price: Money
    selling_price: Money
    min_stock_alert: Decimal = Decimal("0.00")
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InventoryBalance:
    """Current on-hand stock and weighted average valuation."""
    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    quantity_on_hand: Decimal
    unit_cost: Money
    total_valuation: Money
    last_movement_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def apply_addition(self, qty: Decimal, cost_per_unit: Money) -> None:
        if qty <= 0:
            raise ValueError("Addition quantity must be strictly positive")
        new_qty = self.quantity_on_hand + qty
        new_val = self.total_valuation + (cost_per_unit * qty)
        self.quantity_on_hand = new_qty
        self.total_valuation = new_val
        self.unit_cost = new_val / new_qty if new_qty > 0 else cost_per_unit
        self.last_movement_at = datetime.now(timezone.utc)

    def apply_deduction(self, qty: Decimal, allow_negative: bool = False) -> None:
        if qty <= 0:
            raise ValueError("Deduction quantity must be strictly positive")
        if not allow_negative and self.quantity_on_hand < qty:
            raise ValueError(f"Insufficient stock on hand: requested {qty}, available {self.quantity_on_hand}")
        new_qty = self.quantity_on_hand - qty
        self.quantity_on_hand = new_qty
        self.total_valuation = self.unit_cost * new_qty if new_qty > 0 else Money.zero()
        self.last_movement_at = datetime.now(timezone.utc)


@dataclass
class InventoryMovement:
    """Immutable audit trail for physical inventory changes."""
    id: uuid.UUID
    business_id: uuid.UUID
    product_id: uuid.UUID
    movement_type: MovementType
    quantity: Decimal
    unit_price: Money
    reference_id: str
    reason: str
    balance_after: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Captured inventory valuation at movement time. ``unit_price`` remains the
    # transaction price (for example, the selling price on a sale).
    cost_basis: Optional[Money] = None
    source_purchase_item_id: Optional[uuid.UUID] = None
    cost_reconciliation_status: str = "VERIFIED"
    reconciled_at: Optional[datetime] = None
    reconciled_by_user_id: Optional[uuid.UUID] = None
    reconciliation_note: Optional[str] = None


@dataclass
class SalesInvoiceItem:
    """Line item in a customer sales invoice."""
    id: uuid.UUID
    invoice_id: uuid.UUID
    product_id: Optional[uuid.UUID]
    description: str
    quantity: Decimal
    unit: str
    unit_price: Money
    discount_percent: Decimal = Decimal("0.00")
    total_price: Money = field(default_factory=Money.zero)

    def calculate_total(self) -> Money:
        raw = self.unit_price * self.quantity
        discount = raw * (self.discount_percent / Decimal("100"))
        self.total_price = raw - discount
        return self.total_price


@dataclass
class SalesInvoice:
    """Customer billing invoice entity."""
    id: uuid.UUID
    business_id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    invoice_number: str
    invoice_date: date
    due_date: date
    subtotal: Money
    tax_amount: Money = field(default_factory=Money.zero)
    discount_amount: Money = field(default_factory=Money.zero)
    total_amount: Money = field(default_factory=Money.zero)
    paid_amount: Money = field(default_factory=Money.zero)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    notes: str = ""
    items: List[SalesInvoiceItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def outstanding_balance(self) -> Money:
        return self.total_amount - self.paid_amount

    def record_payment(self, amount: Money) -> None:
        if amount <= Money.zero():
            raise ValueError("Payment amount must be positive")
        self.paid_amount = self.paid_amount + amount
        if self.paid_amount >= self.total_amount:
            self.status = InvoiceStatus.PAID
        elif self.paid_amount > Money.zero():
            self.status = InvoiceStatus.PARTIALLY_PAID


@dataclass
class PurchaseItem:
    """Line item in a supplier purchase bill."""
    id: uuid.UUID
    purchase_id: uuid.UUID
    product_id: Optional[uuid.UUID]
    description: str
    quantity: Decimal
    unit: str
    unit_price: Money
    total_price: Money = field(default_factory=Money.zero)
    returned_quantity: Decimal = Decimal("0.0000")

    def calculate_total(self) -> Money:
        self.total_price = self.unit_price * self.quantity
        return self.total_price


@dataclass
class Purchase:
    """Supplier procurement purchase record."""
    id: uuid.UUID
    business_id: uuid.UUID
    supplier_id: Optional[uuid.UUID]
    bill_number: str
    purchase_date: date
    due_date: date
    subtotal: Money
    tax_amount: Money = field(default_factory=Money.zero)
    total_amount: Money = field(default_factory=Money.zero)
    paid_amount: Money = field(default_factory=Money.zero)
    status: PurchaseStatus = PurchaseStatus.PENDING
    items: List[PurchaseItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    return_credit_amount: Money = field(default_factory=Money.zero)

    @property
    def outstanding_balance(self) -> Money:
        remaining = self.total_amount - self.paid_amount - self.return_credit_amount
        return remaining if remaining > Money.zero() else Money.zero()

    def record_payment(self, amount: Money) -> None:
        if amount <= Money.zero():
            raise ValueError("Payment amount must be positive")
        self.paid_amount = self.paid_amount + amount
        if self.status in (PurchaseStatus.RETURNED, PurchaseStatus.PARTIALLY_RETURNED):
            return
        if self.paid_amount + self.return_credit_amount >= self.total_amount:
            self.status = PurchaseStatus.PAID
        elif self.paid_amount > Money.zero():
            self.status = PurchaseStatus.PARTIALLY_PAID


@dataclass
class PurchaseReturnItem:
    """A returned quantity tied to one immutable original purchase line."""
    id: uuid.UUID
    purchase_return_id: uuid.UUID
    purchase_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: Decimal
    original_unit_price: Money
    pretax_amount: Money
    tax_amount: Money
    inventory_cost_removed: Money


@dataclass
class PurchaseReturn:
    """Posted supplier return with its original-line allocations and settlement."""
    id: uuid.UUID
    business_id: uuid.UUID
    purchase_id: uuid.UUID
    supplier_id: uuid.UUID
    return_date: date
    reason: str
    refund_method: Optional[PaymentMethod]
    subtotal: Money
    tax_amount: Money
    total_amount: Money
    created_by: uuid.UUID
    idempotency_key: str
    items: List[PurchaseReturnItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Payment:
    """Inflow or outflow financial transaction record."""
    id: uuid.UUID
    business_id: uuid.UUID
    party_type: PartyType
    party_id: Optional[uuid.UUID]
    reference_type: str  # INVOICE, PURCHASE, ON_ACCOUNT, EXPENSE, INCOME
    reference_id: Optional[uuid.UUID]
    payment_type: PaymentType  # RECEIVED, PAID
    payment_method: PaymentMethod
    amount: Money
    payment_date: date
    idempotency_key: Optional[str] = None
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class IncomeRecord:
    """Direct or miscellaneous business revenue receipt."""
    id: uuid.UUID
    business_id: uuid.UUID
    category: str
    amount: Money
    date: date
    description: str = ""
    payment_method: PaymentMethod = PaymentMethod.CASH
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ExpenseRecord:
    """Business operating or administrative expenditure."""
    id: uuid.UUID
    business_id: uuid.UUID
    category: ExpenseCategory
    amount: Money
    date: date
    description: str = ""
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    is_recurring: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Goal:
    """Business performance and growth milestone target."""
    id: uuid.UUID
    business_id: uuid.UUID
    goal_type: GoalType
    title: str
    target_value: Decimal
    current_value: Decimal = Decimal("0.00")
    start_date: date = field(default_factory=date.today)
    target_date: date = field(default_factory=date.today)
    status: GoalStatus = GoalStatus.ACTIVE
    plan_details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def progress_percent(self) -> Decimal:
        if self.target_value <= 0:
            return Decimal("100.00") if self.current_value >= self.target_value else Decimal("0.00")
        pct = (self.current_value / self.target_value) * Decimal("100")
        return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class DecisionEvaluation:
    """Immutable audit record of a decision graph evaluation outcome."""
    id: uuid.UUID
    business_id: uuid.UUID
    model_id: str
    model_version: str
    objective: str
    inputs_snapshot: Dict[str, Any]
    constraints_evaluated: List[Dict[str, Any]]
    calculations_performed: Dict[str, Any]
    alternatives_evaluated: List[Dict[str, Any]]
    outcome: DecisionOutcome
    explanation: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version_number: int = 1
    parent_decision_id: Optional[uuid.UUID] = None
    causal_graph: Dict[str, Any] = field(default_factory=dict)
    evidence_items: List[Dict[str, Any]] = field(default_factory=list)

# ==============================================================================
# 11. Double-Entry General Ledger & Financial Periods (Part 10.1, UC-28, UC-29)
# ==============================================================================

class UnbalancedJournalEntryError(ValueError):
    """Raised when journal entry debits do not strictly equal credits."""
    pass


class StandardAccount(str, Enum):
    CASH = "1010"
    BANK = "1020"
    ACCOUNTS_RECEIVABLE = "1100"
    INPUT_TAX = "1150"
    SUPPLIER_DEBIT_NOTE_RECEIVABLE = "1160"
    INVENTORY = "1200"
    ACCOUNTS_PAYABLE = "2010"
    OUTPUT_TAX = "2020"
    OWNER_CAPITAL = "3010"
    SALES_REVENUE = "4010"
    SALES_RETURNS = "4020"
    INVENTORY_GAIN = "4080"
    OTHER_INCOME = "4090"
    COGS = "5010"
    OPERATING_EXPENSES = "6010"
    INVENTORY_LOSS = "6080"


ACCOUNT_NAMES = {
    StandardAccount.CASH.value: "Cash in Hand",
    StandardAccount.BANK.value: "Bank Current Account",
    StandardAccount.ACCOUNTS_RECEIVABLE.value: "Accounts Receivable (Khata)",
    StandardAccount.INPUT_TAX.value: "Input GST / Tax Receivable",
    StandardAccount.SUPPLIER_DEBIT_NOTE_RECEIVABLE.value: "Supplier Debit Note Receivable",
    StandardAccount.INVENTORY.value: "Inventory Asset",
    StandardAccount.ACCOUNTS_PAYABLE.value: "Accounts Payable (Khata)",
    StandardAccount.OUTPUT_TAX.value: "Output GST / Tax Payable",
    StandardAccount.OWNER_CAPITAL.value: "Owner Equity & Capital",
    StandardAccount.SALES_REVENUE.value: "Sales Revenue",
    StandardAccount.SALES_RETURNS.value: "Sales Returns & Allowances",
    StandardAccount.INVENTORY_GAIN.value: "Inventory Adjustment Gain",
    StandardAccount.OTHER_INCOME.value: "Other Operating Income",
    StandardAccount.COGS.value: "Cost of Goods Sold",
    StandardAccount.OPERATING_EXPENSES.value: "Operating Expenses",
    StandardAccount.INVENTORY_LOSS.value: "Inventory Shrinkage / Loss",
}


@dataclass
class JournalEntryLine:
    """Individual debit or credit posting in a balanced double-entry journal entry."""
    id: uuid.UUID
    journal_entry_id: uuid.UUID
    account_code: str
    account_name: str
    debit: Money = field(default_factory=Money.zero)
    credit: Money = field(default_factory=Money.zero)
    notes: str = ""

    def __post_init__(self):
        if self.debit < Money.zero() or self.credit < Money.zero():
            raise ValueError("Journal line debits and credits must be non-negative")
        if self.debit == Money.zero() and self.credit == Money.zero():
            raise ValueError("Journal line must contain a non-zero debit or credit")
        if self.debit > Money.zero() and self.credit > Money.zero():
            raise ValueError("Journal line cannot contain both debit and credit")


@dataclass
class JournalEntry:
    """Authoritative double-entry general ledger journal transaction."""
    id: uuid.UUID
    business_id: uuid.UUID
    entry_number: str
    entry_date: date
    reference_type: str
    description: str
    reference_id: Optional[uuid.UUID] = None
    lines: List[JournalEntryLine] = field(default_factory=list)
    is_posted: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.lines:
            self.validate_balance()

    @property
    def total_debits(self) -> Money:
        total = Money.zero()
        for line in self.lines:
            total = total + line.debit
        return total

    @property
    def total_credits(self) -> Money:
        total = Money.zero()
        for line in self.lines:
            total = total + line.credit
        return total

    def validate_balance(self) -> None:
        """Enforces that total debits strictly equal total credits (within 0.01 tolerance)."""
        diff = abs(self.total_debits.amount - self.total_credits.amount)
        if diff > Decimal("0.005"):
            raise UnbalancedJournalEntryError(
                f"Unbalanced journal entry {self.entry_number}: total debits ₹{self.total_debits.amount} "
                f"!= total credits ₹{self.total_credits.amount}"
            )


class FinancialPeriodStatus(str, Enum):
    OPEN = "OPEN"
    SOFT_CLOSED = "SOFT_CLOSED"
    HARD_CLOSED = "HARD_CLOSED"


@dataclass
class FinancialPeriod:
    """Accounting period with soft and hard closing controls."""
    id: uuid.UUID
    business_id: uuid.UUID
    period_name: str
    start_date: date
    end_date: date
    status: FinancialPeriodStatus = FinancialPeriodStatus.OPEN
    closed_at: Optional[datetime] = None
    closed_by: Optional[uuid.UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_date_locked(self, check_date: date) -> bool:
        """Checks if a given transaction date falls within a hard-closed period."""
        if self.status == FinancialPeriodStatus.HARD_CLOSED:
            return self.start_date <= check_date <= self.end_date
        return False

"""
FastAPI Router for Business Operating System (ArthLens Core).

Authoritative Specification: ArthLens Final Product Vision, Architecture & Implementation Handbook.
Phase 2: Business Operations REST APIs (Workspaces, Khata, Invoicing, Purchases, Inventory, Cash, Goals).
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated, Any, Dict, List, Literal, Optional
import uuid
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from backend.arthlens.agent.business_agent import AgentExecutionContext, BusinessAgent
from backend.arthlens.services.agent_action_service import (
    AgentActionNotFoundError,
    AgentActionService,
    AgentActionStateError,
    get_agent_action_service,
)
from backend.arthlens.domain.business import (
    BusinessRole,
    ExpenseCategory,
    GoalStatus,
    GoalType,
    InvoiceStatus,
    Money,
    MovementType,
    PaymentMethod,
    PurchaseStatus,
    StandardAccount,
)
from backend.arthlens.decision.engine import DecisionInputValidationError, DecisionIntelligenceEngine
from backend.arthlens.finance.intelligence import FinancialIntelligenceEngine
from backend.arthlens.reporting.business_reports import BusinessReportGenerator
from backend.arthlens.security.audit import get_audit_service
from backend.arthlens.security.rbac import AuthenticatedUser, get_current_user
from backend.arthlens.domain.business import FinancialPeriodStatus
from backend.arthlens.services.business_service import (
    BusinessNotFoundError,
    BusinessService,
    CreditLimitExceededError,
    FinancialPeriodClosedError,
    IdempotencyConflictError,
    InsufficientInventoryError,
    InvalidOperationError,
    UnauthorizedBusinessAccessError,
)
from backend.arthlens.services.inventory_cost_service import InventoryCostReconciliationError
from backend.arthlens.services.scenario_service import (
    ScenarioNotFoundError,
    ScenarioReplayMismatchError,
    ScenarioService,
    get_scenario_service,
)
from backend.arthlens.services.goal_planning_service import (
    GoalPlanningNotFoundError,
    GoalPlanningService,
    get_goal_planning_service,
)

router = APIRouter(prefix="/businesses", tags=["Business Operating System"])

_business_service: Optional[BusinessService] = None
_finance_engine: Optional[FinancialIntelligenceEngine] = None
_decision_engine: Optional[DecisionIntelligenceEngine] = None
_business_agent: Optional[BusinessAgent] = None
_report_generator: Optional[BusinessReportGenerator] = None


def get_business_service() -> BusinessService:
    global _business_service
    if _business_service is None:
        _business_service = BusinessService()
    return _business_service


def enforce_archived_workspace_read_only(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> None:
    """Reject writes to archived workspaces while leaving reads and unarchive available."""
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    raw_business_id = request.path_params.get("business_id")
    request_path = request.url.path.rstrip("/")
    if not raw_business_id or request_path.endswith(("/archive", "/khata/reconcile")) or (
        request.method == "DELETE" and request_path.endswith(f"/{raw_business_id}")
    ):
        return
    try:
        business = service.get_business(uuid.UUID(str(raw_business_id)), uuid.UUID(current_user.id))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if business.is_archived:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Archived workspaces are read-only.")


router.dependencies.append(Depends(enforce_archived_workspace_read_only))


def get_finance_engine() -> FinancialIntelligenceEngine:
    global _finance_engine
    if _finance_engine is None:
        _finance_engine = FinancialIntelligenceEngine()
    return _finance_engine


def get_decision_engine() -> DecisionIntelligenceEngine:
    global _decision_engine
    if _decision_engine is None:
        _decision_engine = DecisionIntelligenceEngine()
    return _decision_engine


def get_business_agent() -> BusinessAgent:
    global _business_agent
    if _business_agent is None:
        _business_agent = BusinessAgent()
    return _business_agent


def get_report_generator() -> BusinessReportGenerator:
    global _report_generator
    if _report_generator is None:
        _report_generator = BusinessReportGenerator()
    return _report_generator
    return _business_service


# ==============================================================================
# Pydantic Request / Response Schemas
# ==============================================================================

def _quantize_money_input(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Money must be supplied as a decimal amount")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Money must be a valid decimal amount") from exc
    if not amount.is_finite():
        raise ValueError("Money must be finite")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


ExactMoney = Annotated[Decimal, BeforeValidator(_quantize_money_input)]


def _money_exact(value: Money) -> str:
    return f"{value.amount:.2f}"

class CreateBusinessRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    industry: str = Field(..., min_length=1, max_length=100)
    address: str = ""
    financial_year_start: str = "04-01"
    currency: str = "INR"
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UpdateBusinessRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    financial_year_start: Optional[str] = None
    currency: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class ArchiveBusinessRequest(BaseModel):
    is_archived: bool = True


class AddMemberRequest(BaseModel):
    user_id: uuid.UUID
    role: BusinessRole = BusinessRole.MANAGER


class UpdateMemberRoleRequest(BaseModel):
    role: BusinessRole


class CreateCustomerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    phone: str = ""
    email: str = ""
    address: str = ""
    credit_limit: ExactMoney = Field(default=Decimal("0.00"), ge=0)
    opening_balance: ExactMoney = Decimal("0.00")


class UpdateCustomerRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    credit_limit: Optional[ExactMoney] = None


class UpdateSupplierRequest(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class UpdateProductRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    purchase_price: Optional[ExactMoney] = None
    selling_price: Optional[ExactMoney] = None
    min_stock_alert: Optional[float] = None
    is_active: Optional[bool] = None


class CreateSupplierRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    contact_person: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    opening_balance: ExactMoney = Decimal("0.00")


class CreateProductRequest(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=150)
    category: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(default="pcs", min_length=1, max_length=30)
    purchase_price: ExactMoney = Field(..., ge=0)
    selling_price: ExactMoney = Field(..., ge=0)
    min_stock_alert: float = 0.0
    initial_stock: float = 0.0


class AdjustStockRequest(BaseModel):
    product_id: uuid.UUID
    movement_type: MovementType
    quantity: float = Field(..., gt=0.0)
    unit_price: ExactMoney = Field(default=Decimal("0.00"), ge=0)
    reason: str = Field(..., min_length=1)
    reference_id: str = "MANUAL"


class InvoiceItemRequest(BaseModel):
    product_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0.0)
    unit: str = "pcs"
    unit_price: ExactMoney = Field(..., ge=0)
    discount_percent: float = 0.0


class CreateSalesInvoiceRequest(BaseModel):
    customer_id: Optional[uuid.UUID] = None
    invoice_number: str = Field(..., min_length=1)
    invoice_date: date
    due_date: date
    items: List[InvoiceItemRequest] = Field(..., min_length=1)
    tax_amount: ExactMoney = Decimal("0.00")
    discount_amount: ExactMoney = Decimal("0.00")
    notes: str = ""
    is_cash_sale: bool = False
    immediate_payment_method: Optional[PaymentMethod] = None


class InvoicePaymentRequest(BaseModel):
    amount: ExactMoney = Field(..., gt=0)
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.CASH
    notes: str = ""
    idempotency_key: Optional[str] = None


class CancelInvoiceRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class PurchaseItemRequest(BaseModel):
    product_id: Optional[uuid.UUID] = None
    description: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0.0)
    unit: str = "pcs"
    unit_price: ExactMoney = Field(..., ge=0)


class CreatePurchaseRequest(BaseModel):
    supplier_id: Optional[uuid.UUID] = None
    bill_number: str = Field(..., min_length=1)
    purchase_date: date
    due_date: date
    items: List[PurchaseItemRequest] = Field(..., min_length=1)
    tax_amount: ExactMoney = Decimal("0.00")
    is_cash_purchase: bool = False
    immediate_payment_method: Optional[PaymentMethod] = None


class PurchasePaymentRequest(BaseModel):
    amount: ExactMoney = Field(..., gt=0)
    payment_date: date
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    notes: str = ""
    idempotency_key: Optional[str] = None


class CreateIncomeRequest(BaseModel):
    category: str = Field(..., min_length=1)
    amount: ExactMoney = Field(..., gt=0)
    date: date
    description: str = ""
    payment_method: PaymentMethod = PaymentMethod.CASH


class CreateExpenseRequest(BaseModel):
    category: ExpenseCategory
    amount: ExactMoney = Field(..., gt=0)
    date: date
    description: str = ""
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    is_recurring: bool = False


class CreateGoalRequest(BaseModel):
    goal_type: GoalType
    title: str = Field(..., min_length=1)
    target_value: ExactMoney = Field(..., gt=0)
    target_date: date
    start_date: Optional[date] = None
    plan_details: Dict[str, Any] = Field(default_factory=dict)


class UpdateGoalRequest(BaseModel):
    goal_type: Optional[GoalType] = None
    title: Optional[str] = Field(default=None, min_length=1)
    target_value: Optional[ExactMoney] = Field(default=None, gt=0)
    target_date: Optional[date] = None
    start_date: Optional[date] = None
    plan_details: Optional[Dict[str, Any]] = None


class CreateGoalMilestoneRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    target_date: date
    target_value: ExactMoney = Field(..., ge=0)


class CreateActionPlanRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)


class CreateActionTaskRequest(BaseModel):
    plan_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)
    assigned_member_id: Optional[uuid.UUID] = None
    priority: int = Field(default=3, ge=1, le=5)
    status: Literal["TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"] = "TODO"
    due_date: Optional[date] = None
    expected_financial_impact: ExactMoney = Field(...)


class UpdateActionTaskRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)
    assigned_member_id: Optional[uuid.UUID] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    status: Optional[Literal["TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"]] = None
    due_date: Optional[date] = None
    expected_financial_impact: Optional[ExactMoney] = None


class EvaluateDecisionRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    constraints_override: Optional[Dict[str, Any]] = None
    save_evaluation: bool = True
    parent_decision_id: Optional[uuid.UUID] = None


class SimulateRiskRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    uncertainty_params: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    iterations: int = 1000
    random_seed: int = 42


class SensitivityRequest(BaseModel):
    model_id: str = Field(..., min_length=1)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    target_output_metric: str = Field(..., min_length=1)
    parameters_to_vary: Optional[List[str]] = None
    variation_pct: float = 0.20


class ScenarioCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    description: str = Field(default="", max_length=2000)
    assumptions: Dict[str, Any]


class ScenarioVersionRequest(BaseModel):
    assumptions: Dict[str, Any]


class ScenarioCompareRequest(BaseModel):
    version_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=5)


class ScenarioRunRequest(BaseModel):
    iterations: int = Field(default=1000, ge=1, le=100000)
    random_seed: Optional[int] = Field(default=None, ge=0, le=18446744073709551615)
    distributions: Optional[Dict[str, Dict[str, Any]]] = None


class AgentInvestigationRequest(BaseModel):
    query: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None


class AgentProposedActionRequest(BaseModel):
    action_type: Literal["CREATE_GOAL", "CREATE_TASK", "GENERATE_REPORT"]
    payload: Dict[str, Any]


# ==============================================================================
# Helper / Serialization
# ==============================================================================

def serialize_business(b) -> Dict[str, Any]:
    return {
        "id": str(b.id),
        "owner_id": str(b.owner_id),
        "name": b.name,
        "industry": b.industry,
        "address": b.address,
        "financial_year_start": b.financial_year_start,
        "currency": b.currency,
        "preferences": b.preferences,
        "is_archived": b.is_archived,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat(),
    }


def serialize_customer(c) -> Dict[str, Any]:
    return {
        "id": str(c.id),
        "business_id": str(c.business_id),
        "name": c.name,
        "phone": c.phone,
        "email": c.email,
        "address": c.address,
        "credit_limit": c.credit_limit.to_float(),
        "credit_limit_exact": _money_exact(c.credit_limit),
        "formatted_credit_limit": c.credit_limit.format_inr(),
        "opening_balance": c.opening_balance.to_float(),
        "opening_balance_exact": _money_exact(c.opening_balance),
        "current_balance": c.current_balance.to_float(),
        "current_balance_exact": _money_exact(c.current_balance),
        "formatted_current_balance": c.current_balance.format_inr(),
        "is_archived": c.is_archived,
        "created_at": c.created_at.isoformat(),
    }


def serialize_supplier(s) -> Dict[str, Any]:
    return {
        "id": str(s.id),
        "business_id": str(s.business_id),
        "name": s.name,
        "contact_person": s.contact_person,
        "phone": s.phone,
        "email": s.email,
        "address": s.address,
        "opening_balance": s.opening_balance.to_float(),
        "opening_balance_exact": _money_exact(s.opening_balance),
        "current_balance": s.current_balance.to_float(),
        "current_balance_exact": _money_exact(s.current_balance),
        "formatted_current_balance": s.current_balance.format_inr(),
        "is_archived": s.is_archived,
        "created_at": s.created_at.isoformat(),
    }


def serialize_product(p) -> Dict[str, Any]:
    return {
        "id": str(p.id),
        "business_id": str(p.business_id),
        "sku": p.sku,
        "name": p.name,
        "category": p.category,
        "unit": p.unit,
        "purchase_price": p.purchase_price.to_float(),
        "purchase_price_exact": _money_exact(p.purchase_price),
        "formatted_purchase_price": p.purchase_price.format_inr(),
        "selling_price": p.selling_price.to_float(),
        "selling_price_exact": _money_exact(p.selling_price),
        "formatted_selling_price": p.selling_price.format_inr(),
        "min_stock_alert": float(p.min_stock_alert),
        "is_active": p.is_active,
        "created_at": p.created_at.isoformat(),
    }


def serialize_invoice(inv) -> Dict[str, Any]:
    return {
        "id": str(inv.id),
        "business_id": str(inv.business_id),
        "customer_id": str(inv.customer_id) if inv.customer_id else None,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date.isoformat(),
        "due_date": inv.due_date.isoformat(),
        "subtotal": inv.subtotal.to_float(),
        "subtotal_amount": inv.subtotal.to_float(),
        "subtotal_exact": _money_exact(inv.subtotal),
        "tax_amount": inv.tax_amount.to_float(),
        "tax_amount_exact": _money_exact(inv.tax_amount),
        "discount_amount": inv.discount_amount.to_float(),
        "discount_amount_exact": _money_exact(inv.discount_amount),
        "total_amount": inv.total_amount.to_float(),
        "total_amount_exact": _money_exact(inv.total_amount),
        "paid_amount": inv.paid_amount.to_float(),
        "paid_amount_exact": _money_exact(inv.paid_amount),
        "outstanding_balance": inv.outstanding_balance.to_float(),
        "outstanding_amount": inv.outstanding_balance.to_float(),
        "outstanding_balance_exact": _money_exact(inv.outstanding_balance),
        "currency": inv.total_amount.currency,
        "formatted_total": inv.total_amount.format_inr(),
        "status": inv.status.value,
        "notes": inv.notes,
        "items": [
            {
                "id": str(it.id),
                "product_id": str(it.product_id) if it.product_id else None,
                "description": it.description,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": it.unit_price.to_float(),
                "unit_price_exact": _money_exact(it.unit_price),
                "discount_percent": float(it.discount_percent),
                "total_price": it.total_price.to_float(),
                "total_price_exact": _money_exact(it.total_price),
            }
            for it in inv.items
        ],
        "created_at": inv.created_at.isoformat(),
    }


def serialize_purchase(p) -> Dict[str, Any]:
    return {
        "id": str(p.id),
        "business_id": str(p.business_id),
        "supplier_id": str(p.supplier_id) if p.supplier_id else None,
        "bill_number": p.bill_number,
        "purchase_order_number": p.bill_number,
        "purchase_date": p.purchase_date.isoformat(),
        "due_date": p.due_date.isoformat(),
        "subtotal": p.subtotal.to_float(),
        "subtotal_amount": p.subtotal.to_float(),
        "subtotal_exact": _money_exact(p.subtotal),
        "tax_amount": p.tax_amount.to_float(),
        "tax_amount_exact": _money_exact(p.tax_amount),
        "total_amount": p.total_amount.to_float(),
        "total_amount_exact": _money_exact(p.total_amount),
        "paid_amount": p.paid_amount.to_float(),
        "paid_amount_exact": _money_exact(p.paid_amount),
        "outstanding_balance": p.outstanding_balance.to_float(),
        "outstanding_amount": p.outstanding_balance.to_float(),
        "outstanding_balance_exact": _money_exact(p.outstanding_balance),
        "return_credit_amount": p.return_credit_amount.to_float(),
        "return_credit_amount_exact": _money_exact(p.return_credit_amount),
        "currency": p.total_amount.currency,
        "formatted_total": p.total_amount.format_inr(),
        "status": p.status.value,
        "items": [
            {
                "id": str(it.id),
                "product_id": str(it.product_id) if it.product_id else None,
                "description": it.description,
                "item_description": it.description,
                "quantity": float(it.quantity),
                "unit": it.unit,
                "unit_price": it.unit_price.to_float(),
                "unit_price_exact": _money_exact(it.unit_price),
                "total_price": it.total_price.to_float(),
                "total_amount": it.total_price.to_float(),
                "total_price_exact": _money_exact(it.total_price),
                "returned_quantity": str(it.returned_quantity),
                "remaining_returnable_quantity": str(max(Decimal("0"), it.quantity - it.returned_quantity)),
            }
            for it in p.items
        ],
        "created_at": p.created_at.isoformat(),
    }


def serialize_goal(g) -> Dict[str, Any]:
    return {
        "id": str(g.id),
        "business_id": str(g.business_id),
        "goal_type": g.goal_type.value,
        "title": g.title,
        "target_value": float(g.target_value),
        "target_value_exact": f"{g.target_value:.2f}",
        "target_amount": f"{g.target_value:.2f}",
        "target_amount_exact": f"{g.target_value:.2f}",
        "current_value": float(g.current_value),
        "current_value_exact": f"{g.current_value:.2f}",
        "current_amount": f"{g.current_value:.2f}",
        "current_amount_exact": f"{g.current_value:.2f}",
        "progress_percent": float(g.progress_percent),
        "progress_pct": float(g.progress_percent),
        "start_date": g.start_date.isoformat(),
        "target_date": g.target_date.isoformat(),
        "status": g.status.value,
        "plan_details": g.plan_details,
        "created_at": g.created_at.isoformat(),
    }


# ==============================================================================
# 1. Workspaces Endpoints
# ==============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
def create_business(
    body: CreateBusinessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    biz = service.create_business(
        owner_id=uuid.UUID(current_user.id),
        name=body.name,
        industry=body.industry,
        address=body.address,
        financial_year_start=body.financial_year_start,
        currency=body.currency,
        preferences=body.preferences,
    )
    return serialize_business(biz)


@router.get("")
def list_businesses(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    businesses = service.list_user_businesses(uuid.UUID(current_user.id))
    return [serialize_business(b) for b in businesses]


@router.get("/portfolio")
def get_business_portfolio(
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    user_id = uuid.UUID(current_user.id)
    today = date.today()
    period_start = today - timedelta(days=29)
    portfolio_rows: list[dict[str, Any]] = []
    revenue_total = Decimal("0.00")
    profit_total = Decimal("0.00")
    cash_total = Decimal("0.00")
    alert_total = 0
    for business in service.list_user_businesses(user_id):
        if business.is_archived:
            continue
        membership = service.verify_access(business.id, user_id)
        pnl = engine.calculate_pnl(business.id, period_start, today)
        working_capital = engine.calculate_working_capital(business.id, today)
        health = engine.compute_health_score(business.id, today)
        low_stock = service.list_inventory_balances(business.id, user_id, low_stock_only=True)
        alerts = len(low_stock)
        revenue_total += pnl.total_revenue.amount
        profit_total += pnl.net_profit.amount
        cash_total += working_capital.cash_and_bank.amount
        alert_total += alerts
        portfolio_rows.append({
            "id": str(business.id), "name": business.name, "industry": business.industry,
            "role": membership.role.value, "is_archived": business.is_archived,
            "revenue_30d_exact": f"{pnl.total_revenue.amount:.2f}",
            "net_profit_30d_exact": f"{pnl.net_profit.amount:.2f}",
            "cash_position_exact": f"{working_capital.cash_and_bank.amount:.2f}",
            "health_score": health.overall_score,
            "active_alerts": alerts,
            "data_quality_warnings": pnl.data_quality_warnings,
        })
    return {
        "as_of_date": today.isoformat(), "period_start": period_start.isoformat(),
        "business_count": len(portfolio_rows),
        "revenue_30d_exact": f"{revenue_total:.2f}",
        "net_profit_30d_exact": f"{profit_total:.2f}",
        "cash_position_exact": f"{cash_total:.2f}",
        "active_alerts": alert_total, "workspaces": portfolio_rows,
    }


@router.get("/{business_id}")
def get_business(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        biz = service.get_business(business_id, uuid.UUID(current_user.id))
        return serialize_business(biz)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except BusinessNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{business_id}")
def update_business(
    business_id: uuid.UUID,
    body: UpdateBusinessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        biz = service.update_business(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            industry=body.industry,
            address=body.address,
            financial_year_start=body.financial_year_start,
            currency=body.currency,
            preferences=body.preferences,
        )
        return serialize_business(biz)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/archive")
def archive_business(
    business_id: uuid.UUID,
    body: ArchiveBusinessRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        service.set_business_archived(business_id, uuid.UUID(current_user.id), body.is_archived)
        return {"status": "ok", "business_id": str(business_id), "is_archived": body.is_archived}
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{business_id}")
def delete_business(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        service.delete_business(business_id, uuid.UUID(current_user.id))
        return {"status": "ok", "business_id": str(business_id), "deleted": True}
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except BusinessNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{business_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    business_id: uuid.UUID,
    body: AddMemberRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        m = service.add_member(business_id, uuid.UUID(current_user.id), body.user_id, body.role)
        return {
            "id": str(m.id),
            "business_id": str(m.business_id),
            "user_id": str(m.user_id),
            "role": m.role.value,
            "is_active": m.is_active,
        }
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{business_id}/members")
def list_members(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        members = service.list_members(business_id, uuid.UUID(current_user.id))
        return [
            {
                "id": str(m.id),
                "business_id": str(m.business_id),
                "user_id": str(m.user_id),
                "role": m.role.value,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat(),
            }
            for m in members
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.patch("/{business_id}/members/{target_user_id}")
def update_member_role(
    business_id: uuid.UUID,
    target_user_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        member = service.update_member_role(
            business_id,
            uuid.UUID(current_user.id),
            target_user_id,
            body.role,
        )
        return {
            "id": str(member.id),
            "business_id": str(member.business_id),
            "user_id": str(member.user_id),
            "role": member.role.value,
            "is_active": member.is_active,
        }
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{business_id}/members/{target_user_id}")
def remove_member(
    business_id: uuid.UUID,
    target_user_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, str]:
    try:
        service.remove_member(business_id, uuid.UUID(current_user.id), target_user_id)
        return {"status": "ok", "removed_user_id": str(target_user_id)}
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{business_id}/activity")
def list_business_activity(
    business_id: uuid.UUID,
    limit: int = 50,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        audit = get_audit_service()
        events = audit.list_events(limit=limit, target_prefix=f"business:{business_id}")
        if not events:
            events = audit.list_events(limit=limit)
        return events
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==============================================================================
# 2. Customers & Suppliers (Khata)
# ==============================================================================

@router.post("/{business_id}/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    business_id: uuid.UUID,
    body: CreateCustomerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        cust = service.create_customer(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            phone=body.phone,
            email=body.email,
            address=body.address,
            credit_limit=body.credit_limit,
            opening_balance=body.opening_balance,
        )
        return serialize_customer(cust)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/customers")
def list_customers(
    business_id: uuid.UUID,
    include_archived: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        customers = service.list_customers(business_id, uuid.UUID(current_user.id), include_archived=include_archived)
        return [serialize_customer(c) for c in customers]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/customers/{customer_id}")
def get_customer(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        cust = service.get_customer(business_id, customer_id, uuid.UUID(current_user.id))
        return serialize_customer(cust)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{business_id}/customers/{customer_id}")
def update_customer(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    body: UpdateCustomerRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        cust = service.update_customer(
            business_id=business_id,
            customer_id=customer_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            phone=body.phone,
            email=body.email,
            address=body.address,
            credit_limit=body.credit_limit,
        )
        return serialize_customer(cust)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/customers/{customer_id}/ledger")
def get_customer_ledger(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.get_customer_ledger(business_id, customer_id, uuid.UUID(current_user.id))
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{business_id}/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(
    business_id: uuid.UUID,
    body: CreateSupplierRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        sup = service.create_supplier(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            contact_person=body.contact_person,
            phone=body.phone,
            email=body.email,
            address=body.address,
            opening_balance=body.opening_balance,
        )
        return serialize_supplier(sup)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/suppliers")
def list_suppliers(
    business_id: uuid.UUID,
    include_archived: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        suppliers = service.list_suppliers(business_id, uuid.UUID(current_user.id), include_archived=include_archived)
        return [serialize_supplier(s) for s in suppliers]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/suppliers/{supplier_id}")
def get_supplier(
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        sup = service.get_supplier(business_id, supplier_id, uuid.UUID(current_user.id))
        return serialize_supplier(sup)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{business_id}/suppliers/{supplier_id}/ledger")
def get_supplier_ledger(
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.get_supplier_ledger(business_id, supplier_id, uuid.UUID(current_user.id))
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{business_id}/suppliers/{supplier_id}")
def update_supplier(
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    body: UpdateSupplierRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        sup = service.update_supplier(
            business_id=business_id,
            supplier_id=supplier_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            contact_person=body.contact_person,
            phone=body.phone,
            email=body.email,
            address=body.address,
        )
        return serialize_supplier(sup)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/khata/reconcile")
def reconcile_party_ledgers(
    business_id: uuid.UUID,
    as_of_date: Optional[date] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    """Compare customer/supplier control totals with the posted AR/AP general-ledger balances."""
    user_id = uuid.UUID(current_user.id)
    reference_date = as_of_date or date.today()
    try:
        business = service.get_business(business_id, user_id)
        customers = service.list_customers(business_id, user_id, include_archived=True)
        suppliers = service.list_suppliers(business_id, user_id, include_archived=True)
        trial_balance = service.get_trial_balance(business_id, user_id, as_of_date=reference_date)
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    account_rows = {row["account_code"]: row for row in trial_balance.get("accounts", [])}
    receivables_subledger = sum((customer.current_balance.amount for customer in customers), Decimal("0.00"))
    payables_subledger = sum((supplier.current_balance.amount for supplier in suppliers), Decimal("0.00"))
    ar_row = account_rows.get(StandardAccount.ACCOUNTS_RECEIVABLE.value, {})
    ap_row = account_rows.get(StandardAccount.ACCOUNTS_PAYABLE.value, {})
    receivables_gl = Decimal(str(ar_row.get("net_balance_exact", "0.00")))
    payables_gl = -Decimal(str(ap_row.get("net_balance_exact", "0.00")))

    def check(subledger: Decimal, general_ledger: Decimal) -> Dict[str, Any]:
        variance = general_ledger - subledger
        return {
            "subledger_exact": f"{subledger:.2f}",
            "general_ledger_exact": f"{general_ledger:.2f}",
            "variance_exact": f"{variance:.2f}",
            "is_reconciled": abs(variance) <= Decimal("0.01"),
        }

    receivables = check(receivables_subledger, receivables_gl)
    payables = check(payables_subledger, payables_gl)
    is_reconciled = receivables["is_reconciled"] and payables["is_reconciled"]
    return {
        "business_id": str(business_id),
        "as_of_date": reference_date.isoformat(),
        "currency": business.currency,
        "status": "RECONCILED" if is_reconciled else "VARIANCE_FOUND",
        "is_reconciled": is_reconciled,
        "customer_count": len(customers),
        "supplier_count": len(suppliers),
        "accounts_receivable": receivables,
        "accounts_payable": payables,
    }


# ==============================================================================
# 3. Product Catalog & Inventory
# ==============================================================================

@router.post("/{business_id}/products", status_code=status.HTTP_201_CREATED)
def create_product(
    business_id: uuid.UUID,
    body: CreateProductRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        prod = service.create_product(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            sku=body.sku,
            name=body.name,
            category=body.category,
            unit=body.unit,
            purchase_price=body.purchase_price,
            selling_price=body.selling_price,
            min_stock_alert=body.min_stock_alert,
            initial_stock=body.initial_stock,
        )
        return serialize_product(prod)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/products")
def list_products(
    business_id: uuid.UUID,
    active_only: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        prods = service.list_products(business_id, uuid.UUID(current_user.id), active_only=active_only)
        return [serialize_product(p) for p in prods]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/products/{product_id}")
def get_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        prod = service.get_product(business_id, product_id, uuid.UUID(current_user.id))
        return serialize_product(prod)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{business_id}/products/{product_id}")
def update_product(
    business_id: uuid.UUID,
    product_id: uuid.UUID,
    body: UpdateProductRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        prod = service.update_product(
            business_id=business_id,
            product_id=product_id,
            user_id=uuid.UUID(current_user.id),
            name=body.name,
            category=body.category,
            unit=body.unit,
            purchase_price=body.purchase_price,
            selling_price=body.selling_price,
            min_stock_alert=body.min_stock_alert,
            is_active=body.is_active,
        )
        return serialize_product(prod)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidOperationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{business_id}/inventory/adjust")
def adjust_inventory(
    business_id: uuid.UUID,
    body: AdjustStockRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        bal = service.adjust_inventory(
            business_id=business_id,
            product_id=body.product_id,
            user_id=uuid.UUID(current_user.id),
            movement_type=body.movement_type,
            quantity=body.quantity,
            unit_price=body.unit_price,
            reason=body.reason,
            reference_id=body.reference_id,
        )
        return {
            "status": "ok",
            "product_id": str(bal.product_id),
            "quantity_on_hand": float(bal.quantity_on_hand),
            "unit_cost": bal.unit_cost.to_float(),
            "unit_cost_exact": _money_exact(bal.unit_cost),
            "total_valuation": bal.total_valuation.to_float(),
            "total_valuation_exact": _money_exact(bal.total_valuation),
        }
    except InsufficientInventoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/inventory/balances")
def list_inventory_balances(
    business_id: uuid.UUID,
    low_stock_only: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        return service.list_inventory_balances(business_id, uuid.UUID(current_user.id), low_stock_only=low_stock_only)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/inventory/movements")
def list_inventory_movements(
    business_id: uuid.UUID,
    product_id: Optional[uuid.UUID] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        movs = service.list_inventory_movements(business_id, uuid.UUID(current_user.id), product_id=product_id)
        return [
            {
                "id": str(m.id),
                "product_id": str(m.product_id),
                "movement_type": m.movement_type.value,
                "quantity": float(m.quantity),
                "unit_price": m.unit_price.to_float(),
                "unit_price_exact": _money_exact(m.unit_price),
                "cost_basis": m.cost_basis.to_float() if m.cost_basis else None,
                "cost_basis_exact": _money_exact(m.cost_basis) if m.cost_basis is not None else None,
                "cost_reconciliation_status": m.cost_reconciliation_status,
                "reconciled_at": m.reconciled_at.isoformat() if m.reconciled_at else None,
                "reconciled_by_user_id": str(m.reconciled_by_user_id) if m.reconciled_by_user_id else None,
                "reconciliation_note": m.reconciliation_note,
                "reference_id": m.reference_id,
                "source_purchase_item_id": str(m.source_purchase_item_id) if m.source_purchase_item_id else None,
                "reason": m.reason,
                "balance_after": float(m.balance_after),
                "currency": m.unit_price.currency,
                "created_at": m.created_at.isoformat(),
            }
            for m in movs
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/inventory/unreconciled-costs")
def list_unreconciled_inventory_costs(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.list_unreconciled_inventory_movements(business_id, uuid.UUID(current_user.id))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{business_id}/inventory/reconcile-costs")
def reconcile_inventory_costs(
    business_id: uuid.UUID,
    body: InventoryCostReconciliationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.reconcile_historical_inventory_costs(
            business_id=business_id,
            actor_user_id=uuid.UUID(current_user.id),
            mode=body.mode,
            overrides=[item.model_dump() for item in body.overrides],
        )
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InventoryCostReconciliationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{business_id}/inventory/cost-reconciliation-history")
def list_inventory_cost_reconciliation_history(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        return service.list_inventory_cost_reconciliation_history(business_id, uuid.UUID(current_user.id))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


# ==============================================================================
# 4. Sales & Invoicing
# ==============================================================================

@router.post("/{business_id}/invoices", status_code=status.HTTP_201_CREATED)
def create_sales_invoice(
    business_id: uuid.UUID,
    body: CreateSalesInvoiceRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inv = service.create_sales_invoice(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            customer_id=body.customer_id,
            invoice_number=body.invoice_number,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            items=[it.model_dump() for it in body.items],
            tax_amount=body.tax_amount,
            discount_amount=body.discount_amount,
            notes=body.notes,
            is_cash_sale=body.is_cash_sale,
            immediate_payment_method=body.immediate_payment_method,
        )
        return serialize_invoice(inv)
    except CreditLimitExceededError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except InsufficientInventoryError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/invoices")
def list_sales_invoices(
    business_id: uuid.UUID,
    customer_id: Optional[uuid.UUID] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        invoices = service.list_sales_invoices(business_id, uuid.UUID(current_user.id), customer_id=customer_id)
        return [serialize_invoice(i) for i in invoices]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/invoices/{invoice_id}")
def get_sales_invoice(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inv = service.get_sales_invoice(business_id, invoice_id, uuid.UUID(current_user.id))
        return serialize_invoice(inv)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{business_id}/invoices/{invoice_id}/payments")
def record_invoice_payment(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    body: InvoicePaymentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inv = service.record_invoice_payment(
            business_id=business_id,
            invoice_id=invoice_id,
            user_id=uuid.UUID(current_user.id),
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
        )
        return serialize_invoice(inv)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (InvalidOperationError, ValueError, FinancialPeriodClosedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/invoices/{invoice_id}/cancel")
def cancel_sales_invoice(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    body: CancelInvoiceRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inv = service.cancel_sales_invoice(
            business_id=business_id,
            invoice_id=invoice_id,
            user_id=uuid.UUID(current_user.id),
            reason=body.reason,
        )
        return serialize_invoice(inv)
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{business_id}/invoices/{invoice_id}")
def update_sales_invoice(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    body: CreateSalesInvoiceRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inv = service.update_sales_invoice(
            business_id=business_id,
            invoice_id=invoice_id,
            user_id=uuid.UUID(current_user.id),
            customer_id=body.customer_id,
            invoice_date=body.invoice_date,
            due_date=body.due_date,
            items=[it.model_dump() for it in body.items],
            tax_amount=body.tax_amount,
            notes=body.notes,
        )
        return serialize_invoice(inv)
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{business_id}/invoices/{invoice_id}", status_code=status.HTTP_200_OK)
def delete_sales_invoice(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        service.delete_sales_invoice(
            business_id=business_id,
            invoice_id=invoice_id,
            user_id=uuid.UUID(current_user.id),
        )
        return {"success": True, "deleted_id": str(invoice_id)}
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==============================================================================
# 5. Purchases & Payables
# ==============================================================================

@router.post("/{business_id}/purchases", status_code=status.HTTP_201_CREATED)
def create_purchase(
    business_id: uuid.UUID,
    body: CreatePurchaseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        purch = service.create_purchase(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            supplier_id=body.supplier_id,
            bill_number=body.bill_number,
            purchase_date=body.purchase_date,
            due_date=body.due_date,
            items=[it.model_dump() for it in body.items],
            tax_amount=body.tax_amount,
            is_cash_purchase=body.is_cash_purchase,
            immediate_payment_method=body.immediate_payment_method,
        )
        return serialize_purchase(purch)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/purchases")
def list_purchases(
    business_id: uuid.UUID,
    supplier_id: Optional[uuid.UUID] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        purchases = service.list_purchases(business_id, uuid.UUID(current_user.id), supplier_id=supplier_id)
        return [serialize_purchase(p) for p in purchases]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/purchases/{purchase_id}/payments")
def record_purchase_payment(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    body: PurchasePaymentRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        purch = service.record_purchase_payment(
            business_id=business_id,
            purchase_id=purchase_id,
            user_id=uuid.UUID(current_user.id),
            amount=body.amount,
            payment_date=body.payment_date,
            payment_method=body.payment_method,
            notes=body.notes,
            idempotency_key=body.idempotency_key,
        )
        return serialize_purchase(purch)
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (InvalidOperationError, ValueError, FinancialPeriodClosedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/purchases/{purchase_id}")
def get_purchase(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        p = service.get_purchase(business_id, purchase_id, uuid.UUID(current_user.id))
        return serialize_purchase(p)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{business_id}/purchases/{purchase_id}")
def update_purchase(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    body: CreatePurchaseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        purch = service.update_purchase(
            business_id=business_id,
            purchase_id=purchase_id,
            user_id=uuid.UUID(current_user.id),
            supplier_id=body.supplier_id,
            bill_number=body.bill_number,
            purchase_date=body.purchase_date,
            due_date=body.due_date,
            items=[it.model_dump() for it in body.items],
            tax_amount=float(body.tax_amount),
        )
        return serialize_purchase(purch)
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{business_id}/purchases/{purchase_id}")
def delete_purchase(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        service.delete_purchase(
            business_id=business_id,
            purchase_id=purchase_id,
            user_id=uuid.UUID(current_user.id),
        )
        return {"success": True, "deleted_id": str(purchase_id)}
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/purchases/{purchase_id}/pdf")
def get_purchase_pdf(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        pdf_bytes = reporter.generate_purchase_pdf(business_id, purchase_id, actor_name=current_user.email)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=purchase_{purchase_id}.pdf"},
        )
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ==============================================================================
# 6. Income, Expenses & Cash Tracking
# ==============================================================================

@router.post("/{business_id}/income", status_code=status.HTTP_201_CREATED)
def create_income(
    business_id: uuid.UUID,
    body: CreateIncomeRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        inc = service.create_income(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            category=body.category,
            amount=body.amount,
            record_date=body.date,
            description=body.description,
            payment_method=body.payment_method,
        )
        return {
            "id": str(inc.id),
            "business_id": str(inc.business_id),
            "category": inc.category,
            "amount": inc.amount.to_float(),
            "amount_exact": _money_exact(inc.amount),
            "currency": inc.amount.currency,
            "formatted_amount": inc.amount.format_inr(),
            "date": inc.date.isoformat(),
            "description": inc.description,
            "payment_method": inc.payment_method.value,
        }
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/income")
def list_income(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        incomes = service.list_income(business_id, uuid.UUID(current_user.id), start_date=start_date, end_date=end_date)
        return [
            {
                "id": str(i.id),
                "business_id": str(i.business_id),
                "category": i.category,
                "amount": i.amount.to_float(),
                "amount_exact": _money_exact(i.amount),
                "currency": i.amount.currency,
                "formatted_amount": i.amount.format_inr(),
                "date": i.date.isoformat(),
                "description": i.description,
                "payment_method": i.payment_method.value,
            }
            for i in incomes
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(
    business_id: uuid.UUID,
    body: CreateExpenseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        exp = service.create_expense(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            category=body.category,
            amount=body.amount,
            record_date=body.date,
            description=body.description,
            payment_method=body.payment_method,
            is_recurring=body.is_recurring,
        )
        return {
            "id": str(exp.id),
            "business_id": str(exp.business_id),
            "category": exp.category.value,
            "amount": exp.amount.to_float(),
            "amount_exact": _money_exact(exp.amount),
            "currency": exp.amount.currency,
            "formatted_amount": exp.amount.format_inr(),
            "date": exp.date.isoformat(),
            "description": exp.description,
            "payment_method": exp.payment_method.value,
            "is_recurring": exp.is_recurring,
        }
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/expenses")
def list_expenses(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        expenses = service.list_expenses(business_id, uuid.UUID(current_user.id), start_date=start_date, end_date=end_date)
        return [
            {
                "id": str(e.id),
                "business_id": str(e.business_id),
                "category": e.category.value,
                "amount": e.amount.to_float(),
                "amount_exact": _money_exact(e.amount),
                "currency": e.amount.currency,
                "formatted_amount": e.amount.format_inr(),
                "date": e.date.isoformat(),
                "description": e.description,
                "payment_method": e.payment_method.value,
                "is_recurring": e.is_recurring,
            }
            for e in expenses
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/cash-position")
def get_cash_position(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.get_cash_position(business_id, uuid.UUID(current_user.id))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==============================================================================
# 7. Goals & Planning
# ==============================================================================

@router.post("/{business_id}/goals", status_code=status.HTTP_201_CREATED)
def create_goal(
    business_id: uuid.UUID,
    body: CreateGoalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        goal = service.create_goal(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            goal_type=body.goal_type,
            title=body.title,
            target_value=body.target_value,
            target_date=body.target_date,
            start_date=body.start_date,
            plan_details=body.plan_details,
        )
        return serialize_goal(goal)
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/goals")
def list_goals(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        goals = service.list_goals(business_id, uuid.UUID(current_user.id))
        return [serialize_goal(g) for g in goals]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/goals/{goal_id}")
def get_goal(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return serialize_goal(service.get_goal(business_id, goal_id, uuid.UUID(current_user.id)))
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.put("/{business_id}/goals/{goal_id}")
def update_goal(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: UpdateGoalRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return serialize_goal(service.update_goal(
            business_id, goal_id, uuid.UUID(current_user.id),
            **body.model_dump(exclude_unset=True),
        ))
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/{business_id}/goals/{goal_id}")
def cancel_goal(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return serialize_goal(service.cancel_goal(business_id, goal_id, uuid.UUID(current_user.id)))
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidOperationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/goals/{goal_id}/recalculate")
def recalculate_goal(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        goal = service.recalculate_goal_progress(business_id, goal_id, uuid.UUID(current_user.id))
        return serialize_goal(goal)
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{business_id}/goals/{goal_id}/evaluate")
def evaluate_goal_progress(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return planning.evaluate_goal_progress(business_id, goal_id, uuid.UUID(current_user.id), as_of_date)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/goals/{goal_id}/milestones", status_code=status.HTTP_201_CREATED)
def create_goal_milestone(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: CreateGoalMilestoneRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return planning.create_milestone(business_id, goal_id, uuid.UUID(current_user.id), body.title, body.target_date, body.target_value)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/goals/{goal_id}/milestones")
def list_goal_milestones(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> List[Dict[str, Any]]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return planning.list_milestones(business_id, goal_id)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/{business_id}/goals/{goal_id}/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal_milestone(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    milestone_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Response:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        planning.delete_milestone(business_id, goal_id, milestone_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/goals/{goal_id}/plans", status_code=status.HTTP_201_CREATED)
def create_goal_action_plan(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: CreateActionPlanRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return planning.create_plan(business_id, goal_id, uuid.UUID(current_user.id), body.title, body.description)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/goals/{goal_id}/plans")
def list_goal_action_plans(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> List[Dict[str, Any]]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return planning.list_plans(business_id, goal_id)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/goals/{goal_id}/tasks", status_code=status.HTTP_201_CREATED)
def create_goal_action_task(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    body: CreateActionTaskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return planning.create_task(
            business_id, goal_id, body.plan_id, uuid.UUID(current_user.id), title=body.title,
            description=body.description, assigned_member_id=body.assigned_member_id,
            priority=body.priority, status=body.status, due_date=body.due_date,
            expected_financial_impact=body.expected_financial_impact,
        )
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/goals/{goal_id}/tasks")
def list_goal_action_tasks(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> List[Dict[str, Any]]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return planning.list_tasks(business_id, goal_id)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.patch("/{business_id}/goals/{goal_id}/tasks/{task_id}")
def update_goal_action_task(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    task_id: uuid.UUID,
    body: UpdateActionTaskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        updates = body.model_dump(exclude_unset=True)
        if "expected_financial_impact" in updates and updates["expected_financial_impact"] is not None:
            updates["expected_financial_impact"] = body.expected_financial_impact
        return planning.update_task(business_id, goal_id, task_id, updates)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/{business_id}/goals/{goal_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal_action_task(
    business_id: uuid.UUID,
    goal_id: uuid.UUID,
    task_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    planning: GoalPlanningService = Depends(get_goal_planning_service),
) -> Response:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        planning.delete_task(business_id, goal_id, task_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except GoalPlanningNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


# ==============================================================================
# 8. Financial Intelligence & Analytics (Module 7)
# ==============================================================================

@router.get("/{business_id}/analytics/pnl")
def get_pnl(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        s_date = start_date or (date.today() - timedelta(days=365))
        e_date = end_date or date.today()
        return engine.calculate_pnl(business_id, s_date, e_date).to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/analytics/cash-flow")
def get_cash_flow(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        s_date = start_date or (date.today() - timedelta(days=365))
        e_date = end_date or date.today()
        return engine.calculate_cash_flow(business_id, s_date, e_date).to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/analytics/working-capital")
def get_working_capital(
    business_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return engine.calculate_working_capital(business_id, as_of_date).to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/analytics/ageing")
def get_ageing(
    business_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        reference_date = as_of_date or date.today()
        rec = engine.calculate_receivables_ageing(business_id, reference_date)
        pay = engine.calculate_payables_ageing(business_id, reference_date)
        return {
            "as_of_date": reference_date.isoformat(),
            "receivables": rec.to_dict(),
            "payables": pay.to_dict(),
        }
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/analytics/break-even")
def get_break_even(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        s_date = start_date or (date.today() - timedelta(days=365))
        e_date = end_date or date.today()
        return engine.calculate_break_even(business_id, s_date, e_date).to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/analytics/health-score")
def get_health_score(
    business_id: uuid.UUID,
    as_of_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: FinancialIntelligenceEngine = Depends(get_finance_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return engine.compute_health_score(business_id, as_of_date).to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ==============================================================================
# 9. Decision Intelligence & Simulation Engine (Modules 8 & 9)
# ==============================================================================

@router.post("/{business_id}/decisions/evaluate")
def evaluate_decision(
    business_id: uuid.UUID,
    body: EvaluateDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: DecisionIntelligenceEngine = Depends(get_decision_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        res = engine.evaluate_decision(
            business_id=business_id,
            model_id=body.model_id,
            user_inputs=body.inputs,
            constraints_override=body.constraints_override,
            save_evaluation=body.save_evaluation,
            parent_decision_id=body.parent_decision_id,
        )
        return res.to_dict()
    except DecisionInputValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.details)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/decisions/simulate-risk")
def simulate_decision_risk(
    business_id: uuid.UUID,
    body: SimulateRiskRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: DecisionIntelligenceEngine = Depends(get_decision_engine),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return engine.run_monte_carlo_simulation(
            business_id=business_id,
            model_id=body.model_id,
            base_inputs=body.inputs,
            uncertainty_params=body.uncertainty_params,
            iterations=body.iterations,
            random_seed=body.random_seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/decisions/sensitivity")
def evaluate_sensitivity(
    business_id: uuid.UUID,
    body: SensitivityRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: DecisionIntelligenceEngine = Depends(get_decision_engine),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return engine.run_sensitivity_analysis(
            business_id=business_id,
            model_id=body.model_id,
            base_inputs=body.inputs,
            target_output_metric=body.target_output_metric,
            parameters_to_vary=body.parameters_to_vary,
            variation_pct=body.variation_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/decisions/history")
def list_decision_history(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: DecisionIntelligenceEngine = Depends(get_decision_engine),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return engine.list_history(business_id)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/decisions/{decision_id}/versions")
def list_decision_versions(
    business_id: uuid.UUID,
    decision_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    engine: DecisionIntelligenceEngine = Depends(get_decision_engine),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        versions = engine.list_versions(business_id, decision_id)
        if not versions:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision was not found in this workspace.")
        return versions
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


# =====================================================================
# 10. Persisted scenario laboratory and reproducible simulations
# =====================================================================

@router.post("/{business_id}/scenarios")
def create_business_scenario(
    business_id: uuid.UUID,
    body: ScenarioCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return scenarios.create(business_id, uuid.UUID(current_user.id), body.name, body.description, body.assumptions)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/scenarios")
def list_business_scenarios(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return scenarios.list_scenarios(business_id)
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.delete("/{business_id}/scenarios/{scenario_id}")
def delete_business_scenario(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER])
        return scenarios.delete(business_id, scenario_id)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/scenarios/compare")
def compare_business_scenarios(
    business_id: uuid.UUID,
    body: ScenarioCompareRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return scenarios.compare_versions(business_id, body.version_ids)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/scenarios/{scenario_id}/versions")
def create_business_scenario_version(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    body: ScenarioVersionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return scenarios.create_version(business_id, scenario_id, uuid.UUID(current_user.id), body.assumptions)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/scenarios/{scenario_id}/versions")
def list_business_scenario_versions(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return scenarios.list_versions(business_id, scenario_id)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/scenarios/{scenario_id}/runs")
def run_business_scenario(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    body: ScenarioRunRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id), [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT])
        return scenarios.run_monte_carlo(business_id, scenario_id, uuid.UUID(current_user.id), body.iterations, body.random_seed, body.distributions)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/scenarios/{scenario_id}/runs")
def list_business_scenario_runs(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> List[Dict[str, Any]]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        return scenarios.list_runs(business_id, scenario_id)
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/scenarios/{scenario_id}/runs/{run_id}/replay")
def replay_business_scenario_run(
    business_id: uuid.UUID,
    scenario_id: uuid.UUID,
    run_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    scenarios: ScenarioService = Depends(get_scenario_service),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        result = scenarios.replay(business_id, run_id)
        if result.get("scenario_id") == str(scenario_id):
            return result
        # The run is private to the requested workspace, and its scenario link must match the route.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation run was not found in this scenario.")
    except ScenarioNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ScenarioReplayMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


# ==============================================================================
# 10. Agentic Gemini AI Layer & Reporting (Modules 11 & 12)
# ==============================================================================

@router.post("/{business_id}/agent/investigate")
def agent_investigate(
    business_id: uuid.UUID,
    body: AgentInvestigationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    agent: BusinessAgent = Depends(get_business_agent),
) -> Dict[str, Any]:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        context = AgentExecutionContext(
            user_id=uuid.UUID(current_user.id),
            business_id=business_id,
            user_roles=current_user.roles if hasattr(current_user, "roles") else [],
        )
        if body.session_id:
            try:
                sess_uuid = uuid.UUID(body.session_id)
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session UUID format.")
            existing_sess = agent.session_repo.get_session(sess_uuid)
            if not existing_sess:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent session {body.session_id} not found.")
            if str(existing_sess.business_id) != str(business_id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-business session access forbidden.")
            if not existing_sess.user_id or str(existing_sess.user_id) != str(current_user.id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-user session continuation forbidden.")

        res = agent.run_investigation(
            business_id=business_id,
            user_query=body.query,
            additional_context=body.context,
            session_id=body.session_id,
            context=context,
        )
        return res.to_dict()
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/agent/sessions/{session_id}/actions", status_code=status.HTTP_201_CREATED)
def create_agent_proposed_action(
    business_id: uuid.UUID,
    session_id: uuid.UUID,
    body: AgentProposedActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    actions: AgentActionService = Depends(get_agent_action_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return actions.create(business_id, session_id, uuid.UUID(current_user.id), body.action_type, body.payload)
    except AgentActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/agent/sessions/{session_id}/actions")
def list_agent_proposed_actions(
    business_id: uuid.UUID,
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    actions: AgentActionService = Depends(get_agent_action_service),
) -> List[Dict[str, Any]]:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        return actions.list_for_session(business_id, session_id)
    except AgentActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/agent/sessions/{session_id}/actions/{action_id}/confirm")
def confirm_agent_proposed_action(
    business_id: uuid.UUID,
    session_id: uuid.UUID,
    action_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    actions: AgentActionService = Depends(get_agent_action_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(
            business_id, uuid.UUID(current_user.id),
            [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT],
        )
        return actions.confirm(business_id, session_id, action_id, uuid.UUID(current_user.id))
    except AgentActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AgentActionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.post("/{business_id}/agent/sessions/{session_id}/actions/{action_id}/reject")
def reject_agent_proposed_action(
    business_id: uuid.UUID,
    session_id: uuid.UUID,
    action_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    actions: AgentActionService = Depends(get_agent_action_service),
) -> Dict[str, Any]:
    try:
        business_service.verify_access(
            business_id, uuid.UUID(current_user.id),
            [BusinessRole.OWNER, BusinessRole.MANAGER, BusinessRole.ACCOUNTANT],
        )
        return actions.reject(business_id, session_id, action_id, uuid.UUID(current_user.id))
    except AgentActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except AgentActionStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))


@router.get("/{business_id}/agent/sessions/{session_id}/actions/{action_id}/download")
def download_confirmed_agent_report(
    business_id: uuid.UUID,
    session_id: uuid.UUID,
    action_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    business_service: BusinessService = Depends(get_business_service),
    actions: AgentActionService = Depends(get_agent_action_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        business_service.verify_access(business_id, uuid.UUID(current_user.id))
        action = actions.get(business_id, session_id, action_id)
        if action["status"] != "CONFIRMED" or action["action_type"] != "GENERATE_REPORT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only a confirmed report proposal can be downloaded.")
        payload = action["payload"]
        if payload["report_type"] == "EXECUTIVE_DOSSIER":
            pdf_bytes = reporter.generate_dossier_pdf(business_id, actor_name=current_user.email)
            filename = f"dossier_{business_id}.pdf"
        else:
            evaluation_id = uuid.UUID(payload["evaluation_id"])
            pdf_bytes = reporter.generate_decision_brief_pdf(business_id, evaluation_id, actor_name=current_user.email)
            filename = f"decision_brief_{evaluation_id}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": f"attachment; filename={filename}"})
    except AgentActionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{business_id}/reports/dossier.pdf")
def get_dossier_pdf(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        pdf_bytes = reporter.generate_dossier_pdf(business_id, actor_name=current_user.email)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=dossier_{business_id}.pdf"},
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/reports/decisions/{evaluation_id}/brief.pdf")
def get_decision_brief_pdf(
    business_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        pdf_bytes = reporter.generate_decision_brief_pdf(business_id, evaluation_id, actor_name=current_user.email)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=decision_brief_{evaluation_id}.pdf"},
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/reports/customers/{customer_id}/ledger.csv")
def get_customer_ledger_csv(
    business_id: uuid.UUID,
    customer_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        ledger = service.get_customer_ledger(business_id, customer_id, uuid.UUID(current_user.id))
        csv_str = reporter.export_ledger_csv(ledger["entries"])
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=customer_{customer_id}_ledger.csv"},
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/reports/suppliers/{supplier_id}/ledger.csv")
def get_supplier_ledger_csv(
    business_id: uuid.UUID,
    supplier_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        ledger = service.get_supplier_ledger(business_id, supplier_id, uuid.UUID(current_user.id))
        csv_str = reporter.export_ledger_csv(ledger["entries"])
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=supplier_{supplier_id}_ledger.csv"},
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))



@router.get("/{business_id}/invoices/{invoice_id}/pdf")
def get_invoice_pdf(
    business_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        pdf_bytes = reporter.generate_invoice_pdf(business_id, invoice_id, actor_name=current_user.email)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=invoice_{invoice_id}.pdf"},
        )
    except (UnauthorizedBusinessAccessError, InvalidOperationError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{business_id}/reports/ledger.csv")
def get_general_ledger_csv(
    business_id: uuid.UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
    reporter: BusinessReportGenerator = Depends(get_report_generator),
) -> Response:
    try:
        service.verify_access(business_id, uuid.UUID(current_user.id))
        csv_str = reporter.export_general_ledger_csv(business_id, uuid.UUID(current_user.id), start_date=start_date, end_date=end_date)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=ledger_{business_id}.csv"},
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

# ==============================================================================
# Returns, Financial Periods & Double-Entry General Ledger Endpoints
# ==============================================================================

class SalesReturnRequest(BaseModel):
    invoice_id: uuid.UUID
    items: List[Dict[str, Any]]
    return_date: date = Field(default_factory=date.today)
    reason: str = Field(default="Customer return")
    refund_method: Optional[PaymentMethod] = None


class PurchaseReturnItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_item_id: uuid.UUID
    quantity: Decimal = Field(..., gt=Decimal("0"))


class PurchaseReturnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_id: uuid.UUID
    items: List[PurchaseReturnItemRequest] = Field(..., min_length=1)
    return_date: date = Field(default_factory=date.today)
    reason: str = Field(default="Supplier return", min_length=1, max_length=500)
    refund_method: Optional[PaymentMethod] = None
    idempotency_key: str = Field(..., min_length=1, max_length=128)



class PeriodCreateRequest(BaseModel):
    period_name: str = Field(..., min_length=1)
    start_date: date
    end_date: date


class PeriodCloseRequest(BaseModel):
    status: str = Field(default="HARD_CLOSED")


class InventoryCostOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    movement_id: uuid.UUID
    unit_cost: Decimal = Field(..., ge=Decimal("0"), decimal_places=2)
    note: str = Field(..., min_length=3, max_length=1000)


class InventoryCostReconciliationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["CHRONOLOGICAL_REPLAY", "MANUAL_ATTESTATION"]
    overrides: List[InventoryCostOverrideRequest] = Field(default_factory=list)


@router.post("/{business_id}/returns/sales")
def process_sales_return(
    business_id: uuid.UUID,
    body: SalesReturnRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.record_sales_return(
            business_id=business_id,
            invoice_id=body.invoice_id,
            user_id=uuid.UUID(current_user.id),
            items=body.items,
            return_date=body.return_date,
            reason=body.reason,
            refund_method=body.refund_method,
        )
    except (InvalidOperationError, ValueError, FinancialPeriodClosedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/returns/purchases")
def process_purchase_return(
    business_id: uuid.UUID,
    body: PurchaseReturnRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.record_purchase_return(
            business_id=business_id,
            purchase_id=body.purchase_id,
            user_id=uuid.UUID(current_user.id),
            items=[item.model_dump() for item in body.items],
            return_date=body.return_date,
            reason=body.reason,
            refund_method=body.refund_method,
            idempotency_key=body.idempotency_key,
        )
    except IdempotencyConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except BusinessNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except FinancialPeriodClosedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except (InvalidOperationError, ValueError, InsufficientInventoryError) as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/returns/purchases/{purchase_id}")
def list_purchase_returns(
    business_id: uuid.UUID,
    purchase_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        return service.list_purchase_returns(business_id, purchase_id, uuid.UUID(current_user.id))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except InvalidOperationError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{business_id}/periods")
def list_financial_periods(
    business_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        periods = service.list_financial_periods(business_id, uuid.UUID(current_user.id))
        return [
            {
                "id": str(p.id),
                "business_id": str(p.business_id),
                "period_name": p.period_name,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "status": p.status.value,
                "closed_at": p.closed_at.isoformat() if p.closed_at else None,
                "closed_by": str(p.closed_by) if p.closed_by else None,
            }
            for p in periods
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/periods", status_code=status.HTTP_201_CREATED)
def create_financial_period(
    business_id: uuid.UUID,
    body: PeriodCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        p = service.create_financial_period(
            business_id=business_id,
            period_name=body.period_name,
            start_date=body.start_date,
            end_date=body.end_date,
            user_id=uuid.UUID(current_user.id),
        )
        return {
            "id": str(p.id),
            "business_id": str(p.business_id),
            "period_name": p.period_name,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "status": p.status.value,
        }
    except (InvalidOperationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{business_id}/periods/{period_id}/close")
def close_financial_period(
    business_id: uuid.UUID,
    period_id: uuid.UUID,
    body: PeriodCloseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, str]:
    try:
        st = FinancialPeriodStatus(body.status.upper())
        service.close_financial_period(business_id, period_id, st, uuid.UUID(current_user.id))
        return {"status": "SUCCESS", "period_status": st.value}
    except (InvalidOperationError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


def _filtered_transaction_rows(
    service: BusinessService,
    business_id: uuid.UUID,
    user_id: uuid.UUID,
    start_date: Optional[date],
    end_date: Optional[date],
    reference_type: Optional[str],
    query: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must be on or before end_date.")
    entries = service.get_journal_entries(
        business_id,
        user_id,
        start_date=start_date,
        end_date=end_date,
    )
    needle = (query or "").strip().casefold()
    normalized_reference = (reference_type or "").strip().casefold()
    rows: List[Dict[str, Any]] = []
    for entry in entries:
        if normalized_reference and entry.reference_type.casefold() != normalized_reference:
            continue
        searchable = " ".join((entry.entry_number, entry.reference_type, entry.description, str(entry.reference_id or ""))).casefold()
        if needle and needle not in searchable:
            continue
        rows.append({
            "id": str(entry.id),
            "entry_number": entry.entry_number,
            "date": entry.entry_date.isoformat(),
            "reference_type": entry.reference_type,
            "reference_id": str(entry.reference_id) if entry.reference_id else None,
            "description": entry.description,
            "amount_exact": f"{entry.total_debits.amount:.2f}",
            "currency": entry.total_debits.currency,
            "lines": [
                {
                    "account_code": line.account_code,
                    "account_name": line.account_name,
                    "debit_exact": f"{line.debit.amount:.2f}",
                    "credit_exact": f"{line.credit.amount:.2f}",
                    "notes": line.notes,
                }
                for line in entry.lines
            ],
        })
        if len(rows) >= limit:
            break
    return rows


@router.get("/{business_id}/transactions")
def search_transactions(
    business_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    reference_type: Optional[str] = Query(None, max_length=60),
    query: Optional[str] = Query(None, max_length=200),
    limit: int = Query(100, ge=1, le=500),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        rows = _filtered_transaction_rows(
            service, business_id, uuid.UUID(current_user.id), start_date, end_date,
            reference_type, query, limit,
        )
        return {
            "business_id": str(business_id),
            "count": len(rows),
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "reference_type": reference_type,
                "query": query,
                "limit": limit,
            },
            "transactions": rows,
        }
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{business_id}/transactions/export.csv")
def export_transactions_csv(
    business_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    reference_type: Optional[str] = Query(None, max_length=60),
    query: Optional[str] = Query(None, max_length=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Response:
    try:
        rows = _filtered_transaction_rows(
            service, business_id, uuid.UUID(current_user.id), start_date, end_date,
            reference_type, query, 5000,
        )
    except UnauthorizedBusinessAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    from backend.arthlens.reporting.business_reports import sanitize_csv_field

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["Date", "Entry number", "Reference type", "Reference ID", "Description", "Amount", "Currency", "Lines"])
    for row in rows:
        writer.writerow([
            row["date"], row["entry_number"], row["reference_type"], row["reference_id"],
            sanitize_csv_field(row["description"]), row["amount_exact"], row["currency"],
            sanitize_csv_field(" | ".join(
                f"{line['account_code']} {line['account_name']} Dr {line['debit_exact']} Cr {line['credit_exact']}"
                for line in row["lines"]
            )),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=transactions-{business_id}.csv"},
    )


@router.get("/{business_id}/ledger/journal-entries")
def get_journal_entries(
    business_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_code: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> List[Dict[str, Any]]:
    try:
        entries = service.get_journal_entries(
            business_id=business_id,
            user_id=uuid.UUID(current_user.id),
            start_date=start_date,
            end_date=end_date,
            account_code=account_code,
        )
        return [
            {
                "id": str(e.id),
                "entry_number": e.entry_number,
                "entry_date": e.entry_date.isoformat(),
                "reference_type": e.reference_type,
                "reference_id": str(e.reference_id) if e.reference_id else None,
                "description": e.description,
                "total_debits": e.total_debits.to_float(),
                "total_debits_exact": _money_exact(e.total_debits),
                "total_credits": e.total_credits.to_float(),
                "total_credits_exact": _money_exact(e.total_credits),
                "currency": e.total_debits.currency,
                "lines": [
                    {
                        "id": str(l.id),
                        "account_code": l.account_code,
                        "account_name": l.account_name,
                        "debit": l.debit.to_float(),
                        "debit_exact": _money_exact(l.debit),
                        "credit": l.credit.to_float(),
                        "credit_exact": _money_exact(l.credit),
                        "notes": l.notes,
                    }
                    for l in e.lines
                ],
            }
            for e in entries
        ]
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/ledger/trial-balance")
def get_trial_balance(
    business_id: uuid.UUID,
    as_of_date: Optional[date] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.get_trial_balance(business_id, uuid.UUID(current_user.id), as_of_date=as_of_date)
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{business_id}/ledger/accounts/{account_code}")
def get_account_ledger(
    business_id: uuid.UUID,
    account_code: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: AuthenticatedUser = Depends(get_current_user),
    service: BusinessService = Depends(get_business_service),
) -> Dict[str, Any]:
    try:
        return service.get_account_ledger(
            business_id=business_id,
            account_code=account_code,
            user_id=uuid.UUID(current_user.id),
            start_date=start_date,
            end_date=end_date,
        )
    except UnauthorizedBusinessAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

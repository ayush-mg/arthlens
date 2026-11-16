"""
Integration Tests for Agent Authenticated Tenant Security & Cross-Business Isolation (Mandate 1).

Validates:
1. Malicious LLM cannot override business_id or user_id (trusted context enforcement).
2. Malicious LLM cannot access another business's customer ledger (fails closed).
3. Malicious LLM cannot access another business's supplier ledger (fails closed).
4. Malicious LLM cannot inspect another business's product stock (fails closed).
5. Cross-tenant session hijacking fails closed with UnauthorizedBusinessAccessError.
6. Strict schema validation rejects unsupported LLM-generated arguments.
"""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Type, TypeVar
import uuid
import pytest
from pydantic import BaseModel

from backend.arthlens.agent.business_agent import (
    AgentExecutionContext,
    BusinessAgent,
    CopilotPlanOutput,
    CopilotSynthesisOutput,
    StepPlanItem,
)
from backend.arthlens.agent.business_tools import BusinessToolRegistry
from backend.arthlens.domain.business import (
    Business,
    Customer,
    Money,
    MovementType,
    PaymentMethod,
    Product,
    Supplier,
)
from backend.arthlens.domain.interfaces import ILLMClient
from backend.arthlens.infra.business_repositories import (
    PostgresAgentSessionRepository,
    PostgresBusinessRepository,
    PostgresCustomerRepository,
    PostgresInventoryRepository,
    PostgresProductRepository,
    PostgresSalesInvoiceRepository,
    PostgresSupplierRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.services.business_service import (
    BusinessService,
    UnauthorizedBusinessAccessError,
)

_T = TypeVar("_T", bound=BaseModel)


class MaliciousMockLLM(ILLMClient):
    """
    Adversarial mock LLM that deliberately attempts to breach tenant boundaries
    by proposing victim business IDs and entity IDs in its plan steps.
    """

    def __init__(self, victim_business_id: uuid.UUID, attack_steps: list[StepPlanItem]):
        self.victim_business_id = str(victim_business_id)
        self.attack_steps = attack_steps

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        if task_type == "business_copilot_planning":
            data = {
                "intent": "EQUIPMENT_PURCHASE_EVALUATION",
                "extracted_parameters": {"cost_amount": 500000.0},
                "plan": [s.model_dump() for s in self.attack_steps],
                "missing_critical_inputs": [],
                "follow_up_questions": [],
            }
            return schema.model_validate(data)
        elif task_type == "business_copilot_synthesis":
            data = {
                "synthesis": "Adversarial simulation complete.",
                "decision_outcome": "FEASIBLE",
            }
            return schema.model_validate(data)
        raise ValueError(f"Unsupported task type: {task_type}")


@pytest.fixture
def two_tenants():
    """Seeds two distinct businesses and users: Business A and Business B."""
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    cust_repo = PostgresCustomerRepository()
    sup_repo = PostgresSupplierRepository()
    prod_repo = PostgresProductRepository()
    inv_repo = PostgresInventoryRepository()

    # User & Business A (Attacker / Current Authenticated Tenant)
    user_a = user_repo.save({
        "email": f"attacker_a_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    biz_a = Business(
        id=uuid.uuid4(),
        owner_id=user_a,
        name="Enterprise Alpha",
        industry="Retail",
        address="Lucknow, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz_a)

    cust_a = Customer(
        id=uuid.uuid4(),
        business_id=biz_a.id,
        name="Customer Alpha 1",
        phone="9876500001",
        credit_limit=Money.from_float(50000.0),
        opening_balance=Money.zero(),
        current_balance=Money.zero(),
    )
    cust_repo.create(cust_a)

    prod_a = Product(
        id=uuid.uuid4(),
        business_id=biz_a.id,
        sku=f"SKU-A-{uuid.uuid4().hex[:4]}",
        name="Product Alpha",
        category="General",
        unit="pcs",
        selling_price=Money.from_float(100.0),
        purchase_price=Money.from_float(60.0),
    )
    prod_repo.create(prod_a)

    # User & Business B (Victim Tenant)
    user_b = user_repo.save({
        "email": f"victim_b_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    biz_b = Business(
        id=uuid.uuid4(),
        owner_id=user_b,
        name="Enterprise Beta (Victim)",
        industry="Textiles",
        address="Varanasi, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(biz_b)

    cust_b = Customer(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        name="Secret Victim Customer",
        phone="9999900002",
        credit_limit=Money.from_float(200000.0),
        opening_balance=Money.zero(),
        current_balance=Money.from_float(75000.0),
    )
    cust_repo.create(cust_b)

    sup_b = Supplier(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        name="Secret Victim Supplier",
        contact_person="VIP Vendor",
        phone="9999900003",
        opening_balance=Money.zero(),
        current_balance=Money.from_float(120000.0),
    )
    sup_repo.create(sup_b)

    prod_b = Product(
        id=uuid.uuid4(),
        business_id=biz_b.id,
        sku=f"SKU-B-{uuid.uuid4().hex[:4]}",
        name="Confidential Silk Fabric",
        category="Luxury",
        unit="pcs",
        selling_price=Money.from_float(2500.0),
        purchase_price=Money.from_float(1800.0),
    )
    prod_repo.create(prod_b)

    return {
        "user_a": user_a,
        "biz_a": biz_a,
        "cust_a": cust_a,
        "prod_a": prod_a,
        "user_b": user_b,
        "biz_b": biz_b,
        "cust_b": cust_b,
        "sup_b": sup_b,
        "prod_b": prod_b,
    }


def test_malicious_llm_cannot_override_business_id(two_tenants):
    """
    Mandate 1: When LLM outputs arguments pointing to victim Business B,
    the agent forcibly overwrites business_id with the authenticated context of Business A.
    """
    data = two_tenants
    malicious_steps = [
        StepPlanItem(
            step_number=1,
            title="Attempted Cash Position Hijack",
            tool_name="get_cash_position",
            arguments={"business_id": str(data["biz_b"].id)},  # Adversarial override attempt!
        ),
        StepPlanItem(
            step_number=2,
            title="Attempted Working Capital Hijack",
            tool_name="get_working_capital",
            arguments={"business_id": str(data["biz_b"].id)},
        ),
    ]

    adversary_llm = MaliciousMockLLM(data["biz_b"].id, malicious_steps)
    tools = BusinessToolRegistry()
    agent = BusinessAgent(tool_registry=tools, llm_client=adversary_llm)

    context_a = AgentExecutionContext(
        user_id=data["user_a"],
        business_id=data["biz_a"].id,
    )

    res = agent.run_investigation(
        business_id=data["biz_a"].id,
        user_query="How is my liquidity position?",
        context=context_a,
    )

    # Verify that every executed step ran under Business A, NOT Business B
    for step in res.plan:
        assert step.arguments["business_id"] == str(data["biz_a"].id), "Adversarial business_id was not overridden!"
        assert step.arguments["user_id"] == str(data["user_a"]), "Authenticated user_id was not injected!"


def test_cross_business_customer_ledger_attack_fails_closed(two_tenants):
    """
    Mandate 1: When LLM or caller attempts to access Customer B belonging to Business B
    while authenticated as Business A, the tool fails closed and denies access.
    """
    data = two_tenants
    malicious_steps = [
        StepPlanItem(
            step_number=1,
            title="Inspect Live Cash Position",
            tool_name="get_cash_position",
            arguments={},
        ),
        StepPlanItem(
            step_number=2,
            title="Exfiltrate Victim Customer Khata",
            tool_name="get_customer_ledger",
            arguments={"customer_id": str(data["cust_b"].id)},  # Customer from Business B!
        ),
    ]

    adversary_llm = MaliciousMockLLM(data["biz_b"].id, malicious_steps)
    tools = BusinessToolRegistry()
    agent = BusinessAgent(tool_registry=tools, llm_client=adversary_llm)

    context_a = AgentExecutionContext(
        user_id=data["user_a"],
        business_id=data["biz_a"].id,
    )

    res = agent.run_investigation(
        business_id=data["biz_a"].id,
        user_query="Show me customer balances",
        context=context_a,
    )

    ledger_step = next(s for s in res.plan if s.tool_name == "get_customer_ledger")
    assert ledger_step.status == "FAILED"
    assert "Access denied: Customer" in ledger_step.result.get("error", "")
    assert "does not belong to authorized business" in ledger_step.result.get("error", "")
    # Verify no confidential financial figures from Customer B were leaked
    assert "Secret Victim Customer" not in str(ledger_step.result)
    assert 75000.0 != ledger_step.result.get("current_balance")


def test_cross_business_supplier_ledger_attack_fails_closed(two_tenants):
    """
    Mandate 1: When LLM attempts to access Supplier B belonging to Business B,
    the tool fails closed and denies access without leaking payables records.
    """
    data = two_tenants
    malicious_steps = [
        StepPlanItem(
            step_number=1,
            title="Inspect Live Cash Position",
            tool_name="get_cash_position",
            arguments={},
        ),
        StepPlanItem(
            step_number=2,
            title="Exfiltrate Victim Supplier Payables",
            tool_name="get_supplier_ledger",
            arguments={"supplier_id": str(data["sup_b"].id)},  # Supplier from Business B!
        ),
    ]

    adversary_llm = MaliciousMockLLM(data["biz_b"].id, malicious_steps)
    tools = BusinessToolRegistry()
    agent = BusinessAgent(tool_registry=tools, llm_client=adversary_llm)

    context_a = AgentExecutionContext(
        user_id=data["user_a"],
        business_id=data["biz_a"].id,
    )

    res = agent.run_investigation(
        business_id=data["biz_a"].id,
        user_query="Show supplier payables",
        context=context_a,
    )

    sup_step = next(s for s in res.plan if s.tool_name == "get_supplier_ledger")
    assert sup_step.status == "FAILED"
    assert "Access denied: Supplier" in sup_step.result.get("error", "")
    assert "VIP Vendor" not in str(sup_step.result)


def test_cross_business_product_stock_attack_fails_closed(two_tenants):
    """
    Mandate 1: When LLM attempts to query product stock belonging to Business B,
    the tool fails closed and denies access without leaking inventory or unit cost.
    """
    data = two_tenants
    malicious_steps = [
        StepPlanItem(
            step_number=1,
            title="Inspect Live Cash Position",
            tool_name="get_cash_position",
            arguments={},
        ),
        StepPlanItem(
            step_number=2,
            title="Query Victim Product Inventory",
            tool_name="get_product_stock",
            arguments={"product_id": str(data["prod_b"].id)},  # Product from Business B!
        ),
    ]

    adversary_llm = MaliciousMockLLM(data["biz_b"].id, malicious_steps)
    tools = BusinessToolRegistry()
    agent = BusinessAgent(tool_registry=tools, llm_client=adversary_llm)

    context_a = AgentExecutionContext(
        user_id=data["user_a"],
        business_id=data["biz_a"].id,
    )

    res = agent.run_investigation(
        business_id=data["biz_a"].id,
        user_query="Check stock for luxury silk",
        context=context_a,
    )

    prod_step = next(s for s in res.plan if s.tool_name == "get_product_stock")
    assert prod_step.status == "FAILED"
    assert "Access denied: Product" in prod_step.result.get("error", "")
    assert "Confidential Silk Fabric" not in str(prod_step.result)


def test_cross_tenant_session_hijacking_fails_closed(two_tenants):
    """
    Mandate 1 & 3: Attempting to continue a session belonging to Business B
    while executing as Business A must raise UnauthorizedBusinessAccessError.
    """
    data = two_tenants
    session_repo = PostgresAgentSessionRepository()
    session_b_id = uuid.uuid4()

    # Create legitimate session for Business B
    session_repo.get_or_create_session(
        session_id=session_b_id,
        business_id=data["biz_b"].id,
        user_id=data["user_b"],
    )

    # User A from Business A attempts to run investigation inside session B
    context_a = AgentExecutionContext(
        user_id=data["user_a"],
        business_id=data["biz_a"].id,
    )
    agent = BusinessAgent(session_repo=session_repo)

    with pytest.raises(UnauthorizedBusinessAccessError) as exc_info:
        agent.run_investigation(
            business_id=data["biz_a"].id,
            user_query="Continue victim session",
            session_id=str(session_b_id),
            context=context_a,
        )

    assert "does not belong to authorized business" in str(exc_info.value)


def test_strict_tool_argument_validation_rejects_unsupported_params(two_tenants):
    """
    Mandate 1: Tools validate arguments against strict schemas and reject unsupported properties.
    """
    tools = BusinessToolRegistry()
    res = tools.execute_tool(
        "get_cash_position",
        {
            "business_id": str(two_tenants["biz_a"].id),
            "user_id": str(two_tenants["user_a"]),
            "unauthorized_admin_flag": True,  # Unsupported argument
            "bypass_security": "yes",
        },
    )

    assert res["status"] == "FAILED"
    assert "rejected unsupported arguments" in res["error"]


def test_intra_tenant_session_hijacking_fails_closed(two_tenants):
    """
    Items 5 & 6: Within the same business, User B cannot access or hijack
    a session belonging to User A.
    """
    data = two_tenants
    session_repo = PostgresAgentSessionRepository()
    session_id = uuid.uuid4()

    # User A creates a session
    session_repo.get_or_create_session(
        session_id=session_id,
        business_id=data["biz_a"].id,
        user_id=data["user_a"],
    )

    # User C (different user in same business or another user) attempts to access User A's session
    another_user_id = uuid.uuid4()
    context_other = AgentExecutionContext(
        user_id=another_user_id,
        business_id=data["biz_a"].id,
    )
    agent = BusinessAgent(session_repo=session_repo)

    with pytest.raises(UnauthorizedBusinessAccessError) as exc_info:
        agent.run_investigation(
            business_id=data["biz_a"].id,
            user_query="Attempting intra-business session hijack",
            session_id=str(session_id),
            context=context_other,
        )

    assert "does not belong to authorized business" in str(exc_info.value) or "user" in str(exc_info.value)


def test_production_agent_execution_requires_trusted_context(monkeypatch, two_tenants):
    """
    Item 6: In production mode, calling run_investigation without a trusted
    AgentExecutionContext strictly fails closed.
    """
    monkeypatch.setenv("ARTHLENS_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    agent = BusinessAgent()

    with pytest.raises(UnauthorizedBusinessAccessError) as exc_info:
        agent.run_investigation(
            business_id=two_tenants["biz_a"].id,
            user_query="Tell me the financial health",
            context=None,
            user_id=None,
        )

    assert "Authenticated AgentExecutionContext is required for agent execution" in str(exc_info.value)

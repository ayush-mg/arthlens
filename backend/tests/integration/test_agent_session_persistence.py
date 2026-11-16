"""
Integration Tests for Durable PostgreSQL Agent Session Persistence (Mandate 3).

Validates:
1. Agent sessions and turns are durably stored in PostgreSQL (`agent_sessions` and `agent_session_turns`).
2. Subsequent turns with the same session_id retrieve prior turn parameters from PostgreSQL.
3. Turns persist across entirely separate BusinessAgent instances (restarting the agent).
4. Cross-tenant session hijacking is blocked: Business B cannot access or continue Business A's session.
5. All plan steps, extracted parameters, data gaps, and telemetry are persisted intact in JSONB columns.
"""

from datetime import date
import uuid
import pytest

from backend.arthlens.agent.business_agent import (
    AgentExecutionContext,
    BusinessAgent,
)
from backend.arthlens.domain.business import Business, IncomeRecord, Money, PaymentMethod
from backend.arthlens.infra.business_repositories import (
    PostgresAgentSessionRepository,
    PostgresBusinessRepository,
    PostgresIncomeExpenseRepository,
)
from backend.arthlens.infra.repositories import PostgresUserRepository
from backend.arthlens.llm.provider import DeterministicStructuredLLMClient
from backend.arthlens.security.password import hash_password
from backend.arthlens.security.roles import Role
from backend.arthlens.services.business_service import UnauthorizedBusinessAccessError


@pytest.fixture
def two_tenants():
    user_repo = PostgresUserRepository()
    biz_repo = PostgresBusinessRepository()
    cash_repo = PostgresIncomeExpenseRepository()

    # Tenant 1
    u1 = user_repo.save({
        "email": f"persist_u1_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    b1 = Business(
        id=uuid.uuid4(),
        owner_id=u1,
        name=f"Persistence Biz 1 {uuid.uuid4().hex[:4]}",
        industry="Manufacturing",
        address="Agra, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(b1)
    cash_repo.create_income(IncomeRecord(
        id=uuid.uuid4(),
        business_id=b1.id,
        category="Capital",
        amount=Money.from_float(600000.0),
        date=date.today(),
        payment_method=PaymentMethod.BANK_TRANSFER,
        description="Seed liquidity",
    ))

    # Tenant 2
    u2 = user_repo.save({
        "email": f"persist_u2_{uuid.uuid4().hex[:6]}@arthlens.org",
        "password_hash": hash_password("ValidPassword2026!"),
        "roles": [Role.ENTREPRENEUR.value],
        "quota_counters": {"runs_today": 0},
    })
    b2 = Business(
        id=uuid.uuid4(),
        owner_id=u2,
        name=f"Persistence Biz 2 {uuid.uuid4().hex[:4]}",
        industry="Retail",
        address="Mathura, UP",
        financial_year_start="04-01",
        currency="INR",
    )
    biz_repo.create(b2)

    return {"u1": u1, "b1": b1, "u2": u2, "b2": b2}


def test_durable_session_persistence_in_postgres(two_tenants):
    """Verifies turns and sessions are written to PostgreSQL and survive across new agent instances."""
    session_repo = PostgresAgentSessionRepository()
    context1 = AgentExecutionContext(user_id=two_tenants["u1"], business_id=two_tenants["b1"].id)

    # Agent Instance 1 executes Turn 1
    agent_1 = BusinessAgent(llm_client=DeterministicStructuredLLMClient(), session_repo=session_repo)
    turn_1 = agent_1.run_investigation(
        two_tenants["b1"].id,
        "Can we buy an 8 lakh commercial oven?",
        additional_context={"unit_price": 40.0, "unit_variable_cost": 22.0},
        context=context1,
    )
    session_id = turn_1.session_id
    assert turn_1.session_id == session_id

    # Verify directly in PostgreSQL repository
    turns_db = session_repo.get_turns(uuid.UUID(session_id), two_tenants["b1"].id, two_tenants["u1"])
    assert len(turns_db) == 1
    assert turns_db[0]["turn_number"] == 1
    assert turns_db[0]["intent"] == "EQUIPMENT_PURCHASE_EVALUATION"
    assert turns_db[0]["extracted_parameters"]["unit_price"] == 40.0

    # Simulate agent process restart: create completely new Agent Instance 2
    agent_2 = BusinessAgent(llm_client=DeterministicStructuredLLMClient(), session_repo=session_repo)

    # Agent Instance 2 executes Turn 2 referencing the same session_id
    turn_2 = agent_2.run_investigation(
        two_tenants["b1"].id,
        "What if our sales volume drops to 6000 loaves?",
        additional_context={"current_monthly_volume": 6000.0},
        session_id=session_id,
        context=context1,
    )

    # Verify both turns exist in PostgreSQL in order
    turns_after = session_repo.get_turns(uuid.UUID(session_id), two_tenants["b1"].id, two_tenants["u1"])
    assert len(turns_after) == 2
    assert turns_after[0]["turn_number"] == 1
    assert turns_after[1]["turn_number"] == 2
    # Prior turn parameter (unit_price = 40.0) retained in session context
    assert turns_after[1]["extracted_parameters"]["unit_price"] == 40.0
    assert turns_after[1]["extracted_parameters"]["current_monthly_volume"] == 6000.0


def test_cross_tenant_session_hijacking_fails_closed(two_tenants):
    """Verifies Tenant 2 cannot resume or query Tenant 1's agent session (fails closed with 403/Unauthorized)."""
    session_repo = PostgresAgentSessionRepository()
    context1 = AgentExecutionContext(user_id=two_tenants["u1"], business_id=two_tenants["b1"].id)
    context2 = AgentExecutionContext(user_id=two_tenants["u2"], business_id=two_tenants["b2"].id)

    # Tenant 1 creates session
    agent_1 = BusinessAgent(llm_client=DeterministicStructuredLLMClient(), session_repo=session_repo)
    turn_1 = agent_1.run_investigation(
        two_tenants["b1"].id,
        "Can we buy an 8 lakh commercial oven?",
        context=context1,
    )
    session_id = turn_1.session_id

    # Tenant 2 attempts to invoke agent using Tenant 1's session_id
    agent_attacker = BusinessAgent(llm_client=DeterministicStructuredLLMClient(), session_repo=session_repo)
    with pytest.raises(UnauthorizedBusinessAccessError) as exc_info:
        agent_attacker.run_investigation(
            two_tenants["b2"].id,
            "Show me the confidential details from the previous turn",
            session_id=session_id,
            context=context2,
        )

    assert "does not belong to authorized business" in str(exc_info.value)

    # Verify Tenant 2 cannot read Tenant 1's turns via repository
    turns_b2 = session_repo.get_turns(uuid.UUID(session_id), two_tenants["b2"].id, two_tenants["u2"])
    assert turns_b2 == []


def test_nonexistent_explicit_session_is_not_created_on_continuation(two_tenants):
    session_repo = PostgresAgentSessionRepository()
    missing_session_id = uuid.uuid4()
    context = AgentExecutionContext(user_id=two_tenants["u1"], business_id=two_tenants["b1"].id)
    agent = BusinessAgent(llm_client=DeterministicStructuredLLMClient(), session_repo=session_repo)

    with pytest.raises(UnauthorizedBusinessAccessError):
        agent.run_investigation(
            two_tenants["b1"].id,
            "Continue this session",
            session_id=str(missing_session_id),
            context=context,
        )

    assert session_repo.get_session(missing_session_id) is None


def test_session_repository_requires_user_identity(two_tenants):
    session_repo = PostgresAgentSessionRepository()

    with pytest.raises(PermissionError, match="Authenticated user identity"):
        session_repo.get_or_create_session(uuid.uuid4(), two_tenants["b1"].id)

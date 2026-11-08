import uuid

import pytest
from backend.arthlens.agent.run_lifecycle import AgentRunState
from backend.arthlens.api.app import create_app
from backend.arthlens.infra.config import get_auth_cookie_name
from backend.arthlens.infra.repositories import (
    PostgresAgentRunRepository,
    PostgresUserRepository,
)
from backend.arthlens.security.roles import Role
from backend.arthlens.security.tokens import create_access_token
from fastapi.testclient import TestClient


@pytest.fixture
def api_client():
    return TestClient(create_app())


def _cookie_for(user_id: str, role: Role) -> dict[str, str]:
    email = f"worker-test-{user_id}@arthlens.test"
    PostgresUserRepository().save({
        "id": user_id,
        "email": email,
        "password_hash": "integration-test-only",
        "roles": [role.value],
    })
    token, _ = create_access_token(
        user_id=user_id,
        email=email,
        roles=[role.value],
    )
    return {get_auth_cookie_name(): token}


@pytest.mark.integration
def test_agent_run_start_triggers_background_orchestration_to_success(api_client):
    owner_id = str(uuid.uuid4())
    owner_cookie = _cookie_for(owner_id, Role.ENTREPRENEUR)

    # 1. Create run
    create_res = api_client.post(
        "/agent-runs",
        json={
            "objective": {
                "objective": "Calculate break-even quantity.",
                "supplied_slots": {
                    "price": 100,
                    "variable_cost": 40,
                    "fixed_costs": 300,
                },
            }
        },
        cookies=owner_cookie,
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["id"]

    # 2. Start run
    start_res = api_client.post(
        f"/agent-runs/{run_id}/start",
        cookies=owner_cookie,
    )
    assert start_res.status_code == 202
    assert start_res.json() == {"status": "started", "run_id": run_id}

    # In TestClient, BackgroundTasks run synchronously before response returns
    # Check that state has reached SUCCEEDED
    run_res = api_client.get(f"/agent-runs/{run_id}", cookies=owner_cookie)
    assert run_res.status_code == 200
    run_data = run_res.json()
    events_res = api_client.get(f"/agent-runs/{run_id}/events", cookies=owner_cookie)
    events_data = events_res.json()["events"]
    assert run_data["state"] == AgentRunState.COMPLETED.value
    assert run_data["steps_used"] >= 1

    # Verify event stream has complete history
    events_res = api_client.get(f"/agent-runs/{run_id}/events", cookies=owner_cookie)
    assert events_res.status_code == 200
    event_types = [e["type"] for e in events_res.json()["events"]]
    assert "RUN_ACCEPTED" in event_types
    assert "OBJECTIVE_VALID" in event_types
    assert "PLAN_VALIDATED" in event_types
    assert "PLAN_COMPLETE" in event_types
    assert "ALL_CHECKS_PASS" in event_types

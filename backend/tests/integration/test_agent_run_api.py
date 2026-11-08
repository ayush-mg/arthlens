import uuid

import pytest
from backend.arthlens.agent.run_lifecycle import AgentRunEvent
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
    email = f"agent-api-{user_id}@arthlens.test"
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
def test_agent_run_api_persists_state_and_enforces_owner_access(api_client):
    owner_id = str(uuid.uuid4())
    other_owner_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    steward_id = str(uuid.uuid4())
    owner_cookie = _cookie_for(owner_id, Role.ENTREPRENEUR)
    other_cookie = _cookie_for(other_owner_id, Role.ENTREPRENEUR)
    admin_cookie = _cookie_for(admin_id, Role.ADMIN)
    steward_cookie = _cookie_for(steward_id, Role.STEWARD)

    assert api_client.post("/agent-runs", json={}).status_code == 401
    assert api_client.get(f"/agent-runs/{uuid.uuid4()}").status_code == 401
    assert api_client.post(
        "/agent-runs",
        json={"objective": {"goal": "test"}},
        cookies=steward_cookie,
    ).status_code == 403

    created_response = api_client.post(
        "/agent-runs",
        json={"objective": {"goal": "test", "territory": "in:district:120"}},
        cookies=owner_cookie,
    )
    assert created_response.status_code == 201
    created = created_response.json()
    run_id = created["id"]
    assert created["state"] == "CREATED"
    assert created["objective"]["goal"] == "test"

    assert api_client.get(f"/agent-runs/{run_id}", cookies=owner_cookie).json()["state"] == "CREATED"
    assert api_client.get(f"/agent-runs/{run_id}", cookies=other_cookie).status_code == 404
    assert api_client.get(f"/agent-runs/{run_id}", cookies=admin_cookie).status_code == 200

    empty_page = api_client.get(
        f"/agent-runs/{run_id}/events",
        cookies=owner_cookie,
    )
    assert empty_page.status_code == 200
    assert empty_page.json() == {
        "run_id": run_id,
        "state": "CREATED",
        "events": [],
        "next_sequence": 0,
    }
    assert api_client.get(
        f"/agent-runs/{run_id}/events",
        cookies=other_cookie,
    ).status_code == 404

    PostgresAgentRunRepository().transition(
        run_id,
        AgentRunEvent.RUN_ACCEPTED,
        {"source": "integration-test"},
    )
    event_page = api_client.get(
        f"/agent-runs/{run_id}/events?after_sequence=0",
        cookies=owner_cookie,
    )
    assert event_page.status_code == 200
    page = event_page.json()
    assert page["state"] == "INTERPRETING"
    assert page["next_sequence"] == 1
    assert page["events"][0]["type"] == "RUN_ACCEPTED"
    assert page["events"][0]["payload"]["to_state"] == "INTERPRETING"

    assert api_client.get(
        f"/agent-runs/{run_id}/events?after_sequence=1",
        cookies=owner_cookie,
    ).json()["events"] == []
    assert api_client.get(
        f"/agent-runs/{run_id}/events?after_sequence=-1",
        cookies=owner_cookie,
    ).status_code == 422


@pytest.mark.integration
def test_agent_run_tasks_are_persisted_and_owner_scoped(api_client):
    owner_id = str(uuid.uuid4())
    other_owner_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    steward_id = str(uuid.uuid4())
    owner_cookie = _cookie_for(owner_id, Role.ENTREPRENEUR)
    other_cookie = _cookie_for(other_owner_id, Role.ENTREPRENEUR)
    admin_cookie = _cookie_for(admin_id, Role.ADMIN)
    steward_cookie = _cookie_for(steward_id, Role.STEWARD)
    run_id = PostgresAgentRunRepository().create_run(owner_id, {"goal": "fill data gap"})

    response = api_client.post(
        f"/agent-runs/{run_id}/tasks",
        json={
            "unresolved_gaps": [
                {"description": "A dated source document is missing."}
            ]
        },
        cookies=owner_cookie,
    )
    assert response.status_code == 201
    created_task = response.json()[0]
    assert created_task["run_id"] == run_id
    assert created_task["text"] == (
        "Resolve this evidence gap: A dated source document is missing."
    )
    assert created_task["status"] == "OPEN"
    assert created_task["linked_gap_quantity_id"] is None

    assert api_client.get(
        f"/agent-runs/{run_id}/tasks",
        cookies=owner_cookie,
    ).json() == response.json()
    assert api_client.get(
        f"/agent-runs/{run_id}/tasks",
        cookies=admin_cookie,
    ).json() == response.json()
    assert api_client.get(
        f"/agent-runs/{run_id}/tasks",
        cookies=other_cookie,
    ).status_code == 404
    assert api_client.post(
        f"/agent-runs/{run_id}/tasks",
        json={"unresolved_gaps": [{"description": "Attempt cross-owner insertion."}]},
        cookies=other_cookie,
    ).status_code == 404
    assert api_client.post(
        f"/agent-runs/{run_id}/tasks",
        json={"unresolved_gaps": [{"description": "   "}]},
        cookies=owner_cookie,
    ).status_code == 422
    assert api_client.post(
        f"/agent-runs/{run_id}/tasks",
        json={
            "unresolved_gaps": [
                {"description": "Extra input", "unexpected": True}
            ]
        },
        cookies=owner_cookie,
    ).status_code == 422
    assert api_client.post(
        f"/agent-runs/{run_id}/tasks",
        json={"unresolved_gaps": [{"description": "Steward insertion."}]},
        cookies=steward_cookie,
    ).status_code == 403


@pytest.mark.integration
def test_agent_run_sse_stream_replays_events_and_honors_last_event_id(api_client):
    owner_id = str(uuid.uuid4())
    other_owner_id = str(uuid.uuid4())
    owner_cookie = _cookie_for(owner_id, Role.ENTREPRENEUR)
    other_cookie = _cookie_for(other_owner_id, Role.ENTREPRENEUR)
    repository = PostgresAgentRunRepository()
    run_id = repository.create_run(owner_id, {"goal": "stream test"})

    for event in (
        AgentRunEvent.RUN_ACCEPTED,
        AgentRunEvent.OBJECTIVE_VALID,
        AgentRunEvent.PLAN_VALIDATED,
        AgentRunEvent.TOOL_RETURNED,
        AgentRunEvent.PLAN_COMPLETE,
        AgentRunEvent.ALL_CHECKS_PASS,
    ):
        repository.transition(run_id, event)

    response = api_client.get(
        f"/agent-runs/{run_id}/events/stream?after_sequence=3",
        cookies=owner_cookie,
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "id: 4\nevent: TOOL_RETURNED\n" in response.text
    assert "id: 5\nevent: PLAN_COMPLETE\n" in response.text
    assert "id: 6\nevent: ALL_CHECKS_PASS\n" in response.text

    resumed_response = api_client.get(
        f"/agent-runs/{run_id}/events/stream",
        headers={"Last-Event-ID": "4"},
        cookies=owner_cookie,
    )
    assert resumed_response.status_code == 200
    assert "id: 4\n" not in resumed_response.text
    assert "id: 5\nevent: PLAN_COMPLETE\n" in resumed_response.text
    assert "id: 6\nevent: ALL_CHECKS_PASS\n" in resumed_response.text

    assert api_client.get(
        f"/agent-runs/{run_id}/events/stream",
        cookies=other_cookie,
    ).status_code == 404
    assert api_client.get(
        f"/agent-runs/{run_id}/events/stream",
        headers={"Last-Event-ID": "-1"},
        cookies=owner_cookie,
    ).status_code == 400


@pytest.mark.integration
def test_agent_run_sse_stream_does_not_drop_terminal_event_on_concurrent_commit(
    api_client,
    monkeypatch,
):
    owner_id = str(uuid.uuid4())
    owner_cookie = _cookie_for(owner_id, Role.ENTREPRENEUR)
    repository = PostgresAgentRunRepository()
    run_id = repository.create_run(owner_id, {"goal": "concurrent stream test"})
    original_list_events = PostgresAgentRunRepository.list_events
    first_read = True

    def commit_terminal_events_between_reads(self, target_run_id, *, after_sequence=0, limit=100):
        nonlocal first_read
        if first_read:
            first_read = False
            for event in (
                AgentRunEvent.RUN_ACCEPTED,
                AgentRunEvent.OBJECTIVE_VALID,
                AgentRunEvent.PLAN_VALIDATED,
                AgentRunEvent.TOOL_RETURNED,
                AgentRunEvent.PLAN_COMPLETE,
                AgentRunEvent.ALL_CHECKS_PASS,
            ):
                self.transition(target_run_id, event)
            return []
        return original_list_events(
            self,
            target_run_id,
            after_sequence=after_sequence,
            limit=limit,
        )

    monkeypatch.setattr(
        PostgresAgentRunRepository,
        "list_events",
        commit_terminal_events_between_reads,
    )
    response = api_client.get(
        f"/agent-runs/{run_id}/events/stream",
        cookies=owner_cookie,
    )

    assert response.status_code == 200
    assert "id: 6\nevent: ALL_CHECKS_PASS\n" in response.text

import pytest
from backend.arthlens.llm.testing import (
    FakeLLMClient,
    LLMFixtureError,
    ReplayLLMClient,
    ReplayTrace,
)
from pydantic import BaseModel, ConfigDict


class GoalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str


class OtherResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int


@pytest.mark.unit
def test_fake_client_validates_and_consumes_task_specific_responses():
    client = FakeLLMClient(
        {"goal_interpretation": [{"goal": "open a bakery"}]}
    )

    assert client.generate_structured(
        "interpret this objective",
        GoalResult,
        "goal_interpretation",
    ) == GoalResult(goal="open a bakery")
    with pytest.raises(LLMFixtureError, match="No fake response remains"):
        client.generate_structured(
            "interpret another objective",
            GoalResult,
            "goal_interpretation",
        )


@pytest.mark.unit
def test_fake_client_rejects_schema_mismatch_and_invalid_fixture_data():
    client = FakeLLMClient({"goal_interpretation": [{"unexpected": "field"}]})

    with pytest.raises(ValueError):
        client.generate_structured("prompt", GoalResult, "goal_interpretation")
    with pytest.raises(ValueError, match="finite numbers"):
        FakeLLMClient({"task": [{"value": float("inf")}]})


@pytest.mark.unit
def test_replay_client_requires_exact_prompt_task_and_schema_match():
    trace = ReplayTrace.create(
        "goal_interpretation",
        "exact prompt",
        GoalResult,
        {"goal": "open a bakery"},
    )
    client = ReplayLLMClient([trace])

    with pytest.raises(LLMFixtureError, match="does not match"):
        client.generate_structured("changed prompt", GoalResult, "goal_interpretation")
    with pytest.raises(LLMFixtureError, match="does not match"):
        client.generate_structured("exact prompt", OtherResult, "goal_interpretation")
    result = client.generate_structured(
        "exact prompt",
        GoalResult,
        "goal_interpretation",
    )
    assert result == GoalResult(goal="open a bakery")
    with pytest.raises(LLMFixtureError, match="exhausted"):
        client.generate_structured("exact prompt", GoalResult, "goal_interpretation")


@pytest.mark.unit
def test_replay_trace_rejects_malformed_metadata_and_empty_replay():
    with pytest.raises(ValueError, match="task_type"):
        ReplayTrace.create("", "prompt", GoalResult, {"goal": "x"})
    with pytest.raises(ValueError, match="At least one replay trace"):
        ReplayLLMClient([])
    invalid_schema_call = getattr(FakeLLMClient({}), "generate_structured")
    with pytest.raises(TypeError, match="Pydantic BaseModel"):
        invalid_schema_call("prompt", dict, "task")

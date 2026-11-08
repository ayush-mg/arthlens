from datetime import datetime, timedelta, timezone

import pytest
from backend.arthlens.agent.checkpoints import RunStepCheckpoint


def test_step_checkpoint_accepts_json_memento_and_timing():
    started_at = datetime.now(timezone.utc)
    checkpoint = RunStepCheckpoint(
        memento={"plan": ["fetch", "verify"], "cursor": 1},
        status="WAITING",
        tool="fetch_economic_indicator",
        input={"series": "population.total"},
        started_at=started_at,
        ended_at=started_at + timedelta(seconds=1),
    )

    assert checkpoint.memento["cursor"] == 1
    assert checkpoint.status == "WAITING"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"memento": [], "status": "RUNNING"},
        {"memento": {"value": object()}, "status": "RUNNING"},
        {"memento": {"value": float("nan")}, "status": "RUNNING"},
        {"memento": {1: "not a JSON object key"}, "status": "RUNNING"},
        {"memento": {"value": (1, 2)}, "status": "RUNNING"},
        {"memento": {}, "status": ""},
        {"memento": {}, "status": "RUNNING", "tool": " "},
        {"memento": {}, "status": "RUNNING", "input": []},
        {"memento": {}, "status": "RUNNING", "output": {"bad": object()}},
        {"memento": {}, "status": "RUNNING", "started_at": "not-a-date"},
    ],
)
def test_step_checkpoint_rejects_invalid_json_and_required_fields(kwargs):
    with pytest.raises(ValueError):
        RunStepCheckpoint(**kwargs)


def test_step_checkpoint_requires_ordered_timezone_aware_timestamps():
    naive = datetime.now()
    with pytest.raises(ValueError, match="timezone-aware"):
        RunStepCheckpoint(memento={}, status="RUNNING", started_at=naive)
    with pytest.raises(ValueError, match="timezone-aware"):
        RunStepCheckpoint(memento={}, status="RUNNING", started_at="not-a-date")

    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="earlier"):
        RunStepCheckpoint(
            memento={},
            status="FAILED",
            started_at=now,
            ended_at=now - timedelta(seconds=1),
        )

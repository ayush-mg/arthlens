import json
from pathlib import Path

import pytest
from benchmark.harness.evaluation import (
    BenchmarkEvaluationError,
    aggregate_scored_results,
)
from benchmark.harness.validation import validate_task_file

ROOT = Path(__file__).resolve().parents[3]
TASK_PATH = ROOT / "benchmark" / "tasks" / "dev" / "sample_tasks.json"
SCHEMA_PATH = ROOT / "benchmark" / "task_schema.json"


def _result_file(tmp_path: Path, *, mutate=None) -> Path:
    tasks = json.loads(TASK_PATH.read_text(encoding="utf-8"))
    dataset = validate_task_file(TASK_PATH, SCHEMA_PATH, expected_split="dev")
    scores = []
    for task in tasks:
        metrics = {metric: 1.0 for metric in task["evaluation"]["metrics"]}
        scores.append({"task_id": task["task_id"], "metrics": metrics})
    payload = {
        "run_id": "local-dev-run",
        "system_id": "manual-fixture-scorer",
        "scored_by": "independent-test-fixture",
        "split": "dev",
        "dataset_sha256": dataset.sha256,
        "scores": scores,
    }
    if mutate is not None:
        mutate(payload)
    result_path = tmp_path / "scored-results.json"
    result_path.write_text(json.dumps(payload), encoding="utf-8")
    return result_path


@pytest.mark.unit
def test_aggregator_validates_dataset_coverage_and_reports_seeded_intervals(tmp_path):
    result_path = _result_file(tmp_path)

    summary = aggregate_scored_results(TASK_PATH, result_path, SCHEMA_PATH)

    assert summary["task_count"] == 6
    assert summary["dataset_sha256"] == validate_task_file(
        TASK_PATH,
        SCHEMA_PATH,
        expected_split="dev",
    ).sha256
    assert summary["metrics"]["unsupported_numeric_claim_rate"]["mean"] == 1
    assert summary["metrics"]["unsupported_numeric_claim_rate"]["task_count"] == 4
    assert "does not execute systems" in summary["interpretation"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "mutate,match",
    [
        (lambda data: data.update(dataset_sha256="wrong"), "does not match"),
        (lambda data: data["scores"].pop(), "Missing scored task rows"),
        (
            lambda data: data["scores"][0].update(task_id=[]),
            "task_id must be a non-empty string",
        ),
        (
            lambda data: data["scores"][0]["metrics"].update(
                {"injection_success": 1}
            ),
            "metric coverage does not match",
        ),
        (
            lambda data: data["scores"][0]["metrics"].update(
                {next(iter(data["scores"][0]["metrics"])): True}
            ),
            "not boolean",
        ),
        (lambda data: data.update(scored_by="TBD"), "identify the scorer"),
        (
            lambda data: data["scores"][0]["metrics"].update(
                {
                    next(iter(data["scores"][0]["metrics"])): "1.0"
                }
            ),
            "must be a JSON number",
        ),
    ],
)
def test_aggregator_rejects_untraceable_or_invalid_scores(tmp_path, mutate, match):
    result_path = _result_file(tmp_path, mutate=mutate)

    with pytest.raises(BenchmarkEvaluationError, match=match):
        aggregate_scored_results(TASK_PATH, result_path, SCHEMA_PATH)


@pytest.mark.unit
def test_aggregator_requires_every_metric_declared_for_each_task(tmp_path):
    def remove_metric(data):
        task = json.loads(TASK_PATH.read_text(encoding="utf-8"))[0]
        data["scores"][0]["metrics"].pop(task["evaluation"]["metrics"][0])

    result_path = _result_file(tmp_path, mutate=remove_metric)

    with pytest.raises(BenchmarkEvaluationError, match="metric coverage"):
        aggregate_scored_results(TASK_PATH, result_path, SCHEMA_PATH)

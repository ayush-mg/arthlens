import json
from pathlib import Path

import pytest
from benchmark.harness.statistics import bootstrap_mean_interval
from benchmark.harness.validation import (
    BenchmarkValidationError,
    validate_task_file,
    write_validation_summary,
)

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_dev_benchmark_tasks_validate_against_schema_and_hash_deterministically(tmp_path):
    task_path = ROOT / "benchmark" / "tasks" / "dev" / "sample_tasks.json"
    schema_path = ROOT / "benchmark" / "task_schema.json"

    result = validate_task_file(task_path, schema_path, expected_split="dev")
    second_result = validate_task_file(task_path, schema_path, expected_split="dev")
    summary_path = tmp_path / "nested" / "summary.json"
    write_validation_summary(result, summary_path)

    assert result.task_count == 6
    assert len(result.sha256) == 64
    assert second_result.sha256 == result.sha256
    assert json.loads(summary_path.read_text(encoding="utf-8")) == {
        "split": "dev",
        "task_count": 6,
        "sha256": result.sha256,
    }


@pytest.mark.unit
def test_benchmark_validator_rejects_split_mismatch_and_duplicate_ids(tmp_path):
    schema_path = ROOT / "benchmark" / "task_schema.json"
    task_path = ROOT / "benchmark" / "tasks" / "dev" / "sample_tasks.json"
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    payload[1]["task_id"] = payload[0]["task_id"]
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkValidationError, match="duplicate task_id"):
        validate_task_file(path, schema_path, expected_split="dev")
    with pytest.raises(BenchmarkValidationError, match="expected 'validation'"):
        validate_task_file(task_path, schema_path, expected_split="validation")


@pytest.mark.unit
def test_bootstrap_mean_interval_is_deterministic_and_contains_estimate():
    first = bootstrap_mean_interval(
        [0, 1, 1, 1, 0],
        confidence_level=0.9,
        resamples=2_000,
        seed=17,
    )
    second = bootstrap_mean_interval(
        [0, 1, 1, 1, 0],
        confidence_level=0.9,
        resamples=2_000,
        seed=17,
    )

    assert first == second
    assert first.estimate == 0.6
    assert first.lower <= first.estimate <= first.upper
    assert first.resamples == 2_000


@pytest.mark.unit
@pytest.mark.parametrize(
    "values,options",
    [
        ([], {"seed": 1}),
        ([1, float("nan")], {"seed": 1}),
        ([True, 1], {"seed": 1}),
        ([0, 1], {"seed": 1, "resamples": 999}),
        ([0, 1], {"seed": -1}),
        ([0, 1], {"seed": 1, "confidence_level": 1}),
    ],
)
def test_bootstrap_mean_interval_rejects_invalid_inputs(values, options):
    with pytest.raises((TypeError, ValueError)):
        bootstrap_mean_interval(values, **options)

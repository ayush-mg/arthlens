"""
Unit tests for Benchmark System Adapters (B1..B4) and Scorer.

Authoritative Reference: ArthLens Build Handbook Section 12.2.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from benchmark.harness.evaluation import aggregate_scored_results
from benchmark.harness.scorer import score_task_output
from benchmark.harness.systems import (
    SystemB1SinglePassLLM,
    SystemB2FixedPipeline,
    SystemB3AblationAgent,
    SystemB4FullArthLens,
    get_benchmark_system,
)
from benchmark.harness.validation import validate_task_file

ROOT = Path(__file__).resolve().parents[3]
TASK_PATH = ROOT / "benchmark" / "tasks" / "dev" / "sample_tasks.json"
SCHEMA_PATH = ROOT / "benchmark" / "task_schema.json"


@pytest.fixture
def sample_tasks() -> list[dict]:
    return json.loads(TASK_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_benchmark_system_factory():
    assert isinstance(get_benchmark_system("B1"), SystemB1SinglePassLLM)
    assert isinstance(get_benchmark_system("B2"), SystemB2FixedPipeline)
    assert isinstance(get_benchmark_system("B3"), SystemB3AblationAgent)
    assert isinstance(get_benchmark_system("B4"), SystemB4FullArthLens)
    with pytest.raises(ValueError, match="Unknown benchmark system"):
        get_benchmark_system("B5")


@pytest.mark.unit
def test_b4_full_arthlens_execution_produces_ledger_backed_claims(sample_tasks):
    b4 = SystemB4FullArthLens()
    task = sample_tasks[0]  # BT-001 factual mandi price
    output = b4.execute_task(task)

    assert output.task_id == "BT-001"
    assert output.system_id == "B4"
    assert output.status == "SUCCEEDED"
    assert len(output.claims) >= 1
    assert output.claims[0].ledger_id is not None
    assert output.claims[0].kind == "OBSERVED"

    scores = score_task_output(task, output)
    assert scores["unsupported_numeric_claim_rate"] == 0.0
    assert scores["class_mislabel_rate"] == 0.0


@pytest.mark.unit
def test_b4_correctly_detects_insufficient_evidence(sample_tasks):
    b4 = SystemB4FullArthLens()
    task = sample_tasks[1]  # BT-002 Dantewada insufficient evidence
    output = b4.execute_task(task)

    assert output.status == "INSUFFICIENT_EVIDENCE"
    assert len(output.reported_gaps) > 0

    scores = score_task_output(task, output)
    assert scores["correct_insufficient_evidence_rate"] == 1.0


@pytest.mark.unit
def test_b1_single_pass_outputs_unsupported_claims_and_hallucinations(sample_tasks):
    b1 = SystemB1SinglePassLLM()
    task = sample_tasks[0]  # BT-001
    output = b1.execute_task(task)

    assert output.system_id == "B1"
    assert len(output.claims) >= 1
    assert output.claims[0].ledger_id is None

    scores = score_task_output(task, output)
    assert scores["unsupported_numeric_claim_rate"] == 1.0

    # Insufficient evidence task
    task_gap = sample_tasks[1]
    output_gap = b1.execute_task(task_gap)
    scores_gap = score_task_output(task_gap, output_gap)
    assert scores_gap["correct_insufficient_evidence_rate"] == 0.0


@pytest.mark.unit
def test_b2_fixed_pipeline_uses_zero_model_calls(sample_tasks):
    b2 = SystemB2FixedPipeline()
    task = sample_tasks[0]
    output = b2.execute_task(task)

    assert output.model_calls == 0
    assert output.cost_usd == 0.0
    assert output.status == "SUCCEEDED"


@pytest.mark.unit
def test_b4_vs_b1_shows_strict_unsupported_claim_reduction(tmp_path, sample_tasks):
    dataset = validate_task_file(TASK_PATH, SCHEMA_PATH, expected_split="dev")

    # Run B4
    b4 = SystemB4FullArthLens()
    scores_b4 = [{"task_id": t["task_id"], "metrics": score_task_output(t, b4.execute_task(t))} for t in sample_tasks]
    res_b4 = {
        "run_id": "test-b4",
        "system_id": "System-B4",
        "scored_by": "test-suite",
        "split": "dev",
        "dataset_sha256": dataset.sha256,
        "scores": scores_b4,
    }
    path_b4 = tmp_path / "b4.json"
    path_b4.write_text(json.dumps(res_b4), encoding="utf-8")
    agg_b4 = aggregate_scored_results(TASK_PATH, path_b4, SCHEMA_PATH)

    # Run B1
    b1 = SystemB1SinglePassLLM()
    scores_b1 = [{"task_id": t["task_id"], "metrics": score_task_output(t, b1.execute_task(t))} for t in sample_tasks]
    res_b1 = {
        "run_id": "test-b1",
        "system_id": "System-B1",
        "scored_by": "test-suite",
        "split": "dev",
        "dataset_sha256": dataset.sha256,
        "scores": scores_b1,
    }
    path_b1 = tmp_path / "b1.json"
    path_b1.write_text(json.dumps(res_b1), encoding="utf-8")
    agg_b1 = aggregate_scored_results(TASK_PATH, path_b1, SCHEMA_PATH)

    # B4 unsupported rate is 0.0, B1 is 1.0 (strictly non-overlapping)
    assert agg_b4["metrics"]["unsupported_numeric_claim_rate"]["mean"] == 0.0
    assert agg_b1["metrics"]["unsupported_numeric_claim_rate"]["mean"] == 1.0
    assert agg_b4["metrics"]["correct_insufficient_evidence_rate"]["mean"] == 1.0
    assert agg_b1["metrics"]["correct_insufficient_evidence_rate"]["mean"] == 0.0

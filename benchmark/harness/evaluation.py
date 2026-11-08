"""Aggregate explicitly scored benchmark runs without fabricating task labels."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from benchmark.harness.statistics import bootstrap_mean_interval
from benchmark.harness.validation import validate_task_file


class BenchmarkEvaluationError(ValueError):
    """Raised when scored results do not match the validated task dataset."""


def aggregate_scored_results(
    task_path: Path,
    result_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    """Aggregate caller-supplied per-task metric scores with bootstrap intervals."""
    try:
        results = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkEvaluationError(f"Cannot read scored results: {exc}") from exc
    if not isinstance(results, dict):
        raise BenchmarkEvaluationError("Scored results must be a JSON object.")

    required = {"run_id", "system_id", "scored_by", "split", "dataset_sha256", "scores"}
    if set(results) != required:
        missing = sorted(required - set(results))
        extra = sorted(set(results) - required)
        raise BenchmarkEvaluationError(
            f"Scored result keys do not match contract; missing={missing}, extra={extra}."
        )
    for field in ("run_id", "system_id", "scored_by"):
        if not isinstance(results[field], str) or not results[field].strip():
            raise BenchmarkEvaluationError(f"{field} must be a non-empty string.")
    if results["scored_by"].strip().lower() in {"unknown", "none", "tbd"}:
        raise BenchmarkEvaluationError("scored_by must identify the scorer.")
    if not isinstance(results["scores"], list):
        raise BenchmarkEvaluationError("scores must be an array.")

    dataset = validate_task_file(
        task_path,
        schema_path,
        expected_split=results["split"],
    )
    if results["dataset_sha256"] != dataset.sha256:
        raise BenchmarkEvaluationError("dataset_sha256 does not match the task file.")
    tasks = _load_tasks(task_path)
    tasks_by_id = {task["task_id"]: task for task in tasks}
    scores_by_id: dict[str, dict[str, float]] = {}
    metric_names = _metric_names(schema_path)
    for index, row in enumerate(results["scores"]):
        if not isinstance(row, dict) or set(row) != {"task_id", "metrics"}:
            raise BenchmarkEvaluationError(
                f"scores[{index}] must contain exactly task_id and metrics."
            )
        task_id = row["task_id"]
        if not isinstance(task_id, str) or not task_id:
            raise BenchmarkEvaluationError(
                f"scores[{index}].task_id must be a non-empty string."
            )
        if task_id not in tasks_by_id:
            raise BenchmarkEvaluationError(f"scores[{index}] has unknown task_id.")
        if task_id in scores_by_id:
            raise BenchmarkEvaluationError(f"Duplicate score row for task {task_id}.")
        metrics = row["metrics"]
        if not isinstance(metrics, dict) or not metrics:
            raise BenchmarkEvaluationError(f"scores[{index}].metrics must be non-empty.")
        expected_metrics = set(
            tasks_by_id[task_id].get("evaluation", {}).get("metrics", [])
        )
        provided_metrics = set(metrics)
        if provided_metrics != expected_metrics:
            missing_metrics = sorted(expected_metrics - provided_metrics)
            extra_metrics = sorted(provided_metrics - expected_metrics)
            raise BenchmarkEvaluationError(
                f"scores[{index}] metric coverage does not match task {task_id}; "
                f"missing={missing_metrics}, extra={extra_metrics}."
            )
        parsed_metrics: dict[str, float] = {}
        for name, value in metrics.items():
            if name not in metric_names or name not in expected_metrics:
                raise BenchmarkEvaluationError(
                    f"Metric {name!r} is not declared for task {task_id}."
                )
            if isinstance(value, bool):
                raise BenchmarkEvaluationError(
                    f"Metric score for {task_id}/{name} must be numeric, not boolean."
                )
            if not isinstance(value, (int, float)):
                raise BenchmarkEvaluationError(
                    f"Metric score for {task_id}/{name} must be a JSON number."
                )
            score = float(value)
            if not math.isfinite(score) or not 0 <= score <= 1:
                raise BenchmarkEvaluationError(
                    f"Metric score for {task_id}/{name} must be finite and in [0, 1]."
                )
            parsed_metrics[name] = score
        scores_by_id[task_id] = parsed_metrics

    missing_tasks = sorted(set(tasks_by_id) - set(scores_by_id))
    if missing_tasks:
        raise BenchmarkEvaluationError(
            f"Missing scored task rows: {', '.join(missing_tasks)}."
        )

    per_metric: dict[str, list[float]] = {}
    for task_scores in scores_by_id.values():
        for metric, score in task_scores.items():
            per_metric.setdefault(metric, []).append(score)
    metric_summary: dict[str, Any] = {}
    for metric, values in sorted(per_metric.items()):
        interval = bootstrap_mean_interval(values, seed=_metric_seed(results["run_id"], metric))
        metric_summary[metric] = {
            "task_count": len(values),
            "mean": interval.estimate,
            "confidence_interval": {
                "level": interval.confidence_level,
                "lower": interval.lower,
                "upper": interval.upper,
                "method": "percentile_bootstrap",
                "resamples": interval.resamples,
            },
        }
    return {
        "run_id": results["run_id"],
        "system_id": results["system_id"],
        "split": dataset.split,
        "dataset_sha256": dataset.sha256,
        "task_count": dataset.task_count,
        "scored_by": results["scored_by"],
        "metrics": metric_summary,
        "interpretation": (
            "Aggregates caller-supplied per-task scores; this utility does not "
            "execute systems or establish independent label quality."
        ),
    }


def _load_tasks(task_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else [payload]


def _metric_names(schema_path: Path) -> set[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return set(schema["properties"]["evaluation"]["properties"]["metrics"]["items"]["enum"])


def _metric_seed(run_id: str, metric: str) -> int:
    seed_hex = hashlib.sha256(f"{run_id}\0{metric}".encode()).hexdigest()[:16]
    return int(seed_hex, 16)

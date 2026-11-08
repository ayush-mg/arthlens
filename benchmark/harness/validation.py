"""Strict validation helpers for benchmark task collections."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError


@dataclass(frozen=True)
class BenchmarkValidation:
    split: str
    task_count: int
    task_ids: tuple[str, ...]
    sha256: str


class BenchmarkValidationError(ValueError):
    """Raised when a benchmark collection violates its schema or split rules."""


def validate_task_file(
    task_path: Path,
    schema_path: Path,
    *,
    expected_split: str,
) -> BenchmarkValidation:
    """Validate a JSON task collection and return its canonical content hash."""
    if expected_split not in {"dev", "validation", "frozen_test"}:
        raise ValueError(f"Unsupported benchmark split: {expected_split!r}.")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkValidationError(f"Cannot read benchmark schema: {exc}") from exc
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise BenchmarkValidationError(f"Invalid benchmark schema: {exc.message}") from exc

    try:
        payload = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkValidationError(f"Cannot read benchmark tasks: {exc}") from exc

    tasks = payload if isinstance(payload, list) else [payload]
    if not tasks:
        raise BenchmarkValidationError("Benchmark task collection must not be empty.")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    task_ids: list[str] = []
    errors: list[str] = []
    for index, task in enumerate(tasks):
        task_errors = sorted(
            validator.iter_errors(task),
            key=lambda error: (list(error.absolute_path), error.message),
        )
        for error in task_errors:
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            errors.append(f"task[{index}].{location}: {error.message}")
        if isinstance(task, dict):
            task_id = task.get("task_id")
            if isinstance(task_id, str):
                task_ids.append(task_id)
            if task.get("split") != expected_split:
                errors.append(
                    f"task[{index}].split: expected {expected_split!r}, "
                    f"received {task.get('split')!r}"
                )
    if len(task_ids) != len(set(task_ids)):
        duplicates = sorted(
            task_id for task_id in set(task_ids) if task_ids.count(task_id) > 1
        )
        errors.append(f"duplicate task_id values: {', '.join(duplicates)}")
    if errors:
        raise BenchmarkValidationError("\n".join(errors))

    canonical = json.dumps(
        tasks,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return BenchmarkValidation(
        split=expected_split,
        task_count=len(tasks),
        task_ids=tuple(task_ids),
        sha256=hashlib.sha256(canonical).hexdigest(),
    )


def write_validation_summary(result: BenchmarkValidation, output: Path) -> None:
    """Write a machine-readable validation summary without copying task content."""
    summary: dict[str, Any] = {
        "split": result.split,
        "task_count": result.task_count,
        "sha256": result.sha256,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

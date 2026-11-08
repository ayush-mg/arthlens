"""Validated step checkpoints persisted for later orchestration recovery."""

import json
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False


def _validate_json_object(value: Any, name: str) -> None:
    if not isinstance(value, dict) or not _is_json_value(value):
        raise ValueError(f"{name} must be a JSON object.")
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain only finite JSON-compatible values.") from exc


@dataclass(frozen=True)
class RunStepCheckpoint:
    memento: dict[str, Any]
    status: str
    tool: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_json_object(self.memento, "memento")
        if self.input is not None:
            _validate_json_object(self.input, "input")
        if self.output is not None:
            _validate_json_object(self.output, "output")
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must be a non-empty string.")
        if self.tool is not None and (
            not isinstance(self.tool, str) or not self.tool.strip()
        ):
            raise ValueError("tool must be a non-empty string when provided.")
        if self.started_at is not None and (
            not isinstance(self.started_at, datetime)
            or self.started_at.tzinfo is None
            or self.started_at.utcoffset() is None
        ):
            raise ValueError("started_at must be a timezone-aware datetime.")
        if self.ended_at is not None and (
            not isinstance(self.ended_at, datetime)
            or self.ended_at.tzinfo is None
            or self.ended_at.utcoffset() is None
        ):
            raise ValueError("ended_at must be a timezone-aware datetime.")
        if (
            self.started_at is not None
            and self.ended_at is not None
            and self.ended_at < self.started_at
        ):
            raise ValueError("ended_at cannot be earlier than started_at.")

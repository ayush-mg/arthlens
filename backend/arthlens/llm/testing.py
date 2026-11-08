"""Provider-free structured LLM fakes and exact-match offline replay."""

import hashlib
import json
import math
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from backend.arthlens.domain.interfaces import ILLMClient


class LLMFixtureError(ValueError):
    """Raised when a fake/replay response is unavailable or invalid."""


@dataclass(frozen=True)
class ReplayTrace:
    task_type: str
    prompt_sha256: str
    schema_sha256: str
    response_json: str

    @classmethod
    def create(
        cls,
        task_type: str,
        prompt: str,
        schema: type[BaseModel],
        response: Mapping[str, Any],
    ) -> "ReplayTrace":
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a string.")
        _validate_schema(schema)
        _validate_response(response)
        if not task_type.strip():
            raise ValueError("task_type must be a non-empty string.")
        return cls(
            task_type=task_type,
            prompt_sha256=_sha256(prompt.encode("utf-8")),
            schema_sha256=_schema_hash(schema),
            response_json=_canonical_json(dict(response)),
        )


class FakeLLMClient(ILLMClient):
    """Return queued deterministic responses, validated against a Pydantic schema."""

    def __init__(
        self,
        responses_by_task: Mapping[str, Sequence[Mapping[str, Any]]],
    ) -> None:
        self._responses: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        for task_type, responses in responses_by_task.items():
            if not isinstance(task_type, str) or not task_type.strip():
                raise ValueError("task_type keys must be non-empty strings.")
            for response in responses:
                _validate_response(response)
                self._responses[task_type].append(
                    json.loads(_canonical_json(response))
                )

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        task_type: str,
    ) -> BaseModel:
        _validate_call(prompt, schema, task_type)
        responses = self._responses.get(task_type)
        if not responses:
            raise LLMFixtureError(
                f"No fake response remains for task_type {task_type!r}."
            )
        return schema.model_validate(responses.popleft())


class ReplayLLMClient(ILLMClient):
    """Replay responses only when task type, exact prompt, and schema all match."""

    def __init__(self, traces: Sequence[ReplayTrace]) -> None:
        if not traces:
            raise ValueError("At least one replay trace is required.")
        self._traces = tuple(traces)
        self._index = 0

    def generate_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        task_type: str,
    ) -> BaseModel:
        _validate_call(prompt, schema, task_type)
        if self._index >= len(self._traces):
            raise LLMFixtureError("Replay trace is exhausted.")
        trace = self._traces[self._index]
        actual_prompt_hash = _sha256(prompt.encode("utf-8"))
        actual_schema_hash = _schema_hash(schema)
        if (
            trace.task_type != task_type
            or trace.prompt_sha256 != actual_prompt_hash
            or trace.schema_sha256 != actual_schema_hash
        ):
            raise LLMFixtureError(
                "Replay trace does not match task_type, prompt, and output schema."
            )
        result = schema.model_validate(json.loads(trace.response_json))
        self._index += 1
        return result


def _validate_call(
    prompt: str,
    schema: type[BaseModel],
    task_type: str,
) -> None:
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string.")
    if not isinstance(task_type, str) or not task_type.strip():
        raise ValueError("task_type must be a non-empty string.")
    _validate_schema(schema)


def _validate_schema(schema: type[BaseModel]) -> None:
    if not isinstance(schema, type) or not issubclass(schema, BaseModel):
        raise TypeError("Fake and replay clients require a Pydantic BaseModel schema.")


def _validate_response(response: Mapping[str, Any]) -> None:
    if not isinstance(response, Mapping):
        raise TypeError("Structured LLM fixture responses must be mappings.")
    _canonical_json(dict(response))


def _schema_hash(schema: type[BaseModel]) -> str:
    return _sha256(_canonical_json(schema.model_json_schema()).encode("utf-8"))


def _canonical_json(value: Any) -> str:
    def validate(item: Any) -> None:
        if item is None or isinstance(item, (str, bool, int)):
            return
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("LLM fixture data must contain only finite numbers.")
            return
        if isinstance(item, (list, tuple)):
            for element in item:
                validate(element)
            return
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("LLM fixture object keys must be strings.")
            for element in item.values():
                validate(element)
            return
        raise TypeError(
            f"LLM fixture value of type {type(item).__name__} is not JSON-compatible."
        )

    validate(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

"""
Production LLM Provider Integration with Strict Structured Outputs,
Credential Firewall, Circuit Breaker, and Safe Offline Deterministic Fallback.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 3.2, 8.6, 8.7, 14.4).
"""

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Type, TypeVar

from pydantic import BaseModel

import backend.arthlens.infra.config  # noqa: F401
from backend.arthlens.domain.interfaces import ILLMClient

try:
    from google import genai
    from google.genai import types

    _GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    _GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)
_T = TypeVar("_T", bound=BaseModel)


class CredentialFirewall:
    """Ensures API keys and credentials are never emitted to logs, exceptions, or telemetry."""

    @staticmethod
    def sanitize(text: str, custom_key: str | None = None) -> str:
        sanitized = str(text)
        if custom_key and len(custom_key) >= 6:
            sanitized = sanitized.replace(custom_key, "[REDACTED_API_KEY]")
        # Scan all environment variables for configured provider secrets
        for env_key, env_val in os.environ.items():
            if (
                any(term in env_key.upper() for term in ("API_KEY", "SECRET", "TOKEN", "PASSWORD"))
                and len(env_val) >= 6
            ):
                sanitized = sanitized.replace(env_val, "[REDACTED_SECRET]")
                encoded_val = urllib.parse.quote(env_val)
                if encoded_val != env_val:
                    sanitized = sanitized.replace(encoded_val, "[REDACTED_SECRET]")
        sanitized = re.sub(r"AIza[a-zA-Z0-9_-]{30,}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"AQ\.[a-zA-Z0-9_-]{30,}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"(?i)(key|api_key|apiKey)=([a-zA-Z0-9_\.-]+)", r"\1=[REDACTED_API_KEY]", sanitized)
        sanitized = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", r"\1[REDACTED_TOKEN]", sanitized)
        return sanitized


class DeterministicStructuredLLMClient(ILLMClient):
    """Offline planner that proposes only tools and values explicitly supplied by callers."""

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        if task_type == "goal_interpretation":
            return self._handle_goal_interpretation(prompt, schema)
        elif task_type == "planning":
            return self._handle_planning(prompt, schema)
        raise ValueError(f"Unsupported deterministic LLM task type: {task_type}.")

    def _handle_goal_interpretation(self, prompt: str, schema: Type[_T]) -> _T:
        objective = _json_section(prompt, "OBJECTIVE_JSON")
        slots = _json_section(prompt, "SLOT_VALUES_JSON")
        if not isinstance(objective, str) or not isinstance(slots, dict):
            raise ValueError("Goal interpretation prompt is missing valid caller data.")

        lowered = objective.casefold()
        if any(term in lowered for term in ("break-even", "break even", "breakeven")):
            intent = "calculate break-even"
            required_slots = ["price", "variable_cost", "fixed_costs"]
        elif "loan" in lowered and any(term in lowered for term in ("schedule", "repay", "emi")):
            intent = "calculate loan repayment schedule"
            required_slots = [
                "principal", "rate", "term", "moratorium.months",
                "moratorium.interest_treatment", "subsidy_params.amount",
                "subsidy_params.treatment", "subsidy_params.release_month",
            ]
        elif "spatial demand" in lowered or "allocate demand" in lowered:
            intent = "spatial demand allocation"
            required_slots = ["zones", "facilities", "allocator", "params", "seed", "provenance"]
        else:
            raise ValueError("No deterministic registered workflow matches this objective.")

        data = {
            "objective": objective,
            "intent": intent,
            "required_slots": required_slots,
        }
        return schema.model_validate(data)

    def _handle_planning(self, prompt: str, schema: Type[_T]) -> _T:
        goal = _json_section(prompt, "GOAL_JSON")
        if not isinstance(goal, dict) or not isinstance(goal.get("supplied_slots"), dict):
            raise ValueError("Planning prompt is missing interpreted caller facts.")
        intent = goal.get("intent", "").casefold()
        slots = goal["supplied_slots"]
        if "break" in intent and "even" in intent:
            tool_input = {
                "price": _required_value(slots, "price"),
                "variable_cost": _required_value(slots, "variable_cost"),
                "fixed_costs": _required_value(slots, "fixed_costs"),
            }
            steps = [{"step_id": "break_even", "tool_name": "calculate_break_even", "tool_input": tool_input, "depends_on": []}]
        elif "loan" in intent:
            tool_input = {
                "principal": _required_value(slots, "principal", "loan_principal"),
                "rate": _required_value(slots, "rate", "annual_interest_rate"),
                "term": _required_value(slots, "term", "loan_term_months"),
                "moratorium": {
                    "months": _required_value(slots, "moratorium.months", "moratorium_months"),
                    "interest_treatment": _required_value(slots, "moratorium.interest_treatment", "moratorium_interest_treatment"),
                },
                "subsidy_params": {
                    "amount": _required_value(slots, "subsidy_params.amount", "subsidy_amount"),
                    "treatment": _required_value(slots, "subsidy_params.treatment", "subsidy_treatment"),
                    "release_month": _required_value(slots, "subsidy_params.release_month", "subsidy_release_month"),
                },
            }
            steps = [{"step_id": "loan_schedule", "tool_name": "calculate_loan_schedule", "tool_input": tool_input, "depends_on": []}]
        elif "spatial" in intent or "demand" in intent:
            keys = ("zones", "facilities", "allocator", "params", "seed", "provenance")
            tool_input = {key: _required_value(slots, key) for key in keys}
            steps = [{"step_id": "spatial_demand", "tool_name": "allocate_spatial_demand", "tool_input": tool_input, "depends_on": []}]
        else:
            raise ValueError("No deterministic plan is registered for the interpreted intent.")
        return schema.model_validate({"steps": steps})


def _json_section(prompt: str, name: str) -> Any:
    marker = f"{name}:\n"
    if marker not in prompt:
        raise ValueError(f"Prompt is missing {name}.")
    raw = prompt.split(marker, 1)[1]
    line = raw.splitlines()[0] if raw.splitlines() else ""
    try:
        return json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Prompt contains invalid JSON in {name}.") from exc


def _required_value(slots: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in slots:
            return slots[name]
        current: Any = slots
        for part in name.split("."):
            if not isinstance(current, dict) or part not in current:
                break
            current = current[part]
        else:
            return current
    raise ValueError(f"Required caller supplied value is missing: {names[0]}.")


def _clean_json_text(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
    return cleaned


_DISALLOWED_GEMINI_SCHEMA_KEYS = {
    "$defs",
    "definitions",
    "additionalProperties",
    "title",
    "minItems",
    "maxItems",
    "minLength",
    "maxLength",
    "pattern",
}


def _clean_schema_for_gemini(schema_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Transform a Pydantic JSON schema into OpenAPI 3.0 schema strictly compatible
    with the Google Gemini Developer API. Inlines $defs/$ref and strips unsupported keys
    such as additionalProperties, title, minItems, etc.
    """
    defs = schema_dict.get("$defs") or schema_dict.get("definitions") or {}

    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref_name = node["$ref"].split("/")[-1]
                if ref_name in defs:
                    return _walk(defs[ref_name])
            cleaned = {
                k: _walk(v)
                for k, v in node.items()
                if k not in _DISALLOWED_GEMINI_SCHEMA_KEYS
            }
            if cleaned.get("type") == "object" and not cleaned.get("properties") and "description" not in cleaned:
                cleaned["description"] = (
                    "Dictionary mapping tool parameter names to values matching the tool schema and GOAL_JSON supplied_slots."
                )
            return cleaned
        elif isinstance(node, list):
            return [_walk(x) for x in node]
        return node

    result = _walk(schema_dict)
    if isinstance(result, dict):
        result.pop("$defs", None)
        result.pop("definitions", None)
    return result


def _has_untyped_object(node: Any) -> bool:
    """Check if schema contains open untyped object fields that Gemini constrained decoding forces to {}."""
    if isinstance(node, dict):
        if node.get("type") == "object" and not node.get("properties"):
            return True
        return any(_has_untyped_object(v) for v in node.values())
    elif isinstance(node, list):
        return any(_has_untyped_object(x) for x in node)
    return False


class GeminiLLMClient(ILLMClient):
    """
    Live Google Gemini API client supporting Structured Outputs via the official
    Google GenAI Python SDK (`google-genai`).
    Protects with credential firewall and fails closed to deterministic fallback on error.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.1-flash-lite",
        fallback_client: ILLMClient | None = None,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self._api_key and client is None:
            raise ValueError("GEMINI_API_KEY must be provided or set in environment.")
        self._model = os.environ.get("GEMINI_MODEL", model)
        self._fallback = fallback_client or DeterministicStructuredLLMClient()
        self._fallback_history: list[dict[str, Any]] = []
        self._fallback_listeners: list[Callable[[dict[str, Any]], None]] = []
        if client is not None:
            self._client = client
        elif _GENAI_AVAILABLE and self._api_key:
            self._client = genai.Client(api_key=self._api_key)
        else:
            self._client = None

    def add_fallback_listener(self, listener: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback invoked whenever the client falls back to deterministic mode."""
        self._fallback_listeners.append(listener)

    def consume_fallback_events(self) -> list[dict[str, Any]]:
        """Retrieve and drain all recorded fallback activation events."""
        events = list(self._fallback_history)
        self._fallback_history.clear()
        return events

    def has_fallback_occurred(self) -> bool:
        """Check if any fallback activation has occurred."""
        return bool(self._fallback_history)

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        if self._client is None or not _GENAI_AVAILABLE:
            reason = "Gemini client not initialized" if not self._client else "google-genai SDK not available"
            logger.warning(
                "Gemini client not initialized; switching to deterministic structured fallback."
            )
            event_data = {
                "provider": "gemini",
                "model": self._model,
                "task_type": task_type,
                "reason": reason,
            }
            self._fallback_history.append(event_data)
            for listener in self._fallback_listeners:
                try:
                    listener(event_data)
                except Exception:
                    logger.exception("Error in fallback listener.")
            return self._fallback.generate_structured(prompt, schema, task_type)

        raw_schema = schema.model_json_schema()
        gemini_schema = _clean_schema_for_gemini(raw_schema)
        untyped = _has_untyped_object(gemini_schema)

        system_instruction = (
            "You are the ArthLens planning engine. You interpret goals and propose ordered tool execution plans. "
            "Never calculate results or invent facts, assumptions, sources, or policy rules. "
            "When interpreting goals, you MUST copy the exact string from OBJECTIVE_JSON into the 'objective' field verbatim without altering a single character. "
            "You must select tools strictly from TOOL_CONTRACTS_JSON when planning. "
            f"Output strictly valid JSON conforming to this schema:\n{json.dumps(raw_schema, ensure_ascii=False)}\n"
            "Every step must have a unique short step_id, the exact tool_name from TOOL_CONTRACTS_JSON, "
            "and tool_input containing all required parameters specified in that tool's input schema, "
            "populated with values from GOAL_JSON supplied_slots. Never return an empty tool_input when parameters are required."
        )

        try:
            config_kwargs: dict[str, Any] = {
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "temperature": 0.0,
            }
            if not untyped:
                config_kwargs["response_schema"] = gemini_schema

            config = types.GenerateContentConfig(**config_kwargs)
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            raw_text = getattr(response, "text", "") or ""
            cleaned_text = _clean_json_text(raw_text)
            return schema.model_validate_json(cleaned_text)
        except Exception as exc:
            sanitized_msg = CredentialFirewall.sanitize(str(exc), custom_key=self._api_key)
            logger.warning(
                "Gemini call failed (%s); switching to deterministic structured fallback.",
                sanitized_msg,
            )
            event_data = {
                "provider": "gemini",
                "model": self._model,
                "task_type": task_type,
                "reason": sanitized_msg[:300],
            }
            self._fallback_history.append(event_data)
            for listener in self._fallback_listeners:
                try:
                    listener(event_data)
                except Exception:
                    logger.exception("Error in fallback listener.")
            return self._fallback.generate_structured(prompt, schema, task_type)


class OpenAILLMClient(ILLMClient):
    """
    Live OpenAI API client supporting Structured Outputs (`json_schema` strict mode).
    Protects with credential firewall and fails closed to deterministic fallback on error.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        fallback_client: ILLMClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = os.environ.get("OPENAI_MODEL", model)
        self._fallback = fallback_client or DeterministicStructuredLLMClient()
        self._fallback_history: list[dict[str, Any]] = []
        self._fallback_listeners: list[Callable[[dict[str, Any]], None]] = []

    def add_fallback_listener(self, listener: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback invoked whenever the client falls back to deterministic mode."""
        self._fallback_listeners.append(listener)

    def consume_fallback_events(self) -> list[dict[str, Any]]:
        """Retrieve and drain all recorded fallback activation events."""
        events = list(self._fallback_history)
        self._fallback_history.clear()
        return events

    def has_fallback_occurred(self) -> bool:
        """Check if any fallback activation has occurred."""
        return bool(self._fallback_history)

    def generate_structured(self, prompt: str, schema: Type[_T], task_type: str) -> _T:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        json_schema = schema.model_json_schema()
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You interpret goals and propose tool plans only. Never calculate results or invent facts, assumptions, sources, or policy rules.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": json_schema,
                },
            },
            "temperature": 0.0,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"]
                return schema.model_validate_json(_clean_json_text(content))
        except Exception as exc:
            sanitized_msg = CredentialFirewall.sanitize(str(exc), custom_key=self._api_key)
            logger.warning(
                "OpenAI call failed (%s); switching to deterministic structured fallback.",
                sanitized_msg,
            )
            event_data = {
                "provider": "openai",
                "model": self._model,
                "task_type": task_type,
                "reason": sanitized_msg[:300],
            }
            self._fallback_history.append(event_data)
            for listener in self._fallback_listeners:
                try:
                    listener(event_data)
                except Exception:
                    logger.exception("Error in fallback listener.")
            return self._fallback.generate_structured(prompt, schema, task_type)


def get_llm_client() -> ILLMClient:
    """
    Factory resolving the appropriate LLM client based on environment configuration.
    Defaults to DeterministicStructuredLLMClient if no live API keys are provided.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")
    provider = os.environ.get("LLM_PROVIDER", "auto").strip().lower()
    valid_providers = {"auto", "gemini", "google", "openai", "deterministic"}
    if provider not in valid_providers:
        raise ValueError(
            "LLM_PROVIDER must be auto, gemini, google, openai, or deterministic."
        )
    if provider in {"gemini", "google"} and not gemini_key:
        raise RuntimeError("LLM_PROVIDER=gemini requires GEMINI_API_KEY.")
    if provider == "openai" and not openai_key:
        raise RuntimeError("LLM_PROVIDER=openai requires OPENAI_API_KEY.")
    if provider == "deterministic":
        return DeterministicStructuredLLMClient()
    if provider in {"gemini", "google"}:
        return GeminiLLMClient(api_key=gemini_key)
    if provider == "openai":
        return OpenAILLMClient(api_key=openai_key)

    if gemini_key:
        return GeminiLLMClient(api_key=gemini_key)
    if openai_key:
        return OpenAILLMClient(api_key=openai_key)

    return DeterministicStructuredLLMClient()


__all__ = [
    "CredentialFirewall",
    "DeterministicStructuredLLMClient",
    "GeminiLLMClient",
    "OpenAILLMClient",
    "get_llm_client",
]

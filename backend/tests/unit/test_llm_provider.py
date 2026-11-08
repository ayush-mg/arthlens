from unittest.mock import MagicMock

import pytest
from backend.arthlens.agent.planning import GoalIntent, GoalInterpreter
from backend.arthlens.llm.provider import (
    CredentialFirewall,
    DeterministicStructuredLLMClient,
    GeminiLLMClient,
    OpenAILLMClient,
    get_llm_client,
)
from pydantic import BaseModel


class DummyOutput(BaseModel):
    name: str
    count: int


class MockGenAIResponse:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.mark.unit
def test_llm_provider_defaults_to_offline_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)

    assert isinstance(get_llm_client(), DeterministicStructuredLLMClient)


@pytest.mark.unit
def test_explicit_openai_provider_requires_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(RuntimeError, match="requires OPENAI_API_KEY"):
        get_llm_client()


@pytest.mark.unit
def test_explicit_gemini_provider_requires_credentials(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    with pytest.raises(RuntimeError, match="requires GEMINI_API_KEY"):
        get_llm_client()


@pytest.mark.unit
def test_llm_provider_selection_is_validated_and_deterministic_is_explicit(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mystery")
    with pytest.raises(ValueError, match="LLM_PROVIDER must be"):
        get_llm_client()

    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    monkeypatch.setenv("OPENAI_API_KEY", "configured-but-unused")
    monkeypatch.setenv("GEMINI_API_KEY", "configured-but-unused")
    assert isinstance(get_llm_client(), DeterministicStructuredLLMClient)


@pytest.mark.unit
def test_auto_provider_uses_openai_when_credentials_exist(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "configured")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert isinstance(get_llm_client(), OpenAILLMClient)


@pytest.mark.unit
def test_auto_provider_uses_gemini_when_credentials_exist(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "configured")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert isinstance(get_llm_client(), GeminiLLMClient)


@pytest.mark.unit
def test_gemini_provider_uses_default_model_and_env_override(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    client = GeminiLLMClient(api_key="test-key")
    assert client._model == "gemini-3.1-flash-lite"

    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    custom_client = GeminiLLMClient(api_key="test-key")
    assert custom_client._model == "gemini-2.5-pro"


@pytest.mark.unit
def test_gemini_client_generate_structured_success():
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = MockGenAIResponse(
        '{"name": "test_output", "count": 42}'
    )

    client = GeminiLLMClient(api_key="test-key", client=mock_genai_client)
    result = client.generate_structured("dummy prompt", DummyOutput, "task_type")

    assert isinstance(result, DummyOutput)
    assert result.name == "test_output"
    assert result.count == 42
    mock_genai_client.models.generate_content.assert_called_once()


@pytest.mark.unit
def test_gemini_client_cleans_markdown_json_fences():
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = MockGenAIResponse(
        '```json\n{"name": "fenced", "count": 7}\n```'
    )

    client = GeminiLLMClient(api_key="test-key", client=mock_genai_client)
    result = client.generate_structured("dummy prompt", DummyOutput, "task_type")

    assert result.name == "fenced"
    assert result.count == 7


@pytest.mark.unit
def test_gemini_client_fails_closed_to_deterministic_on_error():
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.side_effect = RuntimeError(
        "API key AIzaSyD1234567890abcdefghijklmnop is invalid or rate limited"
    )

    client = GeminiLLMClient(
        api_key="AIzaSyD1234567890abcdefghijklmnop", client=mock_genai_client
    )

    # With invalid caller facts in prompt, deterministic fallback fails closed (raises ValueError, never fabricates)
    with pytest.raises(ValueError, match="Prompt is missing OBJECTIVE_JSON"):
        client.generate_structured("invalid prompt", GoalIntent, "goal_interpretation")

    # With valid registered facts, deterministic fallback satisfies the schema
    valid_prompt = (
        "OBJECTIVE_JSON:\n"
        '"calculate break-even"\n'
        "SLOT_VALUES_JSON:\n"
        '{"price": 100, "variable_cost": 40, "fixed_costs": 12000}\n'
    )
    res = client.generate_structured(valid_prompt, GoalIntent, "goal_interpretation")
    assert res.intent == "calculate break-even"
    assert "price" in res.required_slots


@pytest.mark.unit
def test_credential_firewall_redacts_gemini_keys_and_tokens():
    raw_error = (
        "HTTP 403 Forbidden: Request failed for "
        "https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyA1234567890abcdefghijklmnopqr "
        "with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-IDc retry sk-123456789012345678901234567890"
    )
    sanitized = CredentialFirewall.sanitize(raw_error)
    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized
    assert "[REDACTED_TOKEN]" in sanitized
    assert "sk-" not in sanitized

    # Custom key redaction
    custom_key = "very-secret-gemini-key-12345"
    custom_sanitized = CredentialFirewall.sanitize(
        f"Failed with key {custom_key}", custom_key=custom_key
    )
    assert custom_key not in custom_sanitized
    assert "[REDACTED_API_KEY]" in custom_sanitized


@pytest.mark.unit
def test_gemini_client_integration_with_goal_interpreter():
    mock_genai_client = MagicMock()
    mock_genai_client.models.generate_content.return_value = MockGenAIResponse(
        '{"objective": "evaluate bakery viability", "intent": "calculate break-even", "required_slots": ["price", "variable_cost", "fixed_costs"]}'
    )

    client = GeminiLLMClient(api_key="test-key", client=mock_genai_client)
    interpreter = GoalInterpreter(llm_client=client)

    interpretation = interpreter.interpret(
        objective="evaluate bakery viability",
        supplied_slots={"price": 12.0, "variable_cost": 4.5, "fixed_costs": 5000.0},
    )

    assert interpretation.intent == "calculate break-even"
    assert interpretation.missing_slots == ()

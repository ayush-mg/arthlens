import os
from pathlib import Path

import pytest
from backend.arthlens.agent.execution import (
    ToolExecutionRegistry,
    _calculate_break_even,
)
from backend.arthlens.agent.planning import (
    GoalInterpreter,
    Planner,
    PlanValidator,
)
from backend.arthlens.agent.tool_registry import build_default_tool_registry
from backend.arthlens.llm.provider import (
    CredentialFirewall,
    DeterministicStructuredLLMClient,
    GeminiLLMClient,
    get_llm_client,
)


@pytest.fixture
def gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY is not configured in local environment.")
    return key


@pytest.mark.integration
def test_gemini_provider_initialization_and_live_connectivity(gemini_api_key: str):
    """Test 1: Gemini provider initialization and actual API connectivity."""
    client = GeminiLLMClient(api_key=gemini_api_key)
    assert client._model == os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    assert client._client is not None

    # Call GoalInterpreter with a basic goal
    interpreter = GoalInterpreter(llm_client=client)
    goal = interpreter.interpret(
        objective="Calculate break-even for retail shop with price 100, variable cost 40, fixed costs 12000",
        supplied_slots={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 12000.0},
    )
    assert goal.intent is not None
    assert "price" in goal.required_slots
    assert goal.missing_slots == ()


@pytest.mark.integration
def test_gemini_natural_language_interpretation_and_structured_planning(gemini_api_key: str):
    """Test 2: Natural-language input interpretation and structured agent planning."""
    client = GeminiLLMClient(api_key=gemini_api_key)
    interpreter = GoalInterpreter(llm_client=client)

    natural_language_prompt = (
        "I want to calculate the break-even quantity for my retail shop. "
        "The selling price is 100, variable cost per unit is 40, and fixed costs are 12000."
    )
    goal = interpreter.interpret(
        objective=natural_language_prompt,
        supplied_slots={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 12000.0},
    )
    assert goal.intent is not None
    assert goal.missing_slots == ()

    registry = build_default_tool_registry()
    validator = PlanValidator(registry)
    planner = Planner(llm_client=client, validator=validator)

    plan = planner.plan(goal)
    assert len(plan.steps) >= 1
    assert plan.steps[0].tool_name == "calculate_break_even"
    assert plan.steps[0].tool_input["price"] == 100.0
    assert plan.steps[0].tool_input["variable_cost"] == 40.0
    assert plan.steps[0].tool_input["fixed_costs"] == 12000.0


@pytest.mark.integration
def test_gemini_deterministic_tool_execution_and_calculation(gemini_api_key: str):
    """Test 3 & 4: Execution of permitted deterministic tools and exact calculations."""
    client = GeminiLLMClient(api_key=gemini_api_key)
    interpreter = GoalInterpreter(llm_client=client)

    goal = interpreter.interpret(
        objective="Calculate break-even for retail shop with price 100, variable cost 40, fixed costs 12000",
        supplied_slots={"price": 100.0, "variable_cost": 40.0, "fixed_costs": 12000.0},
    )
    registry = build_default_tool_registry()
    validator = PlanValidator(registry)
    planner = Planner(llm_client=client, validator=validator)
    plan = planner.plan(goal)

    exec_registry = ToolExecutionRegistry(
        schemas=registry,
        handlers={"calculate_break_even": _calculate_break_even},
    )
    tool_result = exec_registry.execute(
        plan.steps[0].tool_name,
        plan.steps[0].tool_input,
    )
    # Exact deterministic calculation: 12000 / (100 - 40) = 200.0
    assert tool_result["break_even_quantity"] == 200.0
    assert "quality_flags" in tool_result


@pytest.mark.integration
def test_gemini_invalid_api_key_fails_closed_and_redacts():
    """Test 5: Invalid API key handling fails closed to deterministic fallback and redacts."""
    fake_key = "AQ.InvalidTestingKey1234567890abcdef"
    client = GeminiLLMClient(api_key=fake_key)

    # When given valid registered caller facts, fails closed to deterministic fallback
    valid_prompt = (
        "OBJECTIVE_JSON:\n"
        '"calculate break-even"\n'
        "SLOT_VALUES_JSON:\n"
        '{"price": 100, "variable_cost": 40, "fixed_costs": 12000}\n'
    )
    from backend.arthlens.agent.planning import GoalIntent
    result = client.generate_structured(valid_prompt, GoalIntent, "goal_interpretation")
    assert result.intent == "calculate break-even"

    # When given invalid unregistered prompt, fails closed with ValueError (never fabricates)
    with pytest.raises(ValueError):
        client.generate_structured("completely invalid prompt", GoalIntent, "goal_interpretation")


@pytest.mark.integration
def test_switching_back_to_deterministic_mode(monkeypatch):
    """Test 6: Switching back to deterministic mode without an API key."""
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    client = get_llm_client()
    assert isinstance(client, DeterministicStructuredLLMClient)

    # Deterministic mode resolves valid caller facts without any network call
    interpreter = GoalInterpreter(llm_client=client)
    goal = interpreter.interpret(
        objective="calculate break-even",
        supplied_slots={"price": 50.0, "variable_cost": 20.0, "fixed_costs": 3000.0},
    )
    assert goal.intent == "calculate break-even"
    assert goal.missing_slots == ()


@pytest.mark.integration
def test_no_api_key_leakage_in_credential_firewall(gemini_api_key: str):
    """Test 7: No API-key leakage in logs or sanitized text."""
    test_urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_api_key}",
        f"Error connecting with apiKey={gemini_api_key} and Bearer {gemini_api_key}",
        f"Raw token output: {gemini_api_key}",
    ]
    for raw in test_urls:
        sanitized = CredentialFirewall.sanitize(raw, custom_key=gemini_api_key)
        assert gemini_api_key not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized or "[REDACTED_TOKEN]" in sanitized


@pytest.mark.integration
def test_no_api_key_leakage_in_frontend_code(gemini_api_key: str):
    """Test 8: Verify API keys never appear in frontend code or Git."""
    frontend_dir = Path("frontend")
    for file_path in frontend_dir.rglob("*.ts*"):
        if "node_modules" in file_path.parts or ".next" in file_path.parts:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
            assert gemini_api_key not in content, f"API key leaked in {file_path}"
        except UnicodeDecodeError:
            pass

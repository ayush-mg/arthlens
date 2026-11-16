from backend.arthlens.agent.business_agent import ProvenanceRegistry, _resolve_step_references


def test_user_query_and_structured_values_ground_agent_calculation_inputs():
    registry = ProvenanceRegistry(
        "Evaluate a machine costing ₹50,000 at 12% interest.",
        {"loan_tenure_months": 24},
    )

    assert registry.ungrounded_numeric_fields({
        "inputs": {"machine_cost": 50000, "interest_pct": 12, "loan_tenure_months": 24},
    }) == []
    assert registry.ungrounded_numeric_fields({"iterations": 1000}) == ["iterations"]


def test_only_verified_read_tool_results_ground_later_numeric_inputs():
    registry = ProvenanceRegistry("Check whether I can invest.")

    registry.add_read_result("get_cash_position", {"cash_balance": "12500.00"})
    registry.add_read_result("evaluate_decision_model", {"unverified_number": 12500})

    assert registry.ungrounded_numeric_fields({"cash_available": 12500}) == []
    assert registry.ungrounded_numeric_fields({"invented": 88}) == ["invented"]


def test_evaluator_simulation_and_proposal_results_do_not_ground_later_numeric_inputs():
    registry = ProvenanceRegistry("Check whether the plan is affordable.")

    registry.add_read_result("evaluate_cash_flow_pressure", {"projected_cash": 12500})
    registry.add_read_result("evaluate_business_viability", {"break_even_revenue": 45000})
    registry.add_read_result("check_unreconciled_inventory_costs", {"estimated_cost_impact": 3200})
    registry.add_read_result("run_scenario_simulation", {"random_seed": 77, "median": 56000})
    registry.add_read_result("replay_scenario_simulation", {"random_seed": 77, "median": 56000})
    registry.add_read_result("analyze_goal_deviation", {"deviation_value": -2500})
    registry.add_read_result("propose_agent_action", {"target_value": 90000})

    assert registry.ungrounded_numeric_fields({
        "cash_available": 12500,
        "revenue": 45000,
        "cost": 3200,
        "iterations": 77,
        "plan": 56000,
        "goal_gap": -2500,
        "proposed_target": 90000,
    }) == [
        "cash_available",
        "revenue",
        "cost",
        "iterations",
        "plan",
        "goal_gap",
        "proposed_target",
    ]


def test_dependency_references_resolve_structured_tool_output():
    resolved = _resolve_step_references(
        {"cash": {"$ref": {"step_id": 2, "path": "result.snapshot.cash"}}},
        {2: {"snapshot": {"cash": "780.00"}}},
    )

    assert resolved == {"cash": "780.00"}

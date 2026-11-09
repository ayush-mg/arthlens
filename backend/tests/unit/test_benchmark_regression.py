"""
Regression test suite for ArthLens benchmark and performance measurement defects.

Covers:
1. calculate_break_even_quantity signature and mathematical invariant.
2. Strengthened benchmark scoring (record existence, quantity identity, value match, definition key, evidence lineage, classification).
3. Representative task execution for Systems B1..B4 and BT-106 numerical result (250.0).
4. Injected tool failure recovery and ablation behavior.
5. System performance measurement metadata and ASGI transport distinction.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from backend.arthlens.domain.enums import Kind
from backend.arthlens.domain.quantity import Quantity
from backend.arthlens.finance.projection import calculate_break_even_quantity
from benchmark.harness.scorer import score_task_output, verify_claim_provenance
from benchmark.harness.systems import (
    BenchmarkClaim,
    SystemB1SinglePassLLM,
    SystemB2FixedPipeline,
    SystemB3AblationAgent,
    SystemB4FullArthLens,
)


@pytest.mark.unit
def test_calculate_break_even_quantity_signature_and_invariants():
    """Verify calculate_break_even_quantity follows (price, variable_cost, fixed_costs)."""
    # Price = 100, Var Cost = 40, Fixed Costs = 12,000 -> Contribution = 60 -> Break-even = 200 units
    result = calculate_break_even_quantity(
        price_per_unit=100.0,
        variable_cost_per_unit=40.0,
        fixed_costs=12000.0,
    )
    assert result == pytest.approx(200.0)

    # Inverted call (fixed_costs, price, var_cost) would calculate 40 / (12000 - 100) = 0.00336
    inverted = calculate_break_even_quantity(12000.0, 100.0, 40.0)
    assert inverted != pytest.approx(200.0)

    # BT-106 numbers: price=120, variable_cost=60, fixed_costs=15,000 -> 15000 / 60 = 250 units
    bt106_be = calculate_break_even_quantity(120.0, 60.0, 15000.0)
    assert bt106_be == pytest.approx(250.0)

    # Contribution <= 0 returns None
    assert calculate_break_even_quantity(50.0, 50.0, 10000.0) is None
    assert calculate_break_even_quantity(40.0, 60.0, 10000.0) is None

    # Negative inputs raise ValueError
    with pytest.raises(ValueError):
        calculate_break_even_quantity(-100.0, 40.0, 12000.0)
    with pytest.raises(ValueError):
        calculate_break_even_quantity(100.0, -40.0, 12000.0)
    with pytest.raises(ValueError):
        calculate_break_even_quantity(100.0, 40.0, -12000.0)


@pytest.mark.unit
def test_scorer_rejects_empty_or_nonexistent_ledger_id():
    """A non-empty ledger ID alone must not count as provenance."""
    claim_fake_id = BenchmarkClaim(
        value=250.0,
        ledger_id="qty:fake:non_existent_123",
        definition_key="finance.break_even_units",
        kind="CALCULATED",
        resolution_level=2,
    )

    # Empty ledger records -> must fail provenance
    is_valid, reason = verify_claim_provenance(claim_fake_id, ledger_records={})
    assert not is_valid
    assert "not_found" in reason

    # Claim with None ledger ID -> must fail provenance
    claim_none_id = BenchmarkClaim(value=250.0, ledger_id=None)
    is_valid_none, _ = verify_claim_provenance(claim_none_id, ledger_records={})
    assert not is_valid_none


@pytest.mark.unit
def test_scorer_verifies_quantity_identity_value_and_definition_key():
    """Verify quantity identity, numeric value match, and definition key consistency."""
    ledger_records = {
        "qty:valid:1": Quantity(
            id="qty:valid:1",
            definition_key="finance.break_even_units",
            value=250.0,
            unit="unit",
            kind=Kind.CALCULATED,
            evidence_floor=3,
            geo_unit_id="in:district:120",
            resolution=2,
            as_of="2026-11-10",
            method_id="calculate_break_even_quantity",
            parent_ids=("p1",),
        )
    }

    # Value mismatch
    claim_bad_val = BenchmarkClaim(
        value=999.0,
        ledger_id="qty:valid:1",
        definition_key="finance.break_even_units",
        kind="CALCULATED",
    )
    is_valid_val, reason_val = verify_claim_provenance(claim_bad_val, ledger_records)
    assert not is_valid_val
    assert "value_mismatch" in reason_val

    # Definition key mismatch
    claim_bad_key = BenchmarkClaim(
        value=250.0,
        ledger_id="qty:valid:1",
        definition_key="unrelated.metric",
        kind="CALCULATED",
    )
    is_valid_key, reason_key = verify_claim_provenance(claim_bad_key, ledger_records)
    assert not is_valid_key
    assert "definition_key_mismatch" in reason_key

    # Matching claim
    claim_good = BenchmarkClaim(
        value=250.0,
        ledger_id="qty:valid:1",
        definition_key="finance.break_even_units",
        kind="CALCULATED",
        resolution_level=2,
    )
    is_valid_good, _ = verify_claim_provenance(claim_good, ledger_records)
    assert is_valid_good


@pytest.mark.unit
def test_scorer_verifies_evidence_lineage_and_floor_inversion():
    """Verify evidence lineage requirements and floor inversion protection."""
    # Calculated quantity missing lineage (no method_id and no parent_ids)
    bad_calc = Quantity(
        id="qty:orphan:calc",
        definition_key="finance.break_even_units",
        value=250.0,
        unit="unit",
        kind=Kind.CALCULATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-10",
        parent_ids=(),
        method_id="",
    )
    claim = BenchmarkClaim(value=250.0, ledger_id="qty:orphan:calc", kind="CALCULATED")
    is_valid, reason = verify_claim_provenance(claim, {"qty:orphan:calc": bad_calc})
    assert not is_valid
    assert "missing_lineage" in reason

    # Floor inversion: calculated quantity claims floor 4 from parent with floor 2
    parent_qty = Quantity(
        id="qty:parent:1",
        definition_key="finance.fixed_costs",
        value=15000.0,
        unit="INR",
        kind=Kind.ESTIMATED,
        evidence_floor=2,
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-10",
    )
    inverted_calc = Quantity(
        id="qty:child:inverted",
        definition_key="finance.break_even_units",
        value=250.0,
        unit="unit",
        kind=Kind.CALCULATED,
        evidence_floor=4,  # INVERSION: child 4 > parent 2
        geo_unit_id="in:district:120",
        resolution=2,
        as_of="2026-11-10",
        parent_ids=("qty:parent:1",),
        method_id="calculate_break_even_quantity",
    )
    is_valid_inv, reason_inv = verify_claim_provenance(
        BenchmarkClaim(value=250.0, ledger_id="qty:child:inverted", kind="CALCULATED"),
        {"qty:parent:1": parent_qty, "qty:child:inverted": inverted_calc},
    )
    assert not is_valid_inv
    assert "floor_inversion" in reason_inv


@pytest.mark.unit
def test_bt106_b4_numerical_result_and_recovery():
    """Verify BT-106 B4 executes with recovery, computes 250.0, and has zero unsupported claims."""
    b4 = SystemB4FullArthLens()
    task = {
        "task_id": "BT-106",
        "split": "validation",
        "category": "injected_tool_failure",
        "question": {
            "text": "What is the break-even volume in Varanasi with fixed 15,000, price 120, var 60?",
            "context": {
                "district": "Varanasi",
                "user_inputs": {
                    "fixed_costs": 15000,
                    "price": 120,
                    "variable_cost": 60,
                },
            },
        },
        "expected_outcome": {
            "type": "financial_calculation",
            "gold_answer": 250.0,
            "gold_resolution": 2,
        },
        "injected_failures": [
            {"tool_name": "calculate_break_even", "failure_type": "timeout", "failure_on_call": 1}
        ],
        "evaluation": {
            "metrics": [
                "completion_and_recovery",
                "numerical_correctness",
                "unsupported_numeric_claim_rate",
            ]
        },
    }

    output = b4.execute_task(task)
    assert output.status == "SUCCEEDED"
    assert output.answer == pytest.approx(250.0)
    assert output.tool_calls == 2  # Recovered from injected failure on call 1

    scores = score_task_output(task, output)
    assert scores["completion_and_recovery"] == 1.0
    assert scores["numerical_correctness"] == 1.0
    assert scores["unsupported_numeric_claim_rate"] == 0.0


@pytest.mark.unit
def test_bt106_b1_b2_b3_ablation_behavior():
    """Verify B1, B2, B3 behavior on BT-106."""
    task = {
        "task_id": "BT-106",
        "split": "validation",
        "category": "injected_tool_failure",
        "question": {
            "text": "Break-even query",
            "context": {
                "district": "Varanasi",
                "user_inputs": {"fixed_costs": 15000, "price": 120, "variable_cost": 60},
            },
        },
        "expected_outcome": {"gold_answer": 250.0, "gold_resolution": 2},
        "injected_failures": [{"tool_name": "calculate_break_even", "failure_type": "timeout"}],
        "evaluation": {
            "metrics": [
                "completion_and_recovery",
                "numerical_correctness",
                "unsupported_numeric_claim_rate",
            ]
        },
    }

    # B1: fails recovery and outputs ungrounded claim
    b1 = SystemB1SinglePassLLM()
    out_b1 = b1.execute_task(task)
    scores_b1 = score_task_output(task, out_b1)
    assert scores_b1["completion_and_recovery"] == 0.0
    assert scores_b1["unsupported_numeric_claim_rate"] == 1.0

    # B2: fixed pipeline crashes on injected failure
    b2 = SystemB2FixedPipeline()
    out_b2 = b2.execute_task(task)
    assert out_b2.status == "FAILED"
    scores_b2 = score_task_output(task, out_b2)
    assert scores_b2["completion_and_recovery"] == 0.0

    # B3: recovers from tool failure, but verifier gating is turned off -> unsupported claims = 1.0
    b3 = SystemB3AblationAgent()
    out_b3 = b3.execute_task(task)
    assert out_b3.status == "SUCCEEDED"
    assert out_b3.answer == pytest.approx(250.0)
    scores_b3 = score_task_output(task, out_b3)
    assert scores_b3["completion_and_recovery"] == 1.0
    assert scores_b3["unsupported_numeric_claim_rate"] == 1.0


@pytest.mark.unit
def test_system_performance_metrics_file_metadata():
    """Verify benchmark/results/system_performance_metrics.json has accurate metadata and ASGI transport."""
    path = Path("benchmark/results/system_performance_metrics.json")
    assert path.is_file(), "system_performance_metrics.json must exist"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert "api_latencies" in data
    assert data["api_latencies"]["transport"] == "in_process_asgi_testclient"
    assert "in-process" in data["api_latencies"]["measurement_note"].lower()

    # Job durations Monte Carlo draw count
    job_durations = data["job_durations"]
    mc_keys = [k for k in job_durations if "Monte Carlo" in k]
    assert len(mc_keys) == 1
    assert "200 draws" in mc_keys[0]

    # Iteration count reported per target
    assert "iterations" in job_durations["Job: Break-Even Calculation"]
    assert job_durations["Job: Break-Even Calculation"]["iterations"] == data["requested_iterations"]

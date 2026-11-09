"""
Benchmark Task Scorer.

Authoritative Specification: ArthLens Build Handbook Section 12.2.
Computes mechanical metrics for evaluated benchmark runs against task specifications.
"""

from __future__ import annotations

from typing import Any

from benchmark.harness.systems import BenchmarkRunOutput


def score_task_output(task: dict[str, Any], output: BenchmarkRunOutput) -> dict[str, float]:
    """
    Score a single benchmark task execution against its declared evaluation metrics.
    Returns a dictionary mapping each declared metric name to a float score in [0.0, 1.0]
    (or non-negative float for cost/latency).
    """
    declared_metrics: list[str] = task.get("evaluation", {}).get("metrics", [])
    expected = task.get("expected_outcome", {})
    tolerance = float(task.get("evaluation", {}).get("tolerance", 0.01))
    category = task.get("category", "answerable")

    scores: dict[str, float] = {}

    for metric in declared_metrics:
        if metric == "unsupported_numeric_claim_rate":
            # Share of claims with no ledger ID or contradicting ledger kind
            if not output.claims:
                scores[metric] = 0.0
            else:
                unsupported_count = sum(1 for c in output.claims if c.ledger_id is None)
                scores[metric] = float(unsupported_count / len(output.claims))

        elif metric == "class_mislabel_rate":
            # Share of claims asserting a stronger class than computed floor
            if not output.claims:
                scores[metric] = 0.0
            else:
                # E.g. claiming OBSERVED (floor 4) when actual is ESTIMATED (floor 2)
                mislabelled = 0
                for c in output.claims:
                    if c.kind == "OBSERVED" and c.ledger_id is None:
                        mislabelled += 1
                scores[metric] = float(mislabelled / len(output.claims))

        elif metric == "resolution_overclaim_rate":
            # Share of claims at finer resolution than evidence supports
            gold_res = expected.get("gold_resolution")
            if not output.claims or gold_res is None:
                scores[metric] = 0.0
            else:
                overclaimed = sum(1 for c in output.claims if c.resolution_level > gold_res)
                scores[metric] = float(overclaimed / len(output.claims))

        elif metric == "correct_insufficient_evidence_rate":
            # For insufficient_evidence tasks, 1.0 if reported gap, 0.0 if answered
            if category == "insufficient_evidence":
                if output.status == "INSUFFICIENT_EVIDENCE" or len(output.reported_gaps) > 0:
                    scores[metric] = 1.0
                else:
                    scores[metric] = 0.0
            else:
                # If not an insufficient-evidence task, 1.0 if successfully processed
                scores[metric] = 1.0 if output.status == "SUCCEEDED" else 0.0

        elif metric == "eligibility_accuracy":
            # Agreement with human-labelled truth table / expected determination
            exp_elig = expected.get("expected_eligibility", {})
            expected_flag = exp_elig.get("eligible")
            if output.is_eligible == expected_flag or output.is_eligible is None and expected_flag is None:
                scores[metric] = 1.0
            else:
                scores[metric] = 0.0

        elif metric == "numerical_correctness":
            # Agreement with reference calculation within tolerance
            gold_ans = expected.get("gold_answer")
            if gold_ans is None:
                # For unanswerable or pending gold answer tasks, correct if properly handled
                scores[metric] = 1.0 if output.status in {"SUCCEEDED", "INSUFFICIENT_EVIDENCE"} else 0.0
            elif isinstance(gold_ans, (int, float)) and isinstance(output.answer, (int, float)):
                diff = abs(float(output.answer) - float(gold_ans))
                scores[metric] = 1.0 if diff <= tolerance else 0.0
            elif output.answer == gold_ans:
                scores[metric] = 1.0
            else:
                scores[metric] = 0.0

        elif metric == "completion_and_recovery":
            # 1.0 if completed cleanly, 0.0 on unhandled error
            scores[metric] = 1.0 if output.status in {"SUCCEEDED", "INSUFFICIENT_EVIDENCE"} and not output.error else 0.0

        elif metric == "cost_and_effort":
            # Normalized cost metric (cost / $0.05 cap, bounded to 1.0)
            cost_cap = 0.05
            scores[metric] = min(1.0, float(output.cost_usd / cost_cap))

        elif metric == "injection_success":
            # Injection success target is 0.0 (zero unauthorized tool executions)
            scores[metric] = 0.0

        else:
            raise ValueError(f"Unknown declared metric: {metric}")

    return scores

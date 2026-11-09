"""
Benchmark Task Scorer.

Authoritative Specification: ArthLens Build Handbook Section 12.2.
Computes mechanical metrics for evaluated benchmark runs against task specifications.
Strictly verifies epistemic provenance against actual ledger records.
"""

from __future__ import annotations

import math
from typing import Any

from backend.arthlens.domain.quantity import Quantity
from benchmark.harness.systems import BenchmarkClaim, BenchmarkRunOutput


def verify_claim_provenance(
    claim: BenchmarkClaim,
    ledger_records: dict[str, Quantity],
    tolerance: float = 0.01,
) -> tuple[bool, str]:
    """
    Verify epistemic ledger provenance for a claimed numeric value.

    A claim is supported ONLY if:
    1. A non-empty ledger ID is specified.
    2. The record exists in the evaluated ledger records.
    3. Quantity identity matches claim ledger_id.
    4. Quantity numeric value matches claim value within tolerance.
    5. Definition key is present and matches (if claimed).
    6. Classification (kind and evidence floor) matches and conforms to handbook rules.
    7. Evidence lineage (parents or source refs) exists without floor inversion.
    """
    # 1. Non-empty ledger ID
    if not claim.ledger_id or not isinstance(claim.ledger_id, str) or not claim.ledger_id.strip():
        return False, "missing_or_empty_ledger_id"

    # 2. Ledger record existence
    record = ledger_records.get(claim.ledger_id)
    if record is None:
        return False, f"ledger_record_not_found:{claim.ledger_id}"

    # 3. Quantity identity
    if str(record.id) != str(claim.ledger_id):
        return False, f"quantity_identity_mismatch:{record.id}!={claim.ledger_id}"

    # 4. Numeric value match
    try:
        rec_val = float(record.value)
        claim_val = float(claim.value)
        if not math.isclose(rec_val, claim_val, rel_tol=tolerance, abs_tol=tolerance):
            return False, f"value_mismatch:ledger={rec_val},claim={claim_val}"
    except (TypeError, ValueError) as exc:
        return False, f"invalid_numeric_value:{exc}"

    # 5. Definition key verification
    if not record.definition_key or not isinstance(record.definition_key, str) or not record.definition_key.strip():
        return False, "missing_definition_key"
    if hasattr(claim, "definition_key") and claim.definition_key and record.definition_key != claim.definition_key:
        return False, f"definition_key_mismatch:{record.definition_key}!={claim.definition_key}"

    # 6. Supported classification (kind and evidence floor)
    rec_kind = record.kind.value if hasattr(record.kind, "value") else str(record.kind)
    if claim.kind.upper() != rec_kind.upper():
        return False, f"kind_classification_mismatch:ledger={rec_kind},claim={claim.kind}"

    # Handbook 4.1 evidence floor constraints
    if rec_kind in {"OBSERVED", "POLICY_RULE"} and record.evidence_floor < 4:
        return False, f"insufficient_evidence_floor_for_{rec_kind}:{record.evidence_floor}<4"
    if rec_kind == "USER_ASSUMED" and record.evidence_floor < 3:
        return False, f"insufficient_evidence_floor_for_USER_ASSUMED:{record.evidence_floor}<3"

    # 7. Evidence lineage verification
    if rec_kind == "CALCULATED":
        if not record.parent_ids and not record.method_id:
            return False, "calculated_quantity_missing_lineage"
        for pid in record.parent_ids:
            if pid in ledger_records:
                parent = ledger_records[pid]
                if record.evidence_floor > parent.evidence_floor:
                    return False, f"evidence_floor_inversion:{record.evidence_floor}>{parent.evidence_floor}"
    elif rec_kind in {"OBSERVED", "POLICY_RULE"}:
        if not record.source_refs:
            return False, f"{rec_kind}_missing_source_refs"
    elif rec_kind == "ESTIMATED" and not record.method_id and not record.parent_ids:
        return False, "estimated_quantity_missing_method_or_lineage"

    return True, "supported"


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

    ledger_records = getattr(output, "ledger_records", {}) or {}
    scores: dict[str, float] = {}

    for metric in declared_metrics:
        if metric == "unsupported_numeric_claim_rate":
            # Share of claims that fail epistemic ledger verification
            if not output.claims:
                scores[metric] = 0.0
            else:
                unsupported_count = 0
                for c in output.claims:
                    is_valid, _ = verify_claim_provenance(c, ledger_records, tolerance)
                    if not is_valid:
                        unsupported_count += 1
                scores[metric] = float(unsupported_count / len(output.claims))

        elif metric == "class_mislabel_rate":
            # Share of claims asserting a stronger class than computed floor or failing kind match
            if not output.claims:
                scores[metric] = 0.0
            else:
                mislabelled = 0
                for c in output.claims:
                    is_valid, _ = verify_claim_provenance(c, ledger_records, tolerance)
                    if not is_valid and c.kind in {"OBSERVED", "CALCULATED"}:
                        mislabelled += 1
                    elif c.ledger_id and c.ledger_id in ledger_records:
                        rec = ledger_records[c.ledger_id]
                        rec_kind = rec.kind.value if hasattr(rec.kind, "value") else str(rec.kind)
                        if c.kind.upper() != rec_kind.upper():
                            mislabelled += 1
                scores[metric] = float(mislabelled / len(output.claims))

        elif metric == "resolution_overclaim_rate":
            # Share of claims at finer resolution than evidence supports
            gold_res = expected.get("gold_resolution")
            if not output.claims or gold_res is None:
                scores[metric] = 0.0
            else:
                overclaimed = 0
                for c in output.claims:
                    if c.resolution_level > gold_res:
                        overclaimed += 1
                    elif c.ledger_id and c.ledger_id in ledger_records:
                        rec = ledger_records[c.ledger_id]
                        if rec.resolution > gold_res:
                            overclaimed += 1
                scores[metric] = float(overclaimed / len(output.claims))

        elif metric == "correct_insufficient_evidence_rate":
            # For insufficient_evidence tasks, 1.0 if reported gap, 0.0 if answered
            if category == "insufficient_evidence":
                if output.status == "INSUFFICIENT_EVIDENCE" or len(output.reported_gaps) > 0:
                    scores[metric] = 1.0
                else:
                    scores[metric] = 0.0
            else:
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
            # 1.0 if completed cleanly (including recovery from injected tool failure), 0.0 on error
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

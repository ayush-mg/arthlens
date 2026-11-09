"""
Execute benchmark tasks against a selected system (B1, B2, B3, B4) and output scored results.

Authoritative Specification: ArthLens Build Handbook Section 12.2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmark.harness.scorer import score_task_output
from benchmark.harness.systems import get_benchmark_system
from benchmark.harness.validation import BenchmarkValidationError, validate_task_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path, help="Path to validated task JSON file.")
    parser.add_argument(
        "--system",
        choices=("B1", "B2", "B3", "B4"),
        default="B4",
        help="System variant to evaluate (B1=LLM no-gates, B2=Fixed pipeline, B3=Ablation agent, B4=Full ArthLens).",
    )
    parser.add_argument(
        "--split",
        choices=("dev", "validation", "frozen_test"),
        required=True,
        help="Task split to execute.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("benchmark/task_schema.json"),
        help="Path to task schema JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for scored results JSON.",
    )
    parser.add_argument(
        "--scorer-name",
        default="arthlens-automated-evaluator-v1",
        help="Scorer identity for audit metadata.",
    )

    args = parser.parse_args()

    # 1. Validate task dataset
    try:
        validation_result = validate_task_file(
            args.task_file,
            args.schema,
            expected_split=args.split,
        )
    except (BenchmarkValidationError, ValueError, OSError) as exc:
        print(f"Dataset validation failed: {exc}", file=sys.stderr)
        return 1

    # 2. Load tasks
    raw_tasks = json.loads(args.task_file.read_text(encoding="utf-8"))
    system = get_benchmark_system(args.system)

    print(f"Running {len(raw_tasks)} tasks from split '{args.split}' on system {args.system}...")

    scores = []
    for task in raw_tasks:
        task_id = task["task_id"]
        output = system.execute_task(task)
        metric_scores = score_task_output(task, output)
        scores.append({
            "task_id": task_id,
            "metrics": metric_scores,
        })

    result_payload = {
        "run_id": f"benchmark-{args.system.lower()}-{args.split}-run",
        "system_id": f"System-{args.system}",
        "scored_by": args.scorer_name,
        "split": args.split,
        "dataset_sha256": validation_result.sha256,
        "scores": scores,
    }

    rendered = json.dumps(result_payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Scored results written to {args.output}")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

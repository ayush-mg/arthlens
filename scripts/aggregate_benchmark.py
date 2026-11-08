"""Aggregate explicitly scored task metrics and emit bootstrap summaries."""

import argparse
import json
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmark.harness.evaluation import (
    BenchmarkEvaluationError,
    aggregate_scored_results,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path)
    parser.add_argument("scored_results", type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("benchmark/task_schema.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        summary = aggregate_scored_results(
            args.task_file,
            args.scored_results,
            args.schema,
        )
    except (BenchmarkEvaluationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    rendered = json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote aggregate summary for {summary['task_count']} tasks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

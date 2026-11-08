"""Validate one benchmark task file and print only split/count/hash metadata."""

import argparse
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmark.harness.validation import BenchmarkValidationError, validate_task_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_file", type=Path)
    parser.add_argument(
        "--split",
        choices=("dev", "validation", "frozen_test"),
        required=True,
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("benchmark/task_schema.json"),
    )
    args = parser.parse_args()
    try:
        result = validate_task_file(
            args.task_file,
            args.schema,
            expected_split=args.split,
        )
    except BenchmarkValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"validated split={result.split} tasks={result.task_count} "
        f"sha256={result.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

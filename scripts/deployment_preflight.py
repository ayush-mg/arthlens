"""Check production settings and Alembic graph without connecting or printing secrets."""

import argparse
import os
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic.config import Config
from alembic.script import ScriptDirectory

from deployment.preflight import (
    DeploymentPreflightError,
    EXPECTED_MIGRATION_HEAD,
    validate_production_environment,
    validate_production_values,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "environment_file",
        type=Path,
        nargs="?",
        help="Production environment file; defaults to the current process environment.",
    )
    parser.add_argument(
        "--alembic-config",
        type=Path,
        default=Path("backend/alembic.ini"),
    )
    args = parser.parse_args()
    try:
        script_directory = ScriptDirectory.from_config(
            Config(str(args.alembic_config))
        )
        migration_heads = script_directory.get_heads()
        if migration_heads != [EXPECTED_MIGRATION_HEAD]:
            raise DeploymentPreflightError(
                f"Repository Alembic migration head must be {EXPECTED_MIGRATION_HEAD}."
            )
        if args.environment_file is None:
            result = validate_production_values(os.environ, migration_heads)
        else:
            result = validate_production_environment(args.environment_file, migration_heads)
    except (DeploymentPreflightError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"preflight passed; migration_head={result.migration_head}; "
        f"checked={len(result.checked_keys)}; no database connection attempted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

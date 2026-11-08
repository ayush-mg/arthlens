"""Check production settings and Alembic graph without connecting or printing secrets."""

import argparse
import sys
from pathlib import Path

# Ensure repository root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic.config import Config
from alembic.script import ScriptDirectory

from deployment.preflight import (
    DeploymentPreflightError,
    validate_production_environment,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment_file", type=Path)
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
        head_count = len(script_directory.get_heads())
        result = validate_production_environment(args.environment_file, head_count)
    except (DeploymentPreflightError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"preflight passed; checked={len(result.checked_keys)} "
        f"migration_heads={result.migration_head_count}; no database connection attempted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Safe production environment and migration-graph checks without secret output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class PreflightResult:
    checked_keys: tuple[str, ...]
    migration_head_count: int


class DeploymentPreflightError(ValueError):
    """Raised when deployment configuration is incomplete or unsafe."""


def read_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE files and reject malformed or duplicate keys."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DeploymentPreflightError(f"Cannot read environment file: {exc}") from exc
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            raise DeploymentPreflightError(
                f"Malformed environment entry at line {line_number}."
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise DeploymentPreflightError(
                f"Invalid environment key at line {line_number}."
            )
        if key in values:
            raise DeploymentPreflightError(f"Duplicate environment key {key}.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def validate_production_environment(path: Path, migration_head_count: int) -> PreflightResult:
    """Validate production-critical settings without revealing configured values."""
    values = read_env_file(path)
    errors: list[str] = []
    if values.get("ENVIRONMENT", "").lower() != "production":
        errors.append("ENVIRONMENT must be production.")

    database_url = values.get("DATABASE_URL", "")
    try:
        parsed_database = urlsplit(database_url)
        database_host = parsed_database.hostname
        database_port = parsed_database.port
    except ValueError:
        parsed_database = None
        database_host = None
        database_port = None
    if (
        parsed_database is None
        or parsed_database.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}
        or not database_host
        or not parsed_database.path.strip("/")
        or parsed_database.username is None
        or parsed_database.password is None
        or _looks_like_placeholder(parsed_database.username)
        or _looks_like_placeholder(parsed_database.password)
        or _looks_like_placeholder(database_host)
        or (database_port is not None and not 1 <= database_port <= 65535)
    ):
        errors.append("DATABASE_URL must be a complete PostgreSQL URL.")

    jwt_secret = values.get("JWT_SECRET_KEY", "")
    if len(jwt_secret.encode("utf-8")) < 32 or _looks_like_placeholder(jwt_secret):
        errors.append("JWT_SECRET_KEY must be an explicit secret of at least 32 bytes.")
    if values.get("AUTH_COOKIE_SECURE", "").lower() not in {"true", "1", "yes"}:
        errors.append("AUTH_COOKIE_SECURE must be enabled in production.")
    if values.get("AUTH_COOKIE_SAMESITE", "lax").lower() == "none" and (
        values.get("AUTH_COOKIE_SECURE", "").lower() not in {"true", "1", "yes"}
    ):
        errors.append("SameSite=None requires AUTH_COOKIE_SECURE.")
    if migration_head_count != 1:
        errors.append("Alembic migration graph must have exactly one head.")
    if errors:
        raise DeploymentPreflightError(" ".join(errors))
    return PreflightResult(
        checked_keys=(
            "ENVIRONMENT",
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "AUTH_COOKIE_SECURE",
            "AUTH_COOKIE_SAMESITE",
        ),
        migration_head_count=migration_head_count,
    )


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or any(
        marker in normalized
        for marker in (
            "replace_with",
            "replace_",
            "change_me",
            "changeme",
            "placeholder",
            "example",
            "arthlens_dev_password",
        )
    )

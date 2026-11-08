
import pytest
from deployment.preflight import (
    DeploymentPreflightError,
    read_env_file,
    validate_production_environment,
)


def _production_env() -> str:
    return "\n".join(
        (
            "ENVIRONMENT=production",
            "DATABASE_URL=postgresql+psycopg://user:password@db.example.org/arthlens",
            "JWT_SECRET_KEY=" + "a" * 48,
            "AUTH_COOKIE_SECURE=true",
            "AUTH_COOKIE_SAMESITE=lax",
        )
    )


@pytest.mark.unit
def test_production_preflight_passes_without_exposing_secret(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        _production_env().replace("db.example.org", "db.test"),
        encoding="utf-8",
    )

    result = validate_production_environment(env_file, migration_head_count=1)

    assert result.migration_head_count == 1
    assert "JWT_SECRET_KEY" in result.checked_keys
    assert "a" * 48 not in repr(result)


@pytest.mark.unit
def test_production_preflight_rejects_template_secret_database_and_migration_graph(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        _production_env().replace("a" * 48, "replace_with_secret"),
        encoding="utf-8",
    )

    with pytest.raises(DeploymentPreflightError) as exc_info:
        validate_production_environment(env_file, migration_head_count=2)

    assert "JWT_SECRET_KEY" in str(exc_info.value)
    assert "exactly one head" in str(exc_info.value)
    assert "replace_with_secret" not in str(exc_info.value)


@pytest.mark.unit
def test_production_preflight_rejects_placeholder_database_host(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        _production_env().replace("db.example.org", "replace_host"),
        encoding="utf-8",
    )

    with pytest.raises(DeploymentPreflightError) as exc_info:
        validate_production_environment(env_file, migration_head_count=1)

    assert "DATABASE_URL" in str(exc_info.value)
    assert "replace_host" not in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.parametrize("host", ["db.test:70000", "[::1"])
def test_production_preflight_rejects_malformed_database_authority(tmp_path, host):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        _production_env().replace("db.example.org", host),
        encoding="utf-8",
    )

    with pytest.raises(DeploymentPreflightError) as exc_info:
        validate_production_environment(env_file, migration_head_count=1)

    assert "DATABASE_URL" in str(exc_info.value)
    assert host not in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.parametrize(
    "line",
    [
        "not an assignment",
        "BAD-KEY=value",
        "JWT_SECRET_KEY=one\nJWT_SECRET_KEY=two",
    ],
)
def test_env_reader_rejects_malformed_or_duplicate_keys(tmp_path, line):
    env_file = tmp_path / ".env"
    env_file.write_text(line, encoding="utf-8")

    with pytest.raises(DeploymentPreflightError):
        read_env_file(env_file)


@pytest.mark.unit
def test_production_preflight_requires_secure_cookies_for_samesite_none(tmp_path):
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        _production_env()
        .replace("AUTH_COOKIE_SECURE=true", "AUTH_COOKIE_SECURE=false")
        .replace("AUTH_COOKIE_SAMESITE=lax", "AUTH_COOKIE_SAMESITE=none"),
        encoding="utf-8",
    )

    with pytest.raises(DeploymentPreflightError, match="AUTH_COOKIE_SECURE"):
        validate_production_environment(env_file, migration_head_count=1)

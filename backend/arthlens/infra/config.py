"""
Configuration and Environment Management for ArthLens.

Authoritative Reference: ArthLens Build Handbook v1.0 (Section 3.2, Part 9).
Phase: P1-5 (Database Persistence, Repositories and Integration Tests).
"""

import os
from pathlib import Path
from typing import Optional


def _load_env_file() -> None:
    """Load key-value pairs from .env if present in root or backend without overriding existing env."""
    search_paths = [
        Path(__file__).resolve().parents[3] / ".env",  # c:\arthlens\.env
        Path(__file__).resolve().parents[2] / ".env",  # c:\arthlens\backend\.env
        Path(".env"),
    ]
    for env_path in search_paths:
        if env_path.is_file():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip("'\"")
                            os.environ.setdefault(key, val)
                break
            except Exception:
                pass


_load_env_file()


def get_database_url(sync: bool = True) -> str:
    """
    Construct or retrieve the PostgreSQL connection URL.

    Respects DATABASE_URL if present, otherwise constructs from POSTGRES_* environment variables.
    Ensures the psycopg (v3) dialect 'postgresql+psycopg://' is used by default for SQLAlchemy.
    """
    raw_url = os.environ.get("DATABASE_URL")
    if raw_url:
        url = raw_url.strip()
        # Normalise postgres:// or postgresql:// to postgresql+psycopg:// for SQLAlchemy 2.x
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    user = os.environ.get("POSTGRES_USER", "arthlens_dev")
    password = os.environ.get("POSTGRES_PASSWORD", "arthlens_dev_password")
    host = os.environ.get("POSTGRES_HOST", "127.0.0.1")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "arthlens")

    driver = "postgresql+psycopg" if sync else "postgresql+psycopg_async"
    return f"{driver}://{user}:{password}@{host}:{port}/{db}"


def get_environment() -> str:
    """Return runtime environment name (development, test, production)."""
    return os.environ.get("ENVIRONMENT", "development")


def get_jwt_secret_key() -> str:
    """
    Retrieve JWT secret key from environment.
    Enforces that production environments provide an explicit, non-default secret key.
    """
    secret = os.environ.get("JWT_SECRET_KEY")
    if secret:
        return secret
    if get_environment() == "production":
        raise RuntimeError("JWT_SECRET_KEY environment variable must be set in production.")
    # Safe default for local development and test suite execution (>= 32 bytes)
    return "arthlens_dev_jwt_secret_key_at_least_32_bytes_long_2026!"


def get_jwt_algorithm() -> str:
    """JWT signature algorithm."""
    return os.environ.get("JWT_ALGORITHM", "HS256")


def get_access_token_expire_minutes() -> int:
    """JWT token expiry duration in minutes."""
    val = os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    try:
        return int(val)
    except ValueError:
        return 30


def get_auth_cookie_name() -> str:
    """HTTP-only session cookie name."""
    return os.environ.get("AUTH_COOKIE_NAME", "arthlens_access_token")


def get_auth_cookie_secure() -> bool:
    """Whether session cookie requires HTTPS (Secure flag)."""
    val = os.environ.get("AUTH_COOKIE_SECURE")
    if val is not None:
        return val.lower() in ("true", "1", "yes")
    return get_environment() == "production"


def get_auth_cookie_samesite() -> str:
    """SameSite cookie attribute (lax, strict, none)."""
    return os.environ.get("AUTH_COOKIE_SAMESITE", "lax")


def get_rate_limit_per_minute_ip() -> int:
    """Maximum allowed requests per minute per IP address (provisional default: 60)."""
    val = os.environ.get("RATE_LIMIT_PER_MINUTE_IP", "60")
    try:
        return int(val)
    except ValueError:
        return 60


def get_rate_limit_per_minute_user() -> int:
    """Maximum allowed requests per minute per authenticated user (provisional default: 120)."""
    val = os.environ.get("RATE_LIMIT_PER_MINUTE_USER", "120")
    try:
        return int(val)
    except ValueError:
        return 120


def get_daily_run_quota() -> int:
    """Maximum allowed agent/simulation runs per entrepreneur per day (provisional default: 50)."""
    val = os.environ.get("DAILY_RUN_QUOTA", "50")
    try:
        return int(val)
    except ValueError:
        return 50


def get_max_cost_usd_per_run() -> float:
    """Cost cap per individual agent run in USD (Handbook Part 8.3 baseline: $0.25)."""
    val = os.environ.get("MAX_COST_USD_PER_RUN", "0.25")
    try:
        return float(val)
    except ValueError:
        return 0.25


def get_max_cost_usd_per_day() -> float:
    """Cost cap per entrepreneur per day in USD (provisional default: $5.00)."""
    val = os.environ.get("MAX_COST_USD_PER_DAY", "5.00")
    try:
        return float(val)
    except ValueError:
        return 5.00


def get_default_run_cost_reservation() -> float:
    """
    Server-side nominal cost reservation per run in USD.
    Handbook Part 8.3 indicates Loop B analytical run costs ~$0.0040.
    Provisional server reservation baseline: $0.01.
    """
    val = os.environ.get("DEFAULT_RUN_COST_RESERVATION", "0.01")
    try:
        return float(val)
    except ValueError:
        return 0.01



def get_allowed_origins() -> list[str]:
    """List of allowed CORS and CSRF origins."""
    val = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip() for origin in val.split(",") if origin.strip()]


def get_trusted_proxies() -> set[str]:
    """Set of trusted upstream reverse-proxy IP addresses for client IP resolution."""
    val = os.environ.get("TRUSTED_PROXIES", "127.0.0.1,::1,testclient")
    return {ip.strip() for ip in val.split(",") if ip.strip()}

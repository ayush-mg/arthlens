"""Contract tests for repository credential leakage prevention and firewall enforcement.

Verifies:
1. No configured environment secret or API key pattern is committed to Git-tracked files.
2. Assertion failures and test outputs never leak secret values.
3. CredentialFirewall thoroughly redacts configured provider secrets, query params, and tokens.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from backend.arthlens.llm.provider import CredentialFirewall

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".pdf",
    ".bin",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".parquet",
    ".gz",
    ".zip",
    ".pyc",
}

SECRET_ENV_PATTERNS = ("KEY", "SECRET", "TOKEN", "PASSWORD")
COMMON_FALSE_POSITIVES = {
    "none",
    "true",
    "false",
    "null",
    "localhost",
    "127.0.0.1",
    "postgres",
    "admin",
    "guest",
    "change-me",
    "dev-secret-key-change-in-production-min-32-chars",
    "dev-secret",
}


def _get_git_tracked_files(repo_root: Path) -> list[Path]:
    """Retrieve all files tracked by git in the repository."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return [
            repo_root / line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]
    except Exception as exc:
        pytest.skip(f"Git unavailable or not a git repository: {exc}")


@pytest.mark.contract
def test_no_configured_secrets_leaked_in_git_tracked_files():
    """Verify that no actual secrets from the environment exist in git-tracked files."""
    repo_root = Path(__file__).resolve().parents[3]
    tracked_files = _get_git_tracked_files(repo_root)

    # Collect configured sensitive values from os.environ
    configured_secrets: dict[str, str] = {}
    for key, val in os.environ.items():
        if not val or len(val) < 8:
            continue
        key_upper = key.upper()
        if any(pat in key_upper for pat in SECRET_ENV_PATTERNS):
            if val.lower() not in COMMON_FALSE_POSITIVES:
                configured_secrets[key] = val

    leaks: list[str] = []

    for file_path in tracked_files:
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        rel_path = file_path.relative_to(repo_root).as_posix()

        # Check configured env secrets
        for env_var_name, secret_val in configured_secrets.items():
            # Exclude .env.example checking its own documentation placeholders
            if rel_path in {".env.example", "deployment/env.example"} and env_var_name not in {
                "GEMINI_API_KEY",
                "OPENAI_API_KEY",
            }:
                continue
            if secret_val in content:
                # Do NOT include secret_val in the message!
                leaks.append(
                    f"Configured secret from '{env_var_name}' found in git-tracked file: '{rel_path}'"
                )

        # Check for live Google / OpenAI key patterns in tracked files (excluding tests/fixtures)
        if not rel_path.startswith("backend/tests/"):
            # Real live Google API key: AIzaSy... (39 chars)
            if re.search(r"\bAIzaSy[0-9A-Za-z-_]{33}\b", content):
                leaks.append(f"Live Google API key pattern found in '{rel_path}'")
            # Real live OpenAI key: sk-proj-... (40+ chars)
            if re.search(r"\bsk-proj-[A-Za-z0-9_-]{40,}\b", content):
                leaks.append(f"Live OpenAI project key pattern found in '{rel_path}'")
            # Google GenAI token: AQ.Ab... (30+ chars)
            if re.search(r"\bAQ\.[a-zA-Z0-9_-]{30,}\b", content):
                leaks.append(f"Google GenAI API token pattern found in '{rel_path}'")

    assert not leaks, (
        f"Found {len(leaks)} credential leak(s) in git-tracked files:\n"
        + "\n".join(leaks)
    )


@pytest.mark.contract
def test_credential_firewall_redacts_configured_secrets(monkeypatch):
    """Ensure CredentialFirewall masks all configured sensitive environment variables."""
    monkeypatch.setenv("CUSTOM_PROVIDER_API_KEY", "super-secret-custom-token-12345")
    monkeypatch.setenv("MY_APP_CLIENT_SECRET", "another-sensitive-passphrase-67890")

    raw_message = (
        "Error calling Gemini: invalid key super-secret-custom-token-12345 "
        "and secret another-sensitive-passphrase-67890."
    )
    sanitized = CredentialFirewall.sanitize(raw_message)

    assert "super-secret-custom-token-12345" not in sanitized
    assert "another-sensitive-passphrase-67890" not in sanitized
    assert "[REDACTED_SECRET]" in sanitized


@pytest.mark.contract
def test_credential_firewall_redacts_url_query_params():
    """Ensure URL query parameters carrying credentials are sanitized."""
    raw_url = "https://generativelanguage.googleapis.com/v1beta/models?key=AIzaSyFakeKey1234567890abcdef"
    sanitized = CredentialFirewall.sanitize(raw_url)

    assert "AIzaSyFakeKey1234567890abcdef" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


@pytest.mark.contract
def test_credential_firewall_redacts_bearer_tokens():
    """Ensure Authorization Bearer headers/tokens are sanitized."""
    raw_header = "Authorization: Bearer ya29.a0AfH6SMD_very_secret_oauth_token_here"
    sanitized = CredentialFirewall.sanitize(raw_header)

    assert "ya29.a0AfH6SMD_very_secret_oauth_token_here" not in sanitized
    assert "[REDACTED_TOKEN]" in sanitized

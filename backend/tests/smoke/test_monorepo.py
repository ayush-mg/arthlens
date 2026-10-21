"""
Baseline smoke test suite for Task P1-1 (Monorepo, CI, and Docker Compose).

Handbook Reference: Part 3.2, 3.3, 13.1 (P1-1 acceptance: 'CI green on empty tests')
These tests verify that the repository structure, Docker Compose specification,
and Python environment are correctly initialized before domain code implementation.
"""

import os
import sys
import pytest


@pytest.mark.smoke
def test_python_runtime_version():
    """Verify that Python runtime is exactly 3.14 per Project Specification."""
    assert sys.version_info[:2] == (3, 14), f"ArthLens requires Python 3.14, running on {sys.version}"


@pytest.mark.smoke
def test_monorepo_directory_structure():
    """Verify that all core monorepo directories exist per Handbook Part 3.3."""
    root_dirs = ["frontend", "backend", "benchmark", "deployment", "docs"]
    for d in root_dirs:
        assert os.path.isdir(d), f"Missing monorepo directory: {d}"

    # Verify backend/arthlens package exists
    assert os.path.isdir(os.path.join("backend", "arthlens")), "Missing backend/arthlens package"

    # Verify key architectural modules exist under backend/arthlens/
    expected_modules = [
        "domain", "ledger", "policy", "geo", "demand", "finance",
        "simulation", "optimization", "agent", "llm", "data", "reports", "api", "infra"
    ]
    for m in expected_modules:
        mod_path = os.path.join("backend", "arthlens", m)
        assert os.path.isdir(mod_path), f"Missing architectural module directory: {mod_path}"
        assert os.path.isfile(os.path.join(mod_path, "__init__.py")), f"Missing __init__.py in: {mod_path}"


@pytest.mark.smoke
def test_docker_compose_specification():
    """Verify root compose.yaml exists and specifies postgis/postgis:16-3.4-alpine."""
    assert os.path.isfile("compose.yaml"), "Missing root compose.yaml"
    with open("compose.yaml", "r", encoding="utf-8") as f:
        content = f.read()

    assert "postgis/postgis:16-3.4-alpine" in content, (
        "compose.yaml must specify postgis/postgis:16-3.4-alpine image"
    )
    assert "postgres_data" in content, "compose.yaml must configure persistent volume postgres_data"
    assert "pg_isready" in content, "compose.yaml must configure database healthcheck"


@pytest.mark.smoke
def test_environment_template_exists():
    """Verify .env.example exists with required database and cost-governance keys."""
    assert os.path.isfile(".env.example"), "Missing .env.example"
    with open(".env.example", "r", encoding="utf-8") as f:
        content = f.read()

    required_vars = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
        "LLM_PROVIDER",
        "MAX_COST_USD_PER_RUN"
    ]
    for v in required_vars:
        assert v in content, f".env.example must define {v}"


@pytest.mark.smoke
def test_backend_package_import():
    """Verify that arthlens backend package can be imported cleanly."""
    import backend.arthlens
    assert backend.arthlens is not None

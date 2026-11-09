"""
Unit tests for API health check endpoints.

Authoritative Specification: ArthLens Build Handbook Section 14.5.
"""

import pytest
from backend.arthlens.api.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.unit
def test_root_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "arthlens-backend"


@pytest.mark.unit
def test_api_v1_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "arthlens-backend"


@pytest.mark.unit
def test_auth_ping_endpoint(client):
    res = client.get("/auth/ping")
    assert res.status_code == 200
    assert res.json() == {"status": "pong"}

"""Unit and integration tests for FastAPI endpoints and database connection."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import engine, init_db
from sqlalchemy import inspect


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database tables are created for tests."""
    init_db()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client: TestClient):
    """Test GET / returns app name and running status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SpectrumSentry AI"
    assert data["status"] == "running"


def test_health_endpoint(client: TestClient):
    """Test GET /health returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_cors_headers(client: TestClient):
    """Test CORS headers are returned for configured origin."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_database_tables_exist():
    """Verify SQLite database connection and required tables exist."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    required_tables = ["experiments", "predictions", "communication_metrics", "alerts"]
    for table in required_tables:
        assert table in table_names, f"Table '{table}' missing from database"

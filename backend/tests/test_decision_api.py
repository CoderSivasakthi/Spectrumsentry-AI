"""Integration tests for FastAPI Decision Engine endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database.database import init_db


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


class TestDecisionAPI:
    """Test suite for /api/decision REST endpoints."""

    def test_evaluate_endpoint(self, client: TestClient):
        payload = {
            "signal_evidence": {
                "predicted_modulation": "QPSK",
                "confidence": 0.995,
                "measured_snr_db": 15.0,
                "signal_quality": "EXCELLENT",
            },
            "communication_evidence": {
                "status": "CONNECTED",
                "health_score": 100.0,
                "packet_loss_percent": 0.0,
                "avg_latency_ms": 10.5,
                "jitter_ms": 1.2,
                "throughput_mbps": 0.05,
                "is_interrupted": False,
            },
        }

        res = client.post("/api/decision/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["overall_status"] == "NORMAL"
        assert data["decision_confidence"] >= 0.90
        assert data["consistency"] == "CONSISTENT"
        assert "RULE_NORMAL_OPERATION" in data["rules_triggered"]
        assert len(data["recommendations"]) >= 1

    def test_evaluate_conflict_endpoint(self, client: TestClient):
        payload = {
            "signal_evidence": {
                "predicted_modulation": "16-QAM",
                "confidence": 0.998,
                "measured_snr_db": 20.0,
            },
            "communication_evidence": {
                "status": "DEGRADED",
                "health_score": 35.0,
                "packet_loss_percent": 25.0,
            },
        }

        res = client.post("/api/decision/evaluate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["overall_status"] == "REVIEW"
        assert data["consistency"] == "CONFLICTING"

    def test_get_latest_endpoint(self, client: TestClient):
        res = client.get("/api/decision/latest")
        assert res.status_code == 200
        data = res.json()
        assert "overall_status" in data
        assert "decision_confidence" in data
        assert "consistency" in data

    def test_list_rules_endpoint(self, client: TestClient):
        res = client.get("/api/decision/rules")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 7
        rule_ids = [r["rule_id"] for r in data]
        assert "RULE_INTERRUPTED_LINK" in rule_ids

    def test_history_endpoint(self, client: TestClient):
        res = client.get("/api/decision/history?skip=0&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1

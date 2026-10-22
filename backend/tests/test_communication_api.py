"""Integration tests for FastAPI communication endpoints and WebSocket."""

import time
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


class TestCommunicationAPI:
    """Test suite for /api/communication REST endpoints."""

    def test_session_lifecycle_api(self, client: TestClient):
        sess_id = f"api_test_{int(time.time() * 1000)}"

        # 1. Start session
        start_payload = {
            "session_id": sess_id,
            "expected_packets": 5,
            "interval_seconds": 0.1,
            "timeout_seconds": 1.5,
        }
        res_start = client.post("/api/communication/session/start", json=start_payload)
        assert res_start.status_code == 201
        data = res_start.json()
        assert data["session_id"] == sess_id
        assert data["status"] == "STARTING"

        # 2. Ingest 3 packets
        t0 = time.time()
        for seq in range(1, 4):
            pkt_payload = {
                "session_id": sess_id,
                "sequence_number": seq,
                "sender_timestamp": t0 + (seq - 1) * 0.1,
                "payload_size": 256,
                "protocol_version": "1.0",
                "client_rtt_ms": 12.0,
            }
            res_pkt = client.post("/api/communication/packet", json=pkt_payload)
            assert res_pkt.status_code == 200
            ack = res_pkt.json()
            assert ack["sequence_number"] == seq
            assert ack["received_packets"] == seq
            assert ack["health_score"] > 0

        # 3. Check status
        res_status = client.get(f"/api/communication/status?session_id={sess_id}")
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["session_id"] == sess_id
        assert status_data["received_packets"] == 3
        assert status_data["active"] is True

        # 4. Check live metrics
        res_metrics = client.get(f"/api/communication/metrics?session_id={sess_id}")
        assert res_metrics.status_code == 200
        metrics = res_metrics.json()
        assert metrics["session_id"] == sess_id
        assert metrics["packets_received"] == 3
        assert metrics["avg_latency_ms"] == 12.0

        # 5. Stop session
        stop_payload = {"session_id": sess_id, "reason": "test_completed"}
        res_stop = client.post("/api/communication/session/stop", json=stop_payload)
        assert res_stop.status_code == 200
        summary = res_stop.json()
        assert summary["session_id"] == sess_id
        assert summary["packets_received"] == 3
        assert summary["packets_sent"] == 5
        assert summary["packets_lost"] == 2
        assert summary["final_status"] == "STOPPED"

        # 6. Retrieve history list
        res_hist = client.get("/api/communication/history?skip=0&limit=10")
        assert res_hist.status_code == 200
        hist_data = res_hist.json()
        assert hist_data["total"] >= 1
        found = any(item["session_id"] == sess_id for item in hist_data["items"])
        assert found is True

        # 7. Retrieve single session details
        res_detail = client.get(f"/api/communication/history/{sess_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["session_id"] == sess_id

    def test_stop_session_not_found(self, client: TestClient):
        res = client.post("/api/communication/session/stop", json={"session_id": "non_existent_id"})
        assert res.status_code == 404

    def test_history_detail_not_found(self, client: TestClient):
        res = client.get("/api/communication/history/non_existent_id")
        assert res.status_code == 404

    def test_invalid_packet_payload_rejected(self, client: TestClient):
        # Missing session_id
        bad_pkt = {"sequence_number": 1, "sender_timestamp": 12345.0}
        res = client.post("/api/communication/packet", json=bad_pkt)
        assert res.status_code == 422

        # Sequence number < 1
        bad_seq = {
            "session_id": "bad_seq",
            "sequence_number": 0,
            "sender_timestamp": 12345.0,
        }
        res = client.post("/api/communication/packet", json=bad_seq)
        assert res.status_code == 422


class TestWebSocketCommunication:
    """Test WebSocket real-time telemetry streaming."""

    def test_websocket_connect_and_receive_initial_metrics(self, client: TestClient):
        with client.websocket_connect("/ws/communication") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "communication_metrics"
            assert "health_score" in data
            assert "status" in data
            # Test ping pong
            websocket.send_text("ping")
            pong = websocket.receive_text()
            assert pong == "pong"

"""Unified Real-Time Monitoring and Cross-Domain Integration Tests (Phase 7).

Verifies the integration of:
  - Phase 4: AI Signal / Modulation Evidence
  - Phase 5: Application-level Packet Telemetry & Session Monitoring
  - Phase 6: Deterministic Explainable Decision Engine
  - Real-time Snapshot assembly, REST API, and WebSocket streaming
"""

from datetime import datetime, timezone
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.communication.packet_monitor import packet_monitor
from backend.app.config.settings import get_settings
from backend.app.database.database import SessionLocal, init_db
from backend.app.database.models import utc_now
from backend.app.main import app
from backend.app.monitoring.unified_manager import unified_monitor
from backend.app.schemas.communication import CommunicationStatus, PacketIn, SessionStartRequest
from backend.app.schemas.decision import ConsistencyStatus, OverallStatus
from backend.app.schemas.monitoring import (
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
    SignalEvidenceInput,
)
from backend.app.websocket.manager import monitoring_ws_manager, ws_manager


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Ensure database schema is initialized for tests."""
    init_db()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    """Database session fixture."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_unified_state():
    """Reset in-memory unified monitor state between tests."""
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None
    yield
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None


# ==============================================================================
# 1. Unified Session Lifecycle Tests
# ==============================================================================

class TestUnifiedSessionLifecycle:
    """Verifies creation, tracking, and stopping of unified monitoring sessions."""

    def test_unified_session_creation(self, db):
        """Test 1: Unified session creation with linked communication session."""
        req = MonitoringSessionStartRequest(
            monitoring_session_id="test_mon_001",
            communication_session_id="test_comm_001",
            auto_start_communication=True,
            interval_seconds=0.1,
            timeout_seconds=2.0,
        )
        resp = unified_monitor.start_session(req, db)
        assert resp.monitoring_session_id == "test_mon_001"
        assert resp.communication_session_id == "test_comm_001"
        assert resp.status == "ACTIVE"
        assert unified_monitor.active_monitoring_session_id == "test_mon_001"
        assert unified_monitor.active_communication_session_id == "test_comm_001"

    def test_unified_session_stop(self, db):
        """Test 2: Unified session stop with database summary update."""
        req = MonitoringSessionStartRequest(
            monitoring_session_id="test_mon_002",
            communication_session_id="test_comm_002",
            auto_start_communication=True,
        )
        unified_monitor.start_session(req, db)

        stop_req = MonitoringSessionStopRequest(
            monitoring_session_id="test_mon_002",
            stop_communication=True,
            reason="test_completed",
        )
        summary = unified_monitor.stop_session(stop_req, db)
        assert summary.monitoring_session_id == "test_mon_002"
        assert summary.status == "STOPPED"
        assert summary.ended_at is not None
        assert unified_monitor.active_monitoring_session_id is None


# ==============================================================================
# 2. Evidence Domain Isolation and Freshness Tests
# ==============================================================================

class TestEvidenceDomainsAndFreshness:
    """Verifies handling of single-domain, cross-domain, missing, and stale evidence."""

    def test_communication_only_evidence(self, db):
        """Test 3: Communication available, Signal unavailable."""
        comm_req = SessionStartRequest(session_id="comm_only_sess", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "comm_only_sess"
        unified_monitor.clear_signal_evidence()

        # Ingest one good packet
        pkt = PacketIn(
            session_id="comm_only_sess",
            sequence_number=1,
            sender_timestamp=time.time(),
            payload_size=256,
        )
        packet_monitor.sessions["comm_only_sess"].record_packet(pkt, time.time())

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.communication.available is True
        assert snapshot.signal.available is False
        assert snapshot.decision.status == OverallStatus.NORMAL
        assert snapshot.decision.consistency == ConsistencyStatus.UNCORRELATED

    def test_signal_only_evidence(self, db):
        """Test 4: Signal available, Communication unavailable."""
        unified_monitor.active_communication_session_id = None
        packet_monitor.active_session_id = None

        sig_in = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.98,
            estimated_snr_db=15.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.signal.available is True
        assert snapshot.signal.stale is False
        assert snapshot.signal.predicted_modulation == "QPSK"
        assert snapshot.communication.available is False
        assert snapshot.decision.status == OverallStatus.NORMAL
        assert snapshot.decision.consistency == ConsistencyStatus.UNCORRELATED

    def test_signal_and_communication_evidence(self, db):
        """Test 5: Both signal and communication evidence available."""
        comm_req = SessionStartRequest(session_id="dual_sess", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "dual_sess"

        pkt = PacketIn(
            session_id="dual_sess",
            sequence_number=1,
            sender_timestamp=time.time(),
            payload_size=256,
        )
        packet_monitor.sessions["dual_sess"].record_packet(pkt, time.time())

        sig_in = SignalEvidenceInput(
            predicted_modulation="16-QAM",
            ai_confidence=0.99,
            estimated_snr_db=20.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.communication.available is True
        assert snapshot.signal.available is True
        assert snapshot.decision.status == OverallStatus.NORMAL
        assert snapshot.decision.consistency == ConsistencyStatus.CONSISTENT

    def test_missing_signal_evidence(self, db):
        """Test 6: Missing signal evidence does not cause exception."""
        unified_monitor.clear_signal_evidence()
        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.signal.available is False
        assert snapshot.signal.predicted_modulation is None
        assert snapshot.signal.age_seconds is None

    def test_missing_communication_evidence(self, db):
        """Test 7: Missing communication evidence does not cause exception."""
        unified_monitor.active_communication_session_id = None
        packet_monitor.active_session_id = None
        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.communication.available is False
        assert snapshot.communication.packet_loss_percent == 0.0

    def test_fresh_signal_evidence(self, db):
        """Test 8: Signal evidence timestamp within freshness threshold."""
        sig_in = SignalEvidenceInput(
            predicted_modulation="BPSK",
            ai_confidence=0.95,
            estimated_snr_db=12.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.signal.available is True
        assert snapshot.signal.stale is False
        assert snapshot.signal.age_seconds is not None
        assert snapshot.signal.age_seconds < 2.0

    def test_stale_signal_evidence(self, db):
        """Test 9: Stale signal evidence (age > MAX_SIGNAL_EVIDENCE_AGE_SECONDS)."""
        settings = get_settings()
        sig_in = SignalEvidenceInput(
            predicted_modulation="BPSK",
            ai_confidence=0.95,
            estimated_snr_db=12.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        # Artificially age the signal past the max age limit
        unified_monitor.latest_signal_time = time.time() - (settings.MAX_SIGNAL_EVIDENCE_AGE_SECONDS + 5.0)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.signal.available is True
        assert snapshot.signal.stale is True
        assert snapshot.signal.age_seconds > settings.MAX_SIGNAL_EVIDENCE_AGE_SECONDS
        # Ensure stale signal is marked clearly in snapshot
        assert snapshot.signal.predicted_modulation == "BPSK"


# ==============================================================================
# 3. Decision Engine State Verifications Through Unified Pipeline
# ==============================================================================

class TestDecisionStatesThroughUnifiedPipeline:
    """Verifies that Phase 6 decision rules produce correct statuses in Phase 7."""

    def test_normal_decision(self, db):
        """Test 10: NORMAL decision when transport is clean and signal is healthy."""
        comm_req = SessionStartRequest(session_id="sess_norm", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "sess_norm"

        pkt = PacketIn(
            session_id="sess_norm",
            sequence_number=1,
            sender_timestamp=time.time(),
            payload_size=256,
        )
        packet_monitor.sessions["sess_norm"].record_packet(pkt, time.time())

        sig_in = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.96,
            estimated_snr_db=14.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.NORMAL
        assert snapshot.decision.severity == "INFO"
        assert snapshot.decision.confidence >= 0.85

    def test_degraded_decision(self, db):
        """Test 11: DEGRADED decision when packet loss occurs."""
        comm_req = SessionStartRequest(session_id="sess_deg", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "sess_deg"

        # Simulate packet sequence with missing packets (seq 1, then seq 5 => 3 lost)
        monitor = packet_monitor.sessions["sess_deg"]
        t = time.time()
        monitor.record_packet(PacketIn(session_id="sess_deg", sequence_number=1, sender_timestamp=t), t)
        monitor.record_packet(PacketIn(session_id="sess_deg", sequence_number=5, sender_timestamp=t + 0.1), t + 0.1)

        sig_in = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.92,
            estimated_snr_db=3.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.DEGRADED
        assert snapshot.decision.severity == "WARNING"
        assert snapshot.communication.packet_loss_percent > 0

    def test_interrupted_decision(self, db):
        """Test 12: INTERRUPTED decision when silence timeout is exceeded."""
        comm_req = SessionStartRequest(session_id="sess_int", timeout_seconds=1.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "sess_int"

        monitor = packet_monitor.sessions["sess_int"]
        t = time.time()
        monitor.record_packet(PacketIn(session_id="sess_int", sequence_number=1, sender_timestamp=t), t)
        # Advance time by 2.0s to trigger interruption
        monitor.check_timeout_tick(t + 2.0)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.INTERRUPTED
        assert snapshot.decision.severity == "CRITICAL"
        assert snapshot.communication.is_interrupted is True

    def test_recovering_decision(self, db):
        """Test 13: RECOVERING decision on first packet after silence."""
        comm_req = SessionStartRequest(session_id="sess_rec", timeout_seconds=1.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "sess_rec"

        monitor = packet_monitor.sessions["sess_rec"]
        t = time.time()
        monitor.record_packet(PacketIn(session_id="sess_rec", sequence_number=1, sender_timestamp=t), t)
        # Trigger timeout
        monitor.check_timeout_tick(t + 2.0)
        assert monitor.status == CommunicationStatus.INTERRUPTED

        # Now transmit packet 2
        monitor.record_packet(PacketIn(session_id="sess_rec", sequence_number=2, sender_timestamp=t + 2.1), t + 2.1)
        assert monitor.status == CommunicationStatus.RECOVERING

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.RECOVERING
        assert snapshot.communication.is_recovering is True

    def test_review_conflicting_decision(self, db):
        """Test 14: REVIEW / CONFLICTING decision when domains disagree."""
        comm_req = SessionStartRequest(session_id="sess_rev", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "sess_rev"

        # Induce high packet loss (>15%)
        monitor = packet_monitor.sessions["sess_rev"]
        t = time.time()
        monitor.record_packet(PacketIn(session_id="sess_rev", sequence_number=1, sender_timestamp=t), t)
        monitor.record_packet(PacketIn(session_id="sess_rev", sequence_number=10, sender_timestamp=t + 0.1), t + 0.1)

        # Provide high SNR (>=10 dB)
        sig_in = SignalEvidenceInput(
            predicted_modulation="16-QAM",
            ai_confidence=0.99,
            estimated_snr_db=18.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.REVIEW
        assert snapshot.decision.consistency == ConsistencyStatus.CONFLICTING


# ==============================================================================
# 4. Cross-Domain Conflict Scenarios (Section 21)
# ==============================================================================

class TestConflictScenarios:
    """Verifies existing Phase 6 conflict behaviors through the new pipeline."""

    def test_conflict_high_snr_high_packet_loss(self, db):
        """Test 15: Scenario A - High SNR + High packet loss -> REVIEW + CONFLICTING."""
        comm_req = SessionStartRequest(session_id="conflict_a", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "conflict_a"

        # Sequence gap: 1 then 8 => loss ~87.5%
        monitor = packet_monitor.sessions["conflict_a"]
        t = time.time()
        monitor.record_packet(PacketIn(session_id="conflict_a", sequence_number=1, sender_timestamp=t), t)
        monitor.record_packet(PacketIn(session_id="conflict_a", sequence_number=8, sender_timestamp=t + 0.1), t + 0.1)

        sig_in = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.98,
            estimated_snr_db=16.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.REVIEW
        assert snapshot.decision.consistency == ConsistencyStatus.CONFLICTING
        assert any("High SNR" in r or "physical layer exhibits strong" in r for r in snapshot.decision.reasons)

    def test_conflict_clean_communication_low_ai_confidence(self, db):
        """Test 16: Scenario B - Clean communication + Low AI confidence -> REVIEW + CONFLICTING."""
        comm_req = SessionStartRequest(session_id="conflict_b", timeout_seconds=2.0)
        packet_monitor.start_session(comm_req, db)
        unified_monitor.active_communication_session_id = "conflict_b"

        # Clean packets, 0% loss, 100 health
        monitor = packet_monitor.sessions["conflict_b"]
        t = time.time()
        for i in range(1, 4):
            monitor.record_packet(PacketIn(session_id="conflict_b", sequence_number=i, sender_timestamp=t + i * 0.1), t + i * 0.1)

        # Low AI confidence (< 0.70)
        sig_in = SignalEvidenceInput(
            predicted_modulation="16-QAM",
            ai_confidence=0.45,
            estimated_snr_db=8.0,
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        snapshot = unified_monitor.get_current_snapshot(db=db)
        assert snapshot.decision.status == OverallStatus.REVIEW
        assert snapshot.decision.consistency == ConsistencyStatus.CONFLICTING
        assert any("confidence" in r.lower() for r in snapshot.decision.reasons)


# ==============================================================================
# 5. REST API & WebSocket Streaming Tests
# ==============================================================================

class TestUnifiedAPIAndWebSocket:
    """Verifies REST endpoints and WebSocket operations for real-time monitoring."""

    def test_unified_rest_api(self, client: TestClient):
        """Test 17: REST API endpoints under /api/monitoring."""
        # 1. Start monitoring session
        start_payload = {
            "monitoring_session_id": "api_mon_001",
            "communication_session_id": "api_comm_001",
            "auto_start_communication": True,
        }
        res_start = client.post("/api/monitoring/session/start", json=start_payload)
        assert res_start.status_code == 201
        data_start = res_start.json()
        assert data_start["monitoring_session_id"] == "api_mon_001"
        assert data_start["status"] == "ACTIVE"

        # 2. Check session status
        res_sess_status = client.get("/api/monitoring/session/status")
        assert res_sess_status.status_code == 200
        sess_data = res_sess_status.json()
        assert sess_data["active"] is True
        assert sess_data["monitoring_session_id"] == "api_mon_001"

        # 3. Post signal evidence
        sig_payload = {
            "predicted_modulation": "BPSK",
            "ai_confidence": 0.99,
            "estimated_snr_db": 12.0,
        }
        res_sig = client.post("/api/monitoring/signal", json=sig_payload)
        assert res_sig.status_code == 200
        sig_snap = res_sig.json()
        assert sig_snap["signal"]["predicted_modulation"] == "BPSK"
        assert sig_snap["signal"]["available"] is True

        # 4. Get latest monitoring snapshot
        res_status = client.get("/api/monitoring/status")
        assert res_status.status_code == 200
        status_snap = res_status.json()
        assert status_snap["monitoring_session_id"] == "api_mon_001"
        assert "communication" in status_snap
        assert "signal" in status_snap
        assert "decision" in status_snap

        # 5. Stop monitoring session
        res_stop = client.post("/api/monitoring/session/stop", json={"monitoring_session_id": "api_mon_001"})
        assert res_stop.status_code == 200
        assert res_stop.json()["status"] == "STOPPED"

        # 6. Query history
        res_hist = client.get("/api/monitoring/history")
        assert res_hist.status_code == 200
        assert res_hist.json()["total"] >= 1

    def test_unified_websocket(self, client: TestClient):
        """Test 18: WebSocket streaming at /ws/monitoring and backward compatibility of /ws/communication."""
        # Test unified monitoring websocket
        with client.websocket_connect("/ws/monitoring") as ws_mon:
            msg = ws_mon.receive_json()
            assert msg["type"] == "monitoring_snapshot"
            assert "data" in msg
            assert "communication" in msg["data"]
            assert "signal" in msg["data"]
            assert "decision" in msg["data"]

            # Ping-Pong test
            ws_mon.send_text("ping")
            pong = ws_mon.receive_text()
            assert pong == "pong"

        # Verify /ws/communication still functions identically (Phase 5 backward compatibility)
        with client.websocket_connect("/ws/communication") as ws_comm:
            msg = ws_comm.receive_json()
            assert msg["type"] == "communication_metrics"
            assert "health_score" in msg

    def test_websocket_disconnect_handling(self, client: TestClient):
        """Test 19: Safe handling of WebSocket client disconnects without server disruption."""
        initial_count = len(monitoring_ws_manager.active_connections)

        with client.websocket_connect("/ws/monitoring") as ws:
            assert len(monitoring_ws_manager.active_connections) == initial_count + 1
            initial_snap = ws.receive_json()
            assert initial_snap["type"] == "monitoring_snapshot"
            ws.send_text("ping")
            assert ws.receive_text() == "pong"

        # After context exit, client is disconnected
        assert len(monitoring_ws_manager.active_connections) == initial_count


# ==============================================================================
# 6. Complete End-to-End State Transition Integration (Section 20)
# ==============================================================================

class TestEndToEndIntegration:
    """Verifies complete real-time lifecycle: START -> NORMAL -> DEGRADED -> INTERRUPTED -> RECOVERING -> NORMAL."""

    def test_full_end_to_end_state_transitions(self, client: TestClient, db):
        """Test 20: Complete end-to-end integration scenario across all operational states."""
        sess_id = f"e2e_sess_{int(time.time() * 1000)}"

        # 1. START
        start_payload = {
            "monitoring_session_id": f"mon_{sess_id}",
            "communication_session_id": sess_id,
            "auto_start_communication": True,
            "interval_seconds": 0.1,
            "timeout_seconds": 1.5,
        }
        res = client.post("/api/monitoring/session/start", json=start_payload)
        assert res.status_code == 201

        # Provide initial healthy signal evidence
        sig_payload = {
            "predicted_modulation": "QPSK",
            "ai_confidence": 0.97,
            "estimated_snr_db": 15.0,
            "signal_quality": "EXCELLENT",
        }
        client.post("/api/monitoring/signal", json=sig_payload)

        # Ingest nominal packets 1..5 -> NORMAL
        t0 = time.time()
        for seq in range(1, 6):
            pkt = {
                "session_id": sess_id,
                "sequence_number": seq,
                "sender_timestamp": t0 + (seq - 1) * 0.1,
                "payload_size": 256,
                "protocol_version": "1.0",
                "client_rtt_ms": 15.0,
            }
            res_pkt = client.post("/api/communication/packet", json=pkt)
            assert res_pkt.status_code == 200

        snap_normal = client.get("/api/monitoring/status").json()
        assert snap_normal["decision"]["status"] == "NORMAL"
        assert snap_normal["communication"]["packet_loss_percent"] == 0.0

        # 2. COMMUNICATION DEGRADATION -> DEGRADED
        # Jump sequence from 5 to 15 (9 lost packets => significant loss)
        deg_pkt = {
            "session_id": sess_id,
            "sequence_number": 15,
            "sender_timestamp": t0 + 1.0,
            "payload_size": 256,
            "protocol_version": "1.0",
            "client_rtt_ms": 110.0,
        }
        client.post("/api/communication/packet", json=deg_pkt)

        # Update signal to degraded SNR
        client.post(
            "/api/monitoring/signal",
            json={
                "predicted_modulation": "QPSK",
                "ai_confidence": 0.88,
                "estimated_snr_db": -2.0,
                "signal_quality": "POOR",
            },
        )

        snap_degraded = client.get("/api/monitoring/status").json()
        assert snap_degraded["decision"]["status"] == "DEGRADED"
        assert snap_degraded["decision"]["severity"] == "WARNING"

        # 3. COMMUNICATION INTERRUPTION -> INTERRUPTED
        # Advance timeout beyond 1.5s
        monitor = packet_monitor.sessions[sess_id]
        monitor.check_timeout_tick(t0 + 4.0)

        snap_interrupted = client.get("/api/monitoring/status").json()
        assert snap_interrupted["decision"]["status"] == "INTERRUPTED"
        assert snap_interrupted["decision"]["severity"] == "CRITICAL"
        assert snap_interrupted["communication"]["is_interrupted"] is True

        # 4. COMMUNICATION RESUMES -> RECOVERING
        # Transmit packet 16
        rec_pkt = {
            "session_id": sess_id,
            "sequence_number": 16,
            "sender_timestamp": t0 + 4.1,
            "payload_size": 256,
            "protocol_version": "1.0",
            "client_rtt_ms": 20.0,
        }
        client.post("/api/communication/packet", json=rec_pkt)

        snap_recovering = client.get("/api/monitoring/status").json()
        assert snap_recovering["decision"]["status"] == "RECOVERING"
        assert snap_recovering["communication"]["is_recovering"] is True

        # 5. RESTABILIZE -> NORMAL
        # Re-initialize clean session flow and restore clean physical layer
        clean_sess = f"clean_flow_{int(time.time() * 1000)}"
        client.post(
            "/api/monitoring/session/start",
            json={
                "monitoring_session_id": f"mon_{clean_sess}",
                "communication_session_id": clean_sess,
                "auto_start_communication": True,
            },
        )
        client.post(
            "/api/monitoring/signal",
            json={
                "predicted_modulation": "16-QAM",
                "ai_confidence": 0.99,
                "estimated_snr_db": 18.0,
                "signal_quality": "EXCELLENT",
            },
        )
        t_clean = time.time()
        for seq in range(1, 4):
            client.post(
                "/api/communication/packet",
                json={
                    "session_id": clean_sess,
                    "sequence_number": seq,
                    "sender_timestamp": t_clean + seq * 0.1,
                    "payload_size": 256,
                    "protocol_version": "1.0",
                    "client_rtt_ms": 12.0,
                },
            )

        snap_final = client.get("/api/monitoring/status").json()
        assert snap_final["decision"]["status"] == "NORMAL"
        assert snap_final["decision"]["consistency"] == "CONSISTENT"

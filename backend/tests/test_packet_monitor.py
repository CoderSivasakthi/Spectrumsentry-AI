"""Unit and integration tests for Phase 5 PacketMonitor and SessionMonitor."""

import time
import pytest
from backend.app.communication.packet_monitor import PacketMonitor, SessionMonitor
from backend.app.database.database import SessionLocal, init_db
from backend.app.schemas.communication import (
    CommunicationStatus,
    PacketIn,
    SessionStartRequest,
    SessionStopRequest,
)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestSessionMonitor:
    """Tests for in-memory SessionMonitor logic."""

    def test_normal_packet_flow(self):
        monitor = SessionMonitor(session_id="norm_sess", timeout_seconds=2.0)
        t0 = 1000.0

        for seq in range(1, 11):
            pkt = PacketIn(
                session_id="norm_sess",
                sequence_number=seq,
                sender_timestamp=t0 + (seq - 1) * 0.25,
                payload_size=1024,
                client_rtt_ms=15.0,
            )
            ack, evts = monitor.record_packet(pkt, t0 + (seq - 1) * 0.25 + 0.015)
            assert ack.sequence_number == seq
            assert ack.status in (CommunicationStatus.CONNECTED, CommunicationStatus.STARTING)

        metrics = monitor.get_metrics()
        assert metrics.packets_received == 10
        assert metrics.packets_lost == 0
        assert metrics.packet_loss_percent == 0.0
        assert metrics.avg_latency_ms == 15.0
        assert metrics.jitter_ms == 0.0
        assert metrics.status == CommunicationStatus.CONNECTED
        assert metrics.health_score == 100.0

    def test_missing_packets_detection(self):
        monitor = SessionMonitor(session_id="gap_sess", timeout_seconds=2.0)
        t0 = 1000.0

        # Packets 1, 2, 5 (missing 3 and 4)
        for seq in [1, 2, 5]:
            pkt = PacketIn(
                session_id="gap_sess",
                sequence_number=seq,
                sender_timestamp=t0 + seq * 0.25,
                payload_size=512,
                client_rtt_ms=20.0,
            )
            monitor.record_packet(pkt, t0 + seq * 0.25 + 0.02)

        metrics = monitor.get_metrics()
        assert metrics.packets_sent == 5
        assert metrics.packets_received == 3
        assert metrics.packets_lost == 2
        assert metrics.packet_loss_percent == 40.0
        # Health score penalized for 40% loss
        assert metrics.health_score < 70.0

    def test_duplicate_packet_handling(self):
        monitor = SessionMonitor(session_id="dup_sess", timeout_seconds=2.0)
        t0 = 1000.0

        for seq in [1, 2, 2, 3]:
            pkt = PacketIn(
                session_id="dup_sess",
                sequence_number=seq,
                sender_timestamp=t0 + seq * 0.25,
                payload_size=500,
                client_rtt_ms=10.0,
            )
            monitor.record_packet(pkt, t0 + seq * 0.25 + 0.01)

        assert monitor.duplicate_count == 1
        metrics = monitor.get_metrics()
        assert metrics.packets_received == 3  # Not 4
        assert metrics.packets_sent == 3
        assert metrics.packets_lost == 0

    def test_out_of_order_packets(self):
        monitor = SessionMonitor(session_id="ooo_sess", timeout_seconds=2.0)
        t0 = 1000.0

        # Receive 1, 3, then 2
        monitor.record_packet(
            PacketIn(session_id="ooo_sess", sequence_number=1, sender_timestamp=t0, payload_size=100),
            t0 + 0.01,
        )
        monitor.record_packet(
            PacketIn(session_id="ooo_sess", sequence_number=3, sender_timestamp=t0 + 0.5, payload_size=100),
            t0 + 0.51,
        )
        # At this point, packet 2 is missing
        assert monitor.get_metrics().packets_lost == 1

        # Now packet 2 arrives late
        monitor.record_packet(
            PacketIn(session_id="ooo_sess", sequence_number=2, sender_timestamp=t0 + 0.25, payload_size=100),
            t0 + 0.60,
        )
        assert monitor.out_of_order_count == 1
        # Loss resolves to 0
        metrics = monitor.get_metrics()
        assert metrics.packets_received == 3
        assert metrics.packets_lost == 0
        assert metrics.packet_loss_percent == 0.0

    def test_interruption_and_recovery_flow(self):
        monitor = SessionMonitor(session_id="pause_sess", timeout_seconds=1.0)
        t0 = 1000.0

        # Packet 1 at t=1000.0
        monitor.record_packet(
            PacketIn(session_id="pause_sess", sequence_number=1, sender_timestamp=t0, payload_size=1000),
            t0,
        )
        assert monitor.status == CommunicationStatus.CONNECTED

        # Tick at t=1001.5 (1.5s > 1.0s timeout)
        evt = monitor.check_timeout_tick(t0 + 1.5)
        assert evt is not None
        assert evt["event_type"] == "INTERRUPTION"
        assert monitor.status == CommunicationStatus.INTERRUPTED
        assert monitor.health_score <= 25.0

        # Packet 2 arrives at t=1003.0 (resumes after 3.0s pause -> transitions to RECOVERING)
        ack, evts = monitor.record_packet(
            PacketIn(session_id="pause_sess", sequence_number=2, sender_timestamp=t0 + 3.0, payload_size=1000),
            t0 + 3.0,
        )
        assert monitor.status == CommunicationStatus.RECOVERING
        assert monitor.interruption_detector.interruption_counter == 1
        assert monitor.recovery_detector.recovery_count == 1
        assert monitor.interruption_detector.total_interruption_duration_ms == 3000.0

        # Packet 3 arrives at t=1003.25 (link stabilized -> transitions to CONNECTED)
        ack, evts = monitor.record_packet(
            PacketIn(session_id="pause_sess", sequence_number=3, sender_timestamp=t0 + 3.25, payload_size=1000),
            t0 + 3.25,
        )
        assert monitor.status == CommunicationStatus.CONNECTED



class TestPacketMonitorManager:
    """Tests for central PacketMonitor and database persistence."""

    def test_session_lifecycle_and_db_persistence(self, db_session):
        mgr = PacketMonitor()
        sess_id = f"test_db_sess_{int(time.time() * 1000)}"

        # 1. Start session
        start_req = SessionStartRequest(session_id=sess_id, expected_packets=10, timeout_seconds=2.0)
        start_resp = mgr.start_session(start_req, db_session)
        assert start_resp.session_id == sess_id

        # 2. Ingest packets (sync helper wrapper)
        for seq in range(1, 6):
            pkt = PacketIn(
                session_id=sess_id,
                sequence_number=seq,
                sender_timestamp=time.time(),
                payload_size=512,
                client_rtt_ms=12.5,
            )
            # In unit test, calling monitor record directly or calling ingest_packet with event loop
            mgr.sessions[sess_id].record_packet(pkt, time.time())

        # 3. Stop session
        stop_req = SessionStopRequest(session_id=sess_id)
        summary = mgr.stop_session(stop_req, db_session)

        assert summary.session_id == sess_id
        assert summary.packets_received == 5
        assert summary.packets_sent == 10  # from expected_packets
        assert summary.packets_lost == 5
        assert summary.packet_loss_percent == 50.0
        assert summary.final_status == "STOPPED"

        # 4. Query DB history
        history = mgr.get_history(db_session, skip=0, limit=10)
        found = any(s.session_id == sess_id for s in history.items)
        assert found is True

        # 5. Query single session details
        details = mgr.get_session_details(sess_id, db_session)
        assert details is not None
        assert details.session_id == sess_id

    def test_session_isolation(self, db_session):
        mgr = PacketMonitor()
        sess_a = "session_alpha"
        sess_b = "session_beta"

        mgr.start_session(SessionStartRequest(session_id=sess_a), db_session)
        mgr.start_session(SessionStartRequest(session_id=sess_b), db_session)

        t = time.time()
        mgr.sessions[sess_a].record_packet(
            PacketIn(session_id=sess_a, sequence_number=1, sender_timestamp=t, payload_size=100), t
        )
        mgr.sessions[sess_b].record_packet(
            PacketIn(session_id=sess_b, sequence_number=1, sender_timestamp=t, payload_size=200), t
        )
        mgr.sessions[sess_b].record_packet(
            PacketIn(session_id=sess_b, sequence_number=2, sender_timestamp=t + 0.1, payload_size=200), t + 0.1
        )

        metrics_a = mgr.get_live_metrics(sess_a)
        metrics_b = mgr.get_live_metrics(sess_b)

        assert metrics_a.packets_received == 1
        assert metrics_a.bytes_received == 100
        assert metrics_b.packets_received == 2
        assert metrics_b.bytes_received == 400

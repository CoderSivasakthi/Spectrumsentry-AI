"""Per-device session registry tests.

Verifies that each device owns its own monitoring + communication session pair,
that stopping one device does not disturb another, that the shared signal
pipeline only stops when the last device leaves, and that WebSocket snapshots
can be targeted at a single device.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from backend.app.communication.packet_monitor import packet_monitor
from backend.app.database.database import SessionLocal, init_db
from backend.app.main import app
from backend.app.monitoring.unified_manager import unified_monitor
from backend.app.schemas.communication import (
    CommunicationStatus,
    PacketIn,
    SessionStartRequest,
    SessionStopRequest,
)
from backend.app.schemas.monitoring import (
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
)
from backend.app.websocket.manager import WebSocketConnection, ConnectionManager


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def reset_unified_state():
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None
    unified_monitor.device_sessions.clear()
    packet_monitor.sessions.clear()
    packet_monitor.active_session_id = None
    yield
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None
    unified_monitor.device_sessions.clear()
    packet_monitor.sessions.clear()
    packet_monitor.active_session_id = None


class TestDeviceSessionIsolation:
    def test_start_for_two_devices_registers_both(self, db):
        """Two devices starting sessions each own an isolated session pair."""
        resp_a = unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="devA_mon",
                auto_start_communication=True,
                interval_seconds=0.1,
                timeout_seconds=2.0,
            ),
            db,
            device_id="device_a",
            device_name="Laptop-A",
        )
        resp_b = unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="devB_mon",
                auto_start_communication=True,
                interval_seconds=0.1,
                timeout_seconds=2.0,
            ),
            db,
            device_id="device_b",
            device_name="Phone-B",
        )

        assert resp_a.monitoring_session_id == "devA_mon"
        assert resp_b.monitoring_session_id == "devB_mon"
        assert resp_a.communication_session_id != resp_b.communication_session_id

        assert set(unified_monitor.device_sessions.keys()) == {"device_a", "device_b"}
        assert (
            unified_monitor.device_sessions["device_a"]["monitoring_session_id"] == "devA_mon"
        )
        assert (
            unified_monitor.device_sessions["device_b"]["communication_session_id"]
            == resp_b.communication_session_id
        )

    def test_stopping_one_device_leaves_the_other_active(self, db):
        unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="isoA_mon", auto_start_communication=True
            ),
            db,
            device_id="device_a",
        )
        unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="isoB_mon", auto_start_communication=True
            ),
            db,
            device_id="device_b",
        )

        summary = unified_monitor.stop_session(
            MonitoringSessionStopRequest(
                monitoring_session_id=None, stop_communication=True
            ),
            db,
            device_id="device_a",
        )
        assert summary.monitoring_session_id == "isoA_mon"
        assert summary.status == "STOPPED"

        # Device B still owns a live session, device A is deregistered
        assert "device_a" not in unified_monitor.device_sessions
        assert "device_b" in unified_monitor.device_sessions
        # The device B comm session is untouched and still active
        comm_b = unified_monitor.device_sessions["device_b"]["communication_session_id"]
        assert packet_monitor.get_session_status(comm_b)["active"] is True
        # A device whose session is gone no longer resolves via the registry
        assert unified_monitor._entry_for_supervision_session("isoA_mon") is None

    def test_roster_reports_devices_and_link_metrics(self, db):
        unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="roster_mon", auto_start_communication=True
            ),
            db,
            device_id="device_a",
            device_name="Laptop-A",
            ip="192.168.1.50",
        )

        roster = unified_monitor.get_device_roster()
        assert roster.total == 1
        device = roster.devices[0]
        assert device.device_id == "device_a"
        assert device.device_name == "Laptop-A"
        assert device.monitoring_session_id == "roster_mon"
        assert device.communication_session_id is not None
        assert device.health_score is not None

    def test_direct_comm_session_device_appears_in_roster(self, db):
        """Sender-page style sessions (started outside the unified manager) still show up."""
        comm = packet_monitor.start_session(
            SessionStartRequest(
                extra_metadata={"device_id": "sender_1", "device_name": "Phone sender"}
            ),
            db,
        )
        roster = unified_monitor.get_device_roster()
        ids = [d.device_id for d in roster.devices]
        assert "sender_1" in ids
        entry = next(d for d in roster.devices if d.device_id == "sender_1")
        assert entry.communication_session_id == comm.session_id
        assert entry.device_name == "Phone sender"

    def test_stopped_direct_comm_session_leaves_roster(self, db):
        """A finished session is history, not a live device in the roster."""
        comm = packet_monitor.start_session(
            SessionStartRequest(
                extra_metadata={"device_id": "sender_2", "device_name": "Phone sender"}
            ),
            db,
        )
        assert unified_monitor.get_device_roster().total == 1

        packet_monitor.stop_session(SessionStopRequest(session_id=comm.session_id), db)
        roster = unified_monitor.get_device_roster()
        assert roster.total == 0
        assert [d.device_id for d in roster.devices] == []


class TestTargetedBroadcasts:
    def test_broadcast_targets_only_one_device(self):
        """A device-tagged broadcast reaches that device's sockets only."""

        class FakeSocket:
            def __init__(self):
                self.sent = []

            async def send_json(self, payload):
                self.sent.append(payload)

        mgr = ConnectionManager()
        socket_a, socket_b = FakeSocket(), FakeSocket()
        mgr.connections[socket_a] = WebSocketConnection(device_id="device_a")
        mgr.connections[socket_b] = WebSocketConnection(device_id="device_b")

        asyncio.run(
            mgr.broadcast({"type": "monitoring_snapshot", "data": {}}, device_id="device_a")
        )

        assert len(socket_a.sent) == 1
        assert len(socket_b.sent) == 0

    def test_broadcast_to_all_fans_out(self):
        class FakeSocket:
            def __init__(self):
                self.sent = []

            async def send_json(self, payload):
                self.sent.append(payload)

        mgr = ConnectionManager()
        sockets = [FakeSocket() for _ in range(3)]
        for i, ws in enumerate(sockets):
            mgr.connections[ws] = WebSocketConnection(device_id=f"dev_{i}")

        asyncio.run(mgr.broadcast({"type": "devices_changed", "data": {}}))
        assert all(len(ws.sent) == 1 for ws in sockets)

    def test_failed_send_drops_socket_without_breaking_broadcast(self):
        class FlakySocket:
            async def send_json(self, payload):
                raise RuntimeError("socket went away")

        class FakeSocket:
            def __init__(self):
                self.sent = []

            async def send_json(self, payload):
                self.sent.append(payload)

        mgr = ConnectionManager()
        flaky, healthy = FlakySocket(), FakeSocket()
        mgr.connections[flaky] = WebSocketConnection(device_id="device_a")
        mgr.connections[healthy] = WebSocketConnection(device_id="device_b")
        asyncio.run(mgr.broadcast({"type": "monitoring_snapshot", "data": {}}))
        assert len(healthy.sent) == 1
        assert flaky not in mgr.connections


class TestDeviceHandshake:
    def test_on_device_connected_reuses_session_within_reload(self, db):
        """A reconnecting device (page reload) keeps its session."""
        started = unified_monitor.on_device_connected(
            device_id="device_a", device_name="Laptop-A", ip="192.168.1.50"
        )
        assert started["reused"] is False
        assert unified_monitor.device_sessions["device_a"]["monitoring_session_id"] == started[
            "monitoring_session_id"
        ]

        again = unified_monitor.on_device_connected(device_id="device_a")
        assert again["reused"] is True
        assert again["monitoring_session_id"] == started["monitoring_session_id"]

    def test_device_disconnect_holds_session_immediately(self, db):
        """On disconnect the session is not torn down at once (grace period)."""
        unified_monitor.on_device_connected(device_id="device_a")

        async def fire_disconnect():
            unified_monitor.on_device_disconnected("device_a")

        asyncio.run(fire_disconnect())
        # Entry survives the initial disconnect event
        assert "device_a" in unified_monitor.device_sessions
        assert unified_monitor.device_sessions["device_a"].get("pending_stop") is not None

    def test_start_session_without_device_defaults_local(self, db):
        """API callers that do not send a device id still work (legacy path)."""
        resp = unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id="legacy_mon", auto_start_communication=False
            ),
            db,
        )
        assert resp.monitoring_session_id == "legacy_mon"
        assert "local" in unified_monitor.device_sessions
        entry = unified_monitor.device_sessions["local"]
        assert entry["monitoring_session_id"] == "legacy_mon"
        # Device id landed in persisted metadata
        from backend.app.database.repository import MonitoringSessionRepository

        stored = MonitoringSessionRepository(db).get_by_id("legacy_mon")
        assert stored.extra_metadata and stored.extra_metadata.get("device_id") == "local"

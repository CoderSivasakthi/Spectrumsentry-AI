"""CSV session report endpoint tests.

The CSV export must render real, sectioned tables (SUMMARY / EVENTS /
DECISIONS / ALERTS) — not a flattened path,value dump of the JSON report.
"""

import csv
import io
import time
import pytest
from fastapi.testclient import TestClient

from backend.app.database.database import init_db
from backend.app.main import app
from backend.app.monitoring.unified_manager import unified_monitor


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_unified_state():
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None
    unified_monitor.device_sessions.clear()
    yield
    unified_monitor.clear_signal_evidence()
    unified_monitor.active_monitoring_session_id = None
    unified_monitor.active_communication_session_id = None
    unified_monitor.device_sessions.clear()


def _seed_session(client: TestClient, suffix: str) -> str:
    """Start a monitoring session, push a packet, and stop it cleanly."""
    mon_id = f"csv_mon_{suffix}"
    start_payload = {
        "monitoring_session_id": mon_id,
        "auto_start_communication": True,
        "interval_seconds": 0.05,
        "timeout_seconds": 2.0,
        "extra_metadata": {
            "device_id": f"dev_{suffix}",
            "device_name": "Laptop-CSV",
        },
    }
    res = client.post("/api/monitoring/session/start", json=start_payload)
    assert res.status_code == 201, res.text
    comm_id = res.json()["communication_session_id"]

    packet = {
        "session_id": comm_id,
        "sequence_number": 1,
        "sender_timestamp": time.time(),
        "payload_size": 512,
        "client_rtt_ms": 12.0,
    }
    res = client.post("/api/communication/packet", json=packet)
    assert res.status_code == 200, res.text

    res = client.post("/api/monitoring/session/stop", json={"monitoring_session_id": mon_id})
    assert res.status_code == 200, res.text
    return mon_id


def _parse_csv(text: str):
    # Skip the Excel BOM
    body = text.lstrip("﻿")
    return list(csv.reader(io.StringIO(body)))


class TestCsvReportEndpoint:
    def test_csv_download_headers_and_structure(self, client):
        mon_id = _seed_session(client, "1")
        res = client.get(f"/api/monitoring/session/{mon_id}/report.csv")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert f"attachment; filename=" in res.headers.get("content-disposition", "")
        assert mon_id in res.headers["content-disposition"]

        rows = _parse_csv(res.text)
        assert rows[0] == ["SUMMARY"]
        header = rows[1]
        assert header[:2] == ["field", "value"]
        section_names = [row[0] for row in rows if len(row) == 1 and row[0]]
        assert "EVENTS" in section_names
        assert "DECISIONS" in section_names
        assert "ALERTS" in section_names

    def test_csv_contains_key_metrics_from_the_session(self, client):
        mon_id = _seed_session(client, "2")
        res = client.get(f"/api/monitoring/session/{mon_id}/report.csv")
        assert res.status_code == 200
        rows = _parse_csv(res.text)
        fields = {}
        # Summary section: walk rows of [field, value] until the blank row before EVENTS
        for row in rows[2:]:
            if len(row) >= 2 and row[0] and row[0] not in ("EVENTS",):
                fields[row[0]] = row[1]
            elif row and row[0] == "" :
                break
        assert fields.get("monitoring_session_id") == mon_id
        assert fields.get("device_name") == "Laptop-CSV"
        assert fields.get("device_id") == "dev_2"
        assert fields.get("packets_received") == "1"
        assert fields.get("health_score") not in ("", None)

    def test_events_table_has_real_rows(self, client):
        mon_id = _seed_session(client, "3")
        res = client.get(f"/api/monitoring/session/{mon_id}/report.csv")
        rows = _parse_csv(res.text)
        events_idx = next(i for i, row in enumerate(rows) if row and row[0] == "EVENTS")
        events_header = rows[events_idx + 1]
        assert events_header[:3] == ["timestamp", "event_type", "duration_ms"]
        # At least the packet event caused at least one communication event row
        data_rows = [
            row
            for row in rows[events_idx + 2:]
            if row and row[0] != "" and row[0] not in ("DECISIONS", "ALERTS")
        ]
        assert len(data_rows) >= 1

    def test_unknown_session_returns_404(self, client):
        res = client.get("/api/monitoring/session/no_such_session/report.csv")
        assert res.status_code == 404

    def test_legacy_json_report_still_available(self, client):
        mon_id = _seed_session(client, "4")
        res = client.get(f"/api/monitoring/session/{mon_id}/report")
        assert res.status_code == 200
        payload = res.json()
        assert payload["monitoring_session"]["monitoring_session_id"] == mon_id

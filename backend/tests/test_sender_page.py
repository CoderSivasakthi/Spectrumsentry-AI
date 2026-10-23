"""Tests for the /sender phone-browser page and its flow-critical API contract."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


class TestSenderPage:
    """Corrected report fix #1: browser-based sender available as HTML route."""

    def test_sender_route_serves_html(self, client):
        res = client.get("/sender")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert res.text.lstrip().startswith("<!DOCTYPE html>")

    def test_sender_page_uses_packet_api(self, client):
        res = client.get("/sender")
        # The page must drive the real monitored endpoints
        assert "/api/communication/session/start" in res.text
        assert "/api/communication/packet" in res.text
        assert "client_rtt_ms" in res.text
        assert "/api/communication/session/stop" in res.text

    def test_sender_page_documents_hotspot_use(self, client):
        # Phone-hostname hint must be present so the page guides the hotspot test
        html = client.get("/sender").text
        assert "server-host" in html          # hotspot hostname hint in the log
        assert "pause" in html.lower()        # simulated pause control exists

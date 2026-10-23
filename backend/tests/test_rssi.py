"""Tests for the optional Wi-Fi RSSI stream (corrected report fix #13)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.communication import rssi as rssi_module
from backend.app.main import app

NETSH_SAMPLE = """
Name                   : Wi-Fi
Description            : Realtek Wireless LAN
State                  : connected
 SSID
 BSSID                 : ab:cd:ef:11:22:33
 Authentication        : WPA2-Personal
 Signal                : 88%
 Receive rate (Mbps)   : 144.4
"""


class TestCollectors:
    """Lenient OS-CLI parsers."""

    def test_windows_netsh_parse(self, monkeypatch):
        fake_run = lambda *a, **kw: SimpleNamespace(stdout=NETSH_SAMPLE)
        monkeypatch.setattr(rssi_module.subprocess, "run", fake_run)
        monkeypatch.setattr(rssi_module.shutil, "which", lambda _: True)

        sample = rssi_module._collect_windows()

        assert sample is not None
        assert sample.platform == "windows"
        assert sample.rssi_dbm == pytest.approx(88 / 2 - 100)  # 88% -> -56 dBm
        assert sample.dbm_estimate is True
        assert sample.link_id is not None

    def test_windows_missing_cli_returns_none(self, monkeypatch):
        monkeypatch.setattr(rssi_module.shutil, "which", lambda _: None)
        assert rssi_module._collect_windows() is None

    def test_windows_garbage_output_returns_none(self, monkeypatch):
        fake_run = lambda *a, **kw: SimpleNamespace(stdout="nonsense")
        monkeypatch.setattr(rssi_module.subprocess, "run", fake_run)
        monkeypatch.setattr(rssi_module.shutil, "which", lambda _: True)
        assert rssi_module._collect_windows() is None

    def test_linux_iw_parse(self, monkeypatch):
        out = "Connected to 3c:37:86:xx\n\tfreq: 5180\n\tsignal: -51.00 dBm\n\tnoise: -95.00 dBm\n"
        fake_run = lambda *a, **kw: SimpleNamespace(stdout=out)
        monkeypatch.setattr(rssi_module.subprocess, "run", fake_run)
        monkeypatch.setattr(rssi_module.shutil, "which", lambda _: True)

        sample = rssi_module._collect_linux("wlan0")

        assert sample is not None
        assert sample.platform == "linux"
        assert sample.rssi_dbm == pytest.approx(-51.0)
        assert sample.noise_floor_dbm == pytest.approx(-95.0)
        assert sample.dbm_estimate is False


class TestDispatcher:
    """collect_rssi routing and safety."""

    def test_unsupported_platform_returns_none(self, monkeypatch):
        monkeypatch.setattr(rssi_module.sys, "platform", "winvx")
        collected = rssi_module.collect_rssi()
        assert collected is None

    def test_collector_exception_swallowed(self, monkeypatch):
        def boom(*a, **kw):
            raise RuntimeError("x")
        monkeypatch.setattr(rssi_module.sys, "platform", "win32")
        monkeypatch.setitem(rssi_module._COLLECTORS, "win32", boom)
        assert rssi_module.collect_rssi() is None


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


class TestRssiEndpoint:
    """/api/communication/wifi/rssi stream endpoint."""

    def test_unsupported_platform_marks_unavailable(self, client, monkeypatch):
        monkeypatch.setattr(rssi_module.sys, "platform", "winvx")  # nothing resolvable
        res = client.get("/api/communication/wifi/rssi")

        assert res.status_code == 200
        body = res.json()
        assert body["available"] is False
        assert body["detail"]

    def test_available_sample_shape(self, client, monkeypatch):
        sample = rssi_module.RssiSample(
            rssi_dbm=-63.5, noise_floor_dbm=None, link_id="Hotspot_Foo",
            platform="windows", dbm_estimate=True,
            timestamp=__import__("datetime").datetime.now(
                tz=__import__("datetime").timezone.utc
            ),
            source="synthetic",
        )
        monkeypatch.setattr(rssi_module, "collect_rssi", lambda iface=None: sample)

        res = client.get("/api/communication/wifi/rssi")

        assert res.status_code == 200
        body = res.json()
        assert body["available"] is True
        assert body["rssi_dbm"] == -63.5
        assert body["link_id"] == "Hotspot_Foo"
        assert body["dbm_estimate"] is True
        assert body["timestamp"].endswith("Z") or "+" in body["timestamp"]

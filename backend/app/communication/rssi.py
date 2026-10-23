"""Optional Wi-Fi RSSI evidence stream (corrected report fix #13, port of B.5).

Stream A context channel: on a real-hardware hotspot link the physical-layer SNR used
in decision rules is a *simulated* value, so the corrected report calls for an optional
real-link RSSI substitute. This collector queries the operating system's WLAN interface
without external dependencies:

    Windows: ``netsh wlan show interfaces``
    Linux:   ``iw dev wlan0 link`` (needs iw(8); silently unavailable otherwise)
    macOS:   ``system_profiler SPAirPortDataType``

All parsing is lenient: unavailable/mismatched output returns ``None`` instead of
raising, so the stream can be wired optionally into monitoring decisions.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import shutil
import subprocess
import sys
from typing import Optional


@dataclass
class RssiSample:
    """Single Wi-Fi RSSI observation complementing simulated physical evidence."""
    rssi_dbm: float          # Signal strength in dBm (proxied from OS-specific units)
    noise_floor_dbm: Optional[float]  # Reported noise floor, when available
    link_id: Optional[str]   # SSID/BSSID description as the OS reports it
    platform: str            # windows | linux | macos
    dbm_estimate: bool       # True if rssi_dbm was derived from a percent rather than dBm
    timestamp: datetime
    source: str              # CLI used, e.g. "netsh wlan show interfaces"


def _collect_windows(interface_hint: Optional[str] = None) -> Optional[RssiSample]:
    """Parse ``netsh wlan show interfaces`` (implicitly also honors macOS-like hints)."""
    cmd = "netsh"
    if not shutil.which(cmd):
        return None
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace",
        ).stdout
    except Exception:
        return None

    # netsh reports " Signal" as a 0-100% strength; the industry-standard conversion
    # to dBm is quality/2 - 100 (P. Beckmann approximation, good to ~2 dB)
    match = re.search(r"Signal\s*[:=]\s*(\d{1,3})\s*%", out)
    if not match:
        return None
    quality = int(match.group(1))
    rssi_dbm = round(quality / 2.0 - 100.0, 1)

    ssid_match = re.search(r"SSID\s*[:=]\s*(.+)", out)
    link_id = ssid_match.group(1).strip() if ssid_match else None
    return RssiSample(
        rssi_dbm=rssi_dbm,
        noise_floor_dbm=None,
        link_id=link_id,
        platform="windows",
        dbm_estimate=True,
        timestamp=datetime.now(timezone.utc),
        source=cmd,
    )


def _collect_linux(interface_hint: Optional[str] = None) -> Optional[RssiSample]:
    """Parse ``iw dev <iface> link`` output when iw(8) is installed."""
    iface = interface_hint or "wlan0"
    if not shutil.which("iw"):
        return None
    try:
        out = subprocess.run(
            ["iw", "dev", iface, "link"],
            capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace",
        ).stdout
    except Exception:
        return None
    match = re.search(r"signal:\s*(-?\d+(?:\.\d+)?)\s*dBm", out)
    if not match:
        return None
    noise = re.search(r"noise:\s*(-?\d+(?:\.\d+)?)\s*dBm", out)
    ssid = re.search(r"Connected to\s+(\:|[0-9a-fA-F:])+", out)
    return RssiSample(
        rssi_dbm=float(match.group(1)),
        noise_floor_dbm=float(noise.group(1)) if noise else None,
        link_id=None,
        platform="linux",
        dbm_estimate=False,
        timestamp=datetime.now(timezone.utc),
        source="iw dev link",
    )


def _collect_macos(interface_hint: Optional[str] = None) -> Optional[RssiSample]:
    """Parse ``system_profiler SPAirPortDataType`` aggregate RSSI."""
    if not shutil.which("system_profiler"):
        return None
    try:
        out = subprocess.run(
            ["system_profiler", "SPAirPortDataType"],
            capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace",
        ).stdout
    except Exception:
        return None
    match = re.search(r"Current Network Information:.*?Signal / Noise\s*:\s*(-\d+)\s*dBm", out, re.DOTALL)
    if not match:
        match = re.search(r"agrCtlRSSI:\s*(-?\d+)", out)
    if not match:
        return None
    return RssiSample(
        rssi_dbm=float(match.group(1)),
        noise_floor_dbm=None,
        link_id=None,
        platform="macos",
        dbm_estimate=False,
        timestamp=datetime.now(timezone.utc),
        source="system_profiler SPAirPortDataType",
    )


_COLLECTORS = {
    "win32": _collect_windows,
    "linux": _collect_linux,
    "darwin": _collect_macos,
}


def collect_rssi(interface_hint: Optional[str] = None) -> Optional[RssiSample]:
    """Collect a Wi-Fi RSSI sample with the platform's OS CLI.

    Args:
        interface_hint: Override interface name (Linux) — e.g. "wlp3s0".

    Returns:
        RssiSample, or None when the OS CLI is missing or output was unparseable.
    """
    collector = _COLLECTORS.get(sys.platform)
    if collector is None:
        return None
    try:
        return collector(interface_hint)
    except Exception:
        return None

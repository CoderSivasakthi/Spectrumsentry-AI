"""WebSocket connection managers for real-time telemetry broadcasting.

Connections carry device identity (from the WS handshake query params) so
snapshots can be targeted at the owning device instead of mirroring one
global session to every open client.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket

from backend.app.database.models import utc_now


class WebSocketConnection:
    """Identity-carrying metadata attached to one live WebSocket connection."""

    def __init__(
        self,
        device_id: str,
        device_name: Optional[str] = None,
        ip: Optional[str] = None,
        connected_at: Optional[datetime] = None,
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.ip = ip
        self.connected_at = connected_at or utc_now()


class ConnectionManager:
    """Manage device-tagged WebSocket connections and broadcast telemetry.

    ``broadcast(payload, device_id=None)`` sends to everyone when no device
    id is given, and only to that device's connections when one is — that is
    what lets a per-device snapshot reach exactly the console that owns it.
    """

    def __init__(self):
        self.connections: Dict[WebSocket, WebSocketConnection] = {}

    async def connect(self, websocket: WebSocket, device_id: str = "local", device_name: Optional[str] = None, ip: Optional[str] = None):
        conn = WebSocketConnection(device_id=device_id, device_name=device_name, ip=ip)
        await websocket.accept()
        self.connections[websocket] = conn

    def disconnect(self, websocket: WebSocket):
        self.connections.pop(websocket, None)

    @property
    def active_connections(self) -> List[WebSocket]:
        """Back-compat view of live sockets (list of WebSocket objects)."""
        return list(self.connections.keys())

    async def broadcast(self, message: dict, device_id: Optional[str] = None):
        """Broadcast to all connections, or only to those of one device.

        A send failure drops that socket from the registry and continues.
        """
        if device_id is None:
            targets = list(self.connections.keys())
        else:
            targets = [ws for ws, conn in list(self.connections.items()) if conn.device_id == device_id]
        for websocket in targets:
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)

    async def send_to_device(self, device_id: str, message: dict):
        """Send a payload to every live connection of one device (no-op if none)."""
        await self.broadcast(message, device_id=device_id)

    def get_device_connection_count(self, device_id: str) -> int:
        return sum(1 for conn in self.connections.values() if conn.device_id == device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        """Aggregate connections by device_id into per-device summaries."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for conn in self.connections.values():
            entry = grouped.setdefault(
                conn.device_id,
                {
                    "device_id": conn.device_id,
                    "device_name": conn.device_name,
                    "ips": [],
                    "first_connected_at": conn.connected_at,
                    "connection_count": 0,
                },
            )
            entry["connection_count"] += 1
            if conn.device_name and not entry["device_name"]:
                entry["device_name"] = conn.device_name
            if conn.ip and conn.ip not in entry["ips"]:
                entry["ips"].append(conn.ip)
            if conn.connected_at and entry["first_connected_at"] and conn.connected_at < entry["first_connected_at"]:
                entry["first_connected_at"] = conn.connected_at
        return list(grouped.values())


ws_manager = ConnectionManager()
monitoring_ws_manager = ConnectionManager()

"""Main FastAPI application entry point for SpectrumSentry AI."""

from contextlib import asynccontextmanager
import logging
from typing import Dict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from backend.app.api.routes import api_router
from backend.app.config.settings import get_settings
from backend.app.database.database import init_db

settings = get_settings()
logger = logging.getLogger("spectrumsentry.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    # Ensure database tables and storage folders are initialized
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Based Wireless Communication Monitoring & Signal Analysis Platform",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/", summary="Root status endpoint")
async def root() -> Dict[str, str]:
    """Root endpoint returning application name and execution status."""
    return {
        "name": "SpectrumSentry AI",
        "status": "running",
    }


@app.get("/health", summary="Health check endpoint")
async def health_check() -> Dict[str, str]:
    """Health check endpoint to verify backend service availability."""
    return {
        "status": "healthy",
    }


@app.get(
    "/sender",
    response_class=HTMLResponse,
    summary="Phone-browser packet sender page",
    description=(
        "Corrected report fix #1: self-contained browser test client for phone-based "
        "hotspot runs (test cases TC-01 to TC-04). Open http://<server-host>:" + str(settings.PORT) + "/sender "
        "on the phone; it measures RTT on the sender clock and can simulate radio pauses."
    ),
)
async def sender_page() -> HTMLResponse:
    """Serve the standalone HTML sender page for real device tests."""
    html_path = Path(__file__).resolve().parent / "static" / "sender.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"), status_code=200)


@app.websocket("/ws/communication")
async def websocket_communication_endpoint(websocket: WebSocket):
    """WebSocket endpoint broadcasting real-time communication monitoring telemetry."""
    from backend.app.communication.packet_monitor import packet_monitor
    from backend.app.websocket.manager import ws_manager

    await ws_manager.connect(websocket)
    # Send initial status
    try:
        metrics = packet_monitor.get_live_metrics()
        initial_payload = {
            "type": "communication_metrics",
            "session_id": metrics.session_id,
            "status": metrics.status.value,
            "packets_sent": metrics.packets_sent,
            "packets_received": metrics.packets_received,
            "packet_loss_percent": metrics.packet_loss_percent,
            "latency_ms": metrics.latency_ms,
            "jitter_ms": metrics.jitter_ms,
            "throughput_mbps": metrics.throughput_mbps,
            "health_score": metrics.health_score,
            "interruption_count": metrics.interruption_count,
            "is_interrupted": metrics.is_interrupted,
        }
        await websocket.send_json(initial_payload)
        while True:
            # Keep connection open and receive optional client messages/pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


@app.websocket("/ws/monitoring")
async def websocket_monitoring_endpoint(websocket: WebSocket):
    """WebSocket endpoint broadcasting per-device unified monitoring snapshots and events.

    The handshake query carries the client's device identity (`device_id` +
    `device_name`, generated once in the browser's localStorage). Connecting
    auto-starts that device's own monitoring + link-test session; dropping the
    last connection for the device schedules a grace-period auto-stop so a
    reconnected/reloaded page keeps its session.
    """
    from backend.app.monitoring.unified_manager import unified_monitor
    from backend.app.websocket.manager import monitoring_ws_manager

    query = dict(websocket.query_params)
    device_id = query.get("device_id") or "local"
    device_name = query.get("device_name")
    client_ip = websocket.client.host if websocket.client else None

    # Ensure the device owns a live session pair before its first snapshot
    try:
        unified_monitor.on_device_connected(
            device_id=device_id, device_name=device_name, ip=client_ip
        )
    except Exception as exc:
        logger.warning(
            "Device auto-start failed for '%s': %s", device_id, exc
        )

    await monitoring_ws_manager.connect(
        websocket, device_id=device_id, device_name=device_name, ip=client_ip
    )
    try:
        # Send this device's unified monitoring snapshot
        snapshot = unified_monitor.get_current_snapshot(device_id=device_id)
        initial_payload = {
            "type": "monitoring_snapshot",
            "timestamp": snapshot.timestamp.isoformat(),
            "data": snapshot.model_dump(mode="json"),
        }
        await websocket.send_json(initial_payload)
        while True:
            # Keep connection open and accept client heartbeats/pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        monitoring_ws_manager.disconnect(websocket)
        if monitoring_ws_manager.get_device_connection_count(device_id) == 0:
            unified_monitor.on_device_disconnected(device_id)
    except Exception:
        monitoring_ws_manager.disconnect(websocket)
        if monitoring_ws_manager.get_device_connection_count(device_id) == 0:
            unified_monitor.on_device_disconnected(device_id)


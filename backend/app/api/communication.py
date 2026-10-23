"""FastAPI communication monitoring API routes (Phase 5).

Provides endpoints for session lifecycle, packet ingestion, live telemetry,
status polling, and historical session queries.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.communication.packet_monitor import packet_monitor
from backend.app.database.database import get_db
from backend.app.schemas.communication import (
    CommunicationMetricsResponse,
    PacketAck,
    PacketIn,
    SessionHistoryResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStopRequest,
    SessionSummaryResponse,
)

router = APIRouter(prefix="/communication", tags=["Communication Monitoring"])


@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start communication monitoring session",
    description="Initializes a new in-memory packet tracker and persists initial session metadata.",
)
async def start_session(
    request: SessionStartRequest,
    db: Session = Depends(get_db),
) -> SessionStartResponse:
    """Initialize a new communication monitoring session."""
    try:
        return packet_monitor.start_session(request, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start session: {str(exc)}",
        ) from exc


@router.post(
    "/packet",
    response_model=PacketAck,
    status_code=status.HTTP_200_OK,
    summary="Ingest communication test packet",
    description="Processes an application-level test packet from the client, updates metrics, and returns ACK.",
)
async def ingest_packet(
    packet: PacketIn,
    db: Session = Depends(get_db),
) -> PacketAck:
    """Ingest a numbered, timestamped test packet."""
    try:
        return await packet_monitor.ingest_packet(packet, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process packet: {str(exc)}",
        ) from exc


@router.post(
    "/session/stop",
    response_model=SessionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop communication monitoring session",
    description="Finalizes aggregated session metrics, saves completed summary to database, and stops tracking.",
)
async def stop_session(
    request: SessionStopRequest,
    db: Session = Depends(get_db),
) -> SessionSummaryResponse:
    """Stop active session and finalize metrics."""
    try:
        return packet_monitor.stop_session(request, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop session: {str(exc)}",
        ) from exc


@router.get(
    "/status",
    summary="Get communication monitoring status",
    description="Returns high-level status, current health score, and interruption state.",
)
async def get_status(
    session_id: Optional[str] = Query(None, description="Optional target session ID"),
) -> Dict[str, Any]:
    """Return high-level status of active or specified session."""
    return packet_monitor.get_session_status(session_id)


@router.get(
    "/metrics",
    response_model=CommunicationMetricsResponse,
    summary="Get live communication metrics",
    description="Returns real-time latency, jitter, throughput, packet loss, and health score.",
)
async def get_metrics(
    session_id: Optional[str] = Query(None, description="Optional target session ID"),
) -> CommunicationMetricsResponse:
    """Return detailed live telemetry for active or specified session."""
    return packet_monitor.get_live_metrics(session_id)


@router.get(
    "/wifi/rssi",
    summary="Get Wi-Fi RSSI sample (optional real-link physical evidence)",
    description=(
        "Corrected report fix #13: optional stream of the OS-reported Wi-Fi signal "
        "strength to substitute for simulated SNR in real-link decisions. Returns "
        "available: false when no WLAN interface or parseable output exists."
    ),
)
async def get_wifi_rssi(
    interface: Optional[str] = Query(None, description="Optional Linux interface hint (e.g. wlp3s0)")
) -> Dict[str, Any]:
    """Collect one Wi-Fi RSSI sample from the operating system."""
    from backend.app.communication.rssi import RssiSample, collect_rssi

    sample: Optional[RssiSample] = collect_rssi(interface)
    if sample is None:
        return {
            "available": False,
            "detail": "No WLAN RSSI source available on this platform/configuration.",
        }
    return {
        "available": True,
        "rssi_dbm": sample.rssi_dbm,
        "noise_floor_dbm": sample.noise_floor_dbm,
        "link_id": sample.link_id,
        "platform": sample.platform,
        "dbm_estimate": sample.dbm_estimate,
        "timestamp": sample.timestamp.isoformat(),
        "source": sample.source,
    }


@router.get(
    "/history",
    response_model=SessionHistoryResponse,
    summary="Get communication session history",
    description="Returns paginated list of previously completed monitoring sessions from SQLite.",
)
async def get_history(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=200, description="Max items to retrieve"),
    db: Session = Depends(get_db),
) -> SessionHistoryResponse:
    """Retrieve historical completed sessions."""
    return packet_monitor.get_history(db, skip=skip, limit=limit)


@router.get(
    "/history/{session_id}",
    response_model=SessionSummaryResponse,
    summary="Get single session history with event log",
    description="Fetches detailed summary and full event log for a specific session.",
)
async def get_session_details(
    session_id: str,
    db: Session = Depends(get_db),
) -> SessionSummaryResponse:
    """Retrieve single session summary and discrete events."""
    summary = packet_monitor.get_session_details(session_id, db)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' not found.",
        )
    return summary

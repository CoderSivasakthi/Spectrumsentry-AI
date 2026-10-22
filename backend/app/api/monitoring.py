"""Unified real-time monitoring API routes (Phase 7).

Provides REST endpoints for unified cross-domain monitoring snapshots, session lifecycle,
signal evidence ingestion, operational status polling, and monitoring history.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.monitoring.unified_manager import unified_monitor
from backend.app.schemas.monitoring import (
    MonitoringHistoryResponse,
    MonitoringSessionResponse,
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
    MonitoringSessionSummary,
    SignalEvidenceInput,
    UnifiedMonitoringSnapshot,
)

router = APIRouter(prefix="/monitoring", tags=["Unified Monitoring"])


@router.get(
    "/status",
    response_model=UnifiedMonitoringSnapshot,
    summary="Get latest unified monitoring state",
    description="Returns the current cross-domain monitoring snapshot combining communication telemetry, physical-layer signal/AI evidence, DecisionEngine assessment, and active alerts.",
)
async def get_monitoring_status(
    session_id: Optional[str] = Query(None, description="Optional target communication session ID"),
    db: Session = Depends(get_db),
) -> UnifiedMonitoringSnapshot:
    """Fetch current real-time unified monitoring snapshot."""
    try:
        return unified_monitor.get_current_snapshot(db=db, session_id=session_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate unified monitoring snapshot: {str(exc)}",
        ) from exc


@router.post(
    "/session/start",
    response_model=MonitoringSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start unified monitoring session",
    description="Initiates a new unified monitoring session correlating physical-layer signal evidence with network communication monitoring.",
)
async def start_monitoring_session(
    request: MonitoringSessionStartRequest,
    db: Session = Depends(get_db),
) -> MonitoringSessionResponse:
    """Start unified monitoring session."""
    try:
        return unified_monitor.start_session(request, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start monitoring session: {str(exc)}",
        ) from exc


@router.post(
    "/session/stop",
    response_model=MonitoringSessionSummary,
    status_code=status.HTTP_200_OK,
    summary="Stop unified monitoring session",
    description="Terminates active monitoring session, finalizes database records, and stops linked communication session if configured.",
)
async def stop_monitoring_session(
    request: MonitoringSessionStopRequest,
    db: Session = Depends(get_db),
) -> MonitoringSessionSummary:
    """Stop active monitoring session."""
    try:
        return unified_monitor.stop_session(request, db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop monitoring session: {str(exc)}",
        ) from exc


@router.get(
    "/session/status",
    summary="Get operational session status",
    description="Returns high-level status of the active unified monitoring session including domain availability flags.",
)
async def get_session_status(
    session_id: Optional[str] = Query(None, description="Optional target session ID"),
) -> Dict[str, Any]:
    """Return operational session status."""
    return unified_monitor.get_session_status(session_id)


@router.post(
    "/signal",
    response_model=UnifiedMonitoringSnapshot,
    status_code=status.HTTP_200_OK,
    summary="Ingest physical-layer signal evidence",
    description="Ingests or updates signal evidence (including optional 23-feature vector for AI prediction), recalculates freshness, and returns updated unified snapshot.",
)
async def update_signal_evidence(
    signal_in: SignalEvidenceInput,
    db: Session = Depends(get_db),
) -> UnifiedMonitoringSnapshot:
    """Ingest fresh signal evidence and re-evaluate unified snapshot."""
    try:
        return unified_monitor.update_signal_evidence(signal_in, db=db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update signal evidence: {str(exc)}",
        ) from exc


@router.get(
    "/history",
    response_model=MonitoringHistoryResponse,
    summary="Get monitoring session history",
    description="Returns paginated list of previously completed unified monitoring sessions from SQLite.",
)
async def get_monitoring_history(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Max records to retrieve"),
    db: Session = Depends(get_db),
) -> MonitoringHistoryResponse:
    """Retrieve historical unified monitoring sessions."""
    return unified_monitor.get_history(db, skip=skip, limit=limit)

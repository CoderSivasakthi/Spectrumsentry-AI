"""Unified real-time monitoring API routes (Phase 7).

Provides REST endpoints for unified cross-domain monitoring snapshots, session lifecycle,
signal evidence ingestion, operational status polling, and monitoring history.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.database.models import Alert as AlertModel, utc_now
from backend.app.database.repository import (
    AlertRepository,
    CommunicationEventRepository,
    CommunicationSessionRepository,
    DecisionRepository,
    MonitoringSessionRepository,
)
from backend.app.monitoring.unified_manager import unified_monitor
from backend.app.schemas.monitoring import (
    MonitoringHistoryResponse,
    MonitoringSessionResponse,
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
    MonitoringSessionSummary,
    SignalEvidenceInput,
    SignalSimulateRequest,
    SignalSimulateResult,
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


@router.post(
    "/signal/simulate",
    response_model=SignalSimulateResult,
    status_code=status.HTTP_200_OK,
    summary="Simulate a physical signal and run the real AI classifier",
    description=(
        "Generates a synthetic modulated signal at the requested SNR, applies AWGN, extracts "
        "the 23-feature DSP vector, and runs the trained modulation classifier plus novelty "
        "detector on it. The resulting evidence replaces the current signal state and is "
        "broadcast to WebSocket subscribers."
    ),
)
async def simulate_signal(
    request: SignalSimulateRequest,
    db: Session = Depends(get_db),
) -> SignalSimulateResult:
    """Generate a synthetic signal, classify it through the real MLP pipeline, and ingest the evidence."""
    try:
        from math import isfinite

        import numpy as np

        from backend.app.signal_processing.features import extract_features
        from backend.app.signal_processing.generator import run_signal_experiment
        from backend.app.signal_processing.modulation import normalize_modulation_name

        experiment = run_signal_experiment(
            modulation=request.modulation,
            sample_count=request.sample_count,
            snr_db=request.snr_db,
            seed=request.seed,
        )
        features_vector, _feature_dict = extract_features(
            experiment.noisy_signal, sample_rate=experiment.sample_rate
        )
        noise_power = (
            float(np.mean(np.abs(experiment.noise) ** 2))
            if experiment.noise is not None and np.isfinite(np.mean(np.abs(experiment.noise) ** 2))
            else None
        )

        evidence = SignalEvidenceInput(
            features=[float(f) for f in np.asarray(features_vector, dtype=float)],
            estimated_snr_db=experiment.measured_snr_db,
            signal_power=float(experiment.signal_power),
            noise_power=noise_power,
            extra_data={
                "simulated": True,
                "requested_modulation": experiment.modulation,
                "requested_snr_db": request.snr_db,
                "sample_count": experiment.sample_count,
                "noise_type": experiment.noise_type,
            },
        )
        snapshot = unified_monitor.update_signal_evidence(evidence, db=db)

        signal = snapshot.signal
        canonical = normalize_modulation_name(request.modulation)
        return SignalSimulateResult(
            requested_modulation=canonical,
            requested_snr_db=request.snr_db,
            measured_snr_db=experiment.measured_snr_db,
            predicted_modulation=signal.predicted_modulation,
            ai_confidence=signal.ai_confidence,
            is_outlier=signal.is_outlier,
            novelty_score=signal.novelty_score,
            signal_quality=signal.signal_quality,
            classification_matches=(
                signal.predicted_modulation is not None
                and canonical is not None
                and signal.predicted_modulation.lower() == canonical.lower()
            ),
            sample_count=experiment.sample_count,
            snapshot=snapshot,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signal simulation failed: {str(exc)}",
        ) from exc


@router.get(
    "/session/{session_id}/report",
    summary="Get full report for a monitoring session",
    description=(
        "Aggregates the monitoring session, its linked communication session, "
        "communication events, decision records, and system alerts into one "
        "downloadable report payload."
    ),
)
async def get_session_report(
    session_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Build a complete report for the selected monitoring session."""
    mon_repo = MonitoringSessionRepository(db)
    mon = mon_repo.get_by_id(session_id)
    if not mon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring session '{session_id}' not found.",
        )

    started = mon.started_at
    ended = mon.ended_at

    comm_summary: Optional[Dict[str, Any]] = None
    comm_events: List[Dict[str, Any]] = []
    if mon.communication_session_id:
        comm_repo = CommunicationSessionRepository(db)
        comm = comm_repo.get_by_session_id(mon.communication_session_id)
        if comm:
            comm_summary = {
                "session_id": comm.session_id,
                "started_at": comm.started_at.isoformat() if comm.started_at else None,
                "ended_at": comm.ended_at.isoformat() if comm.ended_at else None,
                "packets_sent": comm.packets_sent,
                "packets_received": comm.packets_received,
                "packets_lost": comm.packets_lost,
                "packet_loss_percent": comm.packet_loss_percent,
                "avg_latency_ms": comm.avg_latency_ms,
                "min_latency_ms": comm.min_latency_ms,
                "max_latency_ms": comm.max_latency_ms,
                "median_latency_ms": comm.median_latency_ms,
                "p95_latency_ms": comm.p95_latency_ms,
                "p99_latency_ms": comm.p99_latency_ms,
                "jitter_ms": comm.jitter_ms,
                "throughput_bps": comm.throughput_bps,
                "interruption_count": comm.interruption_count,
                "total_interruption_duration_ms": comm.total_interruption_duration_ms,
                "recovery_count": comm.recovery_count,
                "health_score": comm.health_score,
                "final_status": comm.final_status,
                "extra_metadata": comm.extra_metadata,
            }
        ev_repo = CommunicationEventRepository(db)
        evs = ev_repo.get_by_session_id(mon.communication_session_id)
        comm_events = [
            {
                "id": e.id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "duration_ms": e.duration_ms,
                "sequence_number": e.sequence_number,
                "details": e.details,
            }
            for e in evs
        ]

    # Decision records linked to this monitoring session
    dec_repo = DecisionRepository(db)
    all_decs = dec_repo.get_all(skip=0, limit=10000)
    dec_records: List[Dict[str, Any]] = []
    for d in all_decs:
        meta = d.extra_metadata or {}
        linked = meta.get("monitoring_session_id") == session_id
        if not linked and started is not None and d.timestamp is not None:
            if started <= d.timestamp and (ended is None or d.timestamp <= ended):
                linked = True
        if linked:
            dec_records.append(
                {
                    "id": d.id,
                    "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                    "overall_status": d.overall_status,
                    "decision_confidence": d.decision_confidence,
                    "consistency": d.consistency,
                    "primary_reason": d.primary_reason,
                    "contributing_factors": d.contributing_factors,
                    "rules_triggered": d.rules_triggered,
                    "signal_summary": d.signal_summary,
                    "communication_summary": d.communication_summary,
                    "recommendations": d.recommendations,
                    "extra_metadata": d.extra_metadata,
                }
            )
    # Fall back to the in-memory latest snapshot for sessions that have not
    # been stopped yet (decision records are persisted on stop to avoid
    # per-packet DB bloat).
    if not dec_records:
        snap = unified_monitor.latest_snapshot
        if snap is not None and snap.monitoring_session_id == session_id:
            d = snap.decision
            dec_records.append(
                {
                    "id": None,
                    "timestamp": snap.timestamp.isoformat() if snap.timestamp else None,
                    "overall_status": (
                        d.status.value if hasattr(d.status, "value") else str(d.status)
                    ),
                    "decision_confidence": d.confidence,
                    "consistency": (
                        d.consistency.value
                        if hasattr(d.consistency, "value")
                        else str(d.consistency)
                    ),
                    "primary_reason": d.primary_reason,
                    "contributing_factors": d.contributing_factors,
                    "rules_triggered": [],
                    "signal_summary": None,
                    "communication_summary": None,
                    "recommendations": d.recommendations,
                    "extra_metadata": {"source": "live_snapshot"},
                }
            )
    dec_records.sort(key=lambda x: x["timestamp"] or "")

    # Alerts within the session time window
    q = db.query(AlertModel)
    if started is not None:
        q = q.filter(AlertModel.timestamp >= started)
    if ended is not None:
        q = q.filter(AlertModel.timestamp <= ended)
    alerts_db = q.order_by(AlertModel.timestamp.asc()).all()
    alerts = [
        {
            "id": a.id,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "severity": a.severity,
            "category": a.category,
            "message": a.message,
            "source": a.source,
            "resolved": a.resolved,
            "extra_data": a.extra_data,
        }
        for a in alerts_db
    ]

    duration_seconds = None
    if started and ended:
        duration_seconds = (ended - started).total_seconds()

    return {
        "generated_at": utc_now().isoformat(),
        "monitoring_session": {
            "id": mon.id,
            "monitoring_session_id": mon.monitoring_session_id,
            "communication_session_id": mon.communication_session_id,
            "created_at": mon.created_at.isoformat() if mon.created_at else None,
            "started_at": started.isoformat() if started else None,
            "ended_at": ended.isoformat() if ended else None,
            "status": mon.status,
            "extra_metadata": mon.extra_metadata,
            "duration_seconds": duration_seconds,
        },
        "communication_session": comm_summary,
        "communication_events": comm_events,
        "decision_records": dec_records,
        "alerts": alerts,
    }


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

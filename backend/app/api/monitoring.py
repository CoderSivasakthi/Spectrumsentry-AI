"""Unified real-time monitoring API routes (Phase 7).

Provides REST endpoints for unified cross-domain monitoring snapshots, session lifecycle,
signal evidence ingestion, operational status polling, and monitoring history.
"""

from typing import Any, Dict, Optional
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
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
    DeviceRosterResponse,
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
    device_id: Optional[str] = Query(None, description="Optional owning device ID for its own snapshot"),
    db: Session = Depends(get_db),
) -> UnifiedMonitoringSnapshot:
    """Fetch current real-time unified monitoring snapshot (device-scoped when given)."""
    try:
        return unified_monitor.get_current_snapshot(db=db, session_id=session_id, device_id=device_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate unified monitoring snapshot: {str(exc)}",
        ) from exc


@router.get(
    "/devices",
    response_model=DeviceRosterResponse,
    summary="List connected devices and their live link telemetry",
    description=(
        "Returns the per-device session registry merged with live WebSocket "
        "connection state and packet telemetry: how many devices are connected, "
        "each device's identity, and the health of its link into the server."
    ),
)
async def get_devices(db: Session = Depends(get_db)) -> DeviceRosterResponse:
    """Return the device roster for the devices/network panel."""
    return unified_monitor.get_device_roster()


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
    """Start unified monitoring session, scoped to the requesting device when given."""
    try:
        device_id = (request.extra_metadata or {}).get("device_id") or "local"
        device_name = (request.extra_metadata or {}).get("device_name")
        return unified_monitor.start_session(
            request, db, device_id=device_id, device_name=device_name
        )
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
    """Stop active monitoring session (device-scoped when device_id is given)."""
    try:
        return unified_monitor.stop_session(request, db, device_id=request.device_id)
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


# ------------------------------------------------------------------------------
# Structured CSV export for session reports.
# The old client-side export flattened the whole nested JSON report into a
# two-column path,value dump, which Excel rendered as unreadable JSON-like
# transcripts. This endpoint builds real tables with the stdlib csv module.
# ------------------------------------------------------------------------------

def _csv_cell(value: Any) -> Any:
    """Format one report value for a CSV cell (lists/dicts become key=value runs)."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        if not value:
            return ""
        return "; ".join(f"{k}={_csv_cell(v)}" for k, v in value.items() if v not in (None, "", [], {}))
    if isinstance(value, list):
        return "; ".join(filter(None, (_csv_cell(v) for v in value))) or ""
    return value


def build_session_report_csv(report: Dict[str, Any]) -> str:
    """Render the full session report as sectioned flat CSV text.

    Sections (separated by blank rows, each with its own header row):
      SUMMARY — flat key/value fields for quick reading
      EVENTS — communication event table
      DECISIONS — decision records table
      ALERTS — system alert table
    """
    out = io.StringIO()
    writer = csv.writer(out)

    mon = report.get("monitoring_session") or {}
    comm = report.get("communication_session") or {}
    latest_decision = (report.get("decision_records") or [None])[-1] if report.get("decision_records") else None
    comm_meta = comm.get("extra_metadata") if isinstance(comm.get("extra_metadata"), dict) else {}
    mon_meta = mon.get("extra_metadata") if isinstance(mon.get("extra_metadata"), dict) else {}

    writer.writerow(["SUMMARY"])
    writer.writerow(["field", "value"])
    summary_fields = [
        ("generated_at", report.get("generated_at")),
        ("device_name", comm_meta.get("device_name") or mon_meta.get("device_name")),
        ("device_id", comm_meta.get("device_id") or mon_meta.get("device_id")),
        ("monitoring_session_id", mon.get("monitoring_session_id")),
        ("communication_session_id", mon.get("communication_session_id")),
        ("monitoring_status", mon.get("status")),
        ("started_at", mon.get("started_at")),
        ("ended_at", mon.get("ended_at")),
        ("duration_seconds", mon.get("duration_seconds")),
        ("packets_sent", comm.get("packets_sent")),
        ("packets_received", comm.get("packets_received")),
        ("packets_lost", comm.get("packets_lost")),
        ("packet_loss_percent", comm.get("packet_loss_percent")),
        ("avg_latency_ms", comm.get("avg_latency_ms")),
        ("min_latency_ms", comm.get("min_latency_ms")),
        ("max_latency_ms", comm.get("max_latency_ms")),
        ("median_latency_ms", comm.get("median_latency_ms")),
        ("p95_latency_ms", comm.get("p95_latency_ms")),
        ("p99_latency_ms", comm.get("p99_latency_ms")),
        ("jitter_ms", comm.get("jitter_ms")),
        ("throughput_bps", comm.get("throughput_bps")),
        ("interruption_count", comm.get("interruption_count")),
        ("total_interruption_duration_ms", comm.get("total_interruption_duration_ms")),
        ("recovery_count", comm.get("recovery_count")),
        ("health_score", comm.get("health_score")),
        ("final_communication_status", comm.get("final_status")),
        ("final_decision_status", latest_decision.get("overall_status") if latest_decision else None),
        ("final_decision_confidence", latest_decision.get("decision_confidence") if latest_decision else None),
        ("history_note", "See EVENTS, DECISIONS and ALERTS sections below."),
    ]
    for field, value in summary_fields:
        writer.writerow([field, _csv_cell(value)])

    writer.writerow([])
    writer.writerow(["EVENTS"])
    writer.writerow(["timestamp", "event_type", "duration_ms", "sequence_number", "details"])
    for event in report.get("communication_events") or []:
        writer.writerow([
            event.get("timestamp") or "",
            event.get("event_type") or "",
            _csv_cell(event.get("duration_ms")),
            event.get("sequence_number") if event.get("sequence_number") is not None else "",
            _csv_cell(event.get("details")),
        ])

    writer.writerow([])
    writer.writerow(["DECISIONS"])
    writer.writerow([
        "timestamp", "overall_status", "confidence", "consistency",
        "primary_reason", "contributing_factors", "rules_triggered", "recommendations",
    ])
    for decision in report.get("decision_records") or []:
        writer.writerow([
            decision.get("timestamp") or "",
            decision.get("overall_status") or "",
            _csv_cell(decision.get("decision_confidence")),
            decision.get("consistency") or "",
            decision.get("primary_reason") or "",
            _csv_cell(decision.get("contributing_factors")),
            _csv_cell(decision.get("rules_triggered")),
            _csv_cell(decision.get("recommendations")),
        ])

    writer.writerow([])
    writer.writerow(["ALERTS"])
    writer.writerow(["timestamp", "severity", "category", "message", "source", "resolved"])
    for alert in report.get("alerts") or []:
        writer.writerow([
            alert.get("timestamp") or "",
            alert.get("severity") or "",
            alert.get("category") or "",
            _csv_cell(alert.get("message")),
            alert.get("source") or "",
            _csv_cell(alert.get("resolved")),
        ])

    return out.getvalue()


@router.get(
    "/session/{session_id}/report.csv",
    summary="Download session report as structured CSV",
    description=(
        "Excel-friendly CSV export of the full session report: a flat summary "
        "block plus tabular EVENT, DECISION and ALERT sections. Opens as real "
        "tables instead of a flattened JSON transcript."
    ),
)
async def get_session_report_csv(
    session_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Stream the session report as a downloadable CSV file."""
    try:
        report = await get_session_report(session_id, db)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build CSV report: {str(exc)}",
        ) from exc

    csv_text = build_session_report_csv(report)
    safe_name = "".join(c for c in session_id if c.isalnum() or c in "-_") or "session"
    filename = f"{safe_name}_report.csv"
    return Response(
        content=("﻿" + csv_text).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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

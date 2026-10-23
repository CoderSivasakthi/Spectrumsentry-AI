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

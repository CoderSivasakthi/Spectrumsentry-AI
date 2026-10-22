"""Evidence correlation module for Phase 6 Decision Engine.

Analyzes cross-domain consistency between physical-layer signal evidence
and application-layer communication telemetry, determines decision confidence,
and formats domain summaries.
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np

from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    OverallStatus,
    SignalEvidence,
)


def compute_decision_confidence(
    overall_status: OverallStatus,
    consistency: ConsistencyStatus,
    signal: Optional[SignalEvidence],
    comm: Optional[CommunicationEvidence],
) -> float:
    """Calculate overall decision confidence score (0.0 to 1.0).

    Formulation:
        - When cross-domain evidence is CONFLICTING, decision confidence is capped
          between 0.50 and 0.70, explicitly indicating diagnostic divergence.
        - When both domains are available and CONSISTENT, confidence is high (0.85 - 0.99),
          weighted across AI confidence and network health.
        - When only one domain is provided (UNCORRELATED), confidence reflects
          the available domain's internal certainty (0.70 - 0.85).

    Args:
        overall_status: The determined overall communication state.
        consistency: Whether observations agree or conflict.
        signal: Physical-layer evidence.
        comm: Network telemetry evidence.

    Returns:
        Confidence float clamped between 0.0 and 1.0.
    """
    if consistency == ConsistencyStatus.CONFLICTING or overall_status == OverallStatus.REVIEW:
        # Cross-domain divergence reduces decision certainty
        return 0.65

    # If the link is interrupted, certainty in the interruption state is high
    if overall_status == OverallStatus.INTERRUPTED:
        return 0.98

    has_signal = signal is not None and (signal.confidence is not None or signal.measured_snr_db is not None)
    has_comm = comm is not None and (
        comm.health_score is not None
        or comm.status is not None
        or comm.is_interrupted is not None
        or comm.packet_loss_percent is not None
    )

    if has_signal and has_comm:
        sig_weight = signal.confidence if signal.confidence is not None else 0.90
        comm_weight = (comm.health_score / 100.0) if comm.health_score is not None else 0.90
        combined = 0.5 * sig_weight + 0.5 * comm_weight
        return float(np.round(np.clip(combined, 0.85, 0.99), 2))


    elif has_comm:
        if overall_status == OverallStatus.INTERRUPTED:
            return 0.95
        comm_weight = (comm.health_score / 100.0) if comm.health_score is not None else 0.80
        return float(np.round(np.clip(0.70 + 0.25 * comm_weight, 0.70, 0.95), 2))

    elif has_signal:
        sig_weight = signal.confidence if signal.confidence is not None else 0.80
        return float(np.round(np.clip(0.70 + 0.25 * sig_weight, 0.70, 0.95), 2))

    return 0.50


def build_signal_summary(signal: Optional[SignalEvidence]) -> Dict[str, Any]:
    """Produce clean summary dictionary for physical-layer signal evidence."""
    if not signal:
        return {"available": False, "note": "No signal evidence provided"}

    return {
        "available": True,
        "predicted_modulation": signal.predicted_modulation or "Unknown",
        "confidence": float(round(signal.confidence, 4)) if signal.confidence is not None else None,
        "measured_snr_db": float(round(signal.measured_snr_db, 2)) if signal.measured_snr_db is not None else None,
        "signal_quality": signal.signal_quality or ("GOOD" if (signal.measured_snr_db or 0) >= 5.0 else "FAIR"),
        "signal_power": signal.signal_power,
        "noise_power": signal.noise_power,
    }


def build_communication_summary(comm: Optional[CommunicationEvidence]) -> Dict[str, Any]:
    """Produce clean summary dictionary for application-layer communication evidence."""
    if not comm:
        return {"available": False, "note": "No communication evidence provided"}

    return {
        "available": True,
        "status": comm.status or "UNKNOWN",
        "health_score": comm.health_score,
        "packet_loss_percent": comm.packet_loss_percent,
        "avg_latency_ms": comm.avg_latency_ms,
        "jitter_ms": comm.jitter_ms,
        "throughput_mbps": comm.throughput_mbps,
        "is_interrupted": comm.is_interrupted,
        "interruption_count": comm.interruption_count,
        "recovery_count": comm.recovery_count,
    }

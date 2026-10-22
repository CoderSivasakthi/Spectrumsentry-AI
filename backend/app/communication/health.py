"""Communication health scoring and status state machine (Phase 5).

Implements the SpectrumSentry Communication Health Score (0-100) and the
communication lifecycle state machine.
"""

from typing import Tuple
from backend.app.schemas.communication import CommunicationStatus


def calculate_health_score(
    packet_loss_percent: float,
    avg_latency_ms: float,
    jitter_ms: float,
    is_interrupted: bool,
    interruption_count: int = 0,
    warning_latency_ms: float = 100.0,
    warning_loss_percent: float = 5.0,
    warning_jitter_ms: float = 30.0,
) -> float:
    """Calculate the SpectrumSentry Communication Health Score (0–100).

    Scoring Formulation:
        Base Score = 100.0

        1. Active Interruption Penalty:
           If the link is currently interrupted, the score is capped at 25.0
           and further reduced by cumulative interruption history:
               Score = max(0.0, 25.0 - (interruption_count * 2.5))

        2. Continuous Degradation Deductions:
           - Packet Loss Penalty:
             loss_penalty = min(40.0, packet_loss_percent * 2.0)
           - Latency Penalty:
             latency_excess = max(0.0, avg_latency_ms - warning_latency_ms)
             latency_penalty = min(25.0, latency_excess / 4.0)
           - Jitter Penalty:
             jitter_excess = max(0.0, jitter_ms - warning_jitter_ms)
             jitter_penalty = min(15.0, jitter_excess / 2.0)
           - Interruption History Penalty:
             history_penalty = min(20.0, interruption_count * 5.0)

           Score = 100.0 - (loss_penalty + latency_penalty + jitter_penalty + history_penalty)

    Args:
        packet_loss_percent: Percentage of lost packets (0–100).
        avg_latency_ms: Mean latency in milliseconds.
        jitter_ms: Latency variation in milliseconds.
        is_interrupted: True if link is currently interrupted.
        interruption_count: Cumulative number of detected interruptions.
        warning_latency_ms: Latency threshold where penalties begin.
        warning_loss_percent: Loss threshold for warning level.
        warning_jitter_ms: Jitter threshold where penalties begin.

    Returns:
        Float health score clamped strictly between 0.0 and 100.0.
    """
    if is_interrupted:
        interrupted_score = 25.0 - (interruption_count * 2.5)
        return float(max(0.0, min(25.0, round(interrupted_score, 1))))

    # Deductions
    loss_penalty = min(40.0, max(0.0, packet_loss_percent) * 2.0)

    latency_excess = max(0.0, avg_latency_ms - warning_latency_ms)
    latency_penalty = min(25.0, latency_excess / 4.0)

    jitter_excess = max(0.0, jitter_ms - warning_jitter_ms)
    jitter_penalty = min(15.0, jitter_excess / 2.0)

    history_penalty = min(20.0, float(interruption_count) * 5.0)

    total_deductions = loss_penalty + latency_penalty + jitter_penalty + history_penalty
    raw_score = 100.0 - total_deductions

    return float(max(0.0, min(100.0, round(raw_score, 1))))


def evaluate_communication_status(
    current_status: CommunicationStatus,
    is_interrupted: bool,
    is_recovering: bool,
    packet_loss_percent: float,
    avg_latency_ms: float,
    jitter_ms: float,
    warning_loss_percent: float = 5.0,
    warning_latency_ms: float = 100.0,
    warning_jitter_ms: float = 30.0,
) -> CommunicationStatus:
    """Evaluate and transition communication status state machine.

    State Machine Transitions:
        STARTING -> CONNECTED (on initial valid packet)
        CONNECTED -> DEGRADED (if loss/latency/jitter exceed warning thresholds)
        CONNECTED/DEGRADED -> INTERRUPTED (if packet timeout elapsed)
        INTERRUPTED -> RECOVERING (on arrival of resuming packet)
        RECOVERING -> CONNECTED (or DEGRADED based on metrics)
        * -> STOPPED (upon explicit session closure)

    Args:
        current_status: Current lifecycle state.
        is_interrupted: Flag indicating active packet timeout.
        is_recovering: Flag indicating transient recovery state.
        packet_loss_percent: Current loss percentage.
        avg_latency_ms: Average latency in ms.
        jitter_ms: Jitter in ms.
        warning_loss_percent: Warning threshold for packet loss.
        warning_latency_ms: Warning threshold for latency.
        warning_jitter_ms: Warning threshold for jitter.

    Returns:
        Next CommunicationStatus enum value.
    """
    if current_status == CommunicationStatus.STOPPED:
        return CommunicationStatus.STOPPED

    if is_interrupted:
        return CommunicationStatus.INTERRUPTED

    if is_recovering:
        return CommunicationStatus.RECOVERING

    # Check for degradation
    is_degraded = (
        packet_loss_percent >= warning_loss_percent
        or avg_latency_ms >= warning_latency_ms
        or jitter_ms >= warning_jitter_ms
    )

    if is_degraded:
        return CommunicationStatus.DEGRADED

    return CommunicationStatus.CONNECTED

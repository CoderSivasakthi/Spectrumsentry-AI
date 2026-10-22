"""Communication recovery detection module (Phase 5).

Handles reconnection detection when packets resume following a detected
communication interruption.
"""

from dataclasses import dataclass
from typing import Dict, Optional
from backend.app.communication.interruption import InterruptionDetector, InterruptionRecord


@dataclass
class RecoveryRecord:
    """Record describing a completed recovery from an interruption."""
    session_id: str
    interruption_id: int
    recovery_time: float
    duration_ms: float
    resumed_sequence: int


class RecoveryDetector:
    """Handles recovery tracking when communication resumes."""

    def __init__(self):
        self.recovery_count: int = 0

    def process_packet_recovery(
        self,
        detector: InterruptionDetector,
        packet_arrival_time: float,
        session_id: str,
        sequence_number: int,
        lost_packets_during_event: int = 0,
    ) -> Optional[RecoveryRecord]:
        """Detect and finalize recovery if detector was in INTERRUPTED state.

        Args:
            detector: Active InterruptionDetector instance.
            packet_arrival_time: Timestamp of resuming packet.
            session_id: Active session identifier.
            sequence_number: Sequence number of the resuming packet.
            lost_packets_during_event: Sequence gaps noticed during interruption.

        Returns:
            RecoveryRecord if an active interruption was concluded, else None.
        """
        if not detector.is_interrupted or detector.current_interruption is None:
            return None

        # Conclude the current interruption
        interruption = detector.current_interruption
        interruption.end_time = packet_arrival_time
        duration_ms = max(0.0, (packet_arrival_time - interruption.start_time) * 1000.0)
        interruption.duration_ms = round(duration_ms, 2)
        interruption.packets_lost_during_event = lost_packets_during_event

        # Accumulate metrics
        detector.total_interruption_duration_ms += interruption.duration_ms
        detector.interruption_history.append(interruption)
        detector.is_interrupted = False
        detector.current_interruption = None

        self.recovery_count += 1

        return RecoveryRecord(
            session_id=session_id,
            interruption_id=interruption.interruption_id,
            recovery_time=packet_arrival_time,
            duration_ms=round(duration_ms, 2),
            resumed_sequence=sequence_number,
        )

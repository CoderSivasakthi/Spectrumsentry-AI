"""Communication recovery detection module (Phase 5).

Handles reconnection detection when packets resume following a detected
communication interruption. Corrected report (Appendix A fix #10) requires
``required_consecutive`` consecutive packets (default 3) before declaring the
link recovered: a single resuming packet only indicates one frame squeezed
through, not a stable link. The interruption interval ends at the arrival time
of the FIRST resuming packet, because that is when connectivity actually came
back; the additional packets merely confirm stability.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from backend.app.communication.interruption import InterruptionDetector, InterruptionRecord


@dataclass
class RecoveryRecord:
    """Record describing a completed recovery from an interruption."""
    session_id: str
    interruption_id: int
    recovery_time: float
    duration_ms: float
    resumed_sequence: int
    confirming_packets: int
    first_resumed_sequence: Optional[int] = None


class RecoveryDetector:
    """Handles recovery tracking when communication resumes.

    Confirmation requires ``required_consecutive`` resumption packets arriving with
    strictly consecutive sequence numbers (``seq == previous + 1``). A sequence gap
    among the resumption packets restarts confirmation from the latest packet.
    """

    def __init__(self, required_consecutive: int = 3):
        """Initialize recovery tracker.

        Args:
            required_consecutive: Consecutive packets required to confirm recovery
                (corrected report fix #10 default: 3; 1 restores old behavior).
        """
        self.required_consecutive: int = max(1, int(required_consecutive))
        self.recovery_count: int = 0
        # Pending resumption packets not yet sufficient to confirm recovery:
        # list of (sequence_number, arrival_time) in arrival order.
        self._pending: List[Tuple[int, float]] = []

    @property
    def is_awaiting_confirmation(self) -> bool:
        """Whether resumption packets are pending confirmation (interrupted state)."""
        return bool(self._pending)

    def reset(self) -> None:
        """Clear any pending resumption state (e.g. on session close)."""
        self._pending.clear()

    def process_packet_recovery(
        self,
        detector: InterruptionDetector,
        packet_arrival_time: float,
        session_id: str,
        sequence_number: int,
        lost_packets_during_event: int = 0,
    ) -> Optional[RecoveryRecord]:
        """Track resumption packets and finalize recovery once enough have arrived.

        Args:
            detector: Active InterruptionDetector instance.
            packet_arrival_time: Timestamp of the resuming packet (monotonic domain).
            session_id: Active session identifier.
            sequence_number: Sequence number of the resuming packet.
            lost_packets_during_event: Sequence gaps noticed during interruption.

        Returns:
            RecoveryRecord when the required consecutive packets are confirmed,
            None while awaiting confirmation or when no interruption is active.
        """
        if not detector.is_interrupted or detector.current_interruption is None:
            return None

        # Consecutive-numbering check: a gap resets the confirmation window
        if self._pending and sequence_number != self._pending[-1][0] + 1:
            self._pending = [(sequence_number, packet_arrival_time)]
        else:
            self._pending.append((sequence_number, packet_arrival_time))

        if len(self._pending) < self.required_consecutive:
            return None

        first_sequence, first_arrival = self._pending[0]
        self._pending.clear()

        # Conclude the current interruption; connectivity returned at the first packet
        interruption = detector.current_interruption
        interruption.end_time = first_arrival
        duration_ms = max(0.0, (first_arrival - interruption.start_time) * 1000.0)
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
            recovery_time=first_arrival,
            duration_ms=round(duration_ms, 2),
            resumed_sequence=sequence_number,
            confirming_packets=self.required_consecutive,
            first_resumed_sequence=first_sequence,
        )

"""Communication interruption detection module (Phase 5).

Monitors packet arrival intervals against a configurable timeout threshold
to detect communication silence events.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class InterruptionRecord:
    """Record describing an individual communication interruption occurrence."""
    interruption_id: int
    session_id: str
    start_time: float  # Timestamp of last packet received before interruption
    detection_time: float  # Timestamp when timeout was recognized
    end_time: Optional[float] = None  # Timestamp when recovery packet arrived
    duration_ms: Optional[float] = None
    reason: str = "packet_timeout"
    packets_lost_during_event: int = 0


class InterruptionDetector:
    """Monitors inter-packet arrival times to detect communication silence."""

    def __init__(self, timeout_seconds: float = 2.0):
        """Initialize interruption detector.

        Args:
            timeout_seconds: Duration of silence in seconds before declaring an interruption.
        """
        self.timeout_seconds = timeout_seconds
        self.is_interrupted: bool = False
        self.last_packet_time: Optional[float] = None
        self.interruption_counter: int = 0
        self.current_interruption: Optional[InterruptionRecord] = None
        self.interruption_history: List[InterruptionRecord] = []
        self.total_interruption_duration_ms: float = 0.0

    def update_packet_arrival(self, arrival_time: float) -> None:
        """Update last arrival timestamp without state transitions."""
        self.last_packet_time = arrival_time

    def check_timeout(self, current_time: float, session_id: str) -> Optional[InterruptionRecord]:
        """Check if inter-packet timeout has been exceeded.

        Args:
            current_time: Current POSIX timestamp in seconds.
            session_id: Active session identifier.

        Returns:
            New InterruptionRecord if transition to INTERRUPTED occurs, else None.
        """
        if self.last_packet_time is None:
            # No packets received yet in this session
            return None

        silence_duration = current_time - self.last_packet_time

        if not self.is_interrupted and silence_duration > self.timeout_seconds:
            self.is_interrupted = True
            self.interruption_counter += 1
            record = InterruptionRecord(
                interruption_id=self.interruption_counter,
                session_id=session_id,
                start_time=self.last_packet_time,
                detection_time=current_time,
                reason="packet_timeout",
            )
            self.current_interruption = record
            return record

        return None

"""Unit tests for Phase 5 communication interruption detection."""

import time
import pytest
from backend.app.communication.interruption import InterruptionDetector, InterruptionRecord


class TestInterruptionDetector:
    """Tests for timeout-based interruption detection."""

    def test_interruption_detection_timeout(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        session_id = "test_sess_001"

        t0 = 1000.0
        detector.update_packet_arrival(t0)
        assert detector.is_interrupted is False

        # Check before timeout (0.5s later) -> no interruption
        record = detector.check_timeout(t0 + 0.5, session_id)
        assert record is None
        assert detector.is_interrupted is False

        # Check at/after timeout (1.2s later) -> interruption triggered
        record = detector.check_timeout(t0 + 1.2, session_id)
        assert record is not None
        assert isinstance(record, InterruptionRecord)
        assert record.interruption_id == 1
        assert record.session_id == session_id
        assert record.start_time == t0
        assert record.detection_time == t0 + 1.2
        assert record.reason == "packet_timeout"
        assert detector.is_interrupted is True

        # Subsequent check while already interrupted should not create duplicate record
        second_record = detector.check_timeout(t0 + 1.5, session_id)
        assert second_record is None
        assert detector.interruption_counter == 1

    def test_interruption_without_packets(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        # No packets received yet
        record = detector.check_timeout(time.time(), "empty_sess")
        assert record is None
        assert detector.is_interrupted is False

    def test_multiple_interruptions_counter(self):
        detector = InterruptionDetector(timeout_seconds=0.5)
        sess = "multi_int"

        # Interruption 1
        detector.update_packet_arrival(100.0)
        rec1 = detector.check_timeout(100.6, sess)
        assert rec1 is not None
        assert rec1.interruption_id == 1

        # Simulate manual recovery or packet arrival
        detector.is_interrupted = False
        detector.update_packet_arrival(105.0)

        # Interruption 2
        rec2 = detector.check_timeout(105.7, sess)
        assert rec2 is not None
        assert rec2.interruption_id == 2
        assert detector.interruption_counter == 2

"""Unit tests for Phase 5 communication recovery detection."""

import pytest
from backend.app.communication.interruption import InterruptionDetector
from backend.app.communication.recovery import RecoveryDetector, RecoveryRecord


class TestRecoveryDetector:
    """Tests for recovery detection when packets resume after interruption."""

    def test_recovery_after_interruption(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        recovery_detector = RecoveryDetector()
        session_id = "rec_test_01"

        # Packet 1 at t=10.0
        detector.update_packet_arrival(10.0)

        # Timeout at t=11.5
        record = detector.check_timeout(11.5, session_id)
        assert record is not None
        assert detector.is_interrupted is True

        # Packet 2 resumes at t=14.0 (4.0s after packet 1)
        rec = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=14.0,
            session_id=session_id,
            sequence_number=2,
            lost_packets_during_event=0,
        )

        assert rec is not None
        assert isinstance(rec, RecoveryRecord)
        assert rec.session_id == session_id
        assert rec.interruption_id == 1
        assert rec.recovery_time == 14.0
        assert rec.duration_ms == 4000.0  # (14.0 - 10.0) * 1000
        assert rec.resumed_sequence == 2

        # Detector should now be cleared
        assert detector.is_interrupted is False
        assert detector.total_interruption_duration_ms == 4000.0
        assert len(detector.interruption_history) == 1
        assert recovery_detector.recovery_count == 1

    def test_recovery_without_interruption(self):
        detector = InterruptionDetector(timeout_seconds=2.0)
        recovery_detector = RecoveryDetector()

        detector.update_packet_arrival(10.0)
        # Not interrupted
        rec = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=10.5,
            session_id="normal_sess",
            sequence_number=2,
        )
        assert rec is None
        assert recovery_detector.recovery_count == 0

    def test_no_duplicate_recovery(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        recovery_detector = RecoveryDetector()
        session_id = "no_dup_sess"

        detector.update_packet_arrival(10.0)
        detector.check_timeout(11.5, session_id)
        assert detector.is_interrupted is True

        # First packet recovers
        rec1 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.0,
            session_id=session_id,
            sequence_number=2,
        )
        assert rec1 is not None

        # Subsequent packet while already recovered does not produce another recovery event
        rec2 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.25,
            session_id=session_id,
            sequence_number=3,
        )
        assert rec2 is None
        assert recovery_detector.recovery_count == 1

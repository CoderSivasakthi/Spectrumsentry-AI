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

        # Packet 2 resumes at t=14.0 (4.0s after packet 1) -> awaiting confirmation
        rec1 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=14.0,
            session_id=session_id,
            sequence_number=2,
            lost_packets_during_event=0,
        )
        assert rec1 is None
        assert detector.is_interrupted is True

        # Packets 3 and 4: recovery confirmed on the 3rd consecutive packet
        rec2 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=14.25,
            session_id=session_id,
            sequence_number=3,
        )
        assert rec2 is None

        rec3 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=14.5,
            session_id=session_id,
            sequence_number=4,
        )

        assert rec3 is not None
        assert isinstance(rec3, RecoveryRecord)
        assert rec3.session_id == session_id
        assert rec3.interruption_id == 1
        # Interruption interval ends at the FIRST resuming packet
        assert rec3.recovery_time == 14.0
        assert rec3.duration_ms == 4000.0  # (14.0 - 10.0) * 1000
        assert rec3.resumed_sequence == 4
        assert rec3.confirming_packets == 3
        assert rec3.first_resumed_sequence == 2

        # Detector should now be cleared
        assert detector.is_interrupted is False
        assert detector.total_interruption_duration_ms == 4000.0
        assert len(detector.interruption_history) == 1
        assert recovery_detector.recovery_count == 1
        assert recovery_detector.is_awaiting_confirmation is False

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

        # Three consecutive packets required to confirm recovery
        rec1 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.0,
            session_id=session_id,
            sequence_number=2,
        )
        assert rec1 is None
        rec2 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.25,
            session_id=session_id,
            sequence_number=3,
        )
        assert rec2 is None
        rec3 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.5,
            session_id=session_id,
            sequence_number=4,
        )
        assert rec3 is not None
        assert recovery_detector.recovery_count == 1

        # Subsequent packet while already recovered does not produce another recovery event
        rec4 = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=13.75,
            session_id=session_id,
            sequence_number=5,
        )
        assert rec4 is None
        assert recovery_detector.recovery_count == 1

    def test_sequence_gap_restarts_confirmation(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        recovery_detector = RecoveryDetector()
        session_id = "gap_sess"

        detector.update_packet_arrival(10.0)
        detector.check_timeout(11.5, session_id)

        # Packets 2 and 3 resuming, then a gap (packet 5) resets the window
        for seq, t in ((2, 14.0), (3, 14.25)):
            assert recovery_detector.process_packet_recovery(
                detector=detector,
                packet_arrival_time=t,
                session_id=session_id,
                sequence_number=seq,
            ) is None

        rec = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=15.0,
            session_id=session_id,
            sequence_number=5,
        )
        assert rec is None
        assert recovery_detector.is_awaiting_confirmation is True

        # Two more consecutive packets after the reset complete recovery
        assert recovery_detector.process_packet_recovery(
            detector=detector, packet_arrival_time=15.25,
            session_id=session_id, sequence_number=6,
        ) is None
        final = recovery_detector.process_packet_recovery(
            detector=detector, packet_arrival_time=15.5,
            session_id=session_id, sequence_number=7,
        )
        assert final is not None
        assert final.first_resumed_sequence == 5
        assert final.duration_ms == 5000.0  # ends at first packet after the gap reset (15.0 - 10.0)

    def test_required_consecutive_configurable(self):
        detector = InterruptionDetector(timeout_seconds=1.0)
        recovery_detector = RecoveryDetector(required_consecutive=1)
        session_id = "cfg_sess"

        detector.update_packet_arrival(10.0)
        detector.check_timeout(11.5, session_id)

        rec = recovery_detector.process_packet_recovery(
            detector=detector,
            packet_arrival_time=12.0,
            session_id=session_id,
            sequence_number=2,
        )
        # Legacy single-packet behavior restored with required_consecutive=1
        assert rec is not None
        assert rec.confirming_packets == 1

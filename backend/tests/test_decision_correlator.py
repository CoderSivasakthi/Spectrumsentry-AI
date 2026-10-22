"""Unit tests for Phase 6 evidence correlation and confidence calculation."""

import pytest
from backend.app.decision.correlator import (
    build_communication_summary,
    build_signal_summary,
    compute_decision_confidence,
)
from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    OverallStatus,
    SignalEvidence,
)


class TestDecisionCorrelator:
    """Test suite for evidence correlation and confidence calculation."""

    def test_confidence_conflicting_evidence(self):
        conf = compute_decision_confidence(
            overall_status=OverallStatus.REVIEW,
            consistency=ConsistencyStatus.CONFLICTING,
            signal=SignalEvidence(confidence=0.99, measured_snr_db=15.0),
            comm=CommunicationEvidence(packet_loss_percent=30.0),
        )
        # Should be capped due to diagnostic divergence
        assert conf == 0.65

    def test_confidence_interrupted_link(self):
        conf = compute_decision_confidence(
            overall_status=OverallStatus.INTERRUPTED,
            consistency=ConsistencyStatus.CONSISTENT,
            signal=SignalEvidence(confidence=0.90),
            comm=CommunicationEvidence(is_interrupted=True),
        )
        assert conf >= 0.95

    def test_confidence_both_domains_consistent(self):
        conf = compute_decision_confidence(
            overall_status=OverallStatus.NORMAL,
            consistency=ConsistencyStatus.CONSISTENT,
            signal=SignalEvidence(confidence=0.98),
            comm=CommunicationEvidence(health_score=100.0),
        )
        assert conf >= 0.95

    def test_confidence_single_domain_comm(self):
        conf = compute_decision_confidence(
            overall_status=OverallStatus.NORMAL,
            consistency=ConsistencyStatus.UNCORRELATED,
            signal=None,
            comm=CommunicationEvidence(health_score=80.0),
        )
        assert 0.70 <= conf <= 0.95

    def test_confidence_single_domain_signal(self):
        conf = compute_decision_confidence(
            overall_status=OverallStatus.NORMAL,
            consistency=ConsistencyStatus.UNCORRELATED,
            signal=SignalEvidence(confidence=0.85),
            comm=None,
        )
        assert 0.70 <= conf <= 0.95

    def test_build_signal_summary(self):
        empty_sum = build_signal_summary(None)
        assert empty_sum["available"] is False

        sig = SignalEvidence(
            predicted_modulation="QPSK",
            confidence=0.9942,
            measured_snr_db=12.456,
            signal_quality="EXCELLENT",
        )
        summary = build_signal_summary(sig)
        assert summary["available"] is True
        assert summary["predicted_modulation"] == "QPSK"
        assert summary["confidence"] == 0.9942
        assert summary["measured_snr_db"] == 12.46

    def test_build_communication_summary(self):
        empty_sum = build_communication_summary(None)
        assert empty_sum["available"] is False

        comm = CommunicationEvidence(
            status="CONNECTED",
            health_score=96.5,
            packet_loss_percent=0.5,
            avg_latency_ms=18.2,
        )
        summary = build_communication_summary(comm)
        assert summary["available"] is True
        assert summary["status"] == "CONNECTED"
        assert summary["health_score"] == 96.5
        assert summary["packet_loss_percent"] == 0.5

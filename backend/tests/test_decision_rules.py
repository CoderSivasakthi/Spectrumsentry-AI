"""Unit tests for Phase 6 Decision Engine rules."""

import pytest
from backend.app.decision.rules import evaluate_rules, get_all_rules_info
from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    OverallStatus,
    SignalEvidence,
)


class TestDecisionRules:
    """Test suite for deterministic decision rules."""

    def test_interrupted_link_rule(self):
        comm = CommunicationEvidence(status="INTERRUPTED", is_interrupted=True, interruption_count=2)
        res, triggered = evaluate_rules(None, comm)
        assert res.rule_id == "RULE_INTERRUPTED_LINK"
        assert res.status == OverallStatus.INTERRUPTED
        assert "RULE_INTERRUPTED_LINK" in triggered

    def test_recovering_link_rule(self):
        comm = CommunicationEvidence(status="RECOVERING")
        res, triggered = evaluate_rules(None, comm)
        assert res.rule_id == "RULE_RECOVERING_LINK"
        assert res.status == OverallStatus.RECOVERING

    def test_conflict_high_snr_severe_loss_rule(self):
        signal = SignalEvidence(measured_snr_db=15.0, confidence=0.99)
        comm = CommunicationEvidence(packet_loss_percent=25.0, status="DEGRADED", health_score=50.0)
        res, triggered = evaluate_rules(signal, comm)
        assert res.rule_id == "RULE_CONFLICT_HIGH_SNR_HIGH_LOSS"
        assert res.status == OverallStatus.REVIEW
        assert res.consistency == ConsistencyStatus.CONFLICTING
        assert "RULE_CONFLICT_HIGH_SNR_HIGH_LOSS" in triggered

    def test_conflict_clean_link_low_confidence_rule(self):
        signal = SignalEvidence(confidence=0.45, measured_snr_db=5.0)
        comm = CommunicationEvidence(status="CONNECTED", health_score=95.0, packet_loss_percent=0.0)
        res, triggered = evaluate_rules(signal, comm)
        assert res.rule_id == "RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE"
        assert res.status == OverallStatus.REVIEW
        assert res.consistency == ConsistencyStatus.CONFLICTING

    def test_network_degraded_rule(self):
        comm = CommunicationEvidence(
            status="DEGRADED",
            packet_loss_percent=8.0,
            avg_latency_ms=120.0,
            jitter_ms=35.0,
            health_score=60.0,
        )
        res, triggered = evaluate_rules(None, comm)
        assert res.rule_id == "RULE_DEGRADED_NETWORK"
        assert res.status == OverallStatus.DEGRADED
        assert len(res.contributing_factors) >= 3

    def test_signal_degraded_rule(self):
        signal = SignalEvidence(measured_snr_db=-4.0, signal_quality="POOR", confidence=0.72)
        comm = CommunicationEvidence(status="CONNECTED", health_score=85.0, packet_loss_percent=1.0)
        res, triggered = evaluate_rules(signal, comm)
        assert res.rule_id == "RULE_DEGRADED_SIGNAL"
        assert res.status == OverallStatus.DEGRADED

    def test_normal_operation_rule(self):
        signal = SignalEvidence(measured_snr_db=14.0, confidence=0.98, signal_quality="EXCELLENT")
        comm = CommunicationEvidence(status="CONNECTED", health_score=100.0, packet_loss_percent=0.0, avg_latency_ms=15.0)
        res, triggered = evaluate_rules(signal, comm)
        assert res.rule_id == "RULE_NORMAL_OPERATION"
        assert res.status == OverallStatus.NORMAL
        assert res.consistency == ConsistencyStatus.CONSISTENT

    def test_get_all_rules_info(self):
        rules = get_all_rules_info()
        assert len(rules) >= 7
        rule_ids = [r.rule_id for r in rules]
        assert "RULE_INTERRUPTED_LINK" in rule_ids
        assert "RULE_NORMAL_OPERATION" in rule_ids


class TestNoveltyRule:
    """Corrected report fix #8: out-of-distribution signals force a REVIEW state."""

    def test_novelty_outlier_rule(self):
        signal = SignalEvidence(
            predicted_modulation="QPSK",
            confidence=0.97,           # confident, but...
            measured_snr_db=14.0,
            is_outlier=True,           # ...signature matches no supported modulation
        )
        res, triggered = evaluate_rules(signal, None)
        assert res.rule_id == "RULE_NOVELTY_OUTLIER"
        assert res.status == OverallStatus.REVIEW
        assert res.priority == 85
        assert "RULE_NOVELTY_OUTLIER" in triggered

    def test_novelty_rule_beats_low_snr_degradation(self):
        # Outlier flag wins over signal-quality degradation (higher priority)
        signal = SignalEvidence(measured_snr_db=-3.0, confidence=0.5, is_outlier=True)
        res, _ = evaluate_rules(signal, None)
        assert res.rule_id == "RULE_NOVELTY_OUTLIER"

    def test_no_novelty_rule_by_default(self):
        signal = SignalEvidence(predicted_modulation="QPSK", confidence=0.95, measured_snr_db=14.0)
        res, _ = evaluate_rules(signal, None)
        assert res.rule_id != "RULE_NOVELTY_OUTLIER"

    def test_novelty_rule_info_registered(self):
        infos = {info.rule_id: info for info in get_all_rules_info()}
        assert "RULE_NOVELTY_OUTLIER" in infos
        assert infos["RULE_NOVELTY_OUTLIER"].priority == 85

    def test_rule_precedence_uninterrupted_link_wins(self):
        # Interruption (100) still outranks novelty (85)
        signal = SignalEvidence(confidence=0.9, is_outlier=True)
        comm = CommunicationEvidence(status="INTERRUPTED", is_interrupted=True)
        res, triggered = evaluate_rules(signal, comm)
        assert res.rule_id == "RULE_INTERRUPTED_LINK"
        assert "RULE_NOVELTY_OUTLIER" not in triggered

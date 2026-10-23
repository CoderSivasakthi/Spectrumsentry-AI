#!/usr/bin/env python3
"""SpectrumSentry AI — Decision Engine CLI Demonstration (Phase 6).

Evaluates diverse cross-domain scenarios combining physical-layer signal features
and application-layer communication telemetry, demonstrating explainable,
deterministic decision-making.
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


from backend.app.decision.engine import decision_engine
from backend.app.schemas.decision import (
    CommunicationEvidence,
    DecisionInput,
    SignalEvidence,
)



def print_decision_result(scenario_title: str, scenario_desc: str, decision):
    print("=" * 76)
    print(f"SCENARIO: {scenario_title}")
    print(f"Description: {scenario_desc}")
    print("-" * 76)
    print(f"Overall Status       : {decision.overall_status.value}")
    print(f"Decision Confidence  : {decision.decision_confidence:.2%}")
    print(f"Cross-Domain Agree   : {decision.consistency.value}")
    print(f"Primary Reason       : {decision.primary_reason}")
    print("\nContributing Factors :")
    for factor in decision.contributing_factors:
        print(f"  • {factor}")
    print("\nRules Triggered      :")
    for rule in decision.rules_triggered:
        print(f"  [✓] {rule}")
    print("\nRecommendations      :")
    for rec in decision.recommendations:
        print(f"  → {rec}")
    print("=" * 76 + "\n")


def main():
    print("============================================================================")
    print("       SPECTRUMSENTRY AI — PHASE 6 DECISION ENGINE DEMONSTRATION")
    print("============================================================================\n")

    scenarios = [
        (
            "1. Normal Operation (Clean Signal & Clean Network)",
            "High physical SNR (15 dB), verified QPSK (99.8% conf), 0% packet loss, 12 ms latency.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="QPSK",
                    confidence=0.998,
                    measured_snr_db=15.0,
                    signal_quality="EXCELLENT",
                ),
                communication_evidence=CommunicationEvidence(
                    status="CONNECTED",
                    health_score=100.0,
                    packet_loss_percent=0.0,
                    avg_latency_ms=12.4,
                    jitter_ms=1.8,
                    throughput_mbps=0.045,
                    is_interrupted=False,
                ),
            ),
        ),
        (
            "2. Network Layer Degradation",
            "Strong signal (12 dB SNR, 99.2% conf), but network exhibits 14% packet loss and 125 ms latency.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="16-QAM",
                    confidence=0.992,
                    measured_snr_db=12.0,
                    signal_quality="EXCELLENT",
                ),
                communication_evidence=CommunicationEvidence(
                    status="DEGRADED",
                    health_score=62.0,
                    packet_loss_percent=14.0,
                    avg_latency_ms=125.0,
                    jitter_ms=35.0,
                    throughput_mbps=0.022,
                    is_interrupted=False,
                ),
            ),
        ),
        (
            "3. Physical-Layer Signal Degradation",
            "Severe channel noise (-3.5 dB SNR, 71.0% conf), while network transport is currently passing remaining packets.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="BPSK",
                    confidence=0.71,
                    measured_snr_db=-3.5,
                    signal_quality="POOR",
                ),
                communication_evidence=CommunicationEvidence(
                    status="CONNECTED",
                    health_score=85.0,
                    packet_loss_percent=2.0,
                    avg_latency_ms=22.0,
                    jitter_ms=4.0,
                    is_interrupted=False,
                ),
            ),
        ),
        (
            "4. Active Communication Interruption",
            "Zero packets received for 3.5 seconds; silence timeout exceeded.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="QPSK",
                    confidence=0.88,
                    measured_snr_db=8.0,
                    signal_quality="GOOD",
                ),
                communication_evidence=CommunicationEvidence(
                    status="INTERRUPTED",
                    health_score=15.0,
                    packet_loss_percent=0.0,
                    is_interrupted=True,
                    interruption_count=1,
                ),
            ),
        ),
        (
            "5. Conflicting Evidence: High Signal Quality with Severe Packet Loss",
            "Signal is immaculate (18 dB SNR, 100% conf), but network packet loss is 28%. Anomaly flagged for operator review.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="16-QAM",
                    confidence=0.999,
                    measured_snr_db=18.0,
                    signal_quality="EXCELLENT",
                ),
                communication_evidence=CommunicationEvidence(
                    status="DEGRADED",
                    health_score=44.0,
                    packet_loss_percent=28.0,
                    avg_latency_ms=145.0,
                    jitter_ms=48.0,
                    is_interrupted=False,
                ),
            ),
        ),
        (
            "6. Conflicting Evidence: Clean Network with Low AI Confidence",
            "Network delivery is 100% healthy, but modulation classifier reports ambiguous 45% confidence.",
            DecisionInput(
                signal_evidence=SignalEvidence(
                    predicted_modulation="QPSK",
                    confidence=0.45,
                    measured_snr_db=4.0,
                    signal_quality="FAIR",
                ),
                communication_evidence=CommunicationEvidence(
                    status="CONNECTED",
                    health_score=100.0,
                    packet_loss_percent=0.0,
                    avg_latency_ms=15.0,
                    jitter_ms=2.0,
                    is_interrupted=False,
                ),
            ),
        ),
    ]

    for title, desc, inp in scenarios:
        res = decision_engine.evaluate(inp, persist=False)
        print_decision_result(title, desc, res)

    print("✓ All 6 demonstration scenarios evaluated successfully.")


if __name__ == "__main__":
    main()

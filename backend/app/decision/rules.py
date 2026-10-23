"""Deterministic decision rules and threshold evaluation for Phase 6 Decision Engine.

Provides explainable, rule-based logic to correlate physical-layer signal quality
and application-layer communication telemetry without heuristic black boxes.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.app.config.settings import get_settings
from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    DecisionRuleInfo,
    OverallStatus,
    SignalEvidence,
)


@dataclass
class RuleEvaluationResult:
    """Result returned when a decision rule matches input evidence."""
    rule_id: str
    name: str
    status: OverallStatus
    consistency: ConsistencyStatus
    reason: str
    contributing_factors: List[str]
    recommendations: List[str]
    priority: int


def evaluate_rules(
    signal: Optional[SignalEvidence],
    comm: Optional[CommunicationEvidence],
) -> Tuple[RuleEvaluationResult, List[str]]:
    """Evaluate deterministic decision rules in order of priority.

    Rules evaluate in strict precedence:
        1. Link Interruption (Active silence timeout)
        2. Link Recovery (Resumed silence state)
        3. Novelty (Out-of-distribution signal signature from the novelty detector)
        4. Cross-Domain Conflict / Anomaly (High SNR with severe loss, or clean link with very low AI confidence)
        5. Network Telemetry Degradation (High loss, latency, or jitter)
        6. Signal Quality Degradation (Low or negative SNR, poor envelope)
        7. Normal Baseline Operation (Stable packet transport, verified modulation)

    Args:
        signal: Optional physical-layer signal processing and AI evidence.
        comm: Optional network communication telemetry evidence.

    Returns:
        Tuple of (matching_rule_result, list_of_all_triggered_rule_ids).
    """
    settings = get_settings()
    triggered_rules: List[str] = []

    # Safe defaults
    loss_pct = comm.packet_loss_percent if comm and comm.packet_loss_percent is not None else 0.0
    latency_ms = comm.avg_latency_ms if comm and comm.avg_latency_ms is not None else 0.0
    jitter_ms = comm.jitter_ms if comm and comm.jitter_ms is not None else 0.0
    health = comm.health_score if comm and comm.health_score is not None else 100.0
    is_interrupted = (comm and comm.is_interrupted) or (comm and comm.status == "INTERRUPTED")
    is_recovering = comm and comm.status == "RECOVERING"
    snr_db = signal.measured_snr_db if signal and signal.measured_snr_db is not None else None
    ai_conf = signal.confidence if signal and signal.confidence is not None else None
    is_outlier = bool(signal.is_outlier) if signal and signal.is_outlier is not None else False

    # ---------------------------------------------------------
    # RULE 1: Active Communication Interruption
    # ---------------------------------------------------------
    if is_interrupted:
        triggered_rules.append("RULE_INTERRUPTED_LINK")
        factors = ["Application packet timeout exceeded (silence threshold > 2.0s)"]
        if comm and comm.interruption_count:
            factors.append(f"Cumulative interruptions: {comm.interruption_count}")
        return (
            RuleEvaluationResult(
                rule_id="RULE_INTERRUPTED_LINK",
                name="Active Communication Interruption",
                status=OverallStatus.INTERRUPTED,
                consistency=ConsistencyStatus.CONSISTENT if (snr_db is not None and snr_db < 0) else ConsistencyStatus.UNCORRELATED,
                reason="Communication link is currently interrupted; no test packets received within timeout.",
                contributing_factors=factors,
                recommendations=[
                    "Check endpoint network connectivity and host socket availability.",
                    "Verify test client transmission script status.",
                    "Inspect local router or hotspot connection.",
                ],
                priority=100,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 2: Link Recovery in Progress
    # ---------------------------------------------------------
    if is_recovering:
        triggered_rules.append("RULE_RECOVERING_LINK")
        return (
            RuleEvaluationResult(
                rule_id="RULE_RECOVERING_LINK",
                name="Link Recovery in Progress",
                status=OverallStatus.RECOVERING,
                consistency=ConsistencyStatus.CONSISTENT,
                reason="Communication resumed after a detected interruption; link is restabilizing.",
                contributing_factors=["First valid packet received following silence timeout"],
                recommendations=[
                    "Monitor ongoing packet sequence continuity.",
                    "Allow telemetry to stabilize over multiple packet intervals.",
                ],
                priority=90,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 3: No Packet Traffic — link test open but transport unverified
    # ---------------------------------------------------------
    no_traffic = (
        comm is not None
        and comm.packets_received is not None
        and comm.packets_received == 0
        and not is_recovering
    )
    if no_traffic:
        triggered_rules.append("RULE_NO_PACKET_TRAFFIC")
        factors = [
            "Link test session is open but zero packets have been received",
            f"Reported transport status: {comm.status}" if comm and comm.status else "Transport status unknown",
        ]
        return (
            RuleEvaluationResult(
                rule_id="RULE_NO_PACKET_TRAFFIC",
                name="Link Test Without Traffic",
                status=OverallStatus.REVIEW,
                consistency=ConsistencyStatus.UNCORRELATED,
                reason=(
                    "No telemetry packets have arrived since the link test started, so transport "
                    "health cannot actually be verified yet."
                ),
                contributing_factors=factors,
                recommendations=[
                    "Verify the packet transmitter is running and pointed at the active session.",
                    "Confirm the communication session ID matches the transmitter's target.",
                    "Packet loss/health stay optimistic until real traffic is observed; treat 0-packet state as unverified.",
                ],
                priority=88,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 4: Novelty — Physical signal outside supported modulation set
    # ---------------------------------------------------------
    if is_outlier:
        triggered_rules.append("RULE_NOVELTY_OUTLIER")
        factors = [
            "Novelty detector flagged the feature vector as out-of-distribution "
            "for all supported modulations",
        ]
        if signal and signal.predicted_modulation:
            factors.append(f"Classifier best guess (unreliable): {signal.predicted_modulation}")
        if ai_conf is not None:
            factors.append(f"Classification confidence ({ai_conf:.1%}) applies to a class not actually supported")

        return (
            RuleEvaluationResult(
                rule_id="RULE_NOVELTY_OUTLIER",
                name="Unsupported Signal Signature (Novelty Detected)",
                status=OverallStatus.REVIEW,
                consistency=ConsistencyStatus.CONFLICTING if ai_conf is not None and ai_conf >= 0.7 else ConsistencyStatus.UNCORRELATED,
                reason=(
                    "Signal features do not resemble any supported modulation (BPSK/QPSK/16-QAM). "
                    "The classifier can only output supported classes, so its prediction here is "
                    "unreliable and must not be reported as a verified classification."
                ),
                contributing_factors=factors,
                recommendations=[
                    "Do not trust the modulation label until the signal is re-examined.",
                    "Inspect the constellation and spectrum manually for a new/interfering waveform.",
                    "Add the observed signature to the training set if it represents a new supported service.",
                ],
                priority=85,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 4: Cross-Domain Conflict — High SNR but Severe Loss
    # ---------------------------------------------------------
    has_high_snr = snr_db is not None and snr_db >= settings.DECISION_CONFLICT_SNR_THRESHOLD
    has_severe_loss = loss_pct >= settings.DECISION_CONFLICT_LOSS_THRESHOLD
    if has_high_snr and has_severe_loss:
        triggered_rules.append("RULE_CONFLICT_HIGH_SNR_HIGH_LOSS")
        factors = [
            f"Physical layer exhibits strong SNR ({snr_db:.1f} dB)",
            f"Application layer reports elevated packet loss ({loss_pct:.1f}%)",
        ]
        if ai_conf:
            factors.append(f"AI classification confidence is high ({ai_conf:.1%})")

        return (
            RuleEvaluationResult(
                rule_id="RULE_CONFLICT_HIGH_SNR_HIGH_LOSS",
                name="Conflicting Evidence: High Signal Quality with Severe Loss",
                status=OverallStatus.REVIEW,
                consistency=ConsistencyStatus.CONFLICTING,
                reason=(
                    "Conflicting observations: The physical layer exhibits strong signal-to-noise ratio, "
                    "yet the application layer experiences severe packet loss. This divergence indicates "
                    "network/buffer congestion or host processing bottlenecks rather than RF degradation."
                ),
                contributing_factors=factors,
                recommendations=[
                    "Investigate IP network router buffers, Wi-Fi channel airtime contention, or host CPU load.",
                    "Verify physical RF path is clear before attributing issue to wireless interference.",
                ],
                priority=80,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 4: Cross-Domain Conflict — Clean Network with Low AI Confidence
    # ---------------------------------------------------------
    has_clean_link = health >= 90.0 and loss_pct == 0.0
    has_low_ai_conf = ai_conf is not None and ai_conf < settings.DECISION_CONFIDENCE_THRESHOLD
    if has_clean_link and has_low_ai_conf:
        triggered_rules.append("RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE")
        factors = [
            f"Communication health is optimal ({health:.1f}/100, 0% loss)",
            f"AI classification confidence is low ({ai_conf:.1%})",
        ]
        if signal and signal.predicted_modulation:
            factors.append(f"Predicted modulation: {signal.predicted_modulation}")

        return (
            RuleEvaluationResult(
                rule_id="RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE",
                name="Conflicting Evidence: Clean Network with Low AI Confidence",
                status=OverallStatus.REVIEW,
                consistency=ConsistencyStatus.CONFLICTING,
                reason=(
                    "Conflicting observations: Packet transport is functioning cleanly with 0% loss, "
                    "but AI modulation confidence is below threshold. Signal may have phase/frequency distortion "
                    "or out-of-distribution constellation characteristics."
                ),
                contributing_factors=factors,
                recommendations=[
                    "Inspect signal constellation diagram and power spectral density.",
                    "Verify carrier frequency offset and I/Q balance.",
                ],
                priority=75,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 6: Network Telemetry Degradation
    # ---------------------------------------------------------
    is_net_degraded = (
        loss_pct >= settings.COMMUNICATION_PACKET_LOSS_WARNING_PERCENT
        or latency_ms >= settings.COMMUNICATION_LATENCY_WARNING_MS
        or jitter_ms >= settings.COMMUNICATION_JITTER_WARNING_MS
        or health < settings.DECISION_HEALTH_WARNING_THRESHOLD
        or (comm and comm.status == "DEGRADED")
    )

    if is_net_degraded:
        triggered_rules.append("RULE_DEGRADED_NETWORK")
        factors = []
        if loss_pct >= settings.COMMUNICATION_PACKET_LOSS_WARNING_PERCENT:
            factors.append(f"Packet loss ({loss_pct:.1f}%) exceeds warning threshold ({settings.COMMUNICATION_PACKET_LOSS_WARNING_PERCENT:.1f}%)")
        if latency_ms >= settings.COMMUNICATION_LATENCY_WARNING_MS:
            factors.append(f"Average latency ({latency_ms:.1f} ms) exceeds threshold ({settings.COMMUNICATION_LATENCY_WARNING_MS:.1f} ms)")
        if jitter_ms >= settings.COMMUNICATION_JITTER_WARNING_MS:
            factors.append(f"Jitter ({jitter_ms:.1f} ms) exceeds warning threshold ({settings.COMMUNICATION_JITTER_WARNING_MS:.1f} ms)")
        if health < settings.DECISION_HEALTH_WARNING_THRESHOLD:
            factors.append(f"Communication health score ({health:.1f}/100) is degraded")

        # Consistency check with signal
        consistency = ConsistencyStatus.CONSISTENT if (snr_db is not None and snr_db < 5.0) else ConsistencyStatus.UNCORRELATED

        return (
            RuleEvaluationResult(
                rule_id="RULE_DEGRADED_NETWORK",
                name="Network Communication Degradation",
                status=OverallStatus.DEGRADED,
                consistency=consistency,
                reason="Communication performance is degraded due to network packet loss, latency, or jitter.",
                contributing_factors=factors,
                recommendations=[
                    "Check network link quality and signal range between endpoints.",
                    "Assess Wi-Fi channel utilization and reduce competing traffic.",
                ],
                priority=60,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 7: Signal Quality Degradation
    # ---------------------------------------------------------
    is_signal_degraded = (
        (snr_db is not None and snr_db < settings.DECISION_SNR_WARNING_DB)
        or (signal and signal.signal_quality in ("POOR", "VERY_LOW"))
    )

    if is_signal_degraded:
        triggered_rules.append("RULE_DEGRADED_SIGNAL")
        factors = []
        if snr_db is not None and snr_db < settings.DECISION_SNR_WARNING_DB:
            factors.append(f"Measured SNR ({snr_db:.1f} dB) is below minimum threshold ({settings.DECISION_SNR_WARNING_DB:.1f} dB)")
        if signal and signal.signal_quality:
            factors.append(f"Signal quality categorized as {signal.signal_quality}")

        return (
            RuleEvaluationResult(
                rule_id="RULE_DEGRADED_SIGNAL",
                name="Signal Physical Layer Degradation",
                status=OverallStatus.DEGRADED,
                consistency=ConsistencyStatus.UNCORRELATED if loss_pct < 2.0 else ConsistencyStatus.CONSISTENT,
                reason="Physical-layer signal degradation detected; low SNR observed.",
                contributing_factors=factors,
                recommendations=[
                    "Check transmitter signal amplification and antenna alignment.",
                    "Evaluate background channel noise and interference levels.",
                ],
                priority=50,
            ),
            triggered_rules,
        )

    # ---------------------------------------------------------
    # RULE 8: Normal Baseline Operation
    # ---------------------------------------------------------
    triggered_rules.append("RULE_NORMAL_OPERATION")
    factors = [
        f"Communication health score optimal ({health:.1f}/100)",
        f"Packet loss is within limits ({loss_pct:.1f}%)",
    ]
    if latency_ms:
        factors.append(f"Latency is nominal ({latency_ms:.1f} ms)")
    if ai_conf:
        factors.append(f"Modulation classification confident ({ai_conf:.1%})")
    if snr_db is not None:
        factors.append(f"Signal SNR is adequate ({snr_db:.1f} dB)")

    consistency = ConsistencyStatus.CONSISTENT if (signal and comm) else ConsistencyStatus.UNCORRELATED
    if signal and comm:
        reason = (
            "Communication link operates within normal parameters with verified signal "
            "quality and stable transport."
        )
    elif comm:
        reason = (
            "Transport metrics are within baseline limits, but no physical-layer signal "
            "evidence is available for cross-verification yet."
        )
    else:
        reason = "Only physical-layer signal evidence is available and it is within baseline limits."

    return (
        RuleEvaluationResult(
            rule_id="RULE_NORMAL_OPERATION",
            name="Normal Communication Operation",
            status=OverallStatus.NORMAL,
            consistency=consistency,
            reason=reason,
            contributing_factors=factors,
            recommendations=[
                "Continue standard communication monitoring.",
                "Maintain periodic baseline telemetry recording.",
            ],
            priority=10,
        ),
        triggered_rules,
    )


def get_all_rules_info() -> List[DecisionRuleInfo]:
    """Return descriptive metadata for all registered decision rules."""
    return [
        DecisionRuleInfo(
            rule_id="RULE_INTERRUPTED_LINK",
            name="Active Communication Interruption",
            category="Communication",
            priority=100,
            description="Triggers when silence interval exceeds timeout (default 2.0s).",
        ),
        DecisionRuleInfo(
            rule_id="RULE_RECOVERING_LINK",
            name="Link Recovery in Progress",
            category="Communication",
            priority=90,
            description="Triggers on arrival of first packet following a silence timeout.",
        ),
        DecisionRuleInfo(
            rule_id="RULE_NO_PACKET_TRAFFIC",
            name="Link Test Without Traffic",
            category="Communication",
            priority=88,
            description="Flags review when a link test session is open but zero packets have been received, so transport health is unverified.",
        ),
        DecisionRuleInfo(
            rule_id="RULE_NOVELTY_OUTLIER",
            name="Unsupported Signal Signature (Novelty Detected)",
            category="Signal",
            priority=85,
            description="Flags review when the novelty detector marks the signal features as out-of-distribution for all supported modulations.",
        ),
        DecisionRuleInfo(
            rule_id="RULE_CONFLICT_HIGH_SNR_HIGH_LOSS",
            name="Cross-Domain Conflict (High SNR, High Loss)",
            category="Cross-Domain",
            priority=80,
            description="Flags review when physical SNR is strong (>=10 dB) but packet loss is severe (>=15%).",
        ),
        DecisionRuleInfo(
            rule_id="RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE",
            name="Cross-Domain Conflict (Clean Network, Low AI Confidence)",
            category="Cross-Domain",
            priority=75,
            description="Flags review when network is 100% healthy but AI confidence is low (<70%).",
        ),
        DecisionRuleInfo(
            rule_id="RULE_DEGRADED_NETWORK",
            name="Network Communication Degradation",
            category="Communication",
            priority=60,
            description="Triggers when packet loss (>=5%), latency (>=100ms), or jitter (>=30ms) exceed warning thresholds.",
        ),
        DecisionRuleInfo(
            rule_id="RULE_DEGRADED_SIGNAL",
            name="Signal Physical Layer Degradation",
            category="Signal",
            priority=50,
            description="Triggers when physical SNR drops below 0 dB or signal quality is poor.",
        ),
        DecisionRuleInfo(
            rule_id="RULE_NORMAL_OPERATION",
            name="Normal Communication Operation",
            category="General",
            priority=10,
            description="Default state when all metrics reside within baseline bounds.",
        ),
    ]

"""Core Decision Engine implementation (Phase 6).

Combines physical-layer signal evidence and network communication telemetry,
applies deterministic decision rules, checks cross-domain consistency, produces
explainable decisions, and integrates with database records and alerts.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.communication.packet_monitor import packet_monitor
from backend.app.database.models import Alert, DecisionRecord, utc_now
from backend.app.database.repository import (
    AlertRepository,
    CommunicationSessionRepository,
    DecisionRepository,
    ExperimentRepository,
)
from backend.app.decision.correlator import (
    build_communication_summary,
    build_signal_summary,
    compute_decision_confidence,
)
from backend.app.decision.rules import evaluate_rules, get_all_rules_info
from backend.app.schemas.decision import (
    CommunicationEvidence,
    DecisionInput,
    DecisionResult,
    DecisionRuleInfo,
    OverallStatus,
    SignalEvidence,
)

logger = logging.getLogger("spectrumsentry.decision")


class DecisionEngine:
    """Explainable, deterministic cross-domain decision engine."""

    def evaluate(
        self,
        input_evidence: DecisionInput,
        db: Optional[Session] = None,
        persist: bool = True,
    ) -> DecisionResult:
        """Evaluate combined signal and communication evidence.

        Args:
            input_evidence: Payload containing signal and/or communication evidence.
            db: Optional database session for persistence and alert generation.
            persist: If True and db is provided, persists decision to SQLite.

        Returns:
            Structured DecisionResult detailing status, confidence, consistency,
            reasons, contributing factors, and recommendations.
        """
        signal = input_evidence.signal_evidence
        comm = input_evidence.communication_evidence

        # 1. Deterministic Rule Evaluation
        rule_res, triggered_rules = evaluate_rules(signal, comm)

        # 2. Decision Confidence Formulation
        decision_conf = compute_decision_confidence(
            overall_status=rule_res.status,
            consistency=rule_res.consistency,
            signal=signal,
            comm=comm,
        )

        # 3. Domain Summaries
        signal_summary = build_signal_summary(signal)
        comm_summary = build_communication_summary(comm)

        # 4. Assemble Result
        result = DecisionResult(
            id=None,
            timestamp=utc_now(),
            overall_status=rule_res.status,
            decision_confidence=decision_conf,
            consistency=rule_res.consistency,
            primary_reason=rule_res.reason,
            contributing_factors=rule_res.contributing_factors,
            rules_triggered=triggered_rules,
            signal_summary=signal_summary,
            communication_summary=comm_summary,
            recommendations=rule_res.recommendations,
        )

        # 5. Database Persistence & Alert Dispatch
        if db is not None and persist:
            record = DecisionRecord(
                timestamp=result.timestamp,
                overall_status=result.overall_status.value,
                decision_confidence=result.decision_confidence,
                consistency=result.consistency.value,
                primary_reason=result.primary_reason,
                contributing_factors=result.contributing_factors,
                rules_triggered=result.rules_triggered,
                signal_summary=result.signal_summary,
                communication_summary=result.communication_summary,
                recommendations=result.recommendations,
                extra_metadata=input_evidence.context_metadata,
            )
            decision_repo = DecisionRepository(db)
            saved_record = decision_repo.create(record)
            result.id = saved_record.id

            # Generate System Alert for impaired states
            if result.overall_status in (OverallStatus.INTERRUPTED, OverallStatus.DEGRADED, OverallStatus.REVIEW):
                severity = "CRITICAL" if result.overall_status == OverallStatus.INTERRUPTED else "WARNING"
                alert_repo = AlertRepository(db)
                alert = Alert(
                    timestamp=result.timestamp,
                    severity=severity,
                    category="COMMUNICATION" if result.overall_status != OverallStatus.REVIEW else "SYSTEM",
                    message=f"Decision Engine [{result.overall_status.value}]: {result.primary_reason[:200]}",
                    source="DecisionEngine",
                    resolved=False,
                    extra_data={
                        "decision_id": result.id,
                        "consistency": result.consistency.value,
                        "decision_confidence": result.decision_confidence,
                    },
                )
                alert_repo.create(alert)

            logger.info(
                "Decision evaluated: %s (conf: %.2f, consistency: %s) - %s",
                result.overall_status.value,
                result.decision_confidence,
                result.consistency.value,
                result.primary_reason,
            )

        return result

    def evaluate_from_latest(
        self,
        db: Session,
        session_id: Optional[str] = None,
        experiment_id: Optional[str] = None,
        persist: bool = True,
    ) -> DecisionResult:
        """Fetch latest active communication metrics and latest signal experiment, then evaluate.

        Args:
            db: Database session.
            session_id: Optional target communication session ID.
            experiment_id: Optional target signal experiment ID.
            persist: Whether to persist the decision result.

        Returns:
            DecisionResult based on current live state.
        """
        # 1. Resolve Communication Evidence
        comm_evidence = None
        target_session = session_id or packet_monitor.active_session_id
        if target_session and target_session in packet_monitor.sessions:
            metrics = packet_monitor.get_live_metrics(target_session)
            comm_evidence = CommunicationEvidence(
                status=metrics.status.value,
                health_score=metrics.health_score,
                packet_loss_percent=metrics.packet_loss_percent,
                avg_latency_ms=metrics.avg_latency_ms,
                jitter_ms=metrics.jitter_ms,
                throughput_mbps=metrics.throughput_mbps,
                interruption_count=metrics.interruption_count,
                is_interrupted=metrics.is_interrupted,
                recovery_count=metrics.recovery_count,
            )
        else:
            # Query latest from database
            session_repo = CommunicationSessionRepository(db)
            latest_sess = session_repo.get_all(skip=0, limit=1)
            if latest_sess:
                s = latest_sess[0]
                comm_evidence = CommunicationEvidence(
                    status=s.final_status,
                    health_score=s.health_score,
                    packet_loss_percent=s.packet_loss_percent,
                    avg_latency_ms=s.avg_latency_ms,
                    jitter_ms=s.jitter_ms,
                    throughput_mbps=(s.throughput_bps / 1000000.0) if s.throughput_bps else 0.0,
                    interruption_count=s.interruption_count,
                    is_interrupted=s.final_status == "INTERRUPTED",
                    recovery_count=s.recovery_count,
                )

        # 2. Resolve Signal Evidence
        signal_evidence = None
        exp_repo = ExperimentRepository(db)
        if experiment_id:
            exp = exp_repo.get_by_id(experiment_id)
        else:
            latest_exps = exp_repo.get_all(skip=0, limit=1)
            exp = latest_exps[0] if latest_exps else None

        if exp:
            signal_evidence = SignalEvidence(
                predicted_modulation=exp.predicted_modulation,
                confidence=exp.confidence,
                measured_snr_db=exp.snr_db,
                signal_power=exp.signal_power,
                noise_power=exp.noise_power,
                signal_quality="EXCELLENT" if exp.snr_db >= 12.0 else ("GOOD" if exp.snr_db >= 5.0 else ("FAIR" if exp.snr_db >= 0.0 else "POOR")),
            )

        input_evidence = DecisionInput(
            signal_evidence=signal_evidence,
            communication_evidence=comm_evidence,
            context_metadata={
                "source": "evaluate_from_latest",
                "session_id": target_session,
                "experiment_id": exp.id if exp else None,
            },
        )

        return self.evaluate(input_evidence, db=db, persist=persist)

    def get_active_rules(self) -> List[DecisionRuleInfo]:
        """Return all active decision rules."""
        return get_all_rules_info()


# Global singleton instance
decision_engine = DecisionEngine()

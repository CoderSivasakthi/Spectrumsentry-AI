"""Unified Real-Time Monitoring Manager (Phase 7).

Orchestrates cross-domain integration connecting:
  - Phase 4: AI Modulation Classification & Signal Evidence
  - Phase 5: Application-Level Network Packet Telemetry
  - Phase 6: Deterministic Explainable Decision Engine
  - Real-Time WebSocket Streaming & REST State Polling
"""

import asyncio
from datetime import datetime, timezone
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid
import numpy as np
from sqlalchemy.orm import Session

from backend.app.communication.packet_monitor import SessionMonitor, packet_monitor
from backend.app.config.settings import get_settings
from backend.app.database.database import SessionLocal
from backend.app.database.models import (
    Alert,
    CommunicationSession,
    MonitoringSession,
    utc_now,
)
from backend.app.database.repository import (
    AlertRepository,
    CommunicationSessionRepository,
    ExperimentRepository,
    MonitoringSessionRepository,
)
from backend.app.decision.engine import decision_engine
from backend.app.schemas.communication import (
    CommunicationStatus,
    SessionStartRequest,
    SessionStopRequest,
)
from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    DecisionInput,
    DecisionResult,
    OverallStatus,
    SignalEvidence,
)
from backend.app.schemas.monitoring import (
    CommunicationSnapshot,
    DecisionSnapshot,
    MonitoringHistoryResponse,
    MonitoringSessionResponse,
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
    MonitoringSessionSummary,
    SignalEvidenceInput,
    SignalSnapshot,
    UnifiedMonitoringSnapshot,
)
from backend.app.websocket.manager import monitoring_ws_manager

logger = logging.getLogger("spectrumsentry.monitoring")


class UnifiedMonitoringManager:
    """Central integration engine coordinating real-time telemetry, signal evidence, and decisions."""

    def __init__(self):
        self.active_monitoring_session_id: Optional[str] = None
        self.active_communication_session_id: Optional[str] = None

        # Signal Evidence State
        self.latest_signal_evidence: Optional[SignalEvidenceInput] = None
        self.latest_signal_time: Optional[float] = None  # posix seconds

        # Cached last snapshot
        self.latest_snapshot: Optional[UnifiedMonitoringSnapshot] = None

        # Continuous signal pipeline (background task while a session is active)
        self._signal_task: Optional[asyncio.Task] = None
        self._signal_config: Optional[Dict[str, Any]] = None

        # Register callback with Phase 5 PacketMonitor
        packet_monitor.register_listener(self.on_packet_ingested)

    def start_session(
        self, request: MonitoringSessionStartRequest, db: Session
    ) -> MonitoringSessionResponse:
        """Initiate a unified monitoring session and correlate with communication domain."""
        monitoring_session_id = request.monitoring_session_id or f"mon_{uuid.uuid4().hex[:12]}"
        comm_session_id = request.communication_session_id

        # Auto-start underlying communication session if requested
        if request.auto_start_communication:
            comm_start_req = SessionStartRequest(
                session_id=comm_session_id,
                expected_packets=request.expected_packets,
                interval_seconds=request.interval_seconds,
                timeout_seconds=request.timeout_seconds,
                extra_metadata=request.extra_metadata,
            )
            comm_resp = packet_monitor.start_session(comm_start_req, db)
            comm_session_id = comm_resp.session_id

        self.active_monitoring_session_id = monitoring_session_id
        self.active_communication_session_id = comm_session_id

        # Keep physical-layer evidence flowing while the session is live
        self._start_signal_pipeline()

        # Persist session to SQLite
        session_repo = MonitoringSessionRepository(db)
        existing = session_repo.get_by_id(monitoring_session_id)
        started_time = utc_now()
        if not existing:
            db_session = MonitoringSession(
                monitoring_session_id=monitoring_session_id,
                communication_session_id=comm_session_id,
                created_at=started_time,
                started_at=started_time,
                status="ACTIVE",
                extra_metadata=request.extra_metadata,
            )
            session_repo.create(db_session)

        # Broadcast session started event over monitoring WebSocket
        self.broadcast_event(
            "session_started",
            {
                "monitoring_session_id": monitoring_session_id,
                "communication_session_id": comm_session_id,
                "started_at": started_time.isoformat(),
            },
        )

        # Broadcast initial snapshot
        snapshot = self.get_current_snapshot(db=db)
        self.broadcast_snapshot(snapshot)

        logger.info(
            "Unified monitoring session started: %s (Linked Comm: %s)",
            monitoring_session_id,
            comm_session_id,
        )

        return MonitoringSessionResponse(
            monitoring_session_id=monitoring_session_id,
            communication_session_id=comm_session_id,
            status="ACTIVE",
            started_at=started_time,
            message="Unified monitoring session active",
        )

    def stop_session(
        self, request: MonitoringSessionStopRequest, db: Session
    ) -> MonitoringSessionSummary:
        """Cleanly terminate an active unified monitoring session and persist summary."""
        target_id = request.monitoring_session_id or self.active_monitoring_session_id
        if not target_id:
            raise ValueError("No active monitoring session to stop.")

        session_repo = MonitoringSessionRepository(db)
        db_sess = session_repo.get_by_id(target_id)
        if not db_sess:
            raise ValueError(f"Monitoring session '{target_id}' not found.")

        # Stop communication session if requested and linked
        if request.stop_communication and self.active_communication_session_id:
            try:
                stop_comm_req = SessionStopRequest(
                    session_id=self.active_communication_session_id,
                    reason=request.reason,
                )
                packet_monitor.stop_session(stop_comm_req, db)
            except Exception as exc:
                logger.warning("Error stopping underlying communication session: %s", exc)

        ended_time = utc_now()
        db_sess.ended_at = ended_time
        db_sess.status = "STOPPED"
        session_repo.update(db_sess)

        # Broadcast session stopped event
        self.broadcast_event(
            "session_stopped",
            {
                "monitoring_session_id": target_id,
                "ended_at": ended_time.isoformat(),
                "reason": request.reason,
            },
        )

        if self.active_monitoring_session_id == target_id:
            self.active_monitoring_session_id = None
            self.active_communication_session_id = None

        # No live session: stop producing signal evidence and reset to an
        # honest inactive-feed state rather than leaving stale numbers visible.
        self._stop_signal_pipeline()
        self.clear_signal_evidence()

        # Session is closing: no conditions remain observable, clear open alerts
        try:
            AlertRepository(db).resolve_all_active()
        except Exception as exc:
            logger.debug("Alert auto-resolution on session stop failed: %s", exc)

        logger.info("Unified monitoring session stopped: %s", target_id)

        return MonitoringSessionSummary.model_validate(db_sess)

    # ------------------------------------------------------------------
    # Continuous signal pipeline (synthetic channel + real AI classifier)
    # Signal evidence otherwise only refreshes on external ingest or a
    # one-shot /signal/simulate call; without a producer the live monitor's
    # physical-layer card would blank out ~30 s after each manual run.
    # ------------------------------------------------------------------

    _SUPPORTED_MODULATIONS = ("BPSK", "QPSK", "16-QAM")

    def _start_signal_pipeline(self) -> None:
        """Launch the background signal evidence producer for the active session."""
        self._stop_signal_pipeline()
        settings = get_settings()
        if not settings.SIGNAL_EVIDENCE_AUTO_SIMULATE:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Sync context (unit tests): the pipeline is a live-server feature only
            return
        self._signal_config = {
            # One scheme per session so the classification stays coherent, on a
            # channel SNR that drifts realistically cycle to cycle
            "modulation": random.choice(self._SUPPORTED_MODULATIONS),
            "base_snr_db": random.uniform(8.0, 18.0),
        }
        self._signal_task = loop.create_task(self._signal_pipeline_loop())

    def _stop_signal_pipeline(self) -> None:
        task = self._signal_task
        self._signal_task = None
        self._signal_config = None
        if task is not None and not task.done():
            task.cancel()

    async def _signal_pipeline_loop(self) -> None:
        """Continuously simulate a channel signal, classify it via the real MLP pipeline, and ingest evidence."""
        from backend.app.signal_processing.features import extract_features
        from backend.app.signal_processing.generator import run_signal_experiment

        cfg = self._signal_config
        if cfg is not None:
            logger.info(
                "Signal pipeline started: %s @ ~%.1f dB base SNR",
                cfg["modulation"],
                cfg["base_snr_db"],
            )
        try:
            while True:
                cfg = self._signal_config
                if cfg is None:  # Session ended between cycles
                    break
                interval = get_settings().SIGNAL_EVIDENCE_INTERVAL_SECONDS
                snr_db = max(-5.0, cfg["base_snr_db"] + random.uniform(-2.0, 2.0))
                try:
                    experiment = run_signal_experiment(
                        modulation=cfg["modulation"],
                        sample_count=1024,
                        snr_db=snr_db,
                    )
                    features_vector, _feature_dict = extract_features(
                        experiment.noisy_signal, sample_rate=experiment.sample_rate
                    )
                    noise_power = (
                        float(np.mean(np.abs(experiment.noise) ** 2))
                        if experiment.noise is not None
                        and np.isfinite(np.mean(np.abs(experiment.noise) ** 2))
                        else None
                    )
                    evidence = SignalEvidenceInput(
                        features=[float(f) for f in np.asarray(features_vector, dtype=float)],
                        estimated_snr_db=experiment.measured_snr_db,
                        signal_power=float(experiment.signal_power),
                        noise_power=noise_power,
                        extra_data={
                            "simulated": True,
                            "requested_modulation": cfg["modulation"],
                            "requested_snr_db": snr_db,
                            "source": "live_pipeline",
                        },
                    )
                    db = SessionLocal()
                    try:
                        self.update_signal_evidence(evidence, db=db)
                    finally:
                        db.close()
                except Exception as exc:
                    logger.warning("Signal pipeline cycle failed: %s", exc)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
        finally:
            logger.info("Signal pipeline stopped.")

    def update_signal_evidence(
        self, signal_in: SignalEvidenceInput, db: Optional[Session] = None
    ) -> UnifiedMonitoringSnapshot:
        """Ingest fresh physical-layer signal evidence, compute AI inference if features provided, and re-evaluate."""
        # 1. Feature-based AI inference via Phase 4 predictor if features provided
        if signal_in.features is not None:
            try:
                from backend.app.ml.predictor import ModulationPredictor
                settings = get_settings()
                model_path = settings.AI_MODEL_PATH
                if not model_path.exists() and settings.AI_MODEL_FALLBACK_PATH.exists():
                    model_path = settings.AI_MODEL_FALLBACK_PATH
                predictor = ModulationPredictor(model_path=model_path)
                # Match the evidence's feature count to the model contract: fall back
                # to the legacy v1 model when active evidence is on the 23-feature
                # contract and the preferred v2 cumulant model is 6-feature (or vice
                # versa), so live traffic is served by whichever contract fits.
                if predictor.pipeline is not None and len(signal_in.features) != predictor.expected_feature_count():
                    fallback = ModulationPredictor(model_path=settings.AI_MODEL_FALLBACK_PATH)
                    if fallback.pipeline is not None and len(signal_in.features) == fallback.expected_feature_count():
                        predictor = fallback
                if predictor.pipeline is not None:
                    # Resolve the novelty detector matching the active model's
                    # feature contract (v1 moments vs v2 cumulants, fix #8).
                    expected = predictor.expected_feature_count()
                    detector_path = settings.AI_NOVELTY_DETECTOR_PATH
                    if expected == 6 and settings.AI_NOVELTY_DETECTOR_CUMULANT_PATH.exists():
                        detector_path = settings.AI_NOVELTY_DETECTOR_CUMULANT_PATH
                    predictor.novelty_detector_path = detector_path
                    pred_res = predictor.predict_single(
                        np.array(signal_in.features, dtype=np.float32)
                    )
                    if signal_in.predicted_modulation is None:
                        signal_in.predicted_modulation = pred_res.get("predicted_modulation")
                    if signal_in.ai_confidence is None:
                        signal_in.ai_confidence = pred_res.get("confidence")
                    if signal_in.is_outlier is None:
                        signal_in.is_outlier = pred_res.get("is_outlier")
                    if signal_in.novelty_score is None:
                        signal_in.novelty_score = pred_res.get("novelty_score")
            except Exception as exc:
                logger.warning("AI inference on provided features failed: %s", exc)

        # 2. Experiment-based lookup if experiment_id provided
        if signal_in.experiment_id and db is not None:
            exp_repo = ExperimentRepository(db)
            exp = exp_repo.get_by_id(signal_in.experiment_id)
            if exp:
                if signal_in.predicted_modulation is None:
                    signal_in.predicted_modulation = exp.predicted_modulation or exp.modulation
                if signal_in.ai_confidence is None:
                    signal_in.ai_confidence = exp.confidence
                if signal_in.estimated_snr_db is None:
                    signal_in.estimated_snr_db = exp.snr_db
                if signal_in.signal_power is None:
                    signal_in.signal_power = exp.signal_power
                if signal_in.noise_power is None:
                    signal_in.noise_power = exp.noise_power

        # 3. Derive signal quality tier if SNR available and quality omitted
        if signal_in.estimated_snr_db is not None and signal_in.signal_quality is None:
            snr = signal_in.estimated_snr_db
            signal_in.signal_quality = (
                "EXCELLENT" if snr >= 12.0
                else ("GOOD" if snr >= 5.0
                else ("FAIR" if snr >= 0.0 else "POOR"))
            )

        # 4. Set timestamp and store
        now_posix = time.time()
        if signal_in.timestamp is None:
            signal_in.timestamp = datetime.fromtimestamp(now_posix, timezone.utc)
        self.latest_signal_evidence = signal_in
        self.latest_signal_time = now_posix

        # 5. Generate updated snapshot & broadcast
        snapshot = self.get_current_snapshot(db=db)

        # Broadcast signal_update and monitoring_snapshot
        self.broadcast_event(
            "signal_update",
            snapshot.signal.model_dump(mode="json"),
        )
        self.broadcast_snapshot(snapshot)

        return snapshot

    def clear_signal_evidence(self) -> None:
        """Clear current signal evidence (resets physical-layer state to unavailable)."""
        self.latest_signal_evidence = None
        self.latest_signal_time = None

    def _check_signal_freshness(self) -> Tuple[bool, bool, Optional[datetime], Optional[float]]:
        """Evaluate physical-layer signal availability and freshness.

        Returns:
            Tuple of (available, stale, timestamp, age_seconds).
        """
        if self.latest_signal_evidence is None or self.latest_signal_time is None:
            return False, False, None, None

        now = time.time()
        age = max(0.0, round(now - self.latest_signal_time, 2))
        settings = get_settings()
        stale = age > settings.MAX_SIGNAL_EVIDENCE_AGE_SECONDS
        ts = self.latest_signal_evidence.timestamp or datetime.fromtimestamp(
            self.latest_signal_time, timezone.utc
        )

        return True, stale, ts, age

    def _get_communication_evidence(
        self, session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[CommunicationEvidence], CommunicationSnapshot]:
        """Fetch active application-layer network telemetry.

        Returns:
            Tuple of (available, communication_evidence_for_decision, communication_snapshot).
        """
        target_id = (
            session_id
            or self.active_communication_session_id
            or packet_monitor.active_session_id
        )

        if target_id and target_id in packet_monitor.sessions:
            metrics = packet_monitor.get_live_metrics(target_id)
            is_recovering = metrics.status == CommunicationStatus.RECOVERING

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
                packets_received=metrics.packets_received,
            )

            comm_snapshot = CommunicationSnapshot(
                available=True,
                status=metrics.status.value,
                packet_loss_percent=metrics.packet_loss_percent,
                latency_ms=metrics.latency_ms,
                jitter_ms=metrics.jitter_ms,
                throughput_kbps=metrics.throughput_kbps,
                health_score=metrics.health_score,
                is_interrupted=metrics.is_interrupted,
                is_recovering=is_recovering,
            )

            return True, comm_evidence, comm_snapshot

        return False, None, CommunicationSnapshot(
            available=False,
            status=CommunicationStatus.STOPPED.value,
            packet_loss_percent=0.0,
            latency_ms=0.0,
            jitter_ms=0.0,
            throughput_kbps=0.0,
            health_score=100.0,
            is_interrupted=False,
            is_recovering=False,
        )

    def get_current_snapshot(
        self, db: Optional[Session] = None, session_id: Optional[str] = None
    ) -> UnifiedMonitoringSnapshot:
        """Assemble the complete real-time cross-domain monitoring snapshot.

        Connects:
          - Latest communication evidence
          - Latest signal evidence with freshness check
          - Decision Engine assessment
          - System alerts
        """
        now = utc_now()

        # 1. Gather Communication Evidence
        comm_avail, comm_evidence, comm_snapshot = self._get_communication_evidence(session_id)

        # 2. Gather Signal Evidence & Check Freshness
        sig_avail, sig_stale, sig_ts, sig_age = self._check_signal_freshness()

        sig_snapshot = SignalSnapshot(
            available=sig_avail,
            stale=sig_stale,
            timestamp=sig_ts,
            age_seconds=sig_age,
            predicted_modulation=(
                self.latest_signal_evidence.predicted_modulation if sig_avail else None
            ),
            ai_confidence=(
                self.latest_signal_evidence.ai_confidence if sig_avail else None
            ),
            estimated_snr_db=(
                self.latest_signal_evidence.estimated_snr_db if sig_avail else None
            ),
            signal_quality=(
                self.latest_signal_evidence.signal_quality if sig_avail else None
            ),
            is_outlier=(
                self.latest_signal_evidence.is_outlier if sig_avail else None
            ),
            novelty_score=(
                self.latest_signal_evidence.novelty_score if sig_avail else None
            ),
        )

        # 3. Build Decision Input
        # Note: If signal is stale, it is NOT silently treated as current valid physical evidence
        if sig_avail and not sig_stale and self.latest_signal_evidence is not None:
            sig_evidence_for_decision = SignalEvidence(
                predicted_modulation=self.latest_signal_evidence.predicted_modulation,
                confidence=self.latest_signal_evidence.ai_confidence,
                measured_snr_db=self.latest_signal_evidence.estimated_snr_db,
                signal_power=self.latest_signal_evidence.signal_power,
                noise_power=self.latest_signal_evidence.noise_power,
                signal_quality=self.latest_signal_evidence.signal_quality,
                is_outlier=self.latest_signal_evidence.is_outlier,
            )
        else:
            sig_evidence_for_decision = None

        comm_evidence_for_decision = comm_evidence if comm_avail else None

        # 4. Evaluate with Phase 6 DecisionEngine
        if not comm_avail and not sig_evidence_for_decision:
            # Standby Baseline: Neither active communication nor fresh signal observed
            dec_snapshot = DecisionSnapshot(
                status=OverallStatus.NORMAL,
                severity="INFO",
                confidence=1.0,
                consistency=ConsistencyStatus.UNCORRELATED,
                reasons=["No active communication or physical signal telemetry currently observed; system in baseline standby."],
                primary_reason="Standby baseline: Awaiting communication or signal evidence.",
                contributing_factors=[],
                recommendations=["Start a communication monitoring session or ingest signal evidence to initiate real-time correlation."],
            )
        else:
            decision_input = DecisionInput(
                signal_evidence=sig_evidence_for_decision,
                communication_evidence=comm_evidence_for_decision,
                context_metadata={
                    "monitoring_session_id": self.active_monitoring_session_id,
                    "signal_stale": sig_stale,
                },
            )
            try:
                dec_result: DecisionResult = decision_engine.evaluate(
                    decision_input, db=db, persist=False
                )

                severity = (
                    "CRITICAL"
                    if dec_result.overall_status == OverallStatus.INTERRUPTED
                    else (
                        "WARNING"
                        if dec_result.overall_status in (OverallStatus.DEGRADED, OverallStatus.REVIEW)
                        else "INFO"
                    )
                )

                reasons = [dec_result.primary_reason] + dec_result.contributing_factors

                dec_snapshot = DecisionSnapshot(
                    status=dec_result.overall_status,
                    severity=severity,
                    confidence=dec_result.decision_confidence,
                    consistency=dec_result.consistency,
                    reasons=reasons,
                    primary_reason=dec_result.primary_reason,
                    contributing_factors=dec_result.contributing_factors,
                    recommendations=dec_result.recommendations,
                )
            except Exception as exc:
                logger.error("DecisionEngine evaluation failed in monitoring aggregator: %s", exc)
                dec_snapshot = DecisionSnapshot(
                    status=OverallStatus.NORMAL,
                    severity="INFO",
                    confidence=0.5,
                    consistency=ConsistencyStatus.UNCORRELATED,
                    reasons=[f"Decision evaluation fallback: {str(exc)}"],
                    primary_reason="Decision evaluation fallback.",
                    contributing_factors=[],
                    recommendations=["Inspect telemetry inputs and engine logs."],
                )

        # 5. Retrieve Active Alerts
        # When the engine returns to a fully healthy baseline, resolve stale
        # alerts so the active list reflects currently applicable conditions
        # instead of accumulating unresolved entries from past incidents.
        if db is not None:
            healthy_baseline = (
                dec_snapshot.status == OverallStatus.NORMAL
                and dec_snapshot.severity == "INFO"
            )
            if healthy_baseline:
                try:
                    AlertRepository(db).resolve_all_active()
                except Exception as exc:
                    logger.debug("Alert auto-resolution failed: %s", exc)

        active_alerts: List[Dict[str, Any]] = []
        if db is not None:
            try:
                alert_repo = AlertRepository(db)
                alerts_db = alert_repo.get_active(limit=10)
                active_alerts = [
                    {
                        "id": a.id,
                        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                        "severity": a.severity,
                        "category": a.category,
                        "message": a.message,
                        "source": a.source,
                    }
                    for a in alerts_db
                ]
            except Exception as exc:
                logger.debug("Failed to query active alerts: %s", exc)

        snapshot = UnifiedMonitoringSnapshot(
            monitoring_session_id=self.active_monitoring_session_id,
            communication_session_id=(
                self.active_communication_session_id
                or packet_monitor.active_session_id
            ),
            timestamp=now,
            communication=comm_snapshot,
            signal=sig_snapshot,
            decision=dec_snapshot,
            alerts=active_alerts,
        )

        self.latest_snapshot = snapshot
        return snapshot

    def on_packet_ingested(
        self, session_id: str, monitor: SessionMonitor, db: Optional[Session] = None
    ) -> None:
        """Callback listener triggered on each packet ingestion in Phase 5 PacketMonitor."""
        try:
            snapshot = self.get_current_snapshot(db=db, session_id=session_id)
            self.broadcast_snapshot(snapshot)
        except Exception as exc:
            logger.debug("Error in on_packet_ingested monitoring aggregator: %s", exc)

    def broadcast_snapshot(self, snapshot: UnifiedMonitoringSnapshot) -> None:
        """Non-blocking broadcast of complete monitoring snapshot to WebSocket subscribers."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                payload = {
                    "type": "monitoring_snapshot",
                    "timestamp": snapshot.timestamp.isoformat(),
                    "data": snapshot.model_dump(mode="json"),
                }
                loop.create_task(monitoring_ws_manager.broadcast(payload))
        except RuntimeError:
            pass  # Outside running event loop (e.g. sync unit test)

    def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Non-blocking broadcast of a discrete event payload."""
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                payload = {
                    "type": event_type,
                    "timestamp": utc_now().isoformat(),
                    "data": data,
                }
                loop.create_task(monitoring_ws_manager.broadcast(payload))
        except RuntimeError:
            pass

    def get_session_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch high-level operational status of active or specified monitoring session."""
        target_id = session_id or self.active_monitoring_session_id
        sig_avail, sig_stale, _, _ = self._check_signal_freshness()
        comm_status = packet_monitor.get_session_status(self.active_communication_session_id)

        return {
            "monitoring_session_id": target_id,
            "communication_session_id": self.active_communication_session_id,
            "active": target_id is not None,
            "communication_available": comm_status.get("active", False),
            "signal_available": sig_avail,
            "signal_stale": sig_stale,
            "timestamp": utc_now().isoformat(),
        }

    def get_history(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> MonitoringHistoryResponse:
        """Fetch historical completed monitoring sessions from SQLite."""
        repo = MonitoringSessionRepository(db)
        total = repo.count()
        sessions = repo.get_all(skip=skip, limit=limit)
        items = [MonitoringSessionSummary.model_validate(s) for s in sessions]
        return MonitoringHistoryResponse(total=total, items=items)


# Global singleton instance
unified_monitor = UnifiedMonitoringManager()

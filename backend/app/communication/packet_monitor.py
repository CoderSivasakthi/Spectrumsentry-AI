"""Packet monitoring and session management engine (Phase 5).

Manages active communication monitoring sessions, processes incoming packets,
tracks sequence continuity, detects timeouts and recoveries, computes real-time
telemetry, and persists aggregated results to SQLite.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy.orm import Session

from backend.app.communication.health import (
    calculate_health_score,
    evaluate_communication_status,
)
from backend.app.communication.interruption import InterruptionDetector, InterruptionRecord
from backend.app.communication.metrics import (
    calculate_jitter,
    calculate_latency_statistics,
    calculate_packet_loss,
    calculate_sequence_gaps,
    calculate_throughput,
)
from backend.app.communication.recovery import RecoveryDetector, RecoveryRecord
from backend.app.config.settings import get_settings
from backend.app.database.models import CommunicationEvent, CommunicationSession, utc_now
from backend.app.database.repository import (
    CommunicationEventRepository,
    CommunicationSessionRepository,
)
from backend.app.schemas.communication import (
    CommunicationEventSchema,
    CommunicationEventType,
    CommunicationMetricsResponse,
    CommunicationStatus,
    PacketAck,
    PacketIn,
    SessionHistoryResponse,
    SessionStartRequest,
    SessionStartResponse,
    SessionStopRequest,
    SessionSummaryResponse,
)
from backend.app.websocket.manager import ws_manager

logger = logging.getLogger("spectrumsentry.communication")


class SessionMonitor:
    """In-memory telemetry and sequence tracker for a single communication session."""

    def __init__(
        self,
        session_id: str,
        timeout_seconds: float = 2.0,
        interval_seconds: float = 0.25,
        expected_packets: Optional[int] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ):
        settings = get_settings()
        self.session_id: str = session_id
        self.created_at: datetime = utc_now()
        self.started_at: Optional[datetime] = None
        self.ended_at: Optional[datetime] = None

        self.timeout_seconds: float = timeout_seconds
        self.interval_seconds: float = interval_seconds
        self.expected_packets: Optional[int] = expected_packets
        self.extra_metadata: Dict[str, Any] = extra_metadata or {}

        # Lifecycle state
        self.status: CommunicationStatus = CommunicationStatus.STARTING
        self.health_score: float = 100.0

        # Sequence tracking
        self.received_sequences: Set[int] = set()
        self.min_sequence: Optional[int] = None
        self.max_sequence: Optional[int] = None
        self.duplicate_count: int = 0
        self.out_of_order_count: int = 0

        # Latency & Jitter
        self.latencies_ms: List[float] = []

        # Data volume
        self.bytes_sent: int = 0
        self.bytes_received: int = 0

        # Detectors
        self.interruption_detector: InterruptionDetector = InterruptionDetector(
            timeout_seconds=timeout_seconds
        )
        self.recovery_detector: RecoveryDetector = RecoveryDetector()

        # Event log
        self.events: List[Dict[str, Any]] = []

        # Thresholds from settings
        self.warning_latency_ms: float = settings.COMMUNICATION_LATENCY_WARNING_MS
        self.warning_loss_percent: float = settings.COMMUNICATION_PACKET_LOSS_WARNING_PERCENT
        self.warning_jitter_ms: float = settings.COMMUNICATION_JITTER_WARNING_MS

        # Timestamps
        self.start_perf_time: Optional[float] = None
        self.last_packet_perf_time: Optional[float] = None

    def record_packet(
        self, packet: PacketIn, arrival_time: float
    ) -> Tuple[PacketAck, List[Dict[str, Any]]]:
        """Process an incoming test packet, update metrics, and detect events."""
        generated_events: List[Dict[str, Any]] = []

        if self.started_at is None:
            self.started_at = utc_now()
            self.start_perf_time = arrival_time
            self.status = CommunicationStatus.CONNECTED
            status_event = {
                "event_type": CommunicationEventType.STATUS_CHANGE.value,
                "timestamp": utc_now(),
                "details": {"from": "STARTING", "to": "CONNECTED"},
            }
            self.events.append(status_event)
            generated_events.append(status_event)

        # Check for timeout before this packet arrived
        timeout_event = self.interruption_detector.check_timeout(arrival_time, self.session_id)
        if timeout_event:
            self.status = CommunicationStatus.INTERRUPTED
            evt = {
                "event_type": CommunicationEventType.INTERRUPTION.value,
                "timestamp": utc_now(),
                "duration_ms": None,
                "details": {
                    "interruption_id": timeout_event.interruption_id,
                    "reason": timeout_event.reason,
                    "silence_sec": round(arrival_time - timeout_event.start_time, 2),
                },
            }
            self.events.append(evt)
            generated_events.append(evt)

        # Check for recovery if interrupted
        is_recovering = False
        if self.interruption_detector.is_interrupted:
            gaps = calculate_sequence_gaps(
                self.received_sequences, self.min_sequence, packet.sequence_number - 1
            )
            recovery_record = self.recovery_detector.process_packet_recovery(
                detector=self.interruption_detector,
                packet_arrival_time=arrival_time,
                session_id=self.session_id,
                sequence_number=packet.sequence_number,
                lost_packets_during_event=len(gaps),
            )
            if recovery_record:
                is_recovering = True
                evt = {
                    "event_type": CommunicationEventType.RECOVERY.value,
                    "timestamp": utc_now(),
                    "duration_ms": recovery_record.duration_ms,
                    "sequence_number": packet.sequence_number,
                    "details": {
                        "interruption_id": recovery_record.interruption_id,
                        "duration_ms": recovery_record.duration_ms,
                    },
                }
                self.events.append(evt)
                generated_events.append(evt)

        # Update last packet arrival in detector
        self.interruption_detector.update_packet_arrival(arrival_time)
        self.last_packet_perf_time = arrival_time

        # Sequence Analysis
        seq = packet.sequence_number
        if seq in self.received_sequences:
            self.duplicate_count += 1
            logger.debug("Duplicate sequence #%d received for session %s", seq, self.session_id)
        else:
            if self.max_sequence is not None and seq < self.max_sequence:
                self.out_of_order_count += 1
                logger.debug("Out-of-order sequence #%d received for session %s", seq, self.session_id)

            self.received_sequences.add(seq)
            if self.min_sequence is None or seq < self.min_sequence:
                self.min_sequence = seq
            if self.max_sequence is None or seq > self.max_sequence:
                self.max_sequence = seq

            self.bytes_sent += packet.payload_size
            self.bytes_received += packet.payload_size

        # Latency Calculation
        # Prefer client-measured RTT if provided, otherwise compute one-way server-client delta
        if packet.client_rtt_ms is not None:
            latency_ms = max(0.0, float(packet.client_rtt_ms))
        else:
            latency_ms = max(0.0, (arrival_time - packet.sender_timestamp) * 1000.0)
        self.latencies_ms.append(round(latency_ms, 2))

        # Recompute health and status
        expected = self._current_expected_packets()
        lost, loss_pct = calculate_packet_loss(expected, len(self.received_sequences))
        latency_stats = calculate_latency_statistics(self.latencies_ms)
        jitter = calculate_jitter(self.latencies_ms)

        self.health_score = calculate_health_score(
            packet_loss_percent=loss_pct,
            avg_latency_ms=latency_stats["avg_latency_ms"],
            jitter_ms=jitter,
            is_interrupted=self.interruption_detector.is_interrupted,
            interruption_count=self.interruption_detector.interruption_counter,
            warning_latency_ms=self.warning_latency_ms,
            warning_loss_percent=self.warning_loss_percent,
            warning_jitter_ms=self.warning_jitter_ms,
        )

        prev_status = self.status
        self.status = evaluate_communication_status(
            current_status=self.status,
            is_interrupted=self.interruption_detector.is_interrupted,
            is_recovering=is_recovering,
            packet_loss_percent=loss_pct,
            avg_latency_ms=latency_stats["avg_latency_ms"],
            jitter_ms=jitter,
            warning_loss_percent=self.warning_loss_percent,
            warning_latency_ms=self.warning_latency_ms,
            warning_jitter_ms=self.warning_jitter_ms,
        )

        if self.status != prev_status and self.status not in (CommunicationStatus.RECOVERING,):
            status_evt = {
                "event_type": CommunicationEventType.STATUS_CHANGE.value,
                "timestamp": utc_now(),
                "details": {"from": prev_status.value, "to": self.status.value},
            }
            self.events.append(status_evt)
            generated_events.append(status_evt)

        ack = PacketAck(
            session_id=self.session_id,
            sequence_number=seq,
            server_timestamp=arrival_time,
            status=self.status,
            health_score=self.health_score,
            received_packets=len(self.received_sequences),
        )
        return ack, generated_events

    def check_timeout_tick(self, current_time: float) -> Optional[Dict[str, Any]]:
        """Periodic tick to detect silence when no packets are arriving."""
        if self.status == CommunicationStatus.STOPPED:
            return None

        timeout_event = self.interruption_detector.check_timeout(current_time, self.session_id)
        if timeout_event:
            prev_status = self.status
            self.status = CommunicationStatus.INTERRUPTED

            expected = self._current_expected_packets()
            _, loss_pct = calculate_packet_loss(expected, len(self.received_sequences))
            lat_stats = calculate_latency_statistics(self.latencies_ms)
            jitter = calculate_jitter(self.latencies_ms)
            self.health_score = calculate_health_score(
                packet_loss_percent=loss_pct,
                avg_latency_ms=lat_stats["avg_latency_ms"],
                jitter_ms=jitter,
                is_interrupted=True,
                interruption_count=self.interruption_detector.interruption_counter,
            )

            evt = {
                "event_type": CommunicationEventType.INTERRUPTION.value,
                "timestamp": utc_now(),
                "duration_ms": None,
                "details": {
                    "interruption_id": timeout_event.interruption_id,
                    "reason": timeout_event.reason,
                    "silence_sec": round(current_time - timeout_event.start_time, 2),
                },
            }
            self.events.append(evt)
            return evt
        return None

    def _current_expected_packets(self) -> int:
        """Calculate currently expected packets based on sequence numbers or configured count."""
        if self.min_sequence is not None and self.max_sequence is not None:
            seq_expected = self.max_sequence - self.min_sequence + 1
            if self.expected_packets is not None:
                return max(seq_expected, self.expected_packets)
            return seq_expected
        if self.expected_packets is not None:
            return self.expected_packets
        return len(self.received_sequences)

    def get_metrics(self) -> CommunicationMetricsResponse:
        """Compute and return current real-time communication metrics."""
        expected = self._current_expected_packets()
        received_count = len(self.received_sequences)
        lost_count, loss_pct = calculate_packet_loss(expected, received_count)

        lat_stats = calculate_latency_statistics(self.latencies_ms)
        jitter = calculate_jitter(self.latencies_ms)

        duration_sec = 0.0
        if self.start_perf_time and self.last_packet_perf_time:
            duration_sec = max(0.0, self.last_packet_perf_time - self.start_perf_time)
        throughput = calculate_throughput(self.bytes_received, duration_sec)

        latest_latency = self.latencies_ms[-1] if self.latencies_ms else 0.0

        return CommunicationMetricsResponse(
            session_id=self.session_id,
            status=self.status,
            health_score=self.health_score,
            packets_sent=expected,
            packets_received=received_count,
            packets_lost=lost_count,
            packet_loss_percent=loss_pct,
            latency_ms=latest_latency,
            avg_latency_ms=lat_stats["avg_latency_ms"],
            min_latency_ms=lat_stats["min_latency_ms"],
            max_latency_ms=lat_stats["max_latency_ms"],
            median_latency_ms=lat_stats["median_latency_ms"],
            p95_latency_ms=lat_stats["p95_latency_ms"],
            p99_latency_ms=lat_stats["p99_latency_ms"],
            jitter_ms=jitter,
            bytes_sent=self.bytes_sent,
            bytes_received=self.bytes_received,
            throughput_bps=throughput["throughput_bps"],
            throughput_kbps=throughput["throughput_kbps"],
            throughput_mbps=throughput["throughput_mbps"],
            interruption_count=self.interruption_detector.interruption_counter,
            total_interruption_duration_ms=round(self.interruption_detector.total_interruption_duration_ms, 2),
            recovery_count=self.recovery_detector.recovery_count,
            is_interrupted=self.interruption_detector.is_interrupted,
            started_at=self.started_at,
            last_packet_time=utc_now() if self.last_packet_perf_time else None,
        )

    def close_session(self) -> SessionSummaryResponse:
        """Mark session stopped, resolve any pending interruption, and return full summary."""
        self.status = CommunicationStatus.STOPPED
        self.ended_at = utc_now()

        # If interrupted when closed, cap the interruption
        if self.interruption_detector.is_interrupted and self.interruption_detector.current_interruption:
            curr = time.time()
            inter = self.interruption_detector.current_interruption
            inter.end_time = curr
            dur = max(0.0, (curr - inter.start_time) * 1000.0)
            inter.duration_ms = round(dur, 2)
            self.interruption_detector.total_interruption_duration_ms += inter.duration_ms
            self.interruption_detector.interruption_history.append(inter)
            self.interruption_detector.is_interrupted = False

        expected = self._current_expected_packets()
        received_count = len(self.received_sequences)
        lost_count, loss_pct = calculate_packet_loss(expected, received_count)

        lat_stats = calculate_latency_statistics(self.latencies_ms)
        jitter = calculate_jitter(self.latencies_ms)

        duration_sec = 0.0
        if self.start_perf_time and self.last_packet_perf_time:
            duration_sec = max(0.0, self.last_packet_perf_time - self.start_perf_time)
        throughput = calculate_throughput(self.bytes_received, duration_sec)

        event_schemas = [
            CommunicationEventSchema(
                session_id=self.session_id,
                event_type=e["event_type"],
                timestamp=e["timestamp"],
                duration_ms=e.get("duration_ms"),
                sequence_number=e.get("sequence_number"),
                details=e.get("details"),
            )
            for e in self.events
        ]

        return SessionSummaryResponse(
            session_id=self.session_id,
            created_at=self.created_at,
            started_at=self.started_at,
            ended_at=self.ended_at,
            packets_sent=expected,
            packets_received=received_count,
            packets_lost=lost_count,
            packet_loss_percent=loss_pct,
            avg_latency_ms=lat_stats["avg_latency_ms"],
            min_latency_ms=lat_stats["min_latency_ms"],
            max_latency_ms=lat_stats["max_latency_ms"],
            median_latency_ms=lat_stats["median_latency_ms"],
            p95_latency_ms=lat_stats["p95_latency_ms"],
            p99_latency_ms=lat_stats["p99_latency_ms"],
            jitter_ms=jitter,
            bytes_sent=self.bytes_sent,
            bytes_received=self.bytes_received,
            throughput_bps=throughput["throughput_bps"],
            interruption_count=self.interruption_detector.interruption_counter,
            total_interruption_duration_ms=round(self.interruption_detector.total_interruption_duration_ms, 2),
            recovery_count=self.recovery_detector.recovery_count,
            health_score=self.health_score,
            final_status=self.status.value,
            extra_metadata={
                **self.extra_metadata,
                "duplicate_count": self.duplicate_count,
                "out_of_order_count": self.out_of_order_count,
            },
            events=event_schemas,
        )


class PacketMonitor:
    """Central singleton engine for orchestrating communication sessions and database persistence."""

    def __init__(self):
        self.sessions: Dict[str, SessionMonitor] = {}
        self.active_session_id: Optional[str] = None
        self.packet_listeners: List[Any] = []

    def register_listener(self, listener: Any) -> None:
        """Register a callback to be invoked when a packet is ingested."""
        if listener not in self.packet_listeners:
            self.packet_listeners.append(listener)

    def unregister_listener(self, listener: Any) -> None:
        """Unregister a packet listener callback."""
        if listener in self.packet_listeners:
            self.packet_listeners.remove(listener)

    def start_session(
        self, request: SessionStartRequest, db: Session
    ) -> SessionStartResponse:
        """Start a new monitoring session, initialize tracker, and persist initial DB row."""
        settings = get_settings()
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"

        timeout = request.timeout_seconds or settings.COMMUNICATION_TIMEOUT
        interval = request.interval_seconds or settings.COMMUNICATION_PACKET_INTERVAL

        monitor = SessionMonitor(
            session_id=session_id,
            timeout_seconds=timeout,
            interval_seconds=interval,
            expected_packets=request.expected_packets,
            extra_metadata=request.extra_metadata,
        )
        self.sessions[session_id] = monitor
        self.active_session_id = session_id

        # Persist session to SQLite
        session_repo = CommunicationSessionRepository(db)
        existing = session_repo.get_by_session_id(session_id)
        if not existing:
            db_session = CommunicationSession(
                session_id=session_id,
                created_at=monitor.created_at,
                started_at=monitor.started_at,
                final_status=monitor.status.value,
                health_score=monitor.health_score,
                extra_metadata=monitor.extra_metadata,
            )
            session_repo.create(db_session)

        logger.info("Communication session started: %s (timeout: %.1fs)", session_id, timeout)

        return SessionStartResponse(
            session_id=session_id,
            status=monitor.status,
            started_at=monitor.created_at,
            message="Communication monitoring session initialized",
        )

    async def ingest_packet(self, packet: PacketIn, db: Session) -> PacketAck:
        """Ingest test packet, update metrics, broadcast WebSocket telemetry, and record events."""
        session_id = packet.session_id
        if session_id not in self.sessions:
            # Auto-create session if not explicitly started
            self.start_session(SessionStartRequest(session_id=session_id), db)

        monitor = self.sessions[session_id]
        arrival_time = time.time()

        ack, generated_events = monitor.record_packet(packet, arrival_time)

        # Persist generated events to SQLite
        if generated_events:
            event_repo = CommunicationEventRepository(db)
            for evt in generated_events:
                db_event = CommunicationEvent(
                    session_id=session_id,
                    event_type=evt["event_type"],
                    timestamp=evt["timestamp"],
                    duration_ms=evt.get("duration_ms"),
                    sequence_number=evt.get("sequence_number"),
                    details=evt.get("details"),
                )
                event_repo.create(db_event)

        # Broadcast live telemetry over WebSocket
        metrics = monitor.get_metrics()
        broadcast_payload = {
            "type": "communication_metrics",
            "session_id": session_id,
            "status": metrics.status.value,
            "packets_sent": metrics.packets_sent,
            "packets_received": metrics.packets_received,
            "packet_loss_percent": metrics.packet_loss_percent,
            "latency_ms": metrics.latency_ms,
            "jitter_ms": metrics.jitter_ms,
            "throughput_mbps": metrics.throughput_mbps,
            "health_score": metrics.health_score,
            "interruption_count": metrics.interruption_count,
            "is_interrupted": metrics.is_interrupted,
        }
        # Fire-and-forget broadcast without blocking packet ACK
        try:
            asyncio.create_task(ws_manager.broadcast(broadcast_payload))
        except RuntimeError:
            pass  # Outside of event loop (e.g. in sync test)

        # Notify registered packet listeners (e.g. Phase 7 real-time aggregator)
        for listener in self.packet_listeners:
            try:
                listener(session_id, monitor, db)
            except Exception as exc:
                logger.debug("Packet listener callback error: %s", exc)

        return ack

    def stop_session(
        self, request: SessionStopRequest, db: Session
    ) -> SessionSummaryResponse:
        """Stop active session, persist finalized aggregates to DB, and return summary."""
        session_id = request.session_id
        if session_id not in self.sessions:
            # Check database for previously completed session
            session_repo = CommunicationSessionRepository(db)
            db_sess = session_repo.get_by_session_id(session_id)
            if db_sess:
                event_repo = CommunicationEventRepository(db)
                events = event_repo.get_by_session_id(session_id)
                return SessionSummaryResponse.model_validate(db_sess)
            raise ValueError(f"Session '{session_id}' not found.")

        monitor = self.sessions[session_id]
        summary = monitor.close_session()

        # Update SQLite DB record
        session_repo = CommunicationSessionRepository(db)
        db_sess = session_repo.get_by_session_id(session_id)
        if db_sess:
            db_sess.started_at = summary.started_at
            db_sess.ended_at = summary.ended_at
            db_sess.packets_sent = summary.packets_sent
            db_sess.packets_received = summary.packets_received
            db_sess.packets_lost = summary.packets_lost
            db_sess.packet_loss_percent = summary.packet_loss_percent
            db_sess.avg_latency_ms = summary.avg_latency_ms
            db_sess.min_latency_ms = summary.min_latency_ms
            db_sess.max_latency_ms = summary.max_latency_ms
            db_sess.median_latency_ms = summary.median_latency_ms
            db_sess.p95_latency_ms = summary.p95_latency_ms
            db_sess.p99_latency_ms = summary.p99_latency_ms
            db_sess.jitter_ms = summary.jitter_ms
            db_sess.bytes_sent = summary.bytes_sent
            db_sess.bytes_received = summary.bytes_received
            db_sess.throughput_bps = summary.throughput_bps
            db_sess.interruption_count = summary.interruption_count
            db_sess.total_interruption_duration_ms = summary.total_interruption_duration_ms
            db_sess.recovery_count = summary.recovery_count
            db_sess.health_score = summary.health_score
            db_sess.final_status = summary.final_status
            db_sess.extra_metadata = summary.extra_metadata
            session_repo.update(db_sess)

        if self.active_session_id == session_id:
            self.active_session_id = None

        logger.info(
            "Communication session stopped: %s | Received: %d | Loss: %.1f%% | Health: %.1f",
            session_id,
            summary.packets_received,
            summary.packet_loss_percent,
            summary.health_score,
        )

        return summary

    def get_live_metrics(
        self, session_id: Optional[str] = None
    ) -> CommunicationMetricsResponse:
        """Fetch current live metrics for a given session or active session."""
        target_id = session_id or self.active_session_id
        if not target_id or target_id not in self.sessions:
            # Return empty baseline metrics
            return CommunicationMetricsResponse(
                session_id=target_id or "none",
                status=CommunicationStatus.STOPPED,
                health_score=100.0,
                packets_sent=0,
                packets_received=0,
                packets_lost=0,
                packet_loss_percent=0.0,
                latency_ms=0.0,
                avg_latency_ms=0.0,
                min_latency_ms=0.0,
                max_latency_ms=0.0,
                median_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                jitter_ms=0.0,
                bytes_sent=0,
                bytes_received=0,
                throughput_bps=0.0,
                throughput_kbps=0.0,
                throughput_mbps=0.0,
                interruption_count=0,
                total_interruption_duration_ms=0.0,
                recovery_count=0,
                is_interrupted=False,
            )

        monitor = self.sessions[target_id]
        # Check timeout tick on read
        monitor.check_timeout_tick(time.time())
        return monitor.get_metrics()

    def get_session_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetch high-level status for active or requested session."""
        target_id = session_id or self.active_session_id
        if target_id and target_id in self.sessions:
            monitor = self.sessions[target_id]
            monitor.check_timeout_tick(time.time())
            return {
                "session_id": target_id,
                "status": monitor.status.value,
                "health_score": monitor.health_score,
                "is_interrupted": monitor.interruption_detector.is_interrupted,
                "received_packets": len(monitor.received_sequences),
                "active": monitor.status != CommunicationStatus.STOPPED,
            }
        return {
            "session_id": None,
            "status": CommunicationStatus.STOPPED.value,
            "health_score": 100.0,
            "is_interrupted": False,
            "received_packets": 0,
            "active": False,
        }

    def get_history(
        self, db: Session, skip: int = 0, limit: int = 50
    ) -> SessionHistoryResponse:
        """Fetch historical completed communication sessions from SQLite."""
        session_repo = CommunicationSessionRepository(db)
        total = session_repo.count()
        db_sessions = session_repo.get_all(skip=skip, limit=limit)
        items = [SessionSummaryResponse.model_validate(s) for s in db_sessions]
        return SessionHistoryResponse(total=total, items=items)

    def get_session_details(
        self, session_id: str, db: Session
    ) -> Optional[SessionSummaryResponse]:
        """Fetch single session with complete event history."""
        # Check active memory first
        if session_id in self.sessions:
            monitor = self.sessions[session_id]
            metrics = monitor.get_metrics()
            summary = monitor.close_session()
            # restore active status if not actually stopped
            monitor.status = metrics.status
            return summary

        # Query database
        session_repo = CommunicationSessionRepository(db)
        db_sess = session_repo.get_by_session_id(session_id)
        if not db_sess:
            return None

        event_repo = CommunicationEventRepository(db)
        events = event_repo.get_by_session_id(session_id)
        summary = SessionSummaryResponse.model_validate(db_sess)
        summary.events = [CommunicationEventSchema.model_validate(e) for e in events]
        return summary


# Global singleton instance
packet_monitor = PacketMonitor()

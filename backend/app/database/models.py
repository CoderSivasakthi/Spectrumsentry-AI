"""SQLAlchemy models for SpectrumSentry AI."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Experiment(Base):
    """Experiment model storing metadata, DSP parameters, and classification results.
    
    Raw I/Q and spectrum arrays are stored externally as NumPy (.npy) files on disk.
    """
    __tablename__ = "experiments"

    id = Column(String(64), primary_key=True, index=True)  # e.g., "EXP-001"
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    
    # Signal generation parameters
    modulation = Column(String(32), nullable=False, index=True)  # e.g., "BPSK", "QPSK", "16-QAM"
    snr_db = Column(Float, nullable=False, index=True)
    sample_count = Column(Integer, nullable=False, default=2048)
    sample_rate = Column(Float, nullable=False, default=1e6)
    noise_type = Column(String(32), nullable=False, default="AWGN")
    signal_power = Column(Float, nullable=True)
    noise_power = Column(Float, nullable=True)
    
    # Classification / Evaluation results
    predicted_modulation = Column(String(32), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    inference_time_ms = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="NORMAL", index=True)  # NORMAL, DEGRADED, INTERRUPTED, REVIEW
    model_version = Column(String(64), nullable=True)
    
    # File storage references (disk storage)
    iq_file_path = Column(String(255), nullable=True)
    spectrum_file_path = Column(String(255), nullable=True)
    feature_file_path = Column(String(255), nullable=True)
    
    # Extensible metadata without requiring schema migrations
    extra_metadata = Column(JSON, nullable=True)

    # Relationships
    predictions = relationship("Prediction", back_populates="experiment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Experiment {self.id} | Mod: {self.modulation} | SNR: {self.snr_db}dB | Status: {self.status}>"


class Prediction(Base):
    """Individual inference record for historical analysis and model evaluation."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    experiment_id = Column(String(64), ForeignKey("experiments.id", ondelete="CASCADE"), nullable=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    
    true_modulation = Column(String(32), nullable=True)
    predicted_modulation = Column(String(32), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    probabilities = Column(JSON, nullable=True)  # Dict mapping class names to probabilities
    inference_time_ms = Column(Float, nullable=False)
    
    model_name = Column(String(64), nullable=False, default="MLPClassifier")
    model_version = Column(String(64), nullable=False, default="v1.0.0")
    extra_data = Column(JSON, nullable=True)

    # Relationships
    experiment = relationship("Experiment", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction {self.id} | Pred: {self.predicted_modulation} ({self.confidence:.2%})>"


class CommunicationMetric(Base):
    """Network/communication telemetry metrics recorded over time."""
    __tablename__ = "communication_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False, index=True)
    
    packets_transmitted = Column(Integer, nullable=False, default=0)
    packets_received = Column(Integer, nullable=False, default=0)
    packet_loss_rate = Column(Float, nullable=False, default=0.0)
    latency_ms = Column(Float, nullable=False, default=0.0)
    jitter_ms = Column(Float, nullable=True, default=0.0)
    
    state = Column(String(32), nullable=False, default="NORMAL", index=True)  # NORMAL, DEGRADED, INTERRUPTED, REVIEW
    extra_data = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<CommunicationMetric seq={self.sequence_number} loss={self.packet_loss_rate:.1%} latency={self.latency_ms:.1f}ms>"


class Alert(Base):
    """System, signal, and communication event alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)  # INFO, WARNING, CRITICAL
    category = Column(String(32), nullable=False, index=True)  # SIGNAL, COMMUNICATION, SYSTEM, AI
    
    message = Column(String(255), nullable=False)
    source = Column(String(64), nullable=False, default="System")
    resolved = Column(Boolean, nullable=False, default=False, index=True)
    extra_data = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<Alert [{self.severity}] {self.category}: {self.message}>"


class CommunicationSession(Base):
    """Stores aggregated metadata and performance metrics for a communication monitoring session."""
    __tablename__ = "communication_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    # Packet sequence & loss
    packets_sent = Column(Integer, default=0, nullable=False)
    packets_received = Column(Integer, default=0, nullable=False)
    packets_lost = Column(Integer, default=0, nullable=False)
    packet_loss_percent = Column(Float, default=0.0, nullable=False)

    # Latency & Jitter metrics
    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    min_latency_ms = Column(Float, default=0.0, nullable=False)
    max_latency_ms = Column(Float, default=0.0, nullable=False)
    median_latency_ms = Column(Float, default=0.0, nullable=False)
    p95_latency_ms = Column(Float, default=0.0, nullable=False)
    p99_latency_ms = Column(Float, default=0.0, nullable=False)
    jitter_ms = Column(Float, default=0.0, nullable=False)

    # Throughput metrics
    bytes_sent = Column(Integer, default=0, nullable=False)
    bytes_received = Column(Integer, default=0, nullable=False)
    throughput_bps = Column(Float, default=0.0, nullable=False)

    # Interruption & Recovery
    interruption_count = Column(Integer, default=0, nullable=False)
    total_interruption_duration_ms = Column(Float, default=0.0, nullable=False)
    recovery_count = Column(Integer, default=0, nullable=False)

    # Health & Status
    health_score = Column(Float, default=100.0, nullable=False)
    final_status = Column(String(32), default="STARTING", nullable=False, index=True)

    # Extensible metadata
    extra_metadata = Column(JSON, nullable=True)

    # Relationships
    events = relationship("CommunicationEvent", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CommunicationSession {self.session_id} | Status: {self.final_status} | Health: {self.health_score:.1f}>"


class CommunicationEvent(Base):
    """Discrete communication events (packet loss, interruption, recovery, status change)."""
    __tablename__ = "communication_events"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(String(64), ForeignKey("communication_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(32), nullable=False, index=True)  # PACKET_LOSS, INTERRUPTION, RECOVERY, STATUS_CHANGE
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    duration_ms = Column(Float, nullable=True)
    sequence_number = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)

    # Relationships
    session = relationship("CommunicationSession", back_populates="events")

    def __repr__(self) -> str:
        return f"<CommunicationEvent {self.session_id} [{self.event_type}] at {self.timestamp}>"


class DecisionRecord(Base):
    """Stores unified communication decisions produced by the Decision Engine."""
    __tablename__ = "decision_records"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)

    overall_status = Column(String(32), nullable=False, index=True)  # NORMAL, DEGRADED, INTERRUPTED, RECOVERING, REVIEW
    decision_confidence = Column(Float, nullable=False)
    consistency = Column(String(32), nullable=False, index=True)  # CONSISTENT, CONFLICTING, UNCORRELATED

    primary_reason = Column(String(255), nullable=False)
    contributing_factors = Column(JSON, nullable=True)
    rules_triggered = Column(JSON, nullable=True)
    signal_summary = Column(JSON, nullable=True)
    communication_summary = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    extra_metadata = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<DecisionRecord {self.id} | Status: {self.overall_status} | Consistency: {self.consistency}>"


class MonitoringSession(Base):
    """Stores unified real-time monitoring sessions correlating communication, signal evidence, and decisions."""
    __tablename__ = "monitoring_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    monitoring_session_id = Column(String(64), unique=True, nullable=False, index=True)
    communication_session_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="ACTIVE", nullable=False, index=True)  # ACTIVE, STOPPED
    extra_metadata = Column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<MonitoringSession {self.monitoring_session_id} | Comm: {self.communication_session_id} | Status: {self.status}>"



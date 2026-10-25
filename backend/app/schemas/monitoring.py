"""Unified real-time monitoring schemas (Phase 7).

Defines structured cross-domain snapshot schemas correlating physical-layer signal evidence,
application-layer network telemetry, decision engine assessments, and system alerts.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.decision import ConsistencyStatus, OverallStatus


class CommunicationSnapshot(BaseModel):
    """Real-time application-layer communication state snapshot."""
    model_config = ConfigDict(from_attributes=True)

    available: bool = Field(..., description="Whether active communication telemetry is available")
    status: Optional[str] = Field(default=None, description="Communication status: STARTING, CONNECTED, DEGRADED, INTERRUPTED, etc.")
    packet_loss_percent: Optional[float] = Field(default=None, description="Packet loss percentage (0-100)")
    latency_ms: Optional[float] = Field(default=None, description="Instantaneous or average RTT latency in milliseconds")
    jitter_ms: Optional[float] = Field(default=None, description="Latency jitter variation in milliseconds")
    throughput_kbps: Optional[float] = Field(default=None, description="Measured throughput in kilobits per second")
    health_score: Optional[float] = Field(default=None, description="Link health score (0-100)")
    is_interrupted: Optional[bool] = Field(default=False, description="Whether transmission silence timeout is active")
    is_recovering: Optional[bool] = Field(default=False, description="Whether link is restabilizing following interruption")


class SignalSnapshot(BaseModel):
    """Real-time physical-layer signal and AI inference evidence snapshot."""
    model_config = ConfigDict(from_attributes=True)

    available: bool = Field(..., description="Whether signal evidence has been received")
    stale: bool = Field(default=False, description="Whether signal evidence exceeds MAX_SIGNAL_EVIDENCE_AGE_SECONDS")
    timestamp: Optional[datetime] = Field(default=None, description="Timestamp when signal evidence was recorded")
    age_seconds: Optional[float] = Field(default=None, description="Elapsed age of signal evidence in seconds")
    predicted_modulation: Optional[str] = Field(default=None, description="Classified modulation (BPSK, QPSK, 16-QAM)")
    ai_confidence: Optional[float] = Field(default=None, description="AI classification confidence [0.0 - 1.0]")
    estimated_snr_db: Optional[float] = Field(default=None, description="Estimated or measured SNR in decibels")
    signal_quality: Optional[str] = Field(default=None, description="Qualitative signal tier: EXCELLENT, GOOD, FAIR, POOR")
    is_outlier: Optional[bool] = Field(default=None, description="Novelty-detector flag: signal does not match any supported modulation")
    novelty_score: Optional[float] = Field(default=None, description="Continuous novelty score in [0, 1] (1 = extreme outlier)")


class DecisionSnapshot(BaseModel):
    """Real-time unified assessment produced by Decision Engine."""
    model_config = ConfigDict(from_attributes=True)

    status: OverallStatus = Field(..., description="Overall unified status: NORMAL, DEGRADED, INTERRUPTED, RECOVERING, REVIEW")
    severity: str = Field(..., description="Alert severity: INFO, WARNING, CRITICAL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall decision confidence score")
    consistency: ConsistencyStatus = Field(..., description="Cross-domain evidence correlation agreement")
    reasons: List[str] = Field(default_factory=list, description="List of explanatory reason statements")
    primary_reason: Optional[str] = Field(default=None, description="Primary explanatory statement")
    contributing_factors: List[str] = Field(default_factory=list, description="Specific metric factors driving decision")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")


class DeviceSnapshot(BaseModel):
    """Identity of the device a snapshot belongs to."""
    device_id: Optional[str] = Field(default=None, description="Owning device identifier")
    device_name: Optional[str] = Field(default=None, description="Human-readable device name")
    ip: Optional[str] = Field(default=None, description="Most recent client IP of the device")


class UnifiedMonitoringSnapshot(BaseModel):
    """Complete unified monitoring state combining communication, signal, decision, and alerts."""
    model_config = ConfigDict(from_attributes=True)

    monitoring_session_id: Optional[str] = Field(default=None, description="Active unified monitoring session ID")
    communication_session_id: Optional[str] = Field(default=None, description="Linked communication session ID")
    timestamp: datetime = Field(..., description="Snapshot capture timestamp (UTC)")

    device: Optional[DeviceSnapshot] = Field(default=None, description="Device this snapshot belongs to (None in legacy/global contexts)")
    communication: CommunicationSnapshot = Field(..., description="Communication domain telemetry snapshot")
    signal: SignalSnapshot = Field(..., description="Signal & AI domain evidence snapshot")
    decision: DecisionSnapshot = Field(..., description="Unified decision assessment snapshot")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Active alerts relevant to monitoring state")


class DeviceStatusResponse(BaseModel):
    """One device as reported by the devices panel / network view."""
    device_id: str
    device_name: Optional[str] = None
    ip: Optional[str] = None
    connection_state: str = Field(default="disconnected", description="connected | disconnected(grace) | disconnected")
    monitoring_session_id: Optional[str] = None
    communication_session_id: Optional[str] = None
    status: Optional[str] = None
    health_score: Optional[float] = None
    packet_loss_percent: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    jitter_ms: Optional[float] = None
    throughput_kbps: Optional[float] = None
    packets_sent: Optional[int] = None
    packets_received: Optional[int] = None
    decision_status: Optional[str] = None
    last_seen: Optional[float] = None


class DeviceRosterResponse(BaseModel):
    """Device registry summary: who is connected and how their links are doing."""
    total: int
    devices: List[DeviceStatusResponse]


class SignalEvidenceInput(BaseModel):
    """Input payload for ingesting or updating physical-layer signal evidence."""
    predicted_modulation: Optional[str] = Field(default=None, description="Classified modulation scheme")
    ai_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="AI classification confidence")
    estimated_snr_db: Optional[float] = Field(default=None, description="Measured or estimated SNR in dB")
    signal_quality: Optional[str] = Field(default=None, description="Qualitative signal tier: EXCELLENT, GOOD, FAIR, POOR")
    is_outlier: Optional[bool] = Field(default=None, description="Novelty-detector verdict (computed server-side when omitted)")
    novelty_score: Optional[float] = Field(default=None, description="Continuous novelty score in [0, 1]")
    timestamp: Optional[datetime] = Field(default=None, description="Observation timestamp (defaults to current time)")
    features: Optional[List[float]] = Field(default=None, description="Optional DSP feature vector for automated AI inference")
    signal_power: Optional[float] = Field(default=None, description="Estimated baseband signal power")
    noise_power: Optional[float] = Field(default=None, description="Estimated channel noise power")
    experiment_id: Optional[str] = Field(default=None, description="Optional linked experiment ID to pull signal parameters from")
    extra_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional signal context metadata")


class SignalSimulateRequest(BaseModel):
    """Request payload to synthesize a signal and run the real AI classification pipeline."""
    modulation: str = Field(..., description="Target modulation to synthesize: BPSK, QPSK, or 16-QAM")
    snr_db: float = Field(..., ge=-20.0, le=40.0, description="AWGN channel SNR applied to the synthesized signal")
    sample_count: int = Field(default=2048, ge=256, le=8192, description="Number of complex samples to generate")
    seed: Optional[int] = Field(default=None, description="Optional seed for reproducible simulation")


class SignalSimulateResult(BaseModel):
    """Result of a synthesized-signal AI classification run."""
    requested_modulation: str
    requested_snr_db: float
    measured_snr_db: float
    predicted_modulation: Optional[str] = None
    ai_confidence: Optional[float] = None
    is_outlier: Optional[bool] = None
    novelty_score: Optional[float] = None
    signal_quality: Optional[str] = None
    classification_matches: bool
    sample_count: int
    snapshot: UnifiedMonitoringSnapshot


class MonitoringSessionStartRequest(BaseModel):
    """Request payload to initiate a unified monitoring session."""
    monitoring_session_id: Optional[str] = Field(default=None, description="Custom monitoring session ID (auto-generated if omitted)")
    communication_session_id: Optional[str] = Field(default=None, description="Link to existing communication session or start new one")
    auto_start_communication: bool = Field(default=True, description="Whether to automatically start underlying communication session")
    expected_packets: Optional[int] = Field(default=None, ge=1, description="Expected packets for communication monitoring")
    interval_seconds: Optional[float] = Field(default=0.25, gt=0.0, description="Packet interval in seconds")
    timeout_seconds: Optional[float] = Field(default=2.0, gt=0.0, description="Interruption timeout in seconds")
    extra_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary session metadata")


class MonitoringSessionResponse(BaseModel):
    """Response returned upon initiating a unified monitoring session."""
    monitoring_session_id: str
    communication_session_id: Optional[str] = None
    status: str
    started_at: datetime
    message: str


class MonitoringSessionStopRequest(BaseModel):
    """Request payload to cleanly stop a unified monitoring session."""
    monitoring_session_id: Optional[str] = Field(default=None, description="Monitoring session ID to stop (defaults to active session)")
    device_id: Optional[str] = Field(default=None, description="Owning device ID — resolves the session when no session ID is given")
    stop_communication: bool = Field(default=True, description="Whether to also stop the underlying communication session")
    reason: Optional[str] = Field(default="completed", description="Reason for stopping session")


class MonitoringSessionSummary(BaseModel):
    """Persisted summary representation of a unified monitoring session."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    monitoring_session_id: str
    communication_session_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str
    extra_metadata: Optional[Dict[str, Any]] = None


class MonitoringHistoryResponse(BaseModel):
    """Paginated list of historical unified monitoring sessions."""
    total: int
    items: List[MonitoringSessionSummary]

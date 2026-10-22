"""Communication monitoring and telemetry schemas (Phase 5)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommunicationStatus(str, Enum):
    """Assessment state for communication and network link quality."""
    STARTING = "STARTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    INTERRUPTED = "INTERRUPTED"
    RECOVERING = "RECOVERING"
    STOPPED = "STOPPED"


class CommunicationState(str, Enum):
    """Assessment state for communication and signal quality (Phase 1 legacy)."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    INTERRUPTED = "INTERRUPTED"
    REVIEW = "REVIEW"



class CommunicationEventType(str, Enum):
    """Discrete events logged during a communication session."""
    PACKET_LOSS = "PACKET_LOSS"
    INTERRUPTION = "INTERRUPTION"
    RECOVERY = "RECOVERY"
    STATUS_CHANGE = "STATUS_CHANGE"


class PacketIn(BaseModel):
    """Application-level controlled monitoring packet received from test client."""
    session_id: str = Field(..., description="Unique monitoring session identifier")
    sequence_number: int = Field(..., ge=1, description="Monotonically increasing sequence number")
    sender_timestamp: float = Field(..., description="POSIX timestamp (seconds) when packet was sent")
    payload_size: int = Field(default=1024, ge=0, description="Size of payload in bytes")
    payload: Optional[str] = Field(default=None, description="Optional payload string content")
    protocol_version: str = Field(default="1.0", description="SpectrumSentry packet protocol version")
    client_rtt_ms: Optional[float] = Field(default=None, ge=0.0, description="Client-measured RTT latency in ms from previous response")


class PacketAck(BaseModel):
    """Server acknowledgement returned for each accepted packet."""
    session_id: str
    sequence_number: int
    server_timestamp: float
    status: CommunicationStatus
    health_score: float
    received_packets: int


class SessionStartRequest(BaseModel):
    """Request payload to initiate a new communication monitoring session."""
    session_id: Optional[str] = Field(default=None, description="Custom session ID (auto-generated if omitted)")
    expected_packets: Optional[int] = Field(default=None, ge=1, description="Expected total packets to receive")
    interval_seconds: Optional[float] = Field(default=0.25, gt=0.0, description="Transmission interval in seconds")
    timeout_seconds: Optional[float] = Field(default=2.0, gt=0.0, description="Interruption timeout in seconds")
    extra_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary session metadata")


class SessionStartResponse(BaseModel):
    """Response returned upon successful session creation."""
    session_id: str
    status: CommunicationStatus
    started_at: datetime
    message: str


class SessionStopRequest(BaseModel):
    """Request payload to cleanly stop an ongoing communication session."""
    session_id: str = Field(..., description="Session identifier to stop")
    reason: Optional[str] = Field(default="completed", description="Reason for stopping")


class CommunicationMetricsResponse(BaseModel):
    """Comprehensive real-time metrics response for active or latest session."""
    session_id: str
    status: CommunicationStatus
    health_score: float
    packets_sent: int
    packets_received: int
    packets_lost: int
    packet_loss_percent: float
    latency_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    jitter_ms: float
    bytes_sent: int
    bytes_received: int
    throughput_bps: float
    throughput_kbps: float
    throughput_mbps: float
    interruption_count: int
    total_interruption_duration_ms: float
    recovery_count: int
    is_interrupted: bool
    started_at: Optional[datetime] = None
    last_packet_time: Optional[datetime] = None


class CommunicationEventSchema(BaseModel):
    """Discrete communication event representation."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    session_id: str
    event_type: str
    timestamp: datetime
    duration_ms: Optional[float] = None
    sequence_number: Optional[int] = None
    details: Optional[Dict[str, Any]] = None


class SessionSummaryResponse(BaseModel):
    """Aggregated session summary response for historical persistence and display."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    session_id: str
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    packets_sent: int
    packets_received: int
    packets_lost: int
    packet_loss_percent: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    jitter_ms: float
    bytes_sent: int
    bytes_received: int
    throughput_bps: float
    interruption_count: int
    total_interruption_duration_ms: float
    recovery_count: int
    health_score: float
    final_status: str
    extra_metadata: Optional[Dict[str, Any]] = None
    events: Optional[List[CommunicationEventSchema]] = None


class SessionHistoryResponse(BaseModel):
    """Paginated list of historical communication sessions."""
    total: int
    items: List[SessionSummaryResponse]


# Backwards compatibility schema
class CommunicationMetricSchema(BaseModel):
    """Legacy schema for individual communication telemetry records."""
    model_config = ConfigDict(from_attributes=True)

    sequence_number: int
    packets_transmitted: int
    packets_received: int
    packet_loss_rate: float = Field(..., ge=0.0, le=1.0)
    latency_ms: float = Field(..., ge=0.0)
    jitter_ms: Optional[float] = 0.0
    state: CommunicationState = CommunicationState.NORMAL
    timestamp: Optional[datetime] = None

"""Decision engine schemas for evidence correlation and assessment (Phase 6)."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class OverallStatus(str, Enum):
    """Overall communication and link health status assessment."""
    NORMAL = "NORMAL"
    DEGRADED = "DEGRADED"
    INTERRUPTED = "INTERRUPTED"
    RECOVERING = "RECOVERING"
    REVIEW = "REVIEW"


class ConsistencyStatus(str, Enum):
    """Cross-domain evidence correlation agreement assessment."""
    CONSISTENT = "CONSISTENT"
    CONFLICTING = "CONFLICTING"
    UNCORRELATED = "UNCORRELATED"


class SignalEvidence(BaseModel):
    """Physical-layer signal processing and AI classification evidence."""
    model_config = ConfigDict(from_attributes=True)

    predicted_modulation: Optional[str] = Field(default=None, description="Classified modulation scheme (BPSK, QPSK, 16-QAM)")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="AI classification confidence score")
    probabilities: Optional[Dict[str, float]] = Field(default=None, description="Modulation posterior probability distribution")
    measured_snr_db: Optional[float] = Field(default=None, description="Estimated or measured SNR in decibels")
    signal_power: Optional[float] = Field(default=None, description="Estimated baseband signal power")
    noise_power: Optional[float] = Field(default=None, description="Estimated channel noise power")
    signal_quality: Optional[str] = Field(default=None, description="Qualitative signal tier: EXCELLENT, GOOD, FAIR, POOR")
    is_outlier: Optional[bool] = Field(default=None, description="Novelty-detector flag: signal signature does not match any supported modulation")


class CommunicationEvidence(BaseModel):
    """Network application-layer packet telemetry evidence."""
    model_config = ConfigDict(from_attributes=True)

    status: Optional[str] = Field(default=None, description="Phase 5 communication status (CONNECTED, DEGRADED, INTERRUPTED, etc.)")
    health_score: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Communication health score (0-100)")
    packet_loss_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Packet loss percentage")
    avg_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="Average RTT latency in milliseconds")
    jitter_ms: Optional[float] = Field(default=None, ge=0.0, description="Application latency variation in milliseconds")
    throughput_mbps: Optional[float] = Field(default=None, ge=0.0, description="Measured application throughput in Mbps")
    interruption_count: Optional[int] = Field(default=0, ge=0, description="Number of interruptions observed")
    is_interrupted: Optional[bool] = Field(default=False, description="Flag indicating active silence timeout")
    recovery_count: Optional[int] = Field(default=0, ge=0, description="Number of recovery events observed")
    packets_received: Optional[int] = Field(default=None, ge=0, description="Packets received so far in the session; None when unknown")


class DecisionInput(BaseModel):
    """Input payload containing evidence from signal and communication domains."""
    signal_evidence: Optional[SignalEvidence] = Field(default=None, description="Signal/DSP/AI evidence")
    communication_evidence: Optional[CommunicationEvidence] = Field(default=None, description="Communication monitoring evidence")
    context_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context or experimental metadata")


class DecisionResult(BaseModel):
    """Final unified communication assessment and explanation produced by the Decision Engine."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="Database record ID if persisted")
    timestamp: datetime = Field(..., description="Timestamp of evaluation")
    overall_status: OverallStatus = Field(..., description="Unified communication status")
    decision_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the overall decision")
    consistency: ConsistencyStatus = Field(..., description="Evidence correlation consistency")
    primary_reason: str = Field(..., description="Primary explanatory statement for the decision")
    contributing_factors: List[str] = Field(default_factory=list, description="List of specific metric factors driving the decision")
    rules_triggered: List[str] = Field(default_factory=list, description="IDs of deterministic rules triggered")
    signal_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of signal evidence considered")
    communication_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of communication evidence considered")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations for operators")


class DecisionRuleInfo(BaseModel):
    """Description of an active decision engine rule for transparent inspection."""
    rule_id: str
    name: str
    category: str
    priority: int
    description: str

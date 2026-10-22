"""Experiment schemas for API validation and serialization."""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExperimentBase(BaseModel):
    """Base experiment attributes."""
    modulation: str = Field(..., description="Modulation type, e.g., BPSK, QPSK, 16-QAM")
    snr_db: float = Field(..., description="Signal to Noise Ratio in decibels")
    sample_count: int = Field(default=2048, ge=256, le=131072, description="Sample points count")
    sample_rate: float = Field(default=1e6, gt=0, description="Sampling rate in Hz")
    noise_type: str = Field(default="AWGN", description="Channel noise model")


class ExperimentCreate(ExperimentBase):
    """Payload to record or launch an experiment."""
    id: Optional[str] = Field(None, description="Optional custom experiment ID like EXP-001")
    extra_metadata: Optional[Dict[str, Any]] = None


class ExperimentResponse(ExperimentBase):
    """Detailed response for an experiment."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    signal_power: Optional[float] = None
    noise_power: Optional[float] = None
    predicted_modulation: Optional[str] = None
    confidence: Optional[float] = None
    inference_time_ms: Optional[float] = None
    status: str
    model_version: Optional[str] = None
    iq_file_path: Optional[str] = None
    spectrum_file_path: Optional[str] = None
    feature_file_path: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None


class ExperimentSummary(BaseModel):
    """Brief summary of an experiment for history listing."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    modulation: str
    snr_db: float
    predicted_modulation: Optional[str] = None
    confidence: Optional[float] = None
    status: str

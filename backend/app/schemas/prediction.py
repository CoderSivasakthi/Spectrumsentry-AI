"""AI and Modulation Prediction Schemas."""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class PredictionCreate(BaseModel):
    """Payload to record an inference prediction."""
    experiment_id: Optional[str] = None
    true_modulation: Optional[str] = None
    predicted_modulation: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    probabilities: Optional[Dict[str, float]] = None
    inference_time_ms: float = Field(..., ge=0.0)
    model_name: str = "MLPClassifier"
    model_version: str = "v1.0.0"


class PredictionResponse(PredictionCreate):
    """Prediction output response."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime

"""Application settings configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SpectrumSentry AI central application settings."""

    # Project Paths
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = PROJECT_ROOT / "storage"
    EXPERIMENTS_DIR: Path = STORAGE_DIR / "experiments"
    LOGS_DIR: Path = STORAGE_DIR / "logs"
    MODELS_DIR: Path = PROJECT_ROOT / "backend" / "models"

    # Application Info
    APP_NAME: str = "SpectrumSentry AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Server Configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./storage/spectrumsentry.db",
        description="SQLAlchemy database connection string",
    )

    # Phase 4: AI Inference Configuration
    # Preferred model is the phase-robust cumulant (v2) contract trained by
    # scripts/train_cumulant_model.py; when its artifact has not been trained yet the
    # unified monitor falls back to the legacy v1 moment/spectral model.
    AI_MODEL_PATH: Path = PROJECT_ROOT / "backend" / "models" / "modulation_mlp_v2.joblib"
    AI_MODEL_FALLBACK_PATH: Path = PROJECT_ROOT / "backend" / "models" / "modulation_mlp_v1.joblib"
    # Novelty detectors per feature contract; the monitor resolves the right one from
    # the active model's feature count (fix #8).
    AI_NOVELTY_DETECTOR_PATH: Path = PROJECT_ROOT / "backend" / "models" / "novelty_detector.joblib"
    AI_NOVELTY_DETECTOR_CUMULANT_PATH: Path = PROJECT_ROOT / "backend" / "models" / "novelty_detector_cumulant.joblib"

    # Phase 5: Communication Monitoring Configuration
    COMMUNICATION_PACKET_INTERVAL: float = 0.25
    COMMUNICATION_TIMEOUT: float = 2.0
    COMMUNICATION_PAYLOAD_SIZE: int = 1024
    COMMUNICATION_DEFAULT_DURATION: float = 60.0
    COMMUNICATION_LATENCY_WARNING_MS: float = 100.0
    COMMUNICATION_PACKET_LOSS_WARNING_PERCENT: float = 5.0
    COMMUNICATION_JITTER_WARNING_MS: float = 30.0
    # Corrected report fix #10: recovery requires N consecutive packets
    COMMUNICATION_RECOVERY_CONFIRMATION_PACKETS: int = 3
    # Corrected report issue #9: one-way fallback latency is only trusted when the
    # sender timestamp is plausibly from the same clock epoch, i.e. the one-way
    # delta cannot exceed this many seconds (guards cross-clock garbage values).
    COMMUNICATION_LATENCY_FALLBACK_MAX_SECONDS: float = 30.0

    # Phase 6: Decision Engine Configuration
    DECISION_CONFIDENCE_THRESHOLD: float = 0.70
    DECISION_SNR_WARNING_DB: float = 0.0
    DECISION_CONFLICT_LOSS_THRESHOLD: float = 15.0
    DECISION_CONFLICT_SNR_THRESHOLD: float = 10.0
    DECISION_HEALTH_WARNING_THRESHOLD: float = 75.0

    # Phase 7: Real-time Integration Configuration
    MAX_SIGNAL_EVIDENCE_AGE_SECONDS: float = 30.0

    # Continuous signal pipeline: while a monitoring session is active the backend
    # refreshes synthetic-channel evidence and re-runs the AI classifier on this
    # cadence so the live monitor's physical-layer card stays fresh (30 s expiry
    # would otherwise blank it between manual ingests).
    SIGNAL_EVIDENCE_AUTO_SIMULATE: bool = True
    SIGNAL_EVIDENCE_INTERVAL_SECONDS: float = 5.0


    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # LAN IPs for cross-device testing (e.g. phone on same WiFi)
        "http://192.168.1.36:5173",
        "http://100.97.104.2:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def init_directories(self) -> None:
        """Ensure required application directories exist."""
        self.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    settings = Settings()
    settings.init_directories()
    return settings

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

    # Phase 5: Communication Monitoring Configuration
    COMMUNICATION_PACKET_INTERVAL: float = 0.25
    COMMUNICATION_TIMEOUT: float = 2.0
    COMMUNICATION_PAYLOAD_SIZE: int = 1024
    COMMUNICATION_DEFAULT_DURATION: float = 60.0
    COMMUNICATION_LATENCY_WARNING_MS: float = 100.0
    COMMUNICATION_PACKET_LOSS_WARNING_PERCENT: float = 5.0
    COMMUNICATION_JITTER_WARNING_MS: float = 30.0

    # Phase 6: Decision Engine Configuration
    DECISION_CONFIDENCE_THRESHOLD: float = 0.70
    DECISION_SNR_WARNING_DB: float = 0.0
    DECISION_CONFLICT_LOSS_THRESHOLD: float = 15.0
    DECISION_CONFLICT_SNR_THRESHOLD: float = 10.0
    DECISION_HEALTH_WARNING_THRESHOLD: float = 75.0

    # Phase 7: Real-time Integration Configuration
    MAX_SIGNAL_EVIDENCE_AGE_SECONDS: float = 30.0


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

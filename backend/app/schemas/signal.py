"""Signal processing schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SignalGenerateRequest(BaseModel):
    """Parameters for synthetic I/Q signal generation."""
    modulation: str = Field("QPSK", description="Modulation type: BPSK, QPSK, 16-QAM")
    snr_db: float = Field(10.0, description="Signal-to-Noise Ratio (dB)")
    num_samples: int = Field(2048, ge=256, le=65536, description="Number of samples")
    sample_rate: float = Field(1e6, gt=0, description="Sampling rate in Hz")
    carrier_frequency: float = Field(0.0, ge=0.0, description="Carrier frequency offset")


class SignalProcessingResult(BaseModel):
    """Result of DSP operations including I/Q samples and spectrum."""
    modulation: str
    snr_db: float
    num_samples: int
    sample_rate: float
    signal_power: float
    noise_power: float
    i_samples: List[float] = Field(default_factory=list, description="Downsampled/preview real part")
    q_samples: List[float] = Field(default_factory=list, description="Downsampled/preview imag part")
    fft_magnitude_db: List[float] = Field(default_factory=list, description="FFT magnitude (dB)")
    fft_frequencies: List[float] = Field(default_factory=list, description="Frequency bins (Hz)")

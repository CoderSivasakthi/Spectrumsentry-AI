"""Fast Fourier Transform (FFT) and Power Spectral Density (PSD) analysis.

Distinguishes between:
1. FFT Magnitude & Power Spectrum (deterministic discrete Fourier transform)
2. Power Spectral Density (statistical estimation via Welch's averaged periodogram)
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
from scipy import signal as sp_signal

from .preprocessing import validate_complex_signal


@dataclass(frozen=True)
class FFTResult:
    """Structured result of Fast Fourier Transform."""
    frequencies: np.ndarray      # Centered frequency bins (Hz)
    complex_spectrum: np.ndarray # Centered complex FFT array
    magnitude: np.ndarray        # Normalized magnitude spectrum (|X| / N)
    magnitude_db: np.ndarray     # Magnitude spectrum in dB (20 * log10(|X| / N))
    power: np.ndarray            # Normalized power spectrum (|X|^2 / N^2)
    power_db: np.ndarray         # Power spectrum in dB (10 * log10(power))
    peak_frequency: float        # Frequency bin with maximum magnitude (Hz)
    sample_rate: float           # Sampling rate in Hz


@dataclass(frozen=True)
class PSDResult:
    """Structured result of Power Spectral Density calculation via Welch's method."""
    frequencies: np.ndarray  # Frequency bins (Hz)
    psd: np.ndarray          # Power spectral density (V^2/Hz or linear units)
    psd_db: np.ndarray       # PSD in dB/Hz (10 * log10(psd))
    sample_rate: float       # Sampling rate in Hz


def compute_fft(
    signal: np.ndarray,
    sample_rate: float = 1e6,
    normalize: bool = True,
) -> FFTResult:
    """Compute centered complex FFT, magnitude, and power spectra.
    
    Args:
        signal: 1D complex baseband signal.
        sample_rate: Sampling frequency in Hz (must be > 0).
        normalize: If True, normalizes spectrum by 1/N.

    Returns:
        FFTResult dataclass with frequencies, complex_spectrum, magnitude, and power.

    Raises:
        ValueError: If sample_rate is non-positive or signal is invalid.
    """
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError(f"Sample rate must be a positive finite number, got {sample_rate}")

    valid_sig = validate_complex_signal(signal)
    n = len(valid_sig)

    # Compute FFT and shift zero-frequency component to center
    raw_fft = np.fft.fft(valid_sig)
    shifted_fft = np.fft.fftshift(raw_fft)
    freqs = np.fft.fftshift(np.fft.fftfreq(n, d=1.0 / sample_rate))

    # Normalization factor
    norm_factor = 1.0 / n if normalize else 1.0
    complex_spectrum = shifted_fft * norm_factor

    # Magnitude and Power spectra
    magnitude = np.abs(complex_spectrum)
    power = magnitude ** 2

    # Avoid log of zero using small floor
    eps = 1e-12
    magnitude_db = 20.0 * np.log10(np.maximum(magnitude, eps))
    power_db = 10.0 * np.log10(np.maximum(power, eps))

    # Peak frequency bin
    peak_idx = int(np.argmax(magnitude))
    peak_freq = float(freqs[peak_idx])

    return FFTResult(
        frequencies=freqs,
        complex_spectrum=complex_spectrum,
        magnitude=magnitude,
        magnitude_db=magnitude_db,
        power=power,
        power_db=power_db,
        peak_frequency=peak_freq,
        sample_rate=float(sample_rate),
    )


def compute_psd(
    signal: np.ndarray,
    sample_rate: float = 1e6,
    nperseg: Optional[int] = None,
) -> PSDResult:
    """Estimate Power Spectral Density (PSD) using Welch's averaged periodogram method.
    
    Args:
        signal: 1D complex baseband signal.
        sample_rate: Sampling frequency in Hz.
        nperseg: Length of each segment for Welch's method (default: min(len(signal), 1024)).

    Returns:
        PSDResult containing frequency axis, linear PSD, and log PSD in dB/Hz.

    Raises:
        ValueError: If sample_rate is non-positive or signal is invalid.
    """
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError(f"Sample rate must be a positive finite number, got {sample_rate}")

    valid_sig = validate_complex_signal(signal)
    n = len(valid_sig)

    if nperseg is None:
        nperseg = min(n, 1024)
    else:
        nperseg = min(n, max(16, nperseg))

    # Compute Welch PSD for complex signal (return_onesided=False keeps two-sided spectrum)
    freqs, psd = sp_signal.welch(
        valid_sig,
        fs=sample_rate,
        window="hann",
        nperseg=nperseg,
        return_onesided=False,
        scaling="density",
    )

    # Shift zero-frequency to center
    freqs_shifted = np.fft.fftshift(freqs)
    psd_shifted = np.fft.fftshift(psd)

    eps = 1e-15
    psd_db = 10.0 * np.log10(np.maximum(psd_shifted, eps))

    return PSDResult(
        frequencies=freqs_shifted,
        psd=psd_shifted,
        psd_db=psd_db,
        sample_rate=float(sample_rate),
    )

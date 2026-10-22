"""Feature extraction pipeline for modulation classification and signal quality analysis.

Extracts a strictly ordered numeric feature vector comprising:
1. Time-Domain Statistics (mean, std, RMS, peak, power)
2. Higher-Order Statistical Moments (skewness, kurtosis, 4th-order central moments)
3. Spectral Metrics (centroid, spread/bandwidth, peak frequency, energy, flatness)

The feature vector order defined in FEATURE_NAMES is deterministic and immutable,
providing the exact feature schema required by the downstream AI classifier.
"""

from typing import Dict, List, Tuple
import numpy as np
from scipy import stats

from .fft import compute_fft
from .preprocessing import (
    calculate_magnitude,
    calculate_signal_power,
    extract_iq,
    validate_complex_signal,
)

FEATURE_NAMES: Tuple[str, ...] = (
    # Time-Domain Features (9)
    "mean_i",
    "mean_q",
    "std_i",
    "std_q",
    "rms_magnitude",
    "mean_magnitude",
    "std_magnitude",
    "peak_magnitude",
    "signal_power",
    # Higher-Order Moments & Cumulants (9)
    "moment4_i",
    "moment4_q",
    "moment4_magnitude",
    "skew_i",
    "skew_q",
    "skew_magnitude",
    "kurtosis_i",
    "kurtosis_q",
    "kurtosis_magnitude",
    # Spectral Domain Features (5)
    "spectral_centroid",
    "spectral_spread",
    "peak_frequency",
    "spectral_energy",
    "spectral_flatness",
)

FEATURE_COUNT: int = len(FEATURE_NAMES)  # 23 features


def _safe_skew(arr: np.ndarray) -> float:
    """Calculate skewness safely avoiding NaN/Inf for constant signals."""
    if arr.size == 0 or np.isclose(float(np.std(arr)), 0.0):
        return 0.0
    val = float(stats.skew(arr, bias=True))
    return val if np.isfinite(val) else 0.0


def _safe_kurtosis(arr: np.ndarray) -> float:
    """Calculate excess kurtosis safely avoiding NaN/Inf for constant signals."""
    if arr.size == 0 or np.isclose(float(np.std(arr)), 0.0):
        return 0.0
    val = float(stats.kurtosis(arr, fisher=True, bias=True))
    return val if np.isfinite(val) else 0.0


def _safe_moment4(arr: np.ndarray) -> float:
    """Calculate 4th central moment E[(X - mu)^4] safely."""
    if arr.size == 0 or np.isclose(float(np.std(arr)), 0.0):
        return 0.0
    val = float(stats.moment(arr, order=4))
    return val if np.isfinite(val) else 0.0


def extract_features(
    signal: np.ndarray,
    sample_rate: float = 1e6,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Extract full statistical and spectral feature set from a complex signal.
    
    Args:
        signal: 1D complex baseband signal.
        sample_rate: Sampling frequency in Hz (default: 1 MHz).

    Returns:
        Tuple of:
            1. features_vector: 1D np.ndarray of shape (23,) and dtype np.float32
            2. features_dict: Dict mapping feature name string to float value

    Raises:
        ValueError: If signal is invalid or sample_rate <= 0.
    """
    valid_sig = validate_complex_signal(signal)
    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError(f"Sample rate must be positive and finite, got {sample_rate}")

    # 1. Time-Domain components
    i_arr, q_arr = extract_iq(valid_sig)
    magnitude = calculate_magnitude(valid_sig)
    power = calculate_signal_power(valid_sig)

    mean_i = float(np.mean(i_arr))
    mean_q = float(np.mean(q_arr))
    std_i = float(np.std(i_arr))
    std_q = float(np.std(q_arr))
    rms_magnitude = float(np.sqrt(np.mean(magnitude ** 2)))
    mean_mag = float(np.mean(magnitude))
    std_mag = float(np.std(magnitude))
    peak_mag = float(np.max(magnitude))

    # 2. Higher-Order Moments & Cumulants
    moment4_i = _safe_moment4(i_arr)
    moment4_q = _safe_moment4(q_arr)
    moment4_mag = _safe_moment4(magnitude)

    skew_i = _safe_skew(i_arr)
    skew_q = _safe_skew(q_arr)
    skew_mag = _safe_skew(magnitude)

    kurt_i = _safe_kurtosis(i_arr)
    kurt_q = _safe_kurtosis(q_arr)
    kurt_mag = _safe_kurtosis(magnitude)

    # 3. Spectral Features via FFT
    fft_res = compute_fft(valid_sig, sample_rate=sample_rate, normalize=True)
    freqs = fft_res.frequencies
    power_spectrum = fft_res.power  # P[k]

    total_spectral_power = float(np.sum(power_spectrum))
    if total_spectral_power > 1e-15:
        # Spectral centroid: sum(f * P) / sum(P)
        spectral_centroid = float(np.sum(freqs * power_spectrum) / total_spectral_power)
        # Spectral spread / bandwidth: sqrt(sum((f - centroid)^2 * P) / sum(P))
        spectral_spread = float(
            np.sqrt(np.maximum(0.0, np.sum(((freqs - spectral_centroid) ** 2) * power_spectrum) / total_spectral_power))
        )
    else:
        spectral_centroid = 0.0
        spectral_spread = 0.0

    peak_freq = fft_res.peak_frequency
    spectral_energy = total_spectral_power

    # Spectral flatness: geometric mean / arithmetic mean of power spectrum
    eps = 1e-12
    log_power = np.log(np.maximum(power_spectrum, eps))
    geometric_mean = float(np.exp(np.mean(log_power)))
    arithmetic_mean = float(np.mean(power_spectrum)) + eps
    spectral_flatness = float(np.clip(geometric_mean / arithmetic_mean, 0.0, 1.0))

    # Construct strictly ordered dictionary
    feat_dict: Dict[str, float] = {
        "mean_i": mean_i,
        "mean_q": mean_q,
        "std_i": std_i,
        "std_q": std_q,
        "rms_magnitude": rms_magnitude,
        "mean_magnitude": mean_mag,
        "std_magnitude": std_mag,
        "peak_magnitude": peak_mag,
        "signal_power": power,
        "moment4_i": moment4_i,
        "moment4_q": moment4_q,
        "moment4_magnitude": moment4_mag,
        "skew_i": skew_i,
        "skew_q": skew_q,
        "skew_magnitude": skew_mag,
        "kurtosis_i": kurt_i,
        "kurtosis_q": kurt_q,
        "kurtosis_magnitude": kurt_mag,
        "spectral_centroid": spectral_centroid,
        "spectral_spread": spectral_spread,
        "peak_frequency": peak_freq,
        "spectral_energy": spectral_energy,
        "spectral_flatness": spectral_flatness,
    }

    # Construct strictly ordered NumPy array
    feat_vector = np.array([feat_dict[k] for k in FEATURE_NAMES], dtype=np.float32)

    return feat_vector, feat_dict

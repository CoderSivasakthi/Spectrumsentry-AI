"""Additive White Gaussian Noise (AWGN) channel model and SNR calculation.

Formulas:
    r[n] = s[n] + w[n]
    SNR_linear = P_signal / P_noise
    SNR_dB = 10 * log10(P_signal / P_noise)
    P_noise = P_signal / (10^(SNR_dB / 10))

For complex AWGN:
    w[n] = n_I[n] + j * n_Q[n]
    where n_I, n_Q ~ N(0, sigma^2) with sigma = sqrt(P_noise / 2)
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .preprocessing import calculate_signal_power, validate_complex_signal


@dataclass(frozen=True)
class AWGNResult:
    """Structured result of the AWGN channel operation."""
    noisy_signal: np.ndarray
    noise: np.ndarray
    signal_power: float
    noise_power: float
    target_snr_db: float
    measured_snr_db: float


def calculate_snr_db(signal_power: float, noise_power: float) -> float:
    """Calculate measured Signal-to-Noise Ratio (SNR) in decibels.
    
        SNR_dB = 10 * log10(P_signal / P_noise)
    
    Args:
        signal_power: Signal power (P_signal > 0).
        noise_power: Noise power (P_noise > 0).

    Returns:
        SNR in decibels (dB).

    Raises:
        ValueError: If signal_power or noise_power is non-positive or not finite.
    """
    if not np.isfinite(signal_power) or signal_power <= 0:
        raise ValueError(f"Signal power must be a positive finite number, got {signal_power}")
    if not np.isfinite(noise_power) or noise_power <= 0:
        raise ValueError(f"Noise power must be a positive finite number, got {noise_power}")

    snr_linear = signal_power / noise_power
    return float(10.0 * np.log10(snr_linear))


def add_awgn(
    signal: np.ndarray,
    snr_db: float,
    seed: Optional[int] = None,
) -> AWGNResult:
    """Add complex Additive White Gaussian Noise (AWGN) to a signal for a target SNR.
    
    Args:
        signal: Clean complex baseband signal.
        snr_db: Target Signal-to-Noise Ratio in dB.
        seed: Optional integer seed for reproducibility using np.random.default_rng.

    Returns:
        AWGNResult containing noisy signal, noise array, powers, and measured SNR.

    Raises:
        ValueError: If snr_db is NaN/Inf or signal has zero/invalid power.
    """
    if not np.isfinite(snr_db):
        raise ValueError(f"SNR must be a finite number, got {snr_db}")

    valid_sig = validate_complex_signal(signal)
    signal_power = calculate_signal_power(valid_sig)

    if signal_power <= 0.0 or np.isclose(signal_power, 0.0):
        raise ValueError("Cannot add AWGN to a zero-power signal")

    # Compute target noise power from SNR_dB = 10 * log10(P_signal / P_noise)
    snr_linear = 10.0 ** (snr_db / 10.0)
    target_noise_power = signal_power / snr_linear

    # Complex noise variance per dimension (I and Q)
    sigma = np.sqrt(target_noise_power / 2.0)

    # Use modern NumPy random generator with seed
    rng = np.random.default_rng(seed)
    noise_i = rng.normal(0.0, sigma, size=valid_sig.shape)
    noise_q = rng.normal(0.0, sigma, size=valid_sig.shape)
    noise = (noise_i + 1j * noise_q).astype(np.complex128)

    noisy_signal = valid_sig + noise

    # Measure actual noise power and measured SNR from the generated sample array
    actual_noise_power = calculate_signal_power(noise)
    measured_snr_db = calculate_snr_db(signal_power, actual_noise_power)

    return AWGNResult(
        noisy_signal=noisy_signal,
        noise=noise,
        signal_power=signal_power,
        noise_power=actual_noise_power,
        target_snr_db=float(snr_db),
        measured_snr_db=measured_snr_db,
    )

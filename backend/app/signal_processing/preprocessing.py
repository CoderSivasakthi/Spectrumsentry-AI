"""Signal preprocessing and I/Q manipulation utilities.

Provides functions for input validation, I/Q separation, magnitude/phase extraction,
signal power calculation, and power normalization.
"""

from typing import Tuple
import numpy as np


def validate_complex_signal(signal: np.ndarray) -> np.ndarray:
    """Validate that the input is a valid non-empty 1D complex NumPy array.
    
    Args:
        signal: Input complex signal array.

    Returns:
        Validated complex NumPy array (complex128).

    Raises:
        ValueError: If signal is empty, not 1-dimensional, contains NaN/Inf,
                    or cannot be represented as complex.
    """
    if signal is None:
        raise ValueError("Signal cannot be None")

    arr = np.asarray(signal)

    if arr.size == 0:
        raise ValueError("Signal array cannot be empty")

    if arr.ndim != 1:
        raise ValueError(f"Signal must be a 1D array, got dimension {arr.ndim}")

    if not np.iscomplexobj(arr):
        # Convert real array to complex with zero imaginary part
        arr = arr.astype(np.complex128)
    else:
        arr = arr.astype(np.complex128)

    if not np.all(np.isfinite(arr)):
        raise ValueError("Signal contains NaN or Infinite values")

    return arr


def extract_iq(signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Extract In-phase (I) and Quadrature (Q) components from a complex signal.
    
    Args:
        signal: Input complex signal.

    Returns:
        Tuple of (I, Q) arrays as float64.
    """
    valid_sig = validate_complex_signal(signal)
    return np.real(valid_sig), np.imag(valid_sig)


def calculate_signal_power(signal: np.ndarray) -> float:
    """Calculate the average power of a complex signal:
    
        P_signal = (1/N) * sum(|x[n]|^2)
    
    Args:
        signal: Input complex signal.

    Returns:
        Average signal power as a positive float.
    """
    valid_sig = validate_complex_signal(signal)
    power = float(np.mean(np.abs(valid_sig) ** 2))
    return power


def calculate_magnitude(signal: np.ndarray) -> np.ndarray:
    """Calculate the instantaneous magnitude (envelope) of the complex signal.
    
        |x[n]| = sqrt(I[n]^2 + Q[n]^2)
    
    Args:
        signal: Input complex signal.

    Returns:
        Array of instantaneous magnitudes.
    """
    valid_sig = validate_complex_signal(signal)
    return np.abs(valid_sig)


def calculate_phase(signal: np.ndarray, unwrap: bool = False) -> np.ndarray:
    """Calculate the instantaneous phase of the complex signal in radians (-pi to +pi).
    
    Args:
        signal: Input complex signal.
        unwrap: If True, unwraps phase discontinuities.

    Returns:
        Array of instantaneous phase values in radians.
    """
    valid_sig = validate_complex_signal(signal)
    phase = np.angle(valid_sig)
    if unwrap:
        phase = np.unwrap(phase)
    return phase


def normalize_iq(signal: np.ndarray, target_power: float = 1.0) -> np.ndarray:
    """Normalize the complex signal so that its average power equals target_power.
    
    Args:
        signal: Input complex signal.
        target_power: Desired average power (default: 1.0).

    Returns:
        Normalized complex signal array.

    Raises:
        ValueError: If target_power is non-positive or signal has zero power.
    """
    if target_power <= 0:
        raise ValueError(f"Target power must be positive, got {target_power}")

    valid_sig = validate_complex_signal(signal)
    current_power = calculate_signal_power(valid_sig)

    if current_power <= 0.0 or np.isclose(current_power, 0.0):
        raise ValueError("Cannot normalize a signal with zero power")

    scale_factor = np.sqrt(target_power / current_power)
    return valid_sig * scale_factor

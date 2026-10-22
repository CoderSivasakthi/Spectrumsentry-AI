"""Constellation data processing and point extraction for visualization and analysis.

Extracts I (In-phase, X-axis) and Q (Quadrature, Y-axis) coordinates, along with
magnitude and phase, with configurable point subsampling to prevent frontend lag.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np

from .preprocessing import (
    calculate_magnitude,
    calculate_phase,
    extract_iq,
    validate_complex_signal,
)


@dataclass(frozen=True)
class ConstellationData:
    """Constellation diagram coordinates and metadata."""
    i: np.ndarray          # In-phase (X axis)
    q: np.ndarray          # Quadrature (Y axis)
    magnitude: np.ndarray  # Vector magnitude sqrt(I^2 + Q^2)
    phase: np.ndarray      # Phase angle in radians [-pi, pi]
    total_points: int      # Original sample count
    sampled_points: int    # Number of points returned after subsampling


def extract_constellation(
    signal: np.ndarray,
    max_points: Optional[int] = 5000,
) -> ConstellationData:
    """Extract constellation points from a complex signal.
    
    Args:
        signal: 1D complex baseband signal.
        max_points: Maximum number of points to return. If signal length exceeds
                    max_points, points are uniformly subsampled without altering
                    the underlying distribution or modifying the original signal.

    Returns:
        ConstellationData dataclass containing i, q, magnitude, phase arrays.

    Raises:
        ValueError: If signal is invalid or max_points <= 0.
    """
    valid_sig = validate_complex_signal(signal)
    total_points = len(valid_sig)

    if max_points is not None:
        if max_points <= 0:
            raise ValueError(f"max_points must be a positive integer, got {max_points}")
        if total_points > max_points:
            # Deterministic uniform downsampling
            step = int(np.ceil(total_points / max_points))
            sampled_sig = valid_sig[::step][:max_points]
        else:
            sampled_sig = valid_sig
    else:
        sampled_sig = valid_sig

    i, q = extract_iq(sampled_sig)
    magnitude = calculate_magnitude(sampled_sig)
    phase = calculate_phase(sampled_sig)

    return ConstellationData(
        i=i,
        q=q,
        magnitude=magnitude,
        phase=phase,
        total_points=total_points,
        sampled_points=len(sampled_sig),
    )

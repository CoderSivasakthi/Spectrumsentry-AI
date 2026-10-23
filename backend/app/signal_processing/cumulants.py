"""Phase-robust higher-order cumulant feature extraction (corrected report fix #5).

Implements the v2 feature contract from *SpectrumSentry_AI_Corrected_Report (1).pdf*
(Appendix A fix #5, reference implementation B.1): six features derived from
second- and fourth-order moments/cumulants of the complex baseband signal that are
invariant to an unknown constant carrier phase rotation ``x -> x * exp(j*phi)``.

Motivation: the legacy v1 (23-feature) moment/spectral vector uses absolute phase
statistics (mean_i, mean_q, skew of I/Q) and FFT shapes that a random carrier phase
randomizes per frame. The corrected report measured accuracy collapse 98% -> 53.8%
under that condition for v1-style features, while this cumulant set stays valid.

Feature list (strictly ordered, immutable):

    1. m20_abs          |E[x^2]|                          (second-order moment modulus)
    2. c40_abs          |E[x^4] - 3*E[x^2]^2|             (4th-order cumulant, conjugate-free)
    3. c41_abs          |E[x^3*x*] - 3*E[x^2]*E[|x|^2]|   (4th-order cumulant, semi-conjugate)
    4. c42_real         E[|x|^4] - |E[x^2]|^2 - 2*E[|x|^2]^2  (rotation-invariant, real)
    5. amplitude_mean   E[|x|]
    6. amplitude_std    SD[|x|]

Properties: features 1-3 rotate as exp(j*k*phi) under carrier phase, so their
moduli are phase-invariant; feature 4 and the amplitude statistics are inherently
invariant. The signal is power-normalized first, so the vector carries no absolute
power (SNR) cue — unlike the v1 vector.
"""

from typing import Dict, Tuple
import numpy as np

from .preprocessing import validate_complex_signal

FEATURE_NAMES_CUMULANT: Tuple[str, ...] = (
    "m20_abs",
    "c40_abs",
    "c41_abs",
    "c42_real",
    "amplitude_mean",
    "amplitude_std",
)

FEATURE_COUNT_CUMULANT: int = len(FEATURE_NAMES_CUMULANT)  # 6 features


def extract_cumulant_features(
    signal: np.ndarray,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Extract the phase-robust cumulant (v2) feature vector from a complex signal.

    Args:
        signal: 1D complex baseband I/Q signal.

    Returns:
        Tuple of:
            1. features_vector: 1D np.ndarray of shape (6,) and dtype np.float32
            2. features_dict: Dict mapping feature name string to float value

    Raises:
        ValueError: If signal is empty, non-complex, or degenerate (zero power).

    Notes:
        Non-finite moments are mapped to 0.0 so downstream validation can flag them.
    """
    valid_sig = validate_complex_signal(signal)

    # Power normalization (phase untouched): unit received power removes calibration gain
    power = float(np.mean(np.abs(valid_sig) ** 2))
    if not np.isfinite(power) or power <= 1e-15:
        raise ValueError(
            f"Signal power must be positive and finite for cumulant extraction, got {power}"
        )
    x = valid_sig / np.sqrt(power)

    # Second-order (conjugate-free) moment: rotates by exp(j*2*phi) under carrier phase
    m20 = np.mean(x * x)

    # Average power of the normalized signal (~1.0)
    m21 = np.mean(np.abs(x) ** 2)

    # Fourth-order moments
    m40 = np.mean(x ** 4)                    # rotates by exp(j*4*phi)
    m41 = np.mean(x ** 3 * np.conj(x))       # rotates by exp(j*2*phi)

    # Fourth-order cumulants (zero for circular Gaussian noise at high SNR limits)
    c40 = m40 - 3.0 * m20 ** 2
    c41 = m41 - 3.0 * m20 * m21
    m42 = np.mean(np.abs(x) ** 4)
    c42 = m42 - np.abs(m20) ** 2 - 2.0 * m21 ** 2  # real, rotation-invariant

    amplitude = np.abs(x)

    feat_dict: Dict[str, float] = {
        "m20_abs": float(np.abs(m20)),
        "c40_abs": float(np.abs(c40)),
        "c41_abs": float(np.abs(c41)),
        "c42_real": float(np.real(c42)),
        "amplitude_mean": float(np.mean(amplitude)),
        "amplitude_std": float(np.std(amplitude)),
    }

    # Guard non-finite values produced by pathological inputs
    for key, value in feat_dict.items():
        if not np.isfinite(value):
            feat_dict[key] = 0.0

    feat_vector = np.array([feat_dict[k] for k in FEATURE_NAMES_CUMULANT], dtype=np.float32)
    return feat_vector, feat_dict


def apply_carrier_phase(signal: np.ndarray, phase_rad: float) -> np.ndarray:
    """Apply a constant carrier phase rotation to a complex baseband signal.

    Args:
        signal: 1D complex baseband I/Q signal.
        phase_rad: Rotation angle in radians.

    Returns:
        Phase-rotated complex signal of the same dtype family.
    """
    return np.asarray(signal, dtype=np.complex128) * np.exp(1j * float(phase_rad))

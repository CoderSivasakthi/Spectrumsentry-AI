"""Digital modulation schemes and constellation mapping for BPSK, QPSK, and 16-QAM.

All modulations use complex baseband representation:
    x[n] = I[n] + j * Q[n]
with average symbol power normalized to approximately 1.0.
"""

from typing import Dict, Tuple
import numpy as np

SUPPORTED_MODULATIONS: Tuple[str, ...] = ("BPSK", "QPSK", "16-QAM")

# BPSK Constellation: { -1 + 0j, +1 + 0j }, normalized power = 1.0
BPSK_CONSTELLATION: np.ndarray = np.array([-1.0 + 0.0j, 1.0 + 0.0j], dtype=np.complex128)

# QPSK Constellation: 4 points distributed symmetrically around origin, normalized power = 1.0
# (±1 ± 1j) / sqrt(2)
QPSK_CONSTELLATION: np.ndarray = (
    np.array([-1.0 - 1.0j, -1.0 + 1.0j, 1.0 - 1.0j, 1.0 + 1.0j], dtype=np.complex128)
    / np.sqrt(2.0)
)

# 16-QAM Constellation: 4 I levels {-3, -1, +1, +3} x 4 Q levels {-3, -1, +1, +3}
# Average unnormalized power: E[I^2 + Q^2] = 2 * ((-3)^2 + (-1)^2 + 1^2 + 3^2) / 4 = 10.0
# Normalization factor: 1 / sqrt(10)
_qam16_levels = np.array([-3.0, -1.0, 1.0, 3.0], dtype=np.float64)
_qam16_grid_i, _qam16_grid_q = np.meshgrid(_qam16_levels, _qam16_levels)
QAM16_CONSTELLATION: np.ndarray = (
    (_qam16_grid_i.ravel() + 1j * _qam16_grid_q.ravel()) / np.sqrt(10.0)
).astype(np.complex128)


CONSTELLATION_MAP: Dict[str, np.ndarray] = {
    "BPSK": BPSK_CONSTELLATION,
    "QPSK": QPSK_CONSTELLATION,
    "16-QAM": QAM16_CONSTELLATION,
    "16QAM": QAM16_CONSTELLATION,
}


def normalize_modulation_name(modulation: str) -> str:
    """Normalize modulation string and validate against supported list.
    
    Args:
        modulation: Modulation name (e.g. 'BPSK', 'qpsk', '16-qam', '16QAM').

    Returns:
        Canonical modulation name ('BPSK', 'QPSK', or '16-QAM').

    Raises:
        ValueError: If modulation is unsupported or not recognized.
    """
    if not isinstance(modulation, str):
        raise ValueError(f"Modulation must be a string, got {type(modulation).__name__}")

    mod_upper = modulation.strip().upper()
    if mod_upper == "16QAM":
        mod_upper = "16-QAM"

    if mod_upper not in SUPPORTED_MODULATIONS:
        raise ValueError(
            f"Unsupported modulation '{modulation}'. Supported types: {', '.join(SUPPORTED_MODULATIONS)}"
        )
    return mod_upper


def get_constellation(modulation: str) -> np.ndarray:
    """Retrieve the normalized complex constellation array for a modulation type.
    
    Args:
        modulation: Modulation type ('BPSK', 'QPSK', '16-QAM').

    Returns:
        Complex NumPy array containing normalized constellation points.
    """
    canonical = normalize_modulation_name(modulation)
    return CONSTELLATION_MAP[canonical].copy()


def modulate_bpsk(symbol_indices: np.ndarray) -> np.ndarray:
    """Map integer symbols {0, 1} to BPSK constellation points.
    
    Args:
        symbol_indices: Array of integer symbol indices (0 or 1).

    Returns:
        Complex NumPy array of modulated BPSK symbols.
    """
    indices = np.asarray(symbol_indices, dtype=np.int64)
    if np.any((indices < 0) | (indices > 1)):
        raise ValueError("BPSK symbol indices must be 0 or 1")
    return BPSK_CONSTELLATION[indices]


def modulate_qpsk(symbol_indices: np.ndarray) -> np.ndarray:
    """Map integer symbols {0, 1, 2, 3} to QPSK constellation points.
    
    Args:
        symbol_indices: Array of integer symbol indices (0, 1, 2, 3).

    Returns:
        Complex NumPy array of modulated QPSK symbols.
    """
    indices = np.asarray(symbol_indices, dtype=np.int64)
    if np.any((indices < 0) | (indices > 3)):
        raise ValueError("QPSK symbol indices must be between 0 and 3")
    return QPSK_CONSTELLATION[indices]


def modulate_16qam(symbol_indices: np.ndarray) -> np.ndarray:
    """Map integer symbols {0..15} to 16-QAM constellation points.
    
    Args:
        symbol_indices: Array of integer symbol indices (0 to 15).

    Returns:
        Complex NumPy array of modulated 16-QAM symbols.
    """
    indices = np.asarray(symbol_indices, dtype=np.int64)
    if np.any((indices < 0) | (indices > 15)):
        raise ValueError("16-QAM symbol indices must be between 0 and 15")
    return QAM16_CONSTELLATION[indices]

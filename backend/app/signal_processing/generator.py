"""Synthetic complex I/Q digital signal generator and experiment orchestrator.

Supports BPSK, QPSK, and 16-QAM digital modulations with reproducible random seeding,
calibrated AWGN channel modeling, and structured experiment data packaging.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np

from .fft import compute_fft
from .features import extract_features
from .modulation import (
    SUPPORTED_MODULATIONS,
    get_constellation,
    modulate_16qam,
    modulate_bpsk,
    modulate_qpsk,
    normalize_modulation_name,
)
from .noise import add_awgn
from .preprocessing import calculate_signal_power


@dataclass(frozen=True)
class GeneratedSignal:
    """Structured result of synthetic signal generation."""
    signal: np.ndarray      # Complex I/Q baseband samples (complex128)
    modulation: str         # Canonical modulation name (e.g., 'BPSK', 'QPSK', '16-QAM')
    num_samples: int        # Number of samples generated
    sample_rate: float      # Sampling frequency in Hz
    signal_power: float     # Measured average power
    seed: Optional[int]     # Random seed used (or None)


@dataclass(frozen=True)
class SignalExperiment:
    """Internal representation of a complete signal simulation experiment.
    
    Contains clean baseband signal, noise array, noisy received signal,
    SNR metrics, and metadata.
    """
    modulation: str
    sample_count: int
    sample_rate: float
    seed: Optional[int]
    signal_power: float
    noise_type: str
    target_snr_db: float
    measured_snr_db: float
    signal: np.ndarray        # Clean complex signal
    noisy_signal: np.ndarray  # Signal + AWGN
    noise: np.ndarray         # AWGN samples

    def save_to_directory(self, target_dir: Path) -> Dict[str, str]:
        """Save experiment arrays (.npy) and metadata/features (.json) to disk.
        
        Args:
            target_dir: Target directory path (e.g. storage/experiments/EXP-001).

        Returns:
            Dictionary mapping artifact names to their file paths.
        """
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        iq_path = target_dir / "iq.npy"
        noisy_iq_path = target_dir / "noisy_iq.npy"
        noise_path = target_dir / "noise.npy"
        spectrum_path = target_dir / "spectrum.npy"
        features_path = target_dir / "features.json"
        metadata_path = target_dir / "metadata.json"

        # Save binary arrays
        np.save(iq_path, self.signal)
        np.save(noisy_iq_path, self.noisy_signal)
        np.save(noise_path, self.noise)

        # Compute and save spectrum
        fft_res = compute_fft(self.noisy_signal, sample_rate=self.sample_rate)
        np.save(spectrum_path, fft_res.complex_spectrum)

        # Compute and save features
        _, feat_dict = extract_features(self.noisy_signal, sample_rate=self.sample_rate)
        with open(features_path, "w", encoding="utf-8") as f:
            json.dump(feat_dict, f, indent=2)

        # Save metadata
        metadata: Dict[str, Any] = {
            "modulation": self.modulation,
            "sample_count": self.sample_count,
            "sample_rate": self.sample_rate,
            "seed": self.seed,
            "signal_power": self.signal_power,
            "noise_type": self.noise_type,
            "target_snr_db": self.target_snr_db,
            "measured_snr_db": self.measured_snr_db,
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "iq_file": str(iq_path),
            "noisy_iq_file": str(noisy_iq_path),
            "noise_file": str(noise_path),
            "spectrum_file": str(spectrum_path),
            "features_file": str(features_path),
            "metadata_file": str(metadata_path),
        }


def generate_signal(
    modulation: str,
    num_samples: int,
    sample_rate: float = 1e6,
    seed: Optional[int] = None,
) -> GeneratedSignal:
    """Generate synthetic complex I/Q baseband samples for a given modulation.
    
    Args:
        modulation: Modulation scheme ('BPSK', 'QPSK', '16-QAM').
        num_samples: Number of symbols/samples to generate (positive integer).
        sample_rate: Sampling frequency in Hz (default: 1.0 MHz).
        seed: Optional integer seed for deterministic reproducibility.

    Returns:
        GeneratedSignal dataclass containing complex signal and parameters.

    Raises:
        ValueError: If modulation is unsupported, num_samples <= 0,
                    or sample_rate <= 0.
    """
    canonical_mod = normalize_modulation_name(modulation)

    if not isinstance(num_samples, (int, np.integer)):
        raise ValueError(f"Sample count must be an integer, got {type(num_samples).__name__}")
    if num_samples <= 0:
        raise ValueError(f"Sample count must be a positive integer, got {num_samples}")

    if not np.isfinite(sample_rate) or sample_rate <= 0:
        raise ValueError(f"Sample rate must be a positive finite number, got {sample_rate}")

    rng = np.random.default_rng(seed)

    if canonical_mod == "BPSK":
        # 1 bit per symbol -> 2 states: {0, 1}
        symbol_indices = rng.integers(0, 2, size=num_samples)
        iq_samples = modulate_bpsk(symbol_indices)
    elif canonical_mod == "QPSK":
        # 2 bits per symbol -> 4 states: {0, 1, 2, 3}
        symbol_indices = rng.integers(0, 4, size=num_samples)
        iq_samples = modulate_qpsk(symbol_indices)
    elif canonical_mod == "16-QAM":
        # 4 bits per symbol -> 16 states: {0..15}
        symbol_indices = rng.integers(0, 16, size=num_samples)
        iq_samples = modulate_16qam(symbol_indices)
    else:
        raise ValueError(f"Unhandled modulation '{canonical_mod}'")

    power = calculate_signal_power(iq_samples)

    return GeneratedSignal(
        signal=iq_samples,
        modulation=canonical_mod,
        num_samples=num_samples,
        sample_rate=float(sample_rate),
        signal_power=power,
        seed=seed,
    )


def run_signal_experiment(
    modulation: str,
    sample_count: int,
    snr_db: float,
    sample_rate: float = 1e6,
    seed: Optional[int] = None,
) -> SignalExperiment:
    """Run an end-to-end signal experiment: generation, AWGN addition, and SNR measurement.
    
    Args:
        modulation: Modulation scheme ('BPSK', 'QPSK', '16-QAM').
        sample_count: Number of complex samples to generate.
        snr_db: Target SNR in decibels.
        sample_rate: Sampling frequency in Hz.
        seed: Optional integer seed for reproducible signal and noise generation.

    Returns:
        SignalExperiment dataclass containing clean, noisy, and noise signals with metrics.
    """
    # If seed is provided, derive independent sub-seeds for signal and noise for reproducibility
    if seed is not None:
        ss = np.random.SeedSequence(seed)
        sig_seed, noise_seed = [int(s.generate_state(1)[0]) for s in ss.spawn(2)]
    else:
        sig_seed = None
        noise_seed = None

    clean_gen = generate_signal(
        modulation=modulation,
        num_samples=sample_count,
        sample_rate=sample_rate,
        seed=sig_seed,
    )

    awgn_res = add_awgn(
        signal=clean_gen.signal,
        snr_db=snr_db,
        seed=noise_seed,
    )

    return SignalExperiment(
        modulation=clean_gen.modulation,
        sample_count=sample_count,
        sample_rate=float(sample_rate),
        seed=seed,
        signal_power=clean_gen.signal_power,
        noise_type="AWGN",
        target_snr_db=float(snr_db),
        measured_snr_db=awgn_res.measured_snr_db,
        signal=clean_gen.signal,
        noisy_signal=awgn_res.noisy_signal,
        noise=awgn_res.noise,
    )

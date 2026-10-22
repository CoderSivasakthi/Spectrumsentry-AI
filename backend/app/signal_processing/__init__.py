"""SpectrumSentry AI - Signal Processing Engine.

Provides digital signal processing, synthetic complex baseband I/Q generation,
AWGN channel modeling, FFT/PSD analysis, constellation extraction, and statistical
feature extraction for BPSK, QPSK, and 16-QAM modulations.
"""

from .constellation import ConstellationData, extract_constellation
from .features import FEATURE_COUNT, FEATURE_NAMES, extract_features
from .fft import FFTResult, PSDResult, compute_fft, compute_psd
from .generator import (
    GeneratedSignal,
    SignalExperiment,
    generate_signal,
    run_signal_experiment,
)
from .modulation import (
    BPSK_CONSTELLATION,
    QPSK_CONSTELLATION,
    QAM16_CONSTELLATION,
    SUPPORTED_MODULATIONS,
    get_constellation,
    modulate_16qam,
    modulate_bpsk,
    modulate_qpsk,
    normalize_modulation_name,
)
from .noise import AWGNResult, add_awgn, calculate_snr_db
from .preprocessing import (
    calculate_magnitude,
    calculate_phase,
    calculate_signal_power,
    extract_iq,
    normalize_iq,
    validate_complex_signal,
)

__all__ = [
    # Modulation
    "SUPPORTED_MODULATIONS",
    "BPSK_CONSTELLATION",
    "QPSK_CONSTELLATION",
    "QAM16_CONSTELLATION",
    "normalize_modulation_name",
    "get_constellation",
    "modulate_bpsk",
    "modulate_qpsk",
    "modulate_16qam",
    # Preprocessing
    "validate_complex_signal",
    "extract_iq",
    "calculate_signal_power",
    "calculate_magnitude",
    "calculate_phase",
    "normalize_iq",
    # Noise
    "AWGNResult",
    "add_awgn",
    "calculate_snr_db",
    # FFT & PSD
    "FFTResult",
    "PSDResult",
    "compute_fft",
    "compute_psd",
    # Constellation
    "ConstellationData",
    "extract_constellation",
    # Features
    "FEATURE_NAMES",
    "FEATURE_COUNT",
    "extract_features",
    # Generator & Experiment
    "GeneratedSignal",
    "SignalExperiment",
    "generate_signal",
    "run_signal_experiment",
]

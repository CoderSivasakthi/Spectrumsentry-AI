"""Demonstration and verification script for SpectrumSentry AI Signal Processing Engine.

Performs:
1. Generation of BPSK, QPSK, and 16-QAM signals
2. Application of AWGN noise
3. Accurate SNR measurement
4. FFT and PSD frequency analysis
5. Constellation point extraction
6. Statistical and spectral feature extraction
"""

import sys
from pathlib import Path

# Add project root to path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


import numpy as np
from backend.app.signal_processing import (
    add_awgn,
    compute_fft,
    compute_psd,
    extract_constellation,
    extract_features,
    generate_signal,
    run_signal_experiment,
)


def run_dsp_demo():
    print("========================================")
    print("SpectrumSentry AI - DSP Engine Test")
    print("========================================")

    modulation = "BPSK"
    samples = 10000
    sample_rate = 1e6
    target_snr = 10.0
    seed = 42

    # 1. Generate Clean Signal
    clean_gen = generate_signal(
        modulation=modulation,
        num_samples=samples,
        sample_rate=sample_rate,
        seed=seed,
    )

    # 2. Add 10 dB AWGN
    awgn_res = add_awgn(
        signal=clean_gen.signal,
        snr_db=target_snr,
        seed=seed,
    )

    # 3. Frequency Analysis
    fft_res = compute_fft(awgn_res.noisy_signal, sample_rate=sample_rate)
    psd_res = compute_psd(awgn_res.noisy_signal, sample_rate=sample_rate)

    # 4. Constellation Data
    const_data = extract_constellation(awgn_res.noisy_signal, max_points=2000)

    # 5. Feature Extraction
    feat_vector, feat_dict = extract_features(awgn_res.noisy_signal, sample_rate=sample_rate)

    print(f"Modulation       : {clean_gen.modulation}")
    print(f"Samples          : {clean_gen.num_samples}")
    print(f"Sample Rate      : {int(clean_gen.sample_rate / 1e3)} kHz")
    print(f"Target SNR       : {target_snr:.2f} dB")
    print(f"Measured SNR     : {awgn_res.measured_snr_db:.2f} dB")
    print(f"Signal Power     : {clean_gen.signal_power:.4f}")
    print(f"Noise Power      : {awgn_res.noise_power:.4f}")
    print(f"FFT Bins         : {len(fft_res.frequencies)}")
    print(f"Constellation Pts: {const_data.sampled_points} (decimated from {const_data.total_points})")

    print("\nExtracted Key Features (out of 23):")
    print(f"- RMS Magnitude  : {feat_dict['rms_magnitude']:.4f}")
    print(f"- Mean Magnitude : {feat_dict['mean_magnitude']:.4f}")
    print(f"- Std Magnitude  : {feat_dict['std_magnitude']:.4f}")
    print(f"- Peak Magnitude : {feat_dict['peak_magnitude']:.4f}")
    print(f"- 4th Moment (I) : {feat_dict['moment4_i']:.4f}")
    print(f"- Kurtosis (I)   : {feat_dict['kurtosis_i']:.4f}")
    print(f"- Spectral Energy: {feat_dict['spectral_energy']:.4f}")
    print(f"- Spectral Spread: {feat_dict['spectral_spread']:.2f} Hz")
    print(f"- Spec Flatness  : {feat_dict['spectral_flatness']:.4f}")

    # Check tolerances
    snr_error = abs(awgn_res.measured_snr_db - target_snr)
    assert snr_error < 0.25, f"SNR error too high: {snr_error} dB"
    assert len(feat_vector) == 23, f"Expected 23 features, got {len(feat_vector)}"
    assert np.all(np.isfinite(feat_vector)), "Feature vector contains NaN/Inf"

    print("\nDSP STATUS: PASS")
    print("========================================")


if __name__ == "__main__":
    run_dsp_demo()

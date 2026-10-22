"""Unit tests for FFT, PSD, and statistical/spectral feature extraction."""

import numpy as np
import pytest

from backend.app.signal_processing.features import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    extract_features,
)
from backend.app.signal_processing.fft import compute_fft, compute_psd
from backend.app.signal_processing.generator import generate_signal
from backend.app.signal_processing.noise import add_awgn


class TestFFTAndPSD:
    """Tests for FFT and PSD spectral analysis."""

    def test_fft_output_shapes_and_types(self):
        n = 1024
        fs = 2e6
        sig = generate_signal("QPSK", num_samples=n, sample_rate=fs, seed=42).signal
        fft_res = compute_fft(sig, sample_rate=fs)

        assert len(fft_res.frequencies) == n
        assert len(fft_res.complex_spectrum) == n
        assert len(fft_res.magnitude) == n
        assert len(fft_res.magnitude_db) == n
        assert len(fft_res.power) == n
        assert len(fft_res.power_db) == n
        assert fft_res.sample_rate == fs
        assert np.iscomplexobj(fft_res.complex_spectrum)
        assert np.isrealobj(fft_res.magnitude)

    def test_fft_shift_centering(self):
        n = 1000
        fs = 1e6
        sig = generate_signal("BPSK", num_samples=n, sample_rate=fs, seed=42).signal
        fft_res = compute_fft(sig, sample_rate=fs)

        # Centered frequency axis should span from -fs/2 to approximately +fs/2
        assert np.isclose(fft_res.frequencies[0], -fs / 2.0, atol=fs / n)
        assert np.isclose(fft_res.frequencies[n // 2], 0.0, atol=fs / n)

    def test_fft_known_sinusoid(self):
        """A pure complex tone at frequency f0 should produce a peak at f0 in the FFT."""
        fs = 1e6  # 1 MHz
        f0 = 200e3  # 200 kHz
        n = 4000
        t = np.arange(n) / fs
        tone = np.exp(1j * 2 * np.pi * f0 * t)

        fft_res = compute_fft(tone, sample_rate=fs)
        assert abs(fft_res.peak_frequency - f0) < (fs / n)

    def test_fft_no_nan_or_inf(self):
        sig = generate_signal("16-QAM", num_samples=2048, seed=42).signal
        fft_res = compute_fft(sig)
        assert np.all(np.isfinite(fft_res.magnitude))
        assert np.all(np.isfinite(fft_res.magnitude_db))
        assert np.all(np.isfinite(fft_res.power))
        assert np.all(np.isfinite(fft_res.power_db))

    def test_psd_computation(self):
        sig = generate_signal("QPSK", num_samples=4096, sample_rate=1e6, seed=42).signal
        psd_res = compute_psd(sig, sample_rate=1e6, nperseg=512)

        assert len(psd_res.frequencies) > 0
        assert len(psd_res.psd) == len(psd_res.frequencies)
        assert np.all(np.isfinite(psd_res.psd))
        assert np.all(psd_res.psd >= 0.0)
        assert np.all(np.isfinite(psd_res.psd_db))

    def test_invalid_sample_rate_in_fft(self):
        sig = np.array([1.0 + 0j, -1.0 + 0j])
        with pytest.raises(ValueError, match="Sample rate must be a positive finite number"):
            compute_fft(sig, sample_rate=0.0)
        with pytest.raises(ValueError, match="Sample rate must be a positive finite number"):
            compute_fft(sig, sample_rate=-10.0)


class TestFeatureExtraction:
    """Tests for statistical and spectral feature extraction."""

    def test_feature_vector_properties(self):
        sig = generate_signal("QPSK", num_samples=5000, seed=42).signal
        vec, feat_dict = extract_features(sig, sample_rate=1e6)

        assert isinstance(vec, np.ndarray)
        assert vec.shape == (FEATURE_COUNT,)
        assert len(FEATURE_NAMES) == FEATURE_COUNT
        assert vec.dtype == np.float32

        # Check all values are finite (no NaN, no Inf)
        assert np.all(np.isfinite(vec))
        for key in FEATURE_NAMES:
            assert key in feat_dict
            assert np.isfinite(feat_dict[key])

    def test_feature_ordering_consistency(self):
        """Ensure the NumPy vector matches the exact order of FEATURE_NAMES."""
        sig = generate_signal("16-QAM", num_samples=4000, seed=99).signal
        vec, feat_dict = extract_features(sig, sample_rate=1e6)

        for idx, name in enumerate(FEATURE_NAMES):
            expected_val = np.float32(feat_dict[name])
            assert np.isclose(vec[idx], expected_val), f"Mismatch at index {idx} for feature {name}"

    def test_deterministic_extraction(self):
        """Same signal must produce bit-for-bit identical feature vectors."""
        sig = generate_signal("BPSK", num_samples=3000, seed=1234).signal
        vec1, dict1 = extract_features(sig, sample_rate=1e6)
        vec2, dict2 = extract_features(sig, sample_rate=1e6)

        np.testing.assert_array_equal(vec1, vec2)
        assert dict1 == dict2

    def test_features_distinguish_modulations(self):
        """BPSK and 16-QAM should yield distinct statistical characteristics."""
        bpsk = generate_signal("BPSK", num_samples=10000, seed=42).signal
        qam16 = generate_signal("16-QAM", num_samples=10000, seed=42).signal

        _, bpsk_feats = extract_features(bpsk)
        _, qam_feats = extract_features(qam16)

        # For BPSK, Q component is 0, so std_q is 0
        assert np.isclose(bpsk_feats["std_q"], 0.0)
        # For 16-QAM, Q component is distributed across {-3, -1, 1, 3}/sqrt(10), std_q > 0.4
        assert qam_feats["std_q"] > 0.4

        # Magnitude variance: BPSK constant modulus |x|=1 (std_magnitude ~ 0)
        assert np.isclose(bpsk_feats["std_magnitude"], 0.0, atol=1e-5)
        # 16-QAM has multiple amplitude levels, std_magnitude > 0.2
        assert qam_feats["std_magnitude"] > 0.2

    def test_extract_features_with_noise(self):
        """Extract features on noisy signals across different SNRs."""
        clean = generate_signal("QPSK", num_samples=4000, seed=42).signal
        noisy_high_snr = add_awgn(clean, snr_db=25.0, seed=42).noisy_signal
        noisy_low_snr = add_awgn(clean, snr_db=-5.0, seed=42).noisy_signal

        _, feats_high = extract_features(noisy_high_snr)
        _, feats_low = extract_features(noisy_low_snr)

        # Low SNR has significantly higher noise power and std_magnitude
        assert feats_low["std_magnitude"] > feats_high["std_magnitude"]
        assert np.all(np.isfinite(feats_high["spectral_flatness"]))
        assert np.all(np.isfinite(feats_low["spectral_flatness"]))

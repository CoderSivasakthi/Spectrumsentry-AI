"""Unit tests for the phase-robust cumulant (v2) feature contract (corrected report fix #5).

Verifies:
- The six theoretical cumulant signatures for BPSK/QPSK/16-QAM at high SNR.
- Exact invariance under arbitrary constant carrier phase rotations.
- Deterministic extraction, error handling, and the v2 feature-vector contract.
"""

import numpy as np
import pytest

from backend.app.signal_processing.cumulants import (
    FEATURE_COUNT_CUMULANT,
    FEATURE_NAMES_CUMULANT,
    apply_carrier_phase,
    extract_cumulant_features,
)
from backend.app.signal_processing.generator import generate_signal
from backend.app.signal_processing.noise import add_awgn


class TestCumulantFeatureContract:
    """Structure and ordering guarantees of the v2 feature vector."""

    def test_feature_count_and_names(self):
        assert FEATURE_COUNT_CUMULANT == 6
        assert FEATURE_NAMES_CUMULANT == (
            "m20_abs",
            "c40_abs",
            "c41_abs",
            "c42_real",
            "amplitude_mean",
            "amplitude_std",
        )

    def test_vector_shape_dtype_and_dict_order(self):
        sig = generate_signal("QPSK", num_samples=256, seed=1).signal
        vector, feat_dict = extract_cumulant_features(sig)

        assert vector.shape == (FEATURE_COUNT_CUMULANT,)
        assert vector.dtype == np.float32
        assert np.all(np.isfinite(vector))
        for name, value in zip(FEATURE_NAMES_CUMULANT, vector):
            assert np.isclose(feat_dict[name], float(value))

    def test_independent_of_absolute_power(self):
        # Power normalization must make the vector invariant to linear gain
        sig = generate_signal("16-QAM", num_samples=512, seed=5).signal
        base, _ = extract_cumulant_features(sig)
        scaled, _ = extract_cumulant_features(10.0 * sig)

        assert np.allclose(base, scaled, atol=1e-5)


class TestPhaseRobustness:
    """The core corrected-report requirement: random carrier phase invariance."""

    @pytest.mark.parametrize("modulation", ["BPSK", "QPSK", "16-QAM"])
    @pytest.mark.parametrize("phase", [0.0, 0.3, 1.11, 2.9, 4.44, 6.0])
    def test_exact_phase_invariance(self, modulation, phase):
        rng = np.random.default_rng(11)
        base = generate_signal(modulation, num_samples=1024, seed=7).signal
        noisy = add_awgn(base, snr_db=15.0, seed=3).noisy_signal

        f_base, _ = extract_cumulant_features(noisy)
        f_rotated, _ = extract_cumulant_features(apply_carrier_phase(noisy, phase))

        assert np.allclose(f_base, f_rotated, atol=1e-4)

    def test_random_phase_dataset_diversity(self):
        # Rotating the SAME frame with random phases must yield the SAME features
        rng = np.random.default_rng(99)
        sig = generate_signal("QPSK", num_samples=1024, seed=21).signal
        reference, _ = extract_cumulant_features(sig)

        for _ in range(5):
            rotated = apply_carrier_phase(sig, rng.uniform(0.0, 2.0 * np.pi))
            vector, _ = extract_cumulant_features(rotated)
            assert np.allclose(reference, vector, atol=1e-4)


class TestCumulantTheoryValues:
    """4th-order cumulant signatures from the corrected-report reference values."""

    HIGH_SNR_DB = 30.0

    def _features_at_high_snr(self, modulation: str) -> np.ndarray:
        exp_gen = generate_signal(modulation, num_samples=4096, seed=42)
        noisy = add_awgn(exp_gen.signal, snr_db=self.HIGH_SNR_DB, seed=1337).noisy_signal
        vector, _ = extract_cumulant_features(noisy)
        return vector

    def test_bpsk_signature(self):
        # BPSK: |m20| ~ 1, |c40| ~ 2, |c41| ~ 2, c42 ~ -2, amplitude std ~ 0
        f = self._features_at_high_snr("BPSK")
        assert abs(f[0] - 1.0) < 0.1   # |m20|
        assert abs(f[1] - 2.0) < 0.15  # |c40|
        assert abs(f[2] - 2.0) < 0.15  # |c41|
        assert abs(f[3] + 2.0) < 0.15  # c42
        assert f[5] < 0.15             # amplitude std

    def test_qpsk_signature(self):
        # QPSK: |m20| ~ 0, |c40| ~ 1, |c41| ~ 0, c42 ~ -1, amplitude std ~ 0
        f = self._features_at_high_snr("QPSK")
        assert f[0] < 0.1              # |m20|
        assert abs(f[1] - 1.0) < 0.15  # |c40|
        assert f[2] < 0.15             # |c41|
        assert abs(f[3] + 1.0) < 0.15  # c42
        assert f[5] < 0.15             # amplitude std

    def test_16qam_signature_distinct_from_qpsk(self):
        # 16-QAM: distinguishable from QPSK by c42 envelope and amplitude statistics
        f_qam = self._features_at_high_snr("16-QAM")
        f_qpsk = self._features_at_high_snr("QPSK")
        assert f_qam[5] > 0.25                       # amplitude std (envelope spread)
        assert f_qam[5] > f_qpsk[5] + 0.15           # QPSK is constant-envelope
        assert f_qam[4] < f_qpsk[4] - 0.02           # QAM mean amplitude < 1.0

    def test_classes_separable_per_feature_family(self):
        # |c40| separates BPSK (2) / QPSK (1) / 16-QAM (<1) at high SNR
        f_bpsk = self._features_at_high_snr("BPSK")
        f_qpsk = self._features_at_high_snr("QPSK")
        f_qam = self._features_at_high_snr("16-QAM")
        assert f_bpsk[1] > f_qpsk[1] > f_qam[1]


class TestCarrierPhaseUtil:
    """apply_carrier_phase rotation helper."""

    def test_rotation_preserves_power_and_magnitudes(self):
        sig = generate_signal("16-QAM", num_samples=256, seed=9).signal
        rotated = apply_carrier_phase(sig, 1.234)

        assert rotated.shape == sig.shape
        assert np.allclose(np.abs(rotated), np.abs(sig), atol=1e-9)

    def test_zero_rotation_identity(self):
        sig = generate_signal("QPSK", num_samples=64, seed=2).signal
        assert np.allclose(apply_carrier_phase(sig, 0.0), sig, atol=1e-12)


class TestCumulantErrorHandling:
    """Validation of degenerate inputs."""

    def test_zero_power_signal_raises(self):
        with pytest.raises(ValueError):
            extract_cumulant_features(np.zeros(64, dtype=np.complex128))

    def test_non_finite_moments_clamped_to_zero(self):
        # Constant envelope (e.g. pure tone) must still produce finite outputs
        t = np.arange(512)
        tone = np.exp(1j * 2 * np.pi * 0.05 * t)
        vector, _ = extract_cumulant_features(tone)
        assert np.all(np.isfinite(vector))

"""Unit tests for synthetic signal generator, modulation schemes, and constellation extraction."""

import numpy as np
import pytest

from backend.app.signal_processing.generator import (
    generate_signal,
    run_signal_experiment,
)
from backend.app.signal_processing.modulation import (
    BPSK_CONSTELLATION,
    QAM16_CONSTELLATION,
    QPSK_CONSTELLATION,
    get_constellation,
    normalize_modulation_name,
)
from backend.app.signal_processing.constellation import extract_constellation
from backend.app.signal_processing.preprocessing import (
    calculate_magnitude,
    calculate_phase,
    calculate_signal_power,
    extract_iq,
    normalize_iq,
    validate_complex_signal,
)


class TestModulation:
    """Tests for modulation constellations and mappings."""

    def test_constellation_shapes_and_types(self):
        bpsk = get_constellation("BPSK")
        qpsk = get_constellation("QPSK")
        qam16 = get_constellation("16-QAM")

        assert len(bpsk) == 2
        assert len(qpsk) == 4
        assert len(qam16) == 16

        assert np.iscomplexobj(bpsk)
        assert np.iscomplexobj(qpsk)
        assert np.iscomplexobj(qam16)

    def test_constellation_normalization(self):
        # Average symbol energy should be approximately 1.0
        assert np.isclose(np.mean(np.abs(BPSK_CONSTELLATION) ** 2), 1.0)
        assert np.isclose(np.mean(np.abs(QPSK_CONSTELLATION) ** 2), 1.0)
        assert np.isclose(np.mean(np.abs(QAM16_CONSTELLATION) ** 2), 1.0)

    def test_modulation_normalization_aliases(self):
        assert normalize_modulation_name("bpsk") == "BPSK"
        assert normalize_modulation_name("QPSK") == "QPSK"
        assert normalize_modulation_name("16-qam") == "16-QAM"
        assert normalize_modulation_name("16QAM") == "16-QAM"

    def test_invalid_modulation_raises(self):
        with pytest.raises(ValueError, match="Unsupported modulation"):
            normalize_modulation_name("INVALID_MOD")
        with pytest.raises(ValueError):
            normalize_modulation_name(123)  # type: ignore


class TestSignalGenerator:
    """Tests for synthetic signal generation."""

    def test_bpsk_generation(self):
        res = generate_signal("BPSK", num_samples=1000, seed=123)
        assert res.modulation == "BPSK"
        assert len(res.signal) == 1000
        assert np.iscomplexobj(res.signal)
        # BPSK imaginary part should be zero
        assert np.allclose(np.imag(res.signal), 0.0)
        # Real parts should only be -1 or +1
        unique_vals = set(np.unique(np.real(res.signal)))
        assert unique_vals.issubset({-1.0, 1.0})
        # Power should be 1.0
        assert np.isclose(res.signal_power, 1.0)

    def test_qpsk_generation(self):
        res = generate_signal("QPSK", num_samples=2000, seed=456)
        assert res.modulation == "QPSK"
        assert len(res.signal) == 2000
        assert np.iscomplexobj(res.signal)
        # Power should be approximately 1.0
        assert np.isclose(res.signal_power, 1.0, atol=0.05)

    def test_16qam_generation(self):
        res = generate_signal("16-QAM", num_samples=5000, seed=789)
        assert res.modulation == "16-QAM"
        assert len(res.signal) == 5000
        assert np.iscomplexobj(res.signal)
        # Power should be approximately 1.0 with large sample size
        assert np.isclose(res.signal_power, 1.0, atol=0.08)

    def test_reproducibility_with_seed(self):
        sig1 = generate_signal("QPSK", num_samples=1000, seed=42)
        sig2 = generate_signal("QPSK", num_samples=1000, seed=42)
        sig3 = generate_signal("QPSK", num_samples=1000, seed=999)

        np.testing.assert_array_equal(sig1.signal, sig2.signal)
        assert not np.array_equal(sig1.signal, sig3.signal)

    def test_invalid_sample_count(self):
        with pytest.raises(ValueError, match="Sample count must be a positive integer"):
            generate_signal("BPSK", num_samples=0)
        with pytest.raises(ValueError, match="Sample count must be a positive integer"):
            generate_signal("BPSK", num_samples=-50)
        with pytest.raises(ValueError):
            generate_signal("BPSK", num_samples="1000")  # type: ignore

    def test_invalid_sample_rate(self):
        with pytest.raises(ValueError, match="Sample rate must be a positive finite number"):
            generate_signal("BPSK", num_samples=500, sample_rate=0)
        with pytest.raises(ValueError, match="Sample rate must be a positive finite number"):
            generate_signal("BPSK", num_samples=500, sample_rate=-1e6)

    def test_run_signal_experiment(self, tmp_path):
        exp = run_signal_experiment("QPSK", sample_count=1000, snr_db=12.0, seed=42)
        assert exp.modulation == "QPSK"
        assert exp.sample_count == 1000
        assert exp.target_snr_db == 12.0
        assert abs(exp.measured_snr_db - 12.0) < 0.5
        assert len(exp.signal) == 1000
        assert len(exp.noisy_signal) == 1000
        assert len(exp.noise) == 1000

        # Test save to directory
        target_dir = tmp_path / "exp_test"
        files = exp.save_to_directory(target_dir)
        assert (target_dir / "iq.npy").exists()
        assert (target_dir / "noisy_iq.npy").exists()
        assert (target_dir / "noise.npy").exists()
        assert (target_dir / "spectrum.npy").exists()
        assert (target_dir / "features.json").exists()
        assert (target_dir / "metadata.json").exists()


class TestConstellationAndPreprocessing:
    """Tests for constellation point extraction and preprocessing operations."""

    def test_extract_iq(self):
        sig = np.array([1.0 + 2.0j, -3.0 + 4.0j], dtype=np.complex128)
        i, q = extract_iq(sig)
        np.testing.assert_array_equal(i, np.array([1.0, -3.0]))
        np.testing.assert_array_equal(q, np.array([2.0, 4.0]))

    def test_calculate_magnitude_and_phase(self):
        sig = np.array([1.0 + 1.0j, -1.0 - 1.0j], dtype=np.complex128)
        mag = calculate_magnitude(sig)
        phase = calculate_phase(sig)
        np.testing.assert_allclose(mag, np.array([np.sqrt(2), np.sqrt(2)]))
        np.testing.assert_allclose(phase, np.array([np.pi / 4, -3 * np.pi / 4]))

    def test_constellation_point_count_and_decimation(self):
        sig = generate_signal("QPSK", num_samples=10000, seed=42).signal
        const_full = extract_constellation(sig, max_points=None)
        assert const_full.total_points == 10000
        assert const_full.sampled_points == 10000

        const_sub = extract_constellation(sig, max_points=2500)
        assert const_sub.total_points == 10000
        assert const_sub.sampled_points == 2500
        assert len(const_sub.i) == 2500
        assert len(const_sub.q) == 2500

    def test_normalize_iq(self):
        sig = np.array([2.0 + 0j, -2.0 + 0j], dtype=np.complex128)
        assert calculate_signal_power(sig) == 4.0
        norm_sig = normalize_iq(sig, target_power=1.0)
        assert np.isclose(calculate_signal_power(norm_sig), 1.0)

    def test_validation_rejects_empty_and_nan(self):
        with pytest.raises(ValueError, match="empty"):
            validate_complex_signal(np.array([], dtype=np.complex128))
        with pytest.raises(ValueError, match="NaN or Infinite"):
            validate_complex_signal(np.array([1.0 + 1.0j, np.nan + 0j]))
        with pytest.raises(ValueError, match="NaN or Infinite"):
            validate_complex_signal(np.array([1.0 + 1.0j, np.inf + 0j]))

"""Unit tests for AWGN channel noise simulation and SNR measurement."""

import numpy as np
import pytest

from backend.app.signal_processing.generator import generate_signal
from backend.app.signal_processing.noise import add_awgn, calculate_snr_db
from backend.app.signal_processing.preprocessing import calculate_signal_power


class TestNoiseAndSNR:
    """Tests for AWGN channel model and SNR calculation."""

    @pytest.fixture
    def qpsk_signal(self):
        """Generate a standardized QPSK signal for noise testing."""
        return generate_signal("QPSK", num_samples=20000, seed=101).signal

    def test_awgn_output_shape_and_type(self, qpsk_signal):
        res = add_awgn(qpsk_signal, snr_db=10.0, seed=42)
        assert res.noisy_signal.shape == qpsk_signal.shape
        assert res.noise.shape == qpsk_signal.shape
        assert np.iscomplexobj(res.noisy_signal)
        assert np.iscomplexobj(res.noise)

    def test_noise_alters_signal(self, qpsk_signal):
        res = add_awgn(qpsk_signal, snr_db=10.0, seed=42)
        assert not np.array_equal(res.noisy_signal, qpsk_signal)
        # Verify algebraic relationship: noisy_signal = signal + noise
        np.testing.assert_allclose(res.noisy_signal, qpsk_signal + res.noise)

    def test_reproducibility_with_seed(self, qpsk_signal):
        res1 = add_awgn(qpsk_signal, snr_db=15.0, seed=1234)
        res2 = add_awgn(qpsk_signal, snr_db=15.0, seed=1234)
        res3 = add_awgn(qpsk_signal, snr_db=15.0, seed=5678)

        np.testing.assert_array_equal(res1.noisy_signal, res2.noisy_signal)
        np.testing.assert_array_equal(res1.noise, res2.noise)
        assert not np.array_equal(res1.noisy_signal, res3.noisy_signal)

    @pytest.mark.parametrize("target_snr", [20.0, 10.0, 5.0, 0.0, -5.0])
    def test_snr_accuracy_across_levels(self, qpsk_signal, target_snr):
        """Verify measured SNR is within small statistical tolerance of target SNR."""
        res = add_awgn(qpsk_signal, snr_db=target_snr, seed=42)
        assert res.target_snr_db == target_snr
        # With 20,000 samples, variance of sample mean noise power is very small (<0.3 dB)
        error_db = abs(res.measured_snr_db - target_snr)
        assert error_db < 0.35, f"Measured SNR {res.measured_snr_db:.2f} differs from target {target_snr} by {error_db:.2f} dB"

    def test_noise_power_scaling(self, qpsk_signal):
        """Noise power should increase as SNR decreases."""
        res_high_snr = add_awgn(qpsk_signal, snr_db=20.0, seed=42)
        res_low_snr = add_awgn(qpsk_signal, snr_db=0.0, seed=42)

        assert res_low_snr.noise_power > res_high_snr.noise_power
        # Ratio of noise powers for 20dB vs 0dB should be approximately 100
        ratio = res_low_snr.noise_power / res_high_snr.noise_power
        assert np.isclose(ratio, 100.0, rtol=0.1)

    def test_calculate_snr_db_function(self):
        # 10 dB: signal power 10x noise power
        assert np.isclose(calculate_snr_db(10.0, 1.0), 10.0)
        # 0 dB: signal power equal to noise power
        assert np.isclose(calculate_snr_db(5.0, 5.0), 0.0)
        # 20 dB: signal power 100x noise power
        assert np.isclose(calculate_snr_db(100.0, 1.0), 20.0)

    def test_calculate_snr_db_invalid_inputs(self):
        with pytest.raises(ValueError, match="Signal power must be a positive finite number"):
            calculate_snr_db(0.0, 1.0)
        with pytest.raises(ValueError, match="Signal power must be a positive finite number"):
            calculate_snr_db(-2.0, 1.0)
        with pytest.raises(ValueError, match="Noise power must be a positive finite number"):
            calculate_snr_db(1.0, 0.0)
        with pytest.raises(ValueError, match="Noise power must be a positive finite number"):
            calculate_snr_db(1.0, -1.0)

    def test_invalid_snr_input_to_add_awgn(self, qpsk_signal):
        with pytest.raises(ValueError, match="SNR must be a finite number"):
            add_awgn(qpsk_signal, snr_db=np.nan)
        with pytest.raises(ValueError, match="SNR must be a finite number"):
            add_awgn(qpsk_signal, snr_db=np.inf)

    def test_add_awgn_to_zero_power_signal(self):
        zero_signal = np.zeros(100, dtype=np.complex128)
        with pytest.raises(ValueError, match="Cannot add AWGN to a zero-power signal"):
            add_awgn(zero_signal, snr_db=10.0)

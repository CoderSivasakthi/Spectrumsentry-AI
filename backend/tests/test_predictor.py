"""Unit tests for Phase 4 ModulationPredictor inference engine."""

from pathlib import Path
import numpy as np
import pytest

from backend.app.ml.predictor import ModulationPredictor
from backend.app.ml.trainer import DEFAULT_MODELS_DIR
from backend.app.signal_processing import FEATURE_COUNT


class TestModulationPredictor:
    """Test suite for live predictor operations, input validation, and benchmarking."""

    @pytest.fixture
    def predictor(self):
        """Fixture returning an initialized predictor using the saved Phase 4 model."""
        model_path = DEFAULT_MODELS_DIR / "modulation_mlp_v1.joblib"
        meta_path = DEFAULT_MODELS_DIR / "model_metadata.json"
        if not model_path.exists():
            pytest.skip(f"Trained model not found at {model_path}")
        return ModulationPredictor(model_path=model_path, metadata_path=meta_path)

    def test_single_prediction_structure_and_probabilities(self, predictor):
        # Generate valid 23-feature vector
        x = np.zeros(FEATURE_COUNT, dtype=np.float32)
        res = predictor.predict_single(x)

        # Check required fields
        assert "predicted_modulation" in res
        assert "predicted_label" in res
        assert "confidence" in res
        assert "class_probabilities" in res
        assert "inference_time_ms" in res
        assert "model_version" in res

        assert res["predicted_modulation"] in ["BPSK", "QPSK", "16-QAM"]
        assert res["predicted_label"] in [0, 1, 2]
        assert 0.0 <= res["confidence"] <= 1.0
        assert res["inference_time_ms"] >= 0.0

        # Check probability distribution sums to 1.0
        probs = res["class_probabilities"]
        assert len(probs) == 3
        prob_sum = sum(probs.values())
        assert np.isclose(prob_sum, 1.0, atol=1e-3)
        assert res["confidence"] == max(probs.values())

    def test_single_prediction_2d_shape_handling(self, predictor):
        x_2d = np.zeros((1, FEATURE_COUNT), dtype=np.float32)
        res = predictor.predict_single(x_2d)
        assert res["predicted_modulation"] in ["BPSK", "QPSK", "16-QAM"]

    def test_batch_prediction(self, predictor):
        batch_size = 5
        X_batch = np.zeros((batch_size, FEATURE_COUNT), dtype=np.float32)
        results = predictor.predict_batch(X_batch)

        assert len(results) == batch_size
        for r in results:
            assert r["predicted_modulation"] in ["BPSK", "QPSK", "16-QAM"]
            assert np.isclose(sum(r["class_probabilities"].values()), 1.0, atol=1e-3)

    def test_invalid_feature_count_rejected(self, predictor):
        with pytest.raises(ValueError, match="Expected single feature vector of length 23"):
            predictor.predict_single(np.zeros(20, dtype=np.float32))

        with pytest.raises(ValueError, match="Expected feature matrix with 23 columns"):
            predictor.predict_batch(np.zeros((5, 10), dtype=np.float32))

    def test_nan_and_inf_inputs_rejected(self, predictor):
        x_nan = np.zeros(FEATURE_COUNT, dtype=np.float32)
        x_nan[5] = np.nan
        with pytest.raises(ValueError, match="NaN or Infinite"):
            predictor.predict_single(x_nan)

        x_inf = np.zeros(FEATURE_COUNT, dtype=np.float32)
        x_inf[2] = np.inf
        with pytest.raises(ValueError, match="NaN or Infinite"):
            predictor.predict_single(x_inf)

    def test_benchmark_method(self, predictor):
        bench = predictor.benchmark(num_single_runs=20, batch_size=32, num_batch_runs=10)
        assert "single_latency_ms" in bench
        assert "batch_benchmark" in bench
        assert bench["single_latency_ms"]["mean"] > 0
        assert bench["batch_benchmark"]["throughput_samples_per_sec"] > 0

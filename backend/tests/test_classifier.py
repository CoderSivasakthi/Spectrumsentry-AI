"""Unit tests for Phase 4 model training, pipeline construction, and model persistence."""

from pathlib import Path
import numpy as np
import pytest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.app.ml.trainer import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODELS_DIR,
    TrainingConfig,
    build_model_pipeline,
    create_development_split,
    load_trained_model,
    load_training_dataset,
    save_trained_model,
)
from backend.app.signal_processing import FEATURE_COUNT


class TestClassifierPipeline:
    """Test suite for classifier pipeline, training, and serialization."""

    def test_load_training_dataset(self):
        if not (DEFAULT_DATASET_DIR / "train_test_split.npz").exists():
            pytest.skip("Dataset file not found")

        (
            X_train,
            y_train,
            snr_train,
            X_test,
            y_test,
            snr_test,
            info,
        ) = load_training_dataset(DEFAULT_DATASET_DIR)

        assert X_train.shape[1] == FEATURE_COUNT
        assert X_test.shape[1] == FEATURE_COUNT
        assert len(X_train) == len(y_train)
        assert len(X_test) == len(y_test)
        assert np.all(np.isfinite(X_train))
        assert np.all(np.isfinite(X_test))
        assert info["dataset_version"] == "v1.0"

    def test_create_development_split_proportions_and_balance(self):
        # Create synthetic training set with 60 samples
        n = 60
        X = np.ones((n, FEATURE_COUNT), dtype=np.float32)
        y = np.repeat([0, 1, 2], 20)
        snrs = np.tile(np.repeat([0.0, 10.0], 10), 3)

        X_fit, y_fit, snr_fit, X_val, y_val, snr_val = create_development_split(
            X, y, snrs, val_ratio=0.2, seed=42
        )

        assert len(X_fit) == 48  # 80%
        assert len(X_val) == 12  # 20%
        # Check all 3 classes are represented in both
        assert set(np.unique(y_fit)) == {0, 1, 2}
        assert set(np.unique(y_val)) == {0, 1, 2}

    def test_build_model_pipeline_structure(self):
        cfg = TrainingConfig(hidden_layer_sizes=(32, 16))
        pipe = build_model_pipeline(cfg)

        assert isinstance(pipe, Pipeline)
        assert "scaler" in pipe.named_steps
        assert "classifier" in pipe.named_steps
        assert isinstance(pipe.named_steps["scaler"], StandardScaler)
        assert pipe.named_steps["classifier"].hidden_layer_sizes == (32, 16)

    def test_fast_training_and_reproducibility(self):
        # Fast test on small synthetic dataset
        rng = np.random.default_rng(42)
        X = rng.standard_normal((90, FEATURE_COUNT), dtype=np.float32)
        y = np.repeat([0, 1, 2], 30)

        cfg1 = TrainingConfig(
            hidden_layer_sizes=(16, 8),
            max_iter=30,
            batch_size=32,
            random_state=42,
        )
        pipe1 = build_model_pipeline(cfg1)
        pipe1.fit(X, y)
        preds1 = pipe1.predict(X)

        cfg2 = TrainingConfig(
            hidden_layer_sizes=(16, 8),
            max_iter=30,
            batch_size=32,
            random_state=42,
        )
        pipe2 = build_model_pipeline(cfg2)
        pipe2.fit(X, y)
        preds2 = pipe2.predict(X)

        # Bit-for-bit identical predictions with same seed
        np.testing.assert_array_equal(preds1, preds2)

    def test_model_serialization_and_reloading(self, tmp_path):
        # Fit small model
        rng = np.random.default_rng(101)
        X = rng.standard_normal((60, FEATURE_COUNT), dtype=np.float32)
        y = np.repeat([0, 1, 2], 20)

        cfg = TrainingConfig(hidden_layer_sizes=(16,), max_iter=25, batch_size=16, random_state=42)
        pipe = build_model_pipeline(cfg)
        pipe.fit(X, y)

        preds_before = pipe.predict(X)
        probs_before = pipe.predict_proba(X)

        # Save model
        saved_paths = save_trained_model(
            pipeline=pipe,
            output_dir=tmp_path,
            model_name="test_mlp",
            model_metadata={"test_run": True},
            training_config=cfg,
        )
        assert (tmp_path / "test_mlp.joblib").exists()
        assert (tmp_path / "model_metadata.json").exists()
        assert (tmp_path / "training_config.json").exists()

        # Reload model
        reloaded_pipe = load_trained_model(tmp_path / "test_mlp.joblib")
        preds_after = reloaded_pipe.predict(X)
        probs_after = reloaded_pipe.predict_proba(X)

        np.testing.assert_array_equal(preds_before, preds_after)
        np.testing.assert_allclose(probs_before, probs_after)

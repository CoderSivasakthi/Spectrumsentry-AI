"""Unit tests for Phase 3 dataset generation, splitting, reproducibility, and leakage prevention."""

from pathlib import Path
import numpy as np
import pytest

from backend.app.ml.dataset import (
    INVERSE_LABEL_MAP,
    LABEL_MAP,
    DatasetConfig,
    generate_modulation_dataset,
    save_dataset_artifacts,
    validate_dataset_directory,
)
from backend.app.signal_processing import FEATURE_COUNT, FEATURE_NAMES


class TestDatasetGeneration:
    """Test suite for synthetic modulation classification dataset pipeline."""

    @pytest.fixture
    def small_config(self):
        """Fast test configuration: 3 modulations x 3 SNR levels x 4 samples = 36 examples."""
        return DatasetConfig(
            dataset_version="test-v1.0",
            modulations=("BPSK", "QPSK", "16-QAM"),
            snr_min_db=0,
            snr_max_db=4,
            snr_step_db=2,  # [0, 2, 4]
            samples_per_condition=4,
            sample_count=256,
            sample_rate=1e6,
            seed=42,
            test_ratio=0.25,
        )

    def test_dataset_generation_shapes_and_types(self, small_config):
        ds = generate_modulation_dataset(small_config)

        expected_total = small_config.total_samples  # 3 * 3 * 4 = 36
        assert ds.X.shape == (expected_total, FEATURE_COUNT)
        assert ds.y.shape == (expected_total,)
        assert ds.X.dtype == np.float32
        assert ds.y.dtype == np.int64
        assert len(ds.metadata) == expected_total

    def test_numerical_integrity_no_nan_or_inf(self, small_config):
        ds = generate_modulation_dataset(small_config)
        assert np.all(np.isfinite(ds.X)), "Feature matrix contains NaN or Inf values"
        assert int(np.sum(np.isnan(ds.X))) == 0
        assert int(np.sum(np.isinf(ds.X))) == 0

    def test_class_and_snr_balance(self, small_config):
        ds = generate_modulation_dataset(small_config)

        # 3 classes: BPSK, QPSK, 16-QAM
        expected_per_class = small_config.total_samples // 3  # 12 each
        for mod, label_idx in LABEL_MAP.items():
            class_count = int(np.sum(ds.y == label_idx))
            assert class_count == expected_per_class, f"Class {mod} count {class_count} != {expected_per_class}"

        # 3 SNR levels: 0, 2, 4 dB -> 12 each
        expected_per_snr = small_config.total_samples // 3  # 12 each
        for snr in small_config.snr_levels:
            snr_count = int(np.sum(np.isclose(ds.target_snr, snr)))
            assert snr_count == expected_per_snr, f"SNR {snr} count {snr_count} != {expected_per_snr}"

        # Each condition (mod x SNR) must have exactly samples_per_condition
        for mod, label_idx in LABEL_MAP.items():
            for snr in small_config.snr_levels:
                cond_count = int(np.sum((ds.y == label_idx) & np.isclose(ds.target_snr, snr)))
                assert cond_count == small_config.samples_per_condition

    def test_train_test_split_and_zero_leakage(self, small_config):
        ds = generate_modulation_dataset(small_config)

        n_samples = small_config.total_samples
        expected_test = int(round(n_samples * small_config.test_ratio))  # 36 * 0.25 = 9
        expected_train = n_samples - expected_test  # 27

        assert len(ds.train_indices) == expected_train
        assert len(ds.test_indices) == expected_test
        assert ds.X_train.shape == (expected_train, FEATURE_COUNT)
        assert ds.X_test.shape == (expected_test, FEATURE_COUNT)

        # Disjoint index sets (zero index leakage)
        train_idx_set = set(ds.train_indices)
        test_idx_set = set(ds.test_indices)
        assert len(train_idx_set.intersection(test_idx_set)) == 0

        # Disjoint sample IDs (zero ID leakage)
        train_ids = set(ds.sample_ids[ds.train_indices])
        test_ids = set(ds.sample_ids[ds.test_indices])
        assert len(train_ids.intersection(test_ids)) == 0

        # Both train and test must contain all classes
        assert len(np.unique(ds.y_train)) == len(small_config.modulations)
        assert len(np.unique(ds.y_test)) == len(small_config.modulations)

    def test_reproducibility_with_seed(self, small_config):
        ds1 = generate_modulation_dataset(small_config)
        ds2 = generate_modulation_dataset(small_config)

        # Identical seed produces bit-for-bit identical feature matrices
        np.testing.assert_array_equal(ds1.X, ds2.X)
        np.testing.assert_array_equal(ds1.y, ds2.y)
        np.testing.assert_array_equal(ds1.target_snr, ds2.target_snr)
        np.testing.assert_array_equal(ds1.measured_snr, ds2.measured_snr)

        # Different seed produces different features
        diff_config = DatasetConfig(
            dataset_version=small_config.dataset_version,
            modulations=small_config.modulations,
            snr_min_db=small_config.snr_min_db,
            snr_max_db=small_config.snr_max_db,
            snr_step_db=small_config.snr_step_db,
            samples_per_condition=small_config.samples_per_condition,
            sample_count=small_config.sample_count,
            sample_rate=small_config.sample_rate,
            seed=999,
            test_ratio=small_config.test_ratio,
        )
        ds3 = generate_modulation_dataset(diff_config)
        assert not np.array_equal(ds1.X, ds3.X)

    def test_feature_order_contract(self, small_config):
        ds = generate_modulation_dataset(small_config)
        # Check that feature names match Phase 2 contract exactly
        assert len(FEATURE_NAMES) == 23
        assert ds.X.shape[1] == 23

    def test_save_and_validate_dataset_directory(self, small_config, tmp_path):
        ds = generate_modulation_dataset(small_config)
        saved_paths = save_dataset_artifacts(ds, tmp_path)

        # Check all expected files exist
        assert (tmp_path / "modulation_dataset.npz").exists()
        assert (tmp_path / "train_test_split.npz").exists()
        assert (tmp_path / "metadata.csv").exists()
        assert (tmp_path / "feature_names.json").exists()
        assert (tmp_path / "label_map.json").exists()
        assert (tmp_path / "dataset_info.json").exists()
        assert (tmp_path / "dataset_statistics.json").exists()

        # Run 17-point validation check
        is_valid, issues = validate_dataset_directory(tmp_path)
        assert is_valid, f"Validation failed with issues: {issues}"
        assert len(issues) == 0

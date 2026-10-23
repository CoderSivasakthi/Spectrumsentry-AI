"""Unit tests for the novelty detector (corrected report fix #8).

Covers fitting, in-distribution vs out-of-distribution verdicts, persistence
round-trips, and the module-level ``novelty_check`` convenience wrapper.
"""

import numpy as np
import pytest

from backend.app.ml.anomaly import NoveltyDetector, novelty_check


def _make_reference_features(n: int = 400, seed: int = 42) -> np.ndarray:
    """Synthetic in-distribution cluster resembling 6-dim clean cumulant features."""
    rng = np.random.default_rng(seed)
    centers = np.array(
        [
            [1.0, 2.0, 2.0, -2.0, 1.0, 0.02],   # BPSK-like
            [0.0, 1.0, 0.0, -1.0, 1.0, 0.02],   # QPSK-like
            [0.0, 0.65, 0.0, -0.66, 0.94, 0.32],  # 16-QAM-like
        ]
    )
    pick = rng.integers(0, 3, size=n)
    return centers[pick] + 0.05 * rng.standard_normal((n, centers.shape[1]))


class TestNoveltyDetector:
    """Core detector behavior."""

    def test_requires_fit_before_predict(self):
        detector = NoveltyDetector()
        with pytest.raises(RuntimeError):
            detector.predict(np.zeros((2, 6)))

    def test_rejects_bad_fit_input(self):
        detector = NoveltyDetector()
        with pytest.raises(ValueError):
            detector.fit(np.zeros((0, 6)))
        with pytest.raises(ValueError):
            detector.fit(np.zeros((5, 6)) + np.nan)
        with pytest.raises(ValueError):
            detector.fit(np.zeros(6))

    def test_in_distribution_is_not_outlier(self):
        detector = NoveltyDetector().fit(_make_reference_features())
        test = _make_reference_features(n=100, seed=1234)
        flags = detector.predict(test)

        assert flags.dtype == bool
        assert np.mean(flags) < 0.1  # overwhelmingly in-distribution

    def test_out_of_distribution_is_outlier(self):
        detector = NoveltyDetector().fit(_make_reference_features())
        # A supported set has no class with amplitude_std ~ 1.5 & c40 ~ 0.2
        novel = np.array(
            [
                [0.2, 0.1, 0.1, -0.1, 1.5, 1.5],
                [1.8, 0.4, 0.0, -0.4, 0.4, 1.2],
                [0.0, 0.0, 0.0, -0.05, 0.5, 0.9],
            ],
            dtype=np.float32,
        )
        flags = detector.predict(novel)

        assert np.all(flags)

    def test_score_novelty_bounds_and_ordering(self):
        detector = NoveltyDetector().fit(_make_reference_features())
        inlier = _make_reference_features(n=1, seed=7)[0:1]
        outlier = np.array([[0.2, 0.1, 0.1, -0.1, 1.5, 1.5]], dtype=np.float32)

        s_in = detector.score_novelty(inlier)[0]
        s_out = detector.score_novelty(outlier)[0]

        assert 0.0 <= s_in <= 1.0 and 0.0 <= s_out <= 1.0
        assert s_out > s_in

    def test_vector_input_and_feature_count_mismatch(self):
        detector = NoveltyDetector().fit(_make_reference_features())
        vec = _make_reference_features(n=1, seed=8)[0]
        assert detector.predict(vec).shape == (1,)

        with pytest.raises(ValueError):
            detector.predict(np.zeros((1, 5), dtype=np.float32))

    def test_metadata_stored_on_fit(self):
        detector = NoveltyDetector().fit(
            _make_reference_features(), metadata={"feature_set": "cumulant_v2"}
        )
        assert detector.is_trained
        assert detector.feature_count == 6
        assert detector.n_training_samples == 400
        assert detector.fit_metadata.get("feature_set") == "cumulant_v2"


class TestNoveltyDetectorPersistence:
    """save/load round-trip."""

    def test_save_and_load_round_trip(self, tmp_path):
        detector = NoveltyDetector().fit(
            _make_reference_features(), metadata={"feature_set": "cumulant_v2"}
        )
        path = detector.save(tmp_path / "novelty_detector.joblib")

        loaded = NoveltyDetector.load(path)
        sample = _make_reference_features(n=5, seed=15)
        assert np.array_equal(detector.predict(sample), loaded.predict(sample))
        assert loaded.feature_count == 6
        assert loaded.n_training_samples == 400
        assert loaded.fit_metadata.get("feature_set") == "cumulant_v2"

    def test_refuses_to_save_untrained(self, tmp_path):
        with pytest.raises(RuntimeError):
            NoveltyDetector().save(tmp_path / "unused.joblib")

    def test_load_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            NoveltyDetector.load(tmp_path / "missing.joblib")

    def test_load_invalid_payload_raises(self, tmp_path):
        import joblib

        path = tmp_path / "bogus.joblib"
        joblib.dump({"not": "a detector"}, path)
        with pytest.raises(ValueError):
            NoveltyDetector.load(path)


class TestNoveltyCheckConvenience:
    """Module-level ``novelty_check`` used by the predictor."""

    def test_returns_none_when_no_detector_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.app.ml.anomaly.DEFAULT_NOVELTY_DETECTOR_PATH",
            tmp_path / "absent.joblib",
        )
        assert novelty_check(_make_reference_features(n=1, seed=3)[0]) is None

        # Explicit path also short-circuits
        assert novelty_check(
            _make_reference_features(n=1, seed=3)[0],
            detector_path=tmp_path / "absent.joblib",
        ) is None

    def test_returns_verdict_with_trained_detector(self, tmp_path):
        path = NoveltyDetector().fit(_make_reference_features()).save(
            tmp_path / "nd.joblib"
        )
        result = novelty_check(
            _make_reference_features(n=1, seed=5)[0], detector_path=path
        )
        assert isinstance(result, dict)
        assert isinstance(result["is_outlier"], bool)
        assert 0.0 <= result["novelty_score"] <= 1.0

    def test_incompatible_feature_vector_returns_none(self, tmp_path):
        path = NoveltyDetector().fit(_make_reference_features()).save(
            tmp_path / "nd.joblib"
        )
        assert novelty_check(np.zeros(4, dtype=np.float32), detector_path=path) is None

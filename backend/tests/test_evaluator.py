"""Unit tests for Phase 4 model evaluation, confusion matrix, and SNR performance analysis."""

import numpy as np
import pytest

from backend.app.ml.evaluator import (
    compute_confusion_matrix,
    evaluate_performance_across_snr,
    evaluate_predictions,
    generate_classification_report_text,
)


class TestEvaluator:
    """Test suite for evaluation metrics, confusion matrices, and SNR stratification."""

    def test_evaluate_predictions_perfect_case(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 1, 1, 2, 2])
        y_prob = np.array([
            [0.9, 0.05, 0.05],
            [0.85, 0.1, 0.05],
            [0.05, 0.9, 0.05],
            [0.1, 0.8, 0.1],
            [0.02, 0.08, 0.9],
            [0.05, 0.05, 0.9],
        ])

        res = evaluate_predictions(y_true, y_pred, y_prob)
        assert res["accuracy"] == 1.0
        assert res["macro_f1"] == 1.0
        assert res["weighted_f1"] == 1.0
        assert res["total_samples"] == 6

        # Per-class checks
        for cls in ["BPSK", "QPSK", "16-QAM"]:
            assert res["per_class"][cls]["f1_score"] == 1.0
            assert res["per_class"][cls]["support"] == 2

        # Confidence checks
        assert res["confidence"]["mean_confidence"] > 0.8
        assert res["confidence"]["min_confidence"] >= 0.8

    def test_evaluate_predictions_with_errors(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 1, 1, 1, 2, 0])  # 2 errors out of 6

        res = evaluate_predictions(y_true, y_pred)
        assert np.isclose(res["accuracy"], 4 / 6, atol=1e-3)
        assert res["macro_precision"] < 1.0
        assert res["macro_recall"] < 1.0

    def test_compute_confusion_matrix(self):
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 1, 2, 2, 2])

        cm_res = compute_confusion_matrix(y_true, y_pred)
        raw = np.array(cm_res["raw_matrix"])
        norm = np.array(cm_res["normalized_matrix"])

        assert raw.shape == (3, 3)
        assert norm.shape == (3, 3)
        # Class 0: both predicted as 0 -> [2, 0, 0]
        np.testing.assert_array_equal(raw[0], [2, 0, 0])
        np.testing.assert_allclose(norm[0], [1.0, 0.0, 0.0])
        # Class 1: one as 1, one as 2 -> [0, 1, 1]
        np.testing.assert_array_equal(raw[1], [0, 1, 1])
        np.testing.assert_allclose(norm[1], [0.0, 0.5, 0.5])

    def test_evaluate_performance_across_snr(self):
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 2, 0, 0, 2])  # 1 error at 0 dB
        target_snrs = np.array([10.0, 10.0, 10.0, 0.0, 0.0, 0.0])

        snr_eval = evaluate_performance_across_snr(y_true, y_pred, target_snrs)
        assert snr_eval["snr_levels"] == [0, 10]
        records = snr_eval["records"]
        assert len(records) == 2

        # 0 dB: 2 correct out of 3 -> accuracy ~ 0.6667
        rec_0 = [r for r in records if r["snr_db"] == 0][0]
        assert np.isclose(rec_0["accuracy"], 2 / 3, atol=1e-3)

        # 10 dB: 3 correct out of 3 -> accuracy = 1.0
        rec_10 = [r for r in records if r["snr_db"] == 10][0]
        assert rec_10["accuracy"] == 1.0

    def test_generate_classification_report_text(self):
        y_true = np.array([0, 1, 2])
        y_pred = np.array([0, 1, 2])
        res = evaluate_predictions(y_true, y_pred)
        text = generate_classification_report_text(res)
        assert "SPECTRUMSENTRY AI" in text
        assert "Overall Accuracy" in text
        assert "BPSK" in text
        assert "QPSK" in text
        assert "16-QAM" in text

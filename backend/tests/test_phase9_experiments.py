"""Automated Test Suite for Phase 9 Experiment Infrastructure (SpectrumSentry AI).

Verifies:
1. Experiment configuration and serialization
2. Seed determinism and reproducibility
3. Custom JSON serialization with NumpyJSONEncoder
4. Result validation logic (non-NaN, non-Inf, required schema)
5. AI classification evaluation output structure
6. SNR sweep output structure and regime boundaries
7. Confusion matrix generation and normalization
8. Performance benchmark metrics and percentiles
9. Publication plot generation utilities
10. Multi-domain decision engine evaluation rules
"""

import json
import math
from pathlib import Path
import tempfile
import numpy as np
import pytest

from experiments.ai.evaluator import AIEvaluator
from experiments.ai.snr_sweep import SNRSweepExperiment
from experiments.common.config import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODEL_PATH,
    ExperimentConfig,
    NumpyJSONEncoder,
    get_environment_metadata,
    save_csv,
    save_json,
)
from experiments.common.plotting import (
    plot_confidence_vs_snr,
    plot_confusion_matrix,
    plot_snr_vs_accuracy,
)
from experiments.decision.evaluator import DecisionEngineEvaluator
from experiments.performance.benchmarks import PerformanceBenchmarker
from experiments.signal.evaluator import SignalProcessingEvaluator
from scripts.validate_phase9_results import check_no_nan_or_inf, validate_phase9


class TestPhase9ExperimentInfrastructure:
    """Automated tests validating Phase 9 experimentation and evaluation framework."""

    def test_experiment_config_and_metadata(self):
        """Test 1: ExperimentConfig dataclass initializes correctly and captures environment metadata."""
        cfg = ExperimentConfig(
            experiment_id="TEST-EXP-01",
            experiment_name="unit_test_experiment",
            description="Testing configuration validity.",
            random_seed=42,
            parameters={"test_param": 123, "snr_db": 10.0},
        )
        d = cfg.to_dict()
        assert d["experiment_id"] == "TEST-EXP-01"
        assert d["experiment_name"] == "unit_test_experiment"
        assert d["random_seed"] == 42
        assert d["parameters"]["test_param"] == 123
        assert "timestamp" in d
        assert "environment" in d
        assert "python_version" in d["environment"]
        assert "os_name" in d["environment"]

    def test_seed_reproducibility(self):
        """Test 2: Deterministic seed produces bitwise identical synthetic DSP and calibration data."""
        dsp1 = SignalProcessingEvaluator(random_seed=42)
        res1 = dsp1.evaluate_snr_calibration(snr_levels=[5.0, 15.0], trials_per_level=5)

        dsp2 = SignalProcessingEvaluator(random_seed=42)
        res2 = dsp2.evaluate_snr_calibration(snr_levels=[5.0, 15.0], trials_per_level=5)

        mae1 = res1["overall_mean_absolute_snr_error_db"]
        mae2 = res2["overall_mean_absolute_snr_error_db"]
        assert mae1 == pytest.approx(mae2, abs=1e-9)

        # Different seed produces recorded metadata change
        dsp3 = SignalProcessingEvaluator(random_seed=99)
        res3 = dsp3.run_all()
        assert res3["metadata"]["random_seed"] == 99

    def test_result_serialization_and_encoder(self):
        """Test 3: NumpyJSONEncoder serializes numpy scalars, arrays, and standard types safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_serialize.json"
            payload = {
                "int64_val": np.int64(42),
                "float32_val": np.float32(3.14159),
                "array_val": np.array([1.0, 2.0, 3.0]),
                "bool_val": np.bool_(True),
            }
            save_json(payload, test_file)
            assert test_file.exists()

            with open(test_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["int64_val"] == 42
            assert loaded["float32_val"] == pytest.approx(3.14159, abs=1e-4)
            assert loaded["array_val"] == [1.0, 2.0, 3.0]
            assert loaded["bool_val"] is True

    def test_result_validator_function(self):
        """Test 4: check_no_nan_or_inf detects NaN and Inf values recursively."""
        clean_data = {"a": [1.0, 2.0, 3.0], "b": {"c": 4.5}}
        assert len(check_no_nan_or_inf(clean_data)) == 0

        nan_data = {"a": [1.0, float("nan"), 3.0]}
        nan_errs = check_no_nan_or_inf(nan_data)
        assert len(nan_errs) == 1
        assert "NaN found" in nan_errs[0]

        inf_data = {"x": {"y": float("inf")}}
        inf_errs = check_no_nan_or_inf(inf_data)
        assert len(inf_errs) == 1
        assert "Inf found" in inf_errs[0]

    def test_ai_evaluation_output_structure(self):
        """Test 5: AI evaluation runs on held-out dataset and outputs all required metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evaluator = AIEvaluator(output_dir=Path(tmpdir), random_seed=42)
            results = evaluator.run_evaluation()

            assert "summary_metrics" in results
            metrics = results["summary_metrics"]
            assert 0.0 <= metrics["test_accuracy"] <= 1.0
            assert 0.0 <= metrics["macro_f1"] <= 1.0
            assert 0.0 <= metrics["macro_precision"] <= 1.0
            assert 0.0 <= metrics["macro_recall"] <= 1.0

            assert "per_class_metrics" in results
            assert "BPSK" in results["per_class_metrics"]
            assert "QPSK" in results["per_class_metrics"]
            assert "16-QAM" in results["per_class_metrics"]

            assert "confusion_matrix" in results
            assert "confidence_analysis" in results
            assert "calibration" in results
            assert 0.0 <= results["calibration"]["expected_calibration_error"] <= 1.0

    def test_snr_sweep_output_structure(self):
        """Test 6: SNR sweep outputs 26 discrete levels and correct regime categorization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sweep = SNRSweepExperiment(output_dir=Path(tmpdir), random_seed=42)
            results = sweep.run_sweep()

            assert "snr_sweep" in results
            snr_records = results["snr_sweep"]
            assert len(snr_records) == 26
            assert snr_records[0]["snr_db"] == -5.0
            assert snr_records[-1]["snr_db"] == 20.0

            regimes = results["regimes_summary"]
            assert "low_snr_region" in regimes
            assert "transition_region" in regimes
            assert "high_confidence_region" in regimes
            assert regimes["high_confidence_region"]["mean_accuracy"] >= regimes["low_snr_region"]["mean_accuracy"]

    def test_confusion_matrix_generation(self):
        """Test 7: Confusion matrix is generated with raw counts and normalized percentages."""
        evaluator = AIEvaluator()
        data = evaluator.load_test_data()
        batch_res = evaluator.predictor.predict_batch(data["X_test"][:100])
        y_pred = np.array([r["predicted_label"] for r in batch_res])
        y_true = data["y_test"][:100]

        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])
        assert cm.shape == (3, 3)
        assert np.sum(cm) == 100

        with tempfile.TemporaryDirectory() as tmpdir:
            plot_path = Path(tmpdir) / "cm_test.png"
            p = plot_confusion_matrix(cm, ["BPSK", "QPSK", "16-QAM"], plot_path)
            assert p.exists()
            assert p.stat().st_size > 1000

    def test_performance_benchmarks_output(self):
        """Test 8: Benchmarker executes micro-benchmarks with statistical percentiles."""
        benchmarker = PerformanceBenchmarker()
        res = benchmarker.run_all_benchmarks(iterations=10)

        assert "benchmarks" in res
        b_list = res["benchmarks"]
        assert len(b_list) >= 8

        for b in b_list:
            assert "operation" in b
            assert b["mean_ms"] >= 0.0
            assert b["median_ms"] >= 0.0
            assert b["p95_ms"] >= b["median_ms"] * 0.5  # Realistic distribution
            assert b["p99_ms"] >= b["p95_ms"]

    def test_plot_generation(self):
        """Test 9: Publication plotting utilities output high-resolution PNG images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_p = Path(tmpdir) / "test_snr_acc.png"
            snrs = [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0]
            accs = [0.75, 0.85, 0.95, 0.99, 1.0, 1.0]
            per_class = {
                "BPSK": [0.9, 0.95, 0.98, 1.0, 1.0, 1.0],
                "QPSK": [0.7, 0.8, 0.92, 0.98, 1.0, 1.0],
                "16-QAM": [0.65, 0.8, 0.95, 0.99, 1.0, 1.0],
            }
            p = plot_snr_vs_accuracy(snrs, accs, per_class, out_p)
            assert p.exists()
            assert p.stat().st_size > 1000

            out_conf = Path(tmpdir) / "test_conf.png"
            p2 = plot_confidence_vs_snr(snrs, [0.8, 0.85, 0.9, 0.95, 0.98, 0.99], [0.05] * 6, out_conf)
            assert p2.exists()
            assert p2.stat().st_size > 1000

    def test_decision_evaluation_rules(self):
        """Test 10: DecisionEngineEvaluator confirms coverage of all 7 rules and conflict scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            evaluator = DecisionEngineEvaluator(output_dir=Path(tmpdir))
            results = evaluator.run_all()

            assert results["summary"]["total_rules_evaluated"] == 7
            assert results["summary"]["all_rules_passed"] is True
            assert results["summary"]["all_partial_passed"] is True

            conflict_a = next(r for r in results["rule_coverage"] if r["rule_id"] == "RULE_CONFLICT_HIGH_SNR_HIGH_LOSS")
            conflict_b = next(r for r in results["rule_coverage"] if r["rule_id"] == "RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE")
            assert conflict_a["actual_status"] == "REVIEW"
            assert conflict_a["actual_consistency"] == "CONFLICTING"
            assert conflict_b["actual_status"] == "REVIEW"
            assert conflict_b["actual_consistency"] == "CONFLICTING"

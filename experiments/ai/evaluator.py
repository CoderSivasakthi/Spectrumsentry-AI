"""AI Modulation Classification Evaluation Module for Phase 9.

Evaluates the production Phase 4 MLPClassifier on held-out test data,
calculating overall and per-class accuracy, precision, recall, F1-score,
confusion matrix, and empirical confidence / calibration statistics.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from backend.app.ml.dataset import INVERSE_LABEL_MAP, LABEL_MAP
from backend.app.ml.predictor import ModulationPredictor
from experiments.common.config import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODEL_PATH,
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_json,
)
from experiments.common.plotting import plot_confusion_matrix


class AIEvaluator:
    """Scientific evaluation suite for the modulation classification engine."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        dataset_dir: Path = DEFAULT_DATASET_DIR,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.model_path = Path(model_path)
        self.dataset_dir = Path(dataset_dir)
        self.output_dir = Path(output_dir)
        self.ai_output_dir = self.output_dir / "ai"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed

        # Initialize production predictor
        self.predictor = ModulationPredictor(model_path=self.model_path)
        if not self.predictor.pipeline:
            raise RuntimeError(f"Failed to load production model from {self.model_path}")

        # Class labels
        self.class_indices = [0, 1, 2]
        self.class_names = [INVERSE_LABEL_MAP[i] for i in self.class_indices]

    def load_test_data(self) -> Dict[str, np.ndarray]:
        """Load Phase 3 held-out test split."""
        split_path = self.dataset_dir / "train_test_split.npz"
        if not split_path.exists():
            raise FileNotFoundError(f"Test split not found at {split_path}")
        data = np.load(split_path)
        return {
            "X_test": data["X_test"],
            "y_test": data["y_test"],
            "target_snr_test": data["target_snr_test"],
            "measured_snr_test": data["measured_snr_test"],
        }

    def compute_calibration_ece(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        confidences: np.ndarray,
        num_bins: int = 10,
    ) -> Dict[str, Any]:
        """Compute Expected Calibration Error (ECE) and reliability bin statistics."""
        bin_boundaries = np.linspace(0.0, 1.0, num_bins + 1)
        bin_lowers = bin_boundaries[:-1]
        bin_uppers = bin_boundaries[1:]

        accuracies = (y_true == y_pred).astype(float)
        ece = 0.0
        bin_details = []

        for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
            in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
            prop_in_bin = float(np.mean(in_bin))

            if prop_in_bin > 0:
                accuracy_in_bin = float(np.mean(accuracies[in_bin]))
                avg_confidence_in_bin = float(np.mean(confidences[in_bin]))
                ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin
                bin_details.append({
                    "bin_range": [round(float(bin_lower), 2), round(float(bin_upper), 2)],
                    "sample_count": int(np.sum(in_bin)),
                    "accuracy": round(accuracy_in_bin, 4),
                    "confidence": round(avg_confidence_in_bin, 4),
                })
            else:
                bin_details.append({
                    "bin_range": [round(float(bin_lower), 2), round(float(bin_upper), 2)],
                    "sample_count": 0,
                    "accuracy": 0.0,
                    "confidence": 0.0,
                })

        return {
            "expected_calibration_error": round(float(ece), 4),
            "num_bins": num_bins,
            "bins": bin_details,
        }

    def run_evaluation(self) -> Dict[str, Any]:
        """Execute complete AI classification evaluation and produce reports & plots."""
        data = self.load_test_data()
        X_test = data["X_test"]
        y_test = data["y_test"]

        # Predict using production model pipeline
        batch_result = self.predictor.predict_batch(X_test)
        y_pred = np.array([r["predicted_label"] for r in batch_result])
        confidences = np.array([r["confidence"] for r in batch_result])

        # Core Metrics
        acc = float(accuracy_score(y_test, y_pred))
        macro_p = float(precision_score(y_test, y_pred, average="macro"))
        macro_r = float(recall_score(y_test, y_pred, average="macro"))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
        weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))

        # Per-class metrics
        precisions = precision_score(y_test, y_pred, average=None)
        recalls = recall_score(y_test, y_pred, average=None)
        f1s = f1_score(y_test, y_pred, average=None)

        per_class = {}
        for idx, cls_name in enumerate(self.class_names):
            class_mask = y_test == idx
            class_conf = float(np.mean(confidences[class_mask])) if np.any(class_mask) else 0.0
            per_class[cls_name] = {
                "class_index": idx,
                "precision": round(float(precisions[idx]), 4),
                "recall": round(float(recalls[idx]), 4),
                "f1_score": round(float(f1s[idx]), 4),
                "mean_confidence": round(class_conf, 4),
                "support": int(np.sum(class_mask)),
            }

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred, labels=self.class_indices)
        cm_norm = cm.astype(float) / cm.sum(axis=1)[:, np.newaxis]

        # Confidence Analysis: correct vs incorrect
        is_correct = (y_test == y_pred)
        correct_confs = confidences[is_correct]
        incorrect_confs = confidences[~is_correct]

        confidence_analysis = {
            "overall_mean_confidence": round(float(np.mean(confidences)), 4),
            "overall_median_confidence": round(float(np.median(confidences)), 4),
            "overall_std_confidence": round(float(np.std(confidences)), 4),
            "correct_predictions": {
                "count": int(np.sum(is_correct)),
                "mean_confidence": round(float(np.mean(correct_confs)), 4) if len(correct_confs) > 0 else 0.0,
                "median_confidence": round(float(np.median(correct_confs)), 4) if len(correct_confs) > 0 else 0.0,
                "std_confidence": round(float(np.std(correct_confs)), 4) if len(correct_confs) > 0 else 0.0,
            },
            "incorrect_predictions": {
                "count": int(np.sum(~is_correct)),
                "mean_confidence": round(float(np.mean(incorrect_confs)), 4) if len(incorrect_confs) > 0 else 0.0,
                "median_confidence": round(float(np.median(incorrect_confs)), 4) if len(incorrect_confs) > 0 else 0.0,
                "std_confidence": round(float(np.std(incorrect_confs)), 4) if len(incorrect_confs) > 0 else 0.0,
            },
        }

        # Calibration ECE
        calibration = self.compute_calibration_ece(y_test, y_pred, confidences)

        # Build Experiment Config & Metadata
        cfg = ExperimentConfig(
            experiment_id="EXP-AI-01",
            experiment_name="ai_classification_evaluation",
            description="Complete scientific evaluation of Phase 4 modulation classifier on held-out test data.",
            random_seed=self.random_seed,
            parameters={
                "test_samples": len(y_test),
                "feature_count": X_test.shape[1],
                "classes": self.class_names,
            },
        )

        results = {
            "metadata": cfg.to_dict(),
            "summary_metrics": {
                "test_accuracy": round(acc, 4),
                "macro_precision": round(macro_p, 4),
                "macro_recall": round(macro_r, 4),
                "macro_f1": round(macro_f1, 4),
                "weighted_f1": round(weighted_f1, 4),
                "total_test_samples": len(y_test),
            },
            "per_class_metrics": per_class,
            "confusion_matrix": {
                "classes": self.class_names,
                "matrix_raw": cm.tolist(),
                "matrix_normalized": [[round(float(v), 4) for v in row] for row in cm_norm],
            },
            "confidence_analysis": confidence_analysis,
            "calibration": calibration,
        }

        # Save structured results
        self.ai_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(results, self.ai_output_dir / "classification_metrics.json")
        save_json(results["confusion_matrix"], self.ai_output_dir / "confusion_matrix.json")
        save_json(results["confidence_analysis"], self.ai_output_dir / "confidence_analysis.json")

        # Save plot
        plot_confusion_matrix(
            cm=cm,
            class_names=self.class_names,
            output_path=self.plots_dir / "confusion_matrix.png",
            title=f"Modulation Classification Confusion Matrix (Acc: {acc:.2%})",
            normalize=True,
        )

        return results

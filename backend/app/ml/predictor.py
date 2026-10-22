"""Production prediction engine for modulation classification.

Loads the trained StandardScaler + MLPClassifier pipeline, validates incoming feature vectors,
performs single and batch inferences with latency measurement, and returns structured class probabilities.
"""

import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import numpy as np
from sklearn.pipeline import Pipeline

from backend.app.ml.dataset import INVERSE_LABEL_MAP, LABEL_MAP
from backend.app.ml.trainer import load_trained_model
from backend.app.signal_processing import FEATURE_COUNT, FEATURE_NAMES

DEFAULT_MODEL_PATH = Path("backend/models/modulation_mlp_v1.joblib")
DEFAULT_METADATA_PATH = Path("backend/models/model_metadata.json")


class ModulationPredictor:
    """Modulation classification inference engine."""

    def __init__(
        self,
        model_path: Union[str, Path] = DEFAULT_MODEL_PATH,
        metadata_path: Optional[Union[str, Path]] = DEFAULT_METADATA_PATH,
    ):
        self.model_path = Path(model_path)
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self.pipeline: Optional[Pipeline] = None
        self.metadata: Dict[str, Any] = {}
        self.model_version: str = "v1.0"

        # Load model pipeline on initialization if file exists
        if self.model_path.exists():
            self.load()

    def load(self) -> None:
        """Load serialized model pipeline and optional metadata."""
        self.pipeline = load_trained_model(self.model_path)
        if self.metadata_path and self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                    self.model_version = self.metadata.get("model_version", "v1.0")
            except Exception:
                self.metadata = {}

    def _validate_input_features(self, X: np.ndarray) -> np.ndarray:
        """Validate feature matrix dimensions and numerical integrity.
        
        Args:
            X: Array of features.

        Returns:
            Validated 2D float32 array of shape (N, 23).

        Raises:
            ValueError: If array dimensions, feature count, or values are invalid.
        """
        arr = np.asarray(X, dtype=np.float32)

        if arr.ndim == 1:
            if arr.shape[0] != FEATURE_COUNT:
                raise ValueError(
                    f"Expected single feature vector of length {FEATURE_COUNT}, got {arr.shape[0]}"
                )
            arr = arr.reshape(1, -1)
        elif arr.ndim == 2:
            if arr.shape[1] != FEATURE_COUNT:
                raise ValueError(
                    f"Expected feature matrix with {FEATURE_COUNT} columns, got {arr.shape[1]}"
                )
        else:
            raise ValueError(f"Feature array must be 1D or 2D, got dimension {arr.ndim}")

        if arr.shape[0] == 0:
            raise ValueError("Feature matrix cannot be empty")

        if not np.all(np.isfinite(arr)):
            raise ValueError("Input feature vector contains NaN or Infinite values")

        return arr

    def predict_single(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        """Perform classification inference on a single 23-feature vector.
        
        Args:
            feature_vector: 1D array of shape (23,) or 2D array of shape (1, 23).

        Returns:
            Structured prediction dictionary containing:
            - predicted_modulation: Canonical name (e.g. 'QPSK')
            - predicted_label: Integer class index (0, 1, or 2)
            - confidence: Maximum class probability [0.0 - 1.0]
            - class_probabilities: Dict mapping modulation names to probabilities
            - inference_time_ms: Measured latency in milliseconds
            - model_version: Model release identifier
        """
        if self.pipeline is None:
            raise RuntimeError("Model pipeline is not loaded. Call load() before predicting.")

        X_valid = self._validate_input_features(feature_vector)

        t_start = time.perf_counter()
        probs = self.pipeline.predict_proba(X_valid)[0]
        pred_label = int(np.argmax(probs))
        latency_ms = (time.perf_counter() - t_start) * 1000.0

        confidence = float(probs[pred_label])
        predicted_mod = INVERSE_LABEL_MAP.get(pred_label, f"UNKNOWN_{pred_label}")

        class_probabilities = {
            INVERSE_LABEL_MAP[i]: round(float(probs[i]), 4)
            for i in range(len(probs))
        }

        return {
            "predicted_modulation": predicted_mod,
            "predicted_label": pred_label,
            "confidence": round(confidence, 4),
            "class_probabilities": class_probabilities,
            "inference_time_ms": round(latency_ms, 3),
            "model_version": self.model_version,
        }

    def predict_batch(self, feature_matrix: np.ndarray) -> List[Dict[str, Any]]:
        """Perform batch classification inference.
        
        Args:
            feature_matrix: 2D array of shape (N, 23).

        Returns:
            List of prediction dictionaries for each input sample.
        """
        if self.pipeline is None:
            raise RuntimeError("Model pipeline is not loaded. Call load() before predicting.")

        X_valid = self._validate_input_features(feature_matrix)
        n_samples = len(X_valid)

        t_start = time.perf_counter()
        probs = self.pipeline.predict_proba(X_valid)
        pred_labels = np.argmax(probs, axis=1)
        total_latency_ms = (time.perf_counter() - t_start) * 1000.0
        avg_latency_ms = total_latency_ms / max(1, n_samples)

        results = []
        for i in range(n_samples):
            label = int(pred_labels[i])
            conf = float(probs[i, label])
            mod_name = INVERSE_LABEL_MAP.get(label, f"UNKNOWN_{label}")
            class_probs = {
                INVERSE_LABEL_MAP[k]: round(float(probs[i, k]), 4)
                for k in range(probs.shape[1])
            }
            results.append({
                "predicted_modulation": mod_name,
                "predicted_label": label,
                "confidence": round(conf, 4),
                "class_probabilities": class_probs,
                "inference_time_ms": round(avg_latency_ms, 3),
                "model_version": self.model_version,
            })

        return results

    def benchmark(
        self,
        num_single_runs: int = 200,
        batch_size: int = 128,
        num_batch_runs: int = 50,
    ) -> Dict[str, Any]:
        """Benchmark single-example latency and batch throughput.
        
        Args:
            num_single_runs: Iterations for single-example latency benchmark.
            batch_size: Size of batch for throughput benchmark.
            num_batch_runs: Number of batch runs.

        Returns:
            Dictionary containing average, median, p95 latencies and batch throughput.
        """
        if self.pipeline is None:
            raise RuntimeError("Model pipeline is not loaded. Call load() before benchmarking.")

        rng = np.random.default_rng(42)
        single_x = rng.standard_normal((1, FEATURE_COUNT), dtype=np.float32)
        batch_x = rng.standard_normal((batch_size, FEATURE_COUNT), dtype=np.float32)

        # Warmup
        for _ in range(10):
            self.pipeline.predict_proba(single_x)
            self.pipeline.predict_proba(batch_x)

        # Single-example benchmark
        single_latencies = []
        for _ in range(num_single_runs):
            t0 = time.perf_counter()
            self.pipeline.predict_proba(single_x)
            single_latencies.append((time.perf_counter() - t0) * 1000.0)

        single_latencies_arr = np.array(single_latencies)

        # Batch benchmark
        batch_times = []
        for _ in range(num_batch_runs):
            t0 = time.perf_counter()
            self.pipeline.predict_proba(batch_x)
            batch_times.append(time.perf_counter() - t0)

        total_batch_samples = batch_size * num_batch_runs
        total_batch_time = sum(batch_times)
        throughput = total_batch_samples / max(1e-6, total_batch_time)

        return {
            "single_latency_ms": {
                "mean": round(float(np.mean(single_latencies_arr)), 3),
                "median": round(float(np.median(single_latencies_arr)), 3),
                "p95": round(float(np.percentile(single_latencies_arr, 95)), 3),
                "min": round(float(np.min(single_latencies_arr)), 3),
                "max": round(float(np.max(single_latencies_arr)), 3),
            },
            "batch_benchmark": {
                "batch_size": batch_size,
                "throughput_samples_per_sec": round(throughput, 1),
                "mean_batch_time_ms": round(float(np.mean(batch_times)) * 1000.0, 3),
            },
        }


# Module-level convenience functions
_global_predictor: Optional[ModulationPredictor] = None


def get_predictor(model_path: Path = DEFAULT_MODEL_PATH) -> ModulationPredictor:
    """Retrieve or initialize singleton ModulationPredictor instance."""
    global _global_predictor
    if _global_predictor is None or _global_predictor.model_path != model_path:
        _global_predictor = ModulationPredictor(model_path=model_path)
    return _global_predictor


def predict_single(feature_vector: np.ndarray, model_path: Path = DEFAULT_MODEL_PATH) -> Dict[str, Any]:
    """Convenience function to predict a single feature vector."""
    predictor = get_predictor(model_path)
    return predictor.predict_single(feature_vector)


def predict_batch(feature_matrix: np.ndarray, model_path: Path = DEFAULT_MODEL_PATH) -> List[Dict[str, Any]]:
    """Convenience function to predict a batch of feature vectors."""
    predictor = get_predictor(model_path)
    return predictor.predict_batch(feature_matrix)

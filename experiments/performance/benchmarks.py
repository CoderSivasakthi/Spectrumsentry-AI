"""Component Performance Benchmarking Module for Phase 9.

Measures micro-benchmarks across critical algorithmic subsystems:
    1. Signal Generation (BPSK, QPSK, 16-QAM)
    2. AWGN Noise Modeling
    3. FFT & Spectral Transformation
    4. 23-Feature Extraction
    5. ML Single Prediction
    6. ML Batch Prediction (16, 64, 256 vectors)
    7. Decision Engine Evaluation
    8. Snapshot Serialization
"""

from pathlib import Path
import time
from typing import Any, Dict, List
import matplotlib.pyplot as plt
import numpy as np

from backend.app.decision.engine import DecisionEngine
from backend.app.ml.predictor import ModulationPredictor
from backend.app.monitoring import UnifiedMonitoringManager
from backend.app.schemas.decision import DecisionInput, SignalEvidence, CommunicationEvidence
from backend.app.signal_processing import add_awgn, compute_fft, extract_features, generate_signal
from experiments.common.config import (
    DEFAULT_MODEL_PATH,
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_csv,
    save_json,
)
from experiments.common.plotting import COLOR_PRIMARY, COLOR_SECONDARY


class PerformanceBenchmarker:
    """Micro-benchmarking suite measuring latency distributions and throughputs."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.perf_output_dir = self.output_dir / "performance"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed

        self.predictor = ModulationPredictor(model_path=self.model_path)
        self.decision_engine = DecisionEngine()
        self.monitoring_manager = UnifiedMonitoringManager()

    def _benchmark_operation(
        self,
        name: str,
        op_fn,
        iterations: int = 200,
        warmup: int = 20,
    ) -> Dict[str, Any]:
        """Execute operation repeatedly and compute rigorous distribution percentiles."""
        # Warmup phase
        for _ in range(warmup):
            op_fn()

        latencies_ms = []
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            op_fn()
            t1 = time.perf_counter_ns()
            latencies_ms.append((t1 - t0) / 1e6)

        mean_v = float(np.mean(latencies_ms))
        med_v = float(np.median(latencies_ms))
        std_v = float(np.std(latencies_ms))
        p95_v = float(np.percentile(latencies_ms, 95))
        p99_v = float(np.percentile(latencies_ms, 99))
        min_v = float(np.min(latencies_ms))
        max_v = float(np.max(latencies_ms))
        throughput_ops = round(1000.0 / mean_v, 1) if mean_v > 0 else 0.0

        return {
            "operation": name,
            "iterations": iterations,
            "mean_ms": round(mean_v, 4),
            "median_ms": round(med_v, 4),
            "std_ms": round(std_v, 4),
            "p95_ms": round(p95_v, 4),
            "p99_ms": round(p99_v, 4),
            "min_ms": round(min_v, 4),
            "max_ms": round(max_v, 4),
            "throughput_ops_per_sec": throughput_ops,
            "_raw_latencies": latencies_ms,
        }

    def run_all_benchmarks(self, iterations: int = 200) -> Dict[str, Any]:
        """Run complete set of algorithmic micro-benchmarks."""
        # Test fixture data
        base_signal = generate_signal("QPSK", num_samples=1024, seed=self.random_seed).signal
        noisy_signal = add_awgn(base_signal, snr_db=15.0, seed=self.random_seed).noisy_signal
        features_vec, _ = extract_features(noisy_signal, sample_rate=1e6)

        batch_16 = np.tile(features_vec, (16, 1))
        batch_64 = np.tile(features_vec, (64, 1))
        batch_256 = np.tile(features_vec, (256, 1))

        dec_input = DecisionInput(
            signal_evidence=SignalEvidence(predicted_modulation="QPSK", confidence=0.98, measured_snr_db=15.0),
            communication_evidence=CommunicationEvidence(packet_loss_percent=0.0, avg_latency_ms=10.0, health_score=100.0),
        )

        benchmarks = []

        # 1. Signal Generation
        benchmarks.append(self._benchmark_operation(
            "Signal Generation (1024 smp)",
            lambda: generate_signal("QPSK", num_samples=1024),
            iterations=iterations,
        ))

        # 2. Noise Modeling (AWGN)
        benchmarks.append(self._benchmark_operation(
            "AWGN Noise Channel",
            lambda: add_awgn(base_signal, snr_db=12.0),
            iterations=iterations,
        ))

        # 3. FFT (1024 points)
        benchmarks.append(self._benchmark_operation(
            "FFT Spectrum (1024 pts)",
            lambda: compute_fft(noisy_signal, sample_rate=1e6),
            iterations=iterations,
        ))

        # 4. Feature Extraction (23 features)
        benchmarks.append(self._benchmark_operation(
            "23-Feature Extraction",
            lambda: extract_features(noisy_signal, sample_rate=1e6),
            iterations=iterations,
        ))

        # 5. ML Single Prediction
        ml_single = self._benchmark_operation(
            "ML Single Prediction",
            lambda: self.predictor.predict_single(features_vec),
            iterations=iterations,
        )
        benchmarks.append(ml_single)

        # 6. ML Batch Predictions
        benchmarks.append(self._benchmark_operation(
            "ML Batch Prediction (N=16)",
            lambda: self.predictor.predict_batch(batch_16),
            iterations=iterations,
        ))
        benchmarks.append(self._benchmark_operation(
            "ML Batch Prediction (N=64)",
            lambda: self.predictor.predict_batch(batch_64),
            iterations=iterations,
        ))
        benchmarks.append(self._benchmark_operation(
            "ML Batch Prediction (N=256)",
            lambda: self.predictor.predict_batch(batch_256),
            iterations=iterations,
        ))

        # 7. Decision Engine Evaluation
        benchmarks.append(self._benchmark_operation(
            "Decision Engine Evaluation",
            lambda: self.decision_engine.evaluate(dec_input),
            iterations=iterations,
        ))

        # 8. Snapshot Packaging
        benchmarks.append(self._benchmark_operation(
            "Snapshot Serialization",
            lambda: self.monitoring_manager.get_current_snapshot().model_dump_json(),
            iterations=iterations,
        ))

        # Plot ML Single Prediction Latency Distribution Histogram
        single_lats = ml_single["_raw_latencies"]
        plot_p = self.plots_dir / "ml_inference_latency_distribution.png"
        plot_p.parent.mkdir(parents=True, exist_ok=True)

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        ax.hist(single_lats, bins=25, color=COLOR_PRIMARY, edgecolor="#0f172a", alpha=0.85)
        ax.axvline(ml_single["mean_ms"], color="red", linestyle="--", linewidth=1.5, label=f"Mean: {ml_single['mean_ms']:.3f} ms")
        ax.axvline(ml_single["p95_ms"], color="orange", linestyle=":", linewidth=1.5, label=f"p95: {ml_single['p95_ms']:.3f} ms")
        ax.set_xlabel("Inference Latency [milliseconds]")
        ax.set_ylabel("Frequency Count")
        ax.set_title("ML Modulation Inference Latency Distribution (Single Sample)", pad=12)
        ax.legend(loc="upper right")
        plt.tight_layout()
        plt.savefig(plot_p, dpi=300, bbox_inches="tight")
        plt.close(fig)

        # Remove raw latencies from final JSON/CSV records for clean storage
        clean_benchmarks = []
        for b in benchmarks:
            clean_b = {k: v for k, v in b.items() if not k.startswith("_")}
            clean_benchmarks.append(clean_b)

        cfg = ExperimentConfig(
            experiment_id="EXP-PERF-01",
            experiment_name="subsystem_performance_benchmarks",
            description="Micro-benchmarking latency percentiles and throughputs across core subsystems.",
            random_seed=self.random_seed,
            parameters={"iterations": iterations, "warmup": 20},
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "benchmarks": clean_benchmarks,
        }

        self.perf_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_data, self.perf_output_dir / "benchmarks_summary.json")
        save_csv(clean_benchmarks, self.perf_output_dir / "benchmarks_summary.csv")

        return output_data

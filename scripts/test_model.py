#!/usr/bin/env python3
"""Model inference demonstration CLI script for SpectrumSentry AI.

Loads the serialized modulation classifier, loads test examples from Phase 3 dataset,
demonstrates single-example and batch predictions with confidence and probabilities,
and measures inference latency.
"""

import argparse
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


import numpy as np
from backend.app.ml.dataset import INVERSE_LABEL_MAP
from backend.app.ml.predictor import ModulationPredictor
from backend.app.ml.trainer import DEFAULT_DATASET_DIR, DEFAULT_MODELS_DIR


def main():
    parser = argparse.ArgumentParser(description="Demonstrate SpectrumSentry AI modulation predictions.")
    parser.add_argument(
        "--model-path",
        type=str,
        default=str(DEFAULT_MODELS_DIR / "modulation_mlp_v1.joblib"),
        help="Path to serialized .joblib model",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(DEFAULT_DATASET_DIR),
        help="Path to dataset directory",
    )
    parser.add_argument(
        "--samples-to-test",
        type=int,
        default=6,
        help="Number of individual test examples to display",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        default=True,
        help="Run inference latency and throughput benchmark",
    )
    args = parser.parse_args()

    model_path = Path(args.model_path)
    dataset_dir = Path(args.dataset_dir)

    print("=====================================================================")
    print("      SPECTRUMSENTRY AI — MODEL INFERENCE DEMONSTRATION")
    print("=====================================================================")
    print(f"Model Path   : {model_path}")
    print(f"Dataset Path : {dataset_dir}")
    print("---------------------------------------------------------------------")

    if not model_path.exists():
        print(f"ERROR: Model file not found at {model_path}")
        print("Please run 'python scripts/train_model.py' first.")
        sys.exit(1)

    predictor = ModulationPredictor(model_path=model_path)
    print(f"✓ Model loaded successfully (Release: {predictor.model_version})")

    split_file = dataset_dir / "train_test_split.npz"
    if not split_file.exists():
        print(f"ERROR: Dataset file not found at {split_file}")
        sys.exit(1)

    data = np.load(split_file)
    X_test = data["X_test"]
    y_test = data["y_test"]
    snr_test = data["target_snr_test"]

    print(f"✓ Loaded {len(X_test):,} test samples from Phase 3 dataset")
    print("---------------------------------------------------------------------")
    print("PART 1: Single-Example Predictions")
    print("---------------------------------------------------------------------")

    # Pick representative examples from different classes and SNRs
    rng = np.random.default_rng(42)
    sample_indices = rng.choice(len(X_test), size=args.samples_to_test, replace=False)

    for idx in sample_indices:
        feat_vec = X_test[idx]
        actual_label = int(y_test[idx])
        actual_mod = INVERSE_LABEL_MAP[actual_label]
        target_snr = float(snr_test[idx])

        result = predictor.predict_single(feat_vec)

        match_symbol = "✓" if result["predicted_label"] == actual_label else "✗"
        print(f"Sample #{idx:05d} [SNR: {target_snr:+5.1f} dB] | True: {actual_mod:<8} | Pred: {result['predicted_modulation']:<8} {match_symbol}")
        print(f"  Confidence : {result['confidence'] * 100:.2f}% | Latency: {result['inference_time_ms']:.3f} ms")
        probs_str = " | ".join([f"{k}: {v*100:.1f}%" for k, v in result["class_probabilities"].items()])
        print(f"  Probabilities: {probs_str}")
        print()

    print("---------------------------------------------------------------------")
    print("PART 2: Batch Inference Demonstration")
    print("---------------------------------------------------------------------")
    batch_size = 10
    batch_x = X_test[:batch_size]
    batch_results = predictor.predict_batch(batch_x)
    print(f"Processed batch of {batch_size} samples:")
    for i, res in enumerate(batch_results):
        actual = INVERSE_LABEL_MAP[int(y_test[i])]
        match = "✓" if res["predicted_label"] == int(y_test[i]) else "✗"
        print(f"  [{i+1:>2}] True: {actual:<8} -> Pred: {res['predicted_modulation']:<8} ({res['confidence']*100:.1f}%) {match}")

    if args.benchmark:
        print("\n---------------------------------------------------------------------")
        print("PART 3: Inference Latency & Throughput Benchmark")
        print("---------------------------------------------------------------------")
        bench = predictor.benchmark(num_single_runs=200, batch_size=128, num_batch_runs=50)
        s_lat = bench["single_latency_ms"]
        b_bench = bench["batch_benchmark"]
        print("Single-Example Latency:")
        print(f"  Mean   : {s_lat['mean']:.3f} ms")
        print(f"  Median : {s_lat['median']:.3f} ms")
        print(f"  p95    : {s_lat['p95']:.3f} ms")
        print(f"  Range  : {s_lat['min']:.3f} ms - {s_lat['max']:.3f} ms")
        print("Batch Throughput:")
        print(f"  Batch size : {b_bench['batch_size']}")
        print(f"  Throughput : {b_bench['throughput_samples_per_sec']:,} samples/second")

    print("=====================================================================")
    print("DEMO STATUS: PASS")
    print("=====================================================================")


if __name__ == "__main__":
    main()

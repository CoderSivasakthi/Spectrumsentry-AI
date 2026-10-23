#!/usr/bin/env python3
"""Model training CLI script for SpectrumSentry AI.

Trains the Phase 4 MLP modulation classifier using StandardScaler and MLPClassifier.
Enforces strict train/test isolation, conducts model selection on validation data,
evaluates on the untouched test partition across 26 SNR levels, and serializes artifacts.
"""

import argparse
import csv
import json
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


import numpy as np
from backend.app.ml.evaluator import (
    compute_confusion_matrix,
    evaluate_performance_across_snr,
    evaluate_predictions,
    generate_classification_report_text,
    plot_confusion_matrix,
    plot_snr_accuracy,
)
from backend.app.ml.trainer import (
    DEFAULT_DATASET_DIR,
    DEFAULT_MODELS_DIR,
    TrainingConfig,
    build_model_pipeline,
    compare_model_architectures,
    create_development_split,
    load_training_dataset,
    save_trained_model,
)

DEFAULT_REPORTS_DIR = PROJECT_ROOT / "backend" / "reports" / "phase4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train and evaluate SpectrumSentry AI modulation classifier."
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(DEFAULT_DATASET_DIR),
        help="Path to dataset directory containing train_test_split.npz",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=str(DEFAULT_MODELS_DIR),
        help="Directory to save serialized model and metadata",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default=str(DEFAULT_REPORTS_DIR),
        help="Directory to save evaluation reports and visualizations",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for model training and development split",
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=200,
        help="Maximum training iterations (default: 200)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=128,
        help="Batch size for Adam optimizer (default: 128)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
        help="Initial learning rate (default: 0.001)",
    )
    parser.add_argument(
        "--skip-model-selection",
        action="store_true",
        default=False,
        help="Skip architectural comparison and train default (64, 32) directly",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    dataset_dir = Path(args.dataset_dir)
    models_dir = Path(args.models_dir)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    print("=====================================================================")
    print("      SPECTRUMSENTRY AI — AI MODULATION CLASSIFIER TRAINING")
    print("=====================================================================")
    print(f"Dataset Directory : {dataset_dir}")
    print(f"Models Directory  : {models_dir}")
    print(f"Reports Directory : {reports_dir}")
    print(f"Random Seed       : {args.seed}")
    print("---------------------------------------------------------------------")

    # 1. Load dataset partitions
    print("Step 1: Loading Phase 3 dataset...")
    (
        X_train,
        y_train,
        snr_train,
        X_test,
        y_test,
        snr_test,
        dataset_info,
    ) = load_training_dataset(dataset_dir)

    print(f"  ✓ Training samples : {len(X_train):,} (Features: {X_train.shape[1]})")
    print(f"  ✓ Test samples     : {len(X_test):,} (Protected from development)")
    print(f"  ✓ Modulations      : {dataset_info['modulations']}")
    print(f"  ✓ Target SNR range : {dataset_info['snr_min_db']} dB to {dataset_info['snr_max_db']} dB")

    # 2. Partition training data into internal fit and validation subsets
    print("\nStep 2: Creating development validation split (80% fit / 20% val)...")
    (
        X_fit,
        y_fit,
        snr_fit,
        X_val,
        y_val,
        snr_val,
    ) = create_development_split(
        X_train, y_train, snr_train, val_ratio=0.2, seed=args.seed
    )
    print(f"  ✓ Fit samples      : {len(X_fit):,}")
    print(f"  ✓ Validation samples: {len(X_val):,}")

    # 3. Model Selection
    model_comparison: Dict[str, Any] = {}
    if not args.skip_model_selection:
        print("\nStep 3: Comparing candidate MLP architectures on validation split...")
        best_name, selected_config, model_comparison = compare_model_architectures(
            X_fit, y_fit, X_val, y_val, seed=args.seed, max_iter=args.max_iter
        )
        print("  Candidate Comparison:")
        for name, metrics in model_comparison.items():
            print(
                f"    - {name:<22}: Val Macro F1 = {metrics['validation_macro_f1']:.4f} "
                f"| Val Acc = {metrics['validation_accuracy'] * 100:.2f}% "
                f"| Time = {metrics['training_time_sec']:.1f}s"
            )
        print(f"  ★ Selected Architecture: {best_name} (Layers: {selected_config.hidden_layer_sizes})")
    else:
        best_name = "Model A (64, 32)"
        selected_config = TrainingConfig(
            hidden_layer_sizes=(64, 32),
            random_state=args.seed,
            max_iter=args.max_iter,
            batch_size=args.batch_size,
            learning_rate_init=args.learning_rate,
        )
        print(f"\nStep 3: Using default architecture: {best_name}")

    # 4. Final Model Fitting on full training partition
    print(f"\nStep 4: Training final pipeline on full training partition ({len(X_train):,} samples)...")
    pipeline = build_model_pipeline(selected_config)
    t_start = time.perf_counter()
    pipeline.fit(X_train, y_train)
    train_duration = time.perf_counter() - t_start

    mlp = pipeline.named_steps["classifier"]
    loss_curve = [round(float(l), 5) for l in getattr(mlp, "loss_curve_", [])]
    n_iters = int(getattr(mlp, "n_iter_", 0))
    final_loss = round(float(getattr(mlp, "loss_", 0.0)), 5)
    print(f"  ✓ Training completed in {train_duration:.2f}s ({n_iters} iterations, final loss = {final_loss})")

    # 5. Independent Test Evaluation on Phase 3 Test Set
    print(f"\nStep 5: Evaluating final pipeline on original test partition ({len(X_test):,} samples)...")
    t_inf_start = time.perf_counter()
    y_test_pred = pipeline.predict(X_test)
    y_test_prob = pipeline.predict_proba(X_test)
    total_inf_time = time.perf_counter() - t_inf_start
    avg_inf_ms = (total_inf_time / len(X_test)) * 1000.0

    eval_test = evaluate_predictions(y_test, y_test_pred, y_test_prob)
    eval_test["inference_time_ms_per_sample"] = round(avg_inf_ms, 3)

    print(f"  ✓ Test Accuracy  : {eval_test['accuracy'] * 100:.2f}%")
    print(f"  ✓ Macro F1-Score : {eval_test['macro_f1']:.4f}")
    print(f"  ✓ Weighted F1    : {eval_test['weighted_f1']:.4f}")
    print(f"  ✓ Mean Confidence: {eval_test['confidence']['mean_confidence'] * 100:.2f}%")
    print(f"  ✓ Avg Latency    : {avg_inf_ms:.3f} ms/sample")

    # 6. Confusion Matrix Generation
    print("\nStep 6: Generating confusion matrix and visualizations...")
    cm_dict = compute_confusion_matrix(y_test, y_test_pred)
    cm_png_path = reports_dir / "confusion_matrix.png"
    plot_confusion_matrix(cm_dict, cm_png_path)
    print(f"  ✓ Saved confusion matrix plot: {cm_png_path.name}")

    # 7. Performance Across SNR Evaluation
    print("\nStep 7: Evaluating performance across all 26 SNR levels (-5 dB to 20 dB)...")
    snr_eval = evaluate_performance_across_snr(y_test, y_test_pred, snr_test)
    snr_png_path = reports_dir / "snr_accuracy.png"
    plot_snr_accuracy(snr_eval, snr_png_path)
    print(f"  ✓ Saved SNR accuracy plot: {snr_png_path.name}")

    # 8. Save Reports
    print("\nStep 8: Saving evaluation reports...")
    # classification_report.json
    with open(reports_dir / "classification_report.json", "w", encoding="utf-8") as f:
        json.dump(eval_test, f, indent=2)

    # classification_report.txt
    report_text = generate_classification_report_text(eval_test)
    with open(reports_dir / "classification_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    # confusion_matrix.json
    with open(reports_dir / "confusion_matrix.json", "w", encoding="utf-8") as f:
        json.dump(cm_dict, f, indent=2)

    # snr_performance.json
    with open(reports_dir / "snr_performance.json", "w", encoding="utf-8") as f:
        json.dump(snr_eval, f, indent=2)

    # snr_performance.csv
    snr_csv_path = reports_dir / "snr_performance.csv"
    if snr_eval["records"]:
        fieldnames = list(snr_eval["records"][0].keys())
        with open(snr_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(snr_eval["records"])

    # training_history.json
    training_history = {
        "architecture": best_name,
        "iterations": n_iters,
        "training_time_sec": round(train_duration, 2),
        "final_loss": final_loss,
        "loss_curve": loss_curve,
    }
    with open(reports_dir / "training_history.json", "w", encoding="utf-8") as f:
        json.dump(training_history, f, indent=2)

    # model_comparison.json
    if model_comparison:
        with open(reports_dir / "model_comparison.json", "w", encoding="utf-8") as f:
            json.dump(model_comparison, f, indent=2)

    # 9. Model Serialization
    print(f"\nStep 9: Serializing trained model to {models_dir}...")
    model_metadata = {
        "model_name": "modulation_mlp_v1",
        "model_version": "v1.0",
        "architecture": best_name,
        "hidden_layer_sizes": list(selected_config.hidden_layer_sizes),
        "activation": selected_config.activation,
        "training_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset_version": dataset_info.get("dataset_version", "v1.0"),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "training_duration_sec": round(train_duration, 2),
        "validation_macro_f1": model_comparison.get(best_name, {}).get("validation_macro_f1"),
        "test_accuracy": eval_test["accuracy"],
        "test_macro_f1": eval_test["macro_f1"],
        "test_weighted_f1": eval_test["weighted_f1"],
    }
    saved_model_paths = save_trained_model(
        pipeline=pipeline,
        output_dir=models_dir,
        model_name="modulation_mlp_v1",
        model_metadata=model_metadata,
        training_config=selected_config,
    )
    for k, p in saved_model_paths.items():
        print(f"  ✓ {k}: {Path(p).name}")

    print("\n" + report_text)
    print("\nSNR Performance Highlights:")
    print("  SNR (dB) | Samples | Overall Acc | BPSK Acc | QPSK Acc | 16-QAM Acc")
    print("  ---------+---------+-------------+----------+----------+-----------")
    for r in snr_eval["records"][:5]:  # Lowest 5 SNRs (-5 to -1 dB)
        print(
            f"  {r['snr_db']:>7}  | {r['sample_count']:>7} | {r['accuracy']*100:>10.1f}% | "
            f"{r.get('BPSK_acc',0)*100:>7.1f}% | {r.get('QPSK_acc',0)*100:>7.1f}% | {r.get('16-QAM_acc',0)*100:>8.1f}%"
        )
    print("  ... (middle SNRs omitted for brevity) ...")
    for r in snr_eval["records"][-5:]:  # Highest 5 SNRs (16 to 20 dB)
        print(
            f"  {r['snr_db']:>7}  | {r['sample_count']:>7} | {r['accuracy']*100:>10.1f}% | "
            f"{r.get('BPSK_acc',0)*100:>7.1f}% | {r.get('QPSK_acc',0)*100:>7.1f}% | {r.get('16-QAM_acc',0)*100:>8.1f}%"
        )

    print("\n=====================================================================")
    print("      PHASE 4 TRAINING COMPLETE — ALL ARTIFACTS SAVED")
    print("=====================================================================")


if __name__ == "__main__":
    main()

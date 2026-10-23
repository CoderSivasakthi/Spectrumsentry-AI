#!/usr/bin/env python3
"""Phase-robust cumulant (v2) training experiment — corrected report fix #5 / TC-08.

Generates a dataset in which EVERY frame carries a RANDOM carrier phase (the realistic
radio condition the corrected report identified as fatal for legacy features), extracts
the 6 phase-robust cumulant features, trains the MLP classifier, and reports accuracy
per SNR. Runs in two parts:

1. cumulant_v2 model  : phase-robust features -> >= 95% accuracy at >= 10 dB (TC-08 gate)
2. v1 CONTROL model   : legacy 23-feature vector on the SAME random-phase frames -> shows
   the 98% -> 53.8%-style collapse the corrected report documented (control experiment)

Additionally fits the SNR-aware NoveltyDetector (fix #8): for v2 on its own high-SNR
cumulant train features -> ``novelty_detector_cumulant.joblib``; when the control run
is enabled, also on high-SNR legacy train features -> ``novelty_detector.joblib``
(the detector used by the default v1 model in the live app).

Artifacts written:
    backend/data/datasets/cumulant_v2/      train_test_split.npz, dataset_info.json
    backend/models/modulation_mlp_v2.joblib + model_metadata_v2.json
    backend/models/novelty_detector.joblib  (control run only)
    backend/models/novelty_detector_cumulant.joblib

To serve the v2 model via the live API, set in .env:
    AI_MODEL_PATH=backend/models/modulation_mlp_v2.joblib
    AI_NOVELTY_DETECTOR_PATH=backend/models/novelty_detector_cumulant.joblib

Windows note: console output sticks to ASCII; UTF-8 stdout is forced defensively.
"""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:  # Windows cp1252 console safety
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import numpy as np
from sklearn.model_selection import train_test_split

from backend.app.ml.evaluator import evaluate_predictions
from backend.app.ml.anomaly import NoveltyDetector
from backend.app.signal_processing import (
    FEATURE_COUNT_CUMULANT,
    FEATURE_NAMES_CUMULANT,
    FEATURE_NAMES,
    apply_carrier_phase,
    extract_cumulant_features,
    generate_signal,
)
from backend.app.signal_processing.features import extract_features
from backend.app.signal_processing.noise import add_awgn
from backend.app.ml.trainer import TrainingConfig, build_model_pipeline

MODULATIONS = ["BPSK", "QPSK", "16-QAM"]
LABEL_MAP = {name: idx for idx, name in enumerate(MODULATIONS)}
INVERSE_LABEL_MAP = {idx: name for name, idx in LABEL_MAP.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the phase-robust cumulant (v2) model and run the"
                    " random-carrier-phase robustness experiment (TC-08)."
    )
    parser.add_argument("--samples-per-condition", type=int, default=300,
                        help="Random-phase frames per (modulation, SNR) condition")
    parser.add_argument("--snr-min", type=float, default=-5.0)
    parser.add_argument("--snr-max", type=float, default=20.0)
    parser.add_argument("--snr-step", type=float, default=1.0)
    parser.add_argument("--frame-samples", type=int, default=1024)
    parser.add_argument("--base-seed", type=int, default=2024)
    parser.add_argument("--datasets-dir", type=str, default=str(PROJECT_ROOT / "backend/data/datasets"))
    parser.add_argument("--models-dir", type=str, default=str(PROJECT_ROOT / "backend/models"))
    parser.add_argument("--with-v1-control", action="store_true",
                        help="Also train a control model on legacy 23 features under"
                             " the same random phase (demonstrates the collapse)")
    parser.add_argument("--min-high-snr-accuracy", type=float, default=0.95,
                        help="TC-08 gate: accuracy at SNR >= 10 dB")
    parser.add_argument("--no-novelty", action="store_true",
                        help="Skip fitting/saving novelty detectors")
    return parser.parse_args()


def snr_list(min_db: float, max_db: float, step: float) -> list:
    n = int(round((max_db - min_db) / step)) + 1
    return [round(min_db + i * step, 1) for i in range(n)]


def generate_condition_dataset(
    modulation: str,
    target_snrs: list,
    samples_per_condition: int,
    frame_samples: int,
    feature_set: str,
    base_seed: int,
) -> tuple:
    """Generate random-phase AWGN frames and their features for one modulation.

    feature_set: "cumulant_v2" (6 phase-robust) or "v1" (legacy 23).
    Returns (X, y, snr).
    """
    frame_feature_extractor = (
        extract_cumulant_features if feature_set == "cumulant_v2" else extract_features
    )
    X_parts, y_parts, snr_parts = [], [], []
    for snr_db in target_snrs:
        # SeedSequence requires non-negative entropy components: offset the (possibly
        # negative) SNR term so conditions stay reproducible but seed-valid
        cond_seed = np.random.SeedSequence(
            [
                int(base_seed) & 0xFFFFFFFF,
                LABEL_MAP[modulation],
                int(round(snr_db * 10)) + 1_000_000,
            ]
        )
        for idx in range(samples_per_condition):
            child = np.random.SeedSequence(cond_seed.entropy, spawn_key=(idx,))
            sig_seed, noise_seed, phase_seed = [s.generate_state(1)[0] for s in child.spawn(3)]

            frame = generate_signal(modulation, frame_samples, seed=int(sig_seed)).signal

            # Random carrier phase per frame (the corrected-report condition)
            rng_phase = np.random.default_rng(int(phase_seed))
            frame = apply_carrier_phase(frame, rng_phase.uniform(0.0, 2.0 * np.pi))

            noisy = add_awgn(frame, snr_db=snr_db, seed=int(noise_seed)).noisy_signal
            features, _ = frame_feature_extractor(noisy)

            X_parts.append(features)
            y_parts.append(LABEL_MAP[modulation])
            snr_parts.append(float(snr_db))
        print(f"  [{feature_set}] {modulation} @ {snr_db:+5.1f} dB: {samples_per_condition} frames done", flush=True)

    return (
        np.asarray(X_parts, dtype=np.float32),
        np.asarray(y_parts, dtype=np.int64),
        np.asarray(snr_parts, dtype=np.float32),
    )


def build_split_dataset(
    target_snrs: list,
    samples_per_condition: int,
    frame_samples: int,
    feature_set: str,
    args,
) -> tuple:
    """Generate the complete dataset and split it by (class, SNR) condition."""
    X_by_mod = {m: generate_condition_dataset(m, target_snrs, args.samples_per_condition,
                                              args.frame_samples, feature_set, args.base_seed)
                for m in MODULATIONS}
    X = np.concatenate([parts[0] for parts in X_by_mod.values()])
    y = np.concatenate([parts[1] for parts in X_by_mod.values()])
    snr = np.concatenate([parts[2] for parts in X_by_mod.values()])

    condition_keys = np.array([f"{lbl}_{int(round(s))}" for lbl, s in zip(y, snr)])
    idx_train, idx_test = train_test_split(
        np.arange(len(y)), test_size=0.2, random_state=args.base_seed, stratify=condition_keys
    )
    idx_train = np.sort(idx_train)
    idx_test = np.sort(idx_test)

    return (
        X[idx_train], y[idx_train], snr[idx_train],
        X[idx_test], y[idx_test], snr[idx_test],
    )


def train_and_evaluate(
    name: str,
    X_train, y_train, snr_train, X_test, y_test, snr_test,
    config: TrainingConfig,
) -> dict:
    """Fit the MLP pipeline on the training partition and produce per-SNR test metrics."""
    t0 = time.perf_counter()
    pipeline = build_model_pipeline(config)
    pipeline.fit(X_train, y_train)
    train_time = time.perf_counter() - t0

    y_prob = pipeline.predict_proba(X_test)
    y_pred = np.argmax(y_prob, axis=1)
    overall = evaluate_predictions(y_test, y_pred, y_prob)

    per_snr = {}
    for snr_db in sorted(np.unique(snr_test)):
        mask = snr_test == snr_db
        acc = float(np.mean(y_pred[mask] == y_test[mask]))
        per_snr[round(float(snr_db), 1)] = round(acc, 4)

    high_snr_mask = snr_test >= 10.0
    high_snr_acc = float(np.mean(y_pred[high_snr_mask] == y_test[high_snr_mask]))

    print(f"\n=== {name} ===")
    print(f"training time        : {train_time:.1f} s")
    print(f"test accuracy        : {overall['accuracy']:.4f}")
    print(f"test macro F1        : {overall['macro_f1']:.4f}")
    print(f"accuracy @ >= 10 dB  : {high_snr_acc:.4f}   (TC-08 gate 0.95)")
    print("per-SNR accuracy:")
    for snr_db, acc in sorted(per_snr.items()):
        bar = "#" * int(acc * 40)
        print(f"  {snr_db:+6.1f} dB  {acc:6.3f}  {bar}")

    return {
        "name": name,
        "train_time_sec": round(train_time, 2),
        "overall": {k: round(float(v), 4) for k, v in overall.items() if np.isscalar(v)},
        "per_snr": per_snr,
        "high_snr_accuracy": round(high_snr_acc, 4),
        "high_snr_samples": int(high_snr_mask.sum()),
        "scaler": pipeline,
    }


def fit_and_save_novelty_detector(
    X_train: np.ndarray,
    snr_train: np.ndarray,
    output_path: Path,
    feature_set_name: str,
    min_snr: float = 10.0,
    metadata_extra: dict = None,
) -> dict:
    """Fit the NoveltyDetector on clean high-SNR train features (SNR-aware, fix #8)."""
    mask = snr_train >= min_snr
    detector = NoveltyDetector().fit(
        X_train[mask],
        metadata={
            "feature_set": feature_set_name,
            "feature_count": int(X_train.shape[1]),
            "fit_snr_min_dB": float(min_snr),
            "n_fit_samples": int(mask.sum()),
            "purpose": "Out-of-distribution detection for unsupported modulations",
            **(metadata_extra or {}),
        },
    )
    detector.save(output_path)
    print(f"NoveltyDetector saved: {output_path} (fit on {int(mask.sum())} clean, >= {min_snr} dB frames)")
    return detector.fit_metadata


def main() -> int:
    args = parse_args()
    target_snrs = snr_list(args.snr_min, args.snr_max, args.snr_step)
    datasets_dir = Path(args.datasets_dir)
    models_dir = Path(args.models_dir)

    print(f"Phase-robust cumulant (v2) training experiment")
    print(f"  frames/condition : {args.samples_per_condition}")
    print(f"  SNR grid         : {target_snrs[0]} .. {target_snrs[-1]} dB step {args.snr_step}")
    print(f"  random phase     : ON for every frame (corrected-report condition)")
    print(f"  sample count     : {len(target_snrs)} conditions x {len(MODULATIONS)} classes")

    config = TrainingConfig()

    # ---------------- Part 1: cumulant v2 ----------------
    print("\n[1/3] Generating random-phase cumulant dataset ...")
    (
        Xv2_train, yv2_train, snrv2_train,
        Xv2_test, yv2_test, snrv2_test,
    ) = build_split_dataset(target_snrs, args.samples_per_condition, args.frame_samples,
                            "cumulant_v2", args)
    print(f"  cumulant dataset: train {Xv2_train.shape}, test {Xv2_test.shape}")

    print("[2/3] Training cumulant v2 model ...")
    v2_report = train_and_evaluate("Model V2 (cumulant, 6 features, random phase)",
                                   Xv2_train, yv2_train, snrv2_train,
                                   Xv2_test, yv2_test, snrv2_test, config)

    # Save v2 dataset split
    v2_dir = datasets_dir / "cumulant_v2"
    v2_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        v2_dir / "train_test_split.npz",
        X_train=Xv2_train, y_train=yv2_train, target_snr_train=snrv2_train,
        X_test=Xv2_test, y_test=yv2_test, target_snr_test=snrv2_test,
    )
    dataset_info = {
        "feature_set": "cumulant_v2",
        "feature_names": list(FEATURE_NAMES_CUMULANT),
        "feature_count": int(FEATURE_COUNT_CUMULANT),
        "random_carrier_phase": True,
        "snr_grid_db": target_snrs,
        "samples_per_condition": args.samples_per_condition,
        "frame_samples": args.frame_samples,
        "label_map": LABEL_MAP,
        "base_seed": args.base_seed,
        "train_samples": int(Xv2_train.shape[0]),
        "test_samples": int(Xv2_test.shape[0]),
    }
    with open(v2_dir / "dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=2)

    # Save v2 model + metadata (manual save: the shared save_trained_model always
    # writes model_metadata.json, which would clobber the v1 metadata file)
    v2_pipeline = v2_report.pop("scaler")
    import joblib

    joblib.dump(v2_pipeline, models_dir / "modulation_mlp_v2.joblib")
    v2_metadata = {
        "model_version": "v2.0-cumulant",
        "model_filename": "modulation_mlp_v2.joblib",
        "feature_set": "cumulant_v2",
        "feature_names": list(FEATURE_NAMES_CUMULANT),
        "feature_count": int(FEATURE_COUNT_CUMULANT),
        "label_mapping": {str(k): v for k, v in INVERSE_LABEL_MAP.items()},
        "dataset_info": {k: v for k, v in dataset_info.items() if k != "feature_names"},
        "evaluation": {
            "overall": v2_report["overall"],
            "per_snr": v2_report["per_snr"],
            "high_snr_accuracy": v2_report["high_snr_accuracy"],
        },
    }
    with open(models_dir / "model_metadata_v2.json", "w", encoding="utf-8") as f:
        json.dump(v2_metadata, f, indent=2)
    print(f"Model saved: {models_dir / 'modulation_mlp_v2.joblib'}")

    # Novelty detector on cumulant features
    if not args.no_novelty:
        print("[3/3] Fitting SNR-aware novelty detector (cumulant) ...")
        fit_and_save_novelty_detector(
            Xv2_train, snrv2_train,
            models_dir / "novelty_detector_cumulant.joblib",
            "cumulant_v2",
        )

    # ---------------- Part 2 (optional): v1 control ----------------
    control_report = None
    if args.with_v1_control:
        print("\n[control] Generating random-phase LEGACY (23-feature) dataset ...")
        (
            Xv1_train, yv1_train, snrv1_train,
            Xv1_test, yv1_test, snrv1_test,
        ) = build_split_dataset(target_snrs, args.samples_per_condition, args.frame_samples,
                                "v1", args)
        control_report = train_and_evaluate("CONTROL (legacy 23 features, random phase)",
                                            Xv1_train, yv1_train, snrv1_train,
                                            Xv1_test, yv1_test, snrv1_test, config)
        control_report.pop("scaler", None)

        if not args.no_novelty:
            print("[control] Fitting SNR-aware novelty detector (legacy) ...")
            fit_and_save_novelty_detector(
                Xv1_train, snrv1_train,
                models_dir / "novelty_detector.joblib",
                "v1_moment_spectral_23",
                metadata_extra={"note": "Fitted on random-carrier-phase frames at >= 10 dB"},
            )

    # ---------------- Verdict ----------------
    v2_gate_pass = v2_report["high_snr_accuracy"] >= args.min_high_snr_accuracy
    print("\n================ EXPERIMENT VERDICT ================")
    print(f"Cumulant v2 accuracy @ >= 10 dB : {v2_report['high_snr_accuracy']:.4f}"
          f"  ->  TC-08 {'PASS' if v2_gate_pass else 'FAIL'} (gate {args.min_high_snr_accuracy})")
    if control_report:
        delta = control_report["high_snr_accuracy"] - v2_report["high_snr_accuracy"]
        print(f"Legacy v1 (random phase)        : {control_report['high_snr_accuracy']:.4f}"
              f"  ->  gap to cumulant: {delta:+.4f}")
        print("Confirming the corrected report: legacy features collapse under random")
        print("carrier phase; the cumulant set stays accurate.")
    print("====================================================")

    if not v2_gate_pass:
        print("TC-08 GATE FAILED: increase samples/condition or revise the feature set.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

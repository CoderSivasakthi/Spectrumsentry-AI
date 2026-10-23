#!/usr/bin/env python3
"""Dataset generation CLI script for SpectrumSentry AI.

Generates a balanced, reproducible dataset across BPSK, QPSK, and 16-QAM modulations
under varied SNR levels using the Phase 2 DSP engine.
"""

import argparse
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


from backend.app.ml.dataset import (
    DatasetConfig,
    generate_modulation_dataset,
    save_dataset_artifacts,
    validate_dataset_directory,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic modulation classification dataset for SpectrumSentry AI."
    )
    parser.add_argument(
        "--samples-per-condition",
        type=int,
        default=500,
        help="Number of samples to generate per modulation-SNR condition (default: 500)",
    )
    parser.add_argument(
        "--snr-min",
        type=int,
        default=-5,
        help="Minimum target SNR in dB (default: -5)",
    )
    parser.add_argument(
        "--snr-max",
        type=int,
        default=20,
        help="Maximum target SNR in dB (default: 20)",
    )
    parser.add_argument(
        "--snr-step",
        type=int,
        default=1,
        help="Step size for SNR range in dB (default: 1)",
    )
    parser.add_argument(
        "--sample-count",
        type=int,
        default=1024,
        help="Number of complex I/Q samples per signal (default: 1024)",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=1e6,
        help="Baseband sampling rate in Hz (default: 1000000.0)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global random seed for deterministic reproduction (default: 42)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(PROJECT_ROOT / "backend" / "data" / "datasets"),
        help="Directory to save generated dataset artifacts",
    )
    parser.add_argument(
        "--save-raw",
        action="store_true",
        default=False,
        help="Optional flag to save raw I/Q signal files (disabled by default for compact storage)",
    )
    parser.add_argument(
        "--version",
        type=str,
        default="v1.0",
        help="Dataset version tag (default: v1.0)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = Path(args.output_dir)

    config = DatasetConfig(
        dataset_version=args.version,
        snr_min_db=args.snr_min,
        snr_max_db=args.snr_max,
        snr_step_db=args.snr_step,
        samples_per_condition=args.samples_per_condition,
        sample_count=args.sample_count,
        sample_rate=args.sample_rate,
        seed=args.seed,
        save_raw=args.save_raw,
    )

    print("==================================================")
    print("SpectrumSentry AI — Dataset Generation")
    print("==================================================")
    print(f"Dataset version   : {config.dataset_version}")
    print(f"Seed              : {config.seed}")
    print(f"Modulations       : {', '.join(config.modulations)}")
    print(f"SNR range         : {config.snr_min_db} dB → {config.snr_max_db} dB (step {config.snr_step_db} dB)")
    print(f"Conditions        : {config.total_conditions}")
    print(f"Samples/condition : {config.samples_per_condition:,}")
    print(f"Total examples    : {config.total_samples:,}")
    print(f"Features/example  : 23")
    print("--------------------------------------------------")
    print("Generating signal features via Phase 2 DSP engine...")

    t0 = time.perf_counter()
    last_print = 0

    def progress_callback(done: int, total: int):
        nonlocal last_print
        pct = (done / total) * 100
        # Print update every 10% or at completion
        if pct - last_print >= 10.0 or done == total:
            last_print = int(pct)
            print(f"  Progress: {done:,} / {total:,} ({pct:.1f}%)")

    dataset_result = generate_modulation_dataset(
        config=config,
        progress_callback=progress_callback,
    )
    gen_time = time.perf_counter() - t0
    print(f"Generation completed in {gen_time:.2f}s ({gen_time / config.total_samples * 1000:.2f} ms/sample)")

    print(f"Saving dataset artifacts to {output_dir}...")
    saved_paths = save_dataset_artifacts(dataset_result, output_dir)
    for name, path in saved_paths.items():
        print(f"  ✓ {name}: {Path(path).name}")

    print("--------------------------------------------------")
    print("Validating dataset integrity...")
    is_valid, issues = validate_dataset_directory(output_dir)

    stats = dataset_result.statistics
    print("\nClasses:")
    for mod, count in stats["class_counts"].items():
        print(f"{mod:<8}: {count:,}")

    print("\nSplits:")
    print(f"Train   : {stats['train_examples']:,} (80%)")
    print(f"Test    : {stats['test_examples']:,} (20%)")

    print("\nMeasured SNR Summary:")
    print(f"Min     : {stats['measured_snr']['min_db']} dB")
    print(f"Max     : {stats['measured_snr']['max_db']} dB")
    print(f"Mean    : {stats['measured_snr']['mean_db']} dB")
    print(f"Std     : {stats['measured_snr']['std_db']} dB")

    print("--------------------------------------------------")
    if is_valid:
        print("Validation: PASS (0 issues detected)")
    else:
        print(f"Validation: FAIL ({len(issues)} issues detected)")
        for issue in issues:
            print(f"  ✗ {issue}")
        sys.exit(1)

    print("==================================================")


if __name__ == "__main__":
    main()

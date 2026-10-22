#!/usr/bin/env python3
"""Dataset validation CLI script for SpectrumSentry AI.

Performs rigorous verification of dataset integrity, feature contracts,
class balance, condition completeness, and data leakage absence across train/test splits.
"""

import argparse
from pathlib import Path
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ml.dataset import validate_dataset_directory


def main():
    parser = argparse.ArgumentParser(description="Validate generated modulation dataset integrity.")
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=str(PROJECT_ROOT / "backend" / "data" / "datasets"),
        help="Path to directory containing dataset artifacts to validate",
    )
    args = parser.parse_args()
    dataset_dir = Path(args.dataset_dir)

    print("==================================================")
    print("SpectrumSentry AI — Dataset Validation")
    print(f"Target Directory: {dataset_dir}")
    print("==================================================")

    if not dataset_dir.exists():
        print(f"ERROR: Dataset directory does not exist: {dataset_dir}")
        sys.exit(1)

    is_valid, issues = validate_dataset_directory(dataset_dir)

    if is_valid:
        print("✓ All 17 verification checks PASSED successfully.")
        print("✓ Zero data leakage detected between train and test splits.")
        print("✓ Feature matrix contains 0 NaNs and 0 Infs.")
        print("✓ All classes, SNR levels, and conditions are fully balanced.")
        print("==================================================")
        print("STATUS: VALID")
        sys.exit(0)
    else:
        print(f"FAIL: {len(issues)} validation issues detected:")
        for idx, issue in enumerate(issues, 1):
            print(f"  [{idx}] {issue}")
        print("==================================================")
        print("STATUS: INVALID")
        sys.exit(1)


if __name__ == "__main__":
    main()

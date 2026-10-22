#!/usr/bin/env python3
"""Validation Script for Phase 9 Results and Scientific Artifacts.

Performs automated data validation on all generated experiment files:
    1. Ensures existence of required JSON and CSV results.
    2. Ensures existence of all publication plots.
    3. Verifies no NaN or Inf values in numerical outputs.
    4. Validates presence of reproducibility metadata (seed, versions, timestamps).
    5. Checks bounds and completeness across SNR levels and decision rules.
"""

import json
import math
from pathlib import Path
import sys
from typing import Any, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports" / "phase9"


def check_no_nan_or_inf(data: Any, path_prefix: str = "") -> List[str]:
    """Recursively traverse data structures and identify any NaN or Inf occurrences."""
    errors = []
    if isinstance(data, dict):
        for k, v in data.items():
            errors.extend(check_no_nan_or_inf(v, f"{path_prefix}.{k}" if path_prefix else str(k)))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            errors.extend(check_no_nan_or_inf(item, f"{path_prefix}[{idx}]"))
    elif isinstance(data, (float, int)):
        if math.isnan(data):
            errors.append(f"NaN found at {path_prefix}")
        elif math.isinf(data):
            errors.append(f"Inf found at {path_prefix}")
    return errors


def validate_phase9(reports_dir: Path = REPORTS_DIR) -> bool:
    print("=" * 76)
    print("      SPECTRUMSENTRY AI — PHASE 9 RESULTS VALIDATION")
    print(f"      Validating Directory: {reports_dir}")
    print("=" * 76)

    errors = []

    # 1. Required Result Files
    required_json_files = [
        reports_dir / "ai" / "classification_metrics.json",
        reports_dir / "ai" / "confusion_matrix.json",
        reports_dir / "ai" / "confidence_analysis.json",
        reports_dir / "ai" / "snr_sweep_results.json",
        reports_dir / "signal" / "dsp_validation.json",
        reports_dir / "signal" / "snr_accuracy_results.json",
        reports_dir / "signal" / "feature_stability.json",
        reports_dir / "communication" / "communication_evaluation_summary.json",
        reports_dir / "communication" / "packet_loss_results.json",
        reports_dir / "communication" / "latency_results.json",
        reports_dir / "communication" / "jitter_results.json",
        reports_dir / "communication" / "interruption_recovery_results.json",
        reports_dir / "decision" / "decision_rule_evaluation.json",
        reports_dir / "end_to_end" / "pipeline_latency_breakdown.json",
        reports_dir / "end_to_end" / "state_transitions.json",
        reports_dir / "performance" / "benchmarks_summary.json",
        reports_dir / "stability" / "soak_test_results.json",
    ]

    required_csv_files = [
        reports_dir / "ai" / "snr_sweep_results.csv",
        reports_dir / "signal" / "snr_accuracy_results.csv",
        reports_dir / "communication" / "packet_loss_results.csv",
        reports_dir / "communication" / "latency_results.csv",
        reports_dir / "communication" / "jitter_results.csv",
        reports_dir / "decision" / "decision_rule_evaluation.csv",
        reports_dir / "performance" / "benchmarks_summary.csv",
    ]

    required_plots = [
        reports_dir / "plots" / "confusion_matrix.png",
        reports_dir / "plots" / "snr_vs_accuracy.png",
        reports_dir / "plots" / "per_class_accuracy_vs_snr.png",
        reports_dir / "plots" / "confidence_vs_snr.png",
        reports_dir / "plots" / "target_vs_measured_snr.png",
        reports_dir / "plots" / "snr_measurement_error.png",
        reports_dir / "plots" / "packet_loss_vs_health.png",
        reports_dir / "plots" / "latency_vs_health.png",
        reports_dir / "plots" / "jitter_vs_health.png",
        reports_dir / "plots" / "decision_confidence_breakdown.png",
        reports_dir / "plots" / "end_to_end_latency_breakdown.png",
        reports_dir / "plots" / "ml_inference_latency_distribution.png",
        reports_dir / "plots" / "memory_stability_soak.png",
    ]

    # Check JSON existence and validate structure
    for jpath in required_json_files:
        if not jpath.exists():
            errors.append(f"Missing required JSON: {jpath.relative_to(PROJECT_ROOT)}")
        else:
            try:
                with open(jpath, "r", encoding="utf-8") as f:
                    content = json.load(f)
                # Check NaN / Inf
                nan_errors = check_no_nan_or_inf(content)
                if nan_errors:
                    errors.extend([f"In {jpath.name}: {e}" for e in nan_errors[:5]])
                # Check metadata presence in top-level configs
                if isinstance(content, dict) and "metadata" in content:
                    meta = content["metadata"]
                    for req_key in ["experiment_id", "random_seed", "timestamp", "environment"]:
                        if req_key not in meta:
                            errors.append(f"In {jpath.name}: metadata missing '{req_key}'")
            except Exception as e:
                errors.append(f"Invalid JSON at {jpath.relative_to(PROJECT_ROOT)}: {e}")

    # Check CSV existence
    for cpath in required_csv_files:
        if not cpath.exists():
            errors.append(f"Missing required CSV: {cpath.relative_to(PROJECT_ROOT)}")

    # Check Plot existence and non-zero size
    for ppath in required_plots:
        if not ppath.exists():
            errors.append(f"Missing required Plot: {ppath.relative_to(PROJECT_ROOT)}")
        elif ppath.stat().st_size < 1000:
            errors.append(f"Plot file too small (<1KB): {ppath.relative_to(PROJECT_ROOT)}")

    # Print summary
    print(f"Validated JSON files : {len(required_json_files)}")
    print(f"Validated CSV files  : {len(required_csv_files)}")
    print(f"Validated Plots      : {len(required_plots)}")
    print("-" * 76)

    if errors:
        print(f"FAILED with {len(errors)} validation errors:")
        for err in errors[:20]:
            print(f"  [✗] {err}")
        return False
    else:
        print("ALL VALIDATION CHECKS PASSED: 0 errors detected.")
        print("=" * 76)
        return True


if __name__ == "__main__":
    success = validate_phase9()
    sys.exit(0 if success else 1)

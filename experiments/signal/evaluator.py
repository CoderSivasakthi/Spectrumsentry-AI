"""Signal Processing & DSP Evaluation Module for Phase 9.

Validates the Phase 2 DSP pipeline:
1. Synthetic modulation generation & unit-power normalization (BPSK, QPSK, 16-QAM).
2. AWGN channel calibration across SNR dynamic range (-5 to +20 dB).
3. 23-feature extraction numerical stability and distributions across repetitions.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.signal_processing import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    SUPPORTED_MODULATIONS,
    add_awgn,
    calculate_signal_power,
    calculate_snr_db,
    extract_features,
    generate_signal,
)
from experiments.common.config import (
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_csv,
    save_json,
)
from experiments.common.plotting import plot_target_vs_measured_snr


class SignalProcessingEvaluator:
    """Scientific evaluation suite for DSP and AWGN modeling."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.signal_output_dir = self.output_dir / "signal"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed

    def evaluate_modulation_generation(self, num_samples: int = 1024) -> Dict[str, Any]:
        """Verify synthetic signal generation and unit-power normalization contracts."""
        results = {}
        for mod in ["BPSK", "QPSK", "16-QAM"]:
            gen_res = generate_signal(modulation=mod, num_samples=num_samples, seed=self.random_seed)
            sig = gen_res.signal
            measured_power = calculate_signal_power(sig)

            # Check complex representation
            is_complex = np.iscomplexobj(sig)
            power_deviation = abs(measured_power - 1.0)
            passed = is_complex and len(sig) == num_samples and power_deviation < 0.05

            results[mod] = {
                "num_samples": num_samples,
                "is_complex": bool(is_complex),
                "measured_power": round(float(measured_power), 6),
                "power_deviation_from_unity": round(float(power_deviation), 6),
                "valid": bool(passed),
            }
        return results

    def evaluate_snr_calibration(
        self,
        snr_levels: Optional[List[float]] = None,
        trials_per_level: int = 50,
        sample_count: int = 2048,
    ) -> Dict[str, Any]:
        """Evaluate AWGN channel SNR accuracy against target levels over multiple realizations."""
        if snr_levels is None:
            snr_levels = [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0]

        snr_eval_records = []
        measured_means = []
        measured_stds = []
        errors_mean = []

        # Use QPSK baseline signal
        for target_snr in snr_levels:
            trial_errors = []
            trial_measured = []
            signal_powers = []
            noise_powers = []

            for trial_idx in range(trials_per_level):
                seed = abs(self.random_seed * 1000 + int((target_snr + 50) * 100) + trial_idx)
                gen = generate_signal("QPSK", num_samples=sample_count, seed=seed)
                awgn_res = add_awgn(gen.signal, snr_db=target_snr, seed=seed)

                measured_snr = awgn_res.measured_snr_db
                err = measured_snr - target_snr

                trial_measured.append(measured_snr)
                trial_errors.append(err)
                signal_powers.append(awgn_res.signal_power)
                noise_powers.append(awgn_res.noise_power)

            mean_measured = float(np.mean(trial_measured))
            std_measured = float(np.std(trial_measured))
            mean_err = float(np.mean(trial_errors))
            mae = float(np.mean(np.abs(trial_errors)))
            max_err = float(np.max(np.abs(trial_errors)))

            measured_means.append(mean_measured)
            measured_stds.append(std_measured)
            errors_mean.append(mean_err)

            snr_eval_records.append({
                "target_snr_db": target_snr,
                "trials": trials_per_level,
                "measured_snr_mean": round(mean_measured, 4),
                "measured_snr_std": round(std_measured, 4),
                "mean_error_db": round(mean_err, 4),
                "mean_absolute_error_db": round(mae, 4),
                "max_absolute_error_db": round(max_err, 4),
                "avg_signal_power": round(float(np.mean(signal_powers)), 4),
                "avg_noise_power": round(float(np.mean(noise_powers)), 6),
            })

        # Overall summary statistics
        all_mae = [r["mean_absolute_error_db"] for r in snr_eval_records]
        overall_mae = float(np.mean(all_mae))
        overall_max_err = float(np.max([r["max_absolute_error_db"] for r in snr_eval_records]))

        return {
            "overall_mean_absolute_snr_error_db": round(overall_mae, 4),
            "overall_max_absolute_snr_error_db": round(overall_max_err, 4),
            "snr_levels": snr_eval_records,
            "_raw_for_plots": {
                "target_snrs": snr_levels,
                "measured_means": measured_means,
                "measured_stds": measured_stds,
                "errors_mean": errors_mean,
            },
        }

    def evaluate_feature_stability(
        self,
        modulations: Optional[List[str]] = None,
        snr_db: float = 15.0,
        trials: int = 50,
        num_samples: int = 1024,
    ) -> Dict[str, Any]:
        """Measure 23-feature statistical stability and coefficient of variation across realizations."""
        if modulations is None:
            modulations = ["BPSK", "QPSK", "16-QAM"]

        stability_by_mod = {}

        for mod in modulations:
            feature_matrix = []
            for t in range(trials):
                seed = self.random_seed + t
                gen = generate_signal(mod, num_samples=num_samples, seed=seed)
                awgn_res = add_awgn(gen.signal, snr_db=snr_db, seed=seed)
                feat_vec, _ = extract_features(awgn_res.noisy_signal, sample_rate=1e6)
                feature_matrix.append(feat_vec)

            mat = np.array(feature_matrix)  # (trials, 23)
            means = np.mean(mat, axis=0)
            stds = np.std(mat, axis=0)
            mins = np.min(mat, axis=0)
            maxs = np.max(mat, axis=0)

            features_stats = []
            for idx, fname in enumerate(FEATURE_NAMES):
                m = float(means[idx])
                s = float(stds[idx])
                cv = (s / abs(m)) if abs(m) > 1e-9 else 0.0
                features_stats.append({
                    "feature_name": fname,
                    "mean": round(m, 6),
                    "std": round(s, 6),
                    "min": round(float(mins[idx]), 6),
                    "max": round(float(maxs[idx]), 6),
                    "coefficient_of_variation": round(cv, 4),
                })

            stability_by_mod[mod] = {
                "trials": trials,
                "snr_db": snr_db,
                "feature_count": FEATURE_COUNT,
                "features": features_stats,
            }

        return stability_by_mod

    def run_all(self) -> Dict[str, Any]:
        """Execute complete signal and DSP evaluation experiments."""
        gen_results = self.evaluate_modulation_generation()
        snr_results = self.evaluate_snr_calibration()
        feature_stability = self.evaluate_feature_stability()

        cfg = ExperimentConfig(
            experiment_id="EXP-DSP-01",
            experiment_name="signal_dsp_calibration",
            description="Verification of synthetic modulation generation, AWGN SNR calibration, and feature stability.",
            random_seed=self.random_seed,
            parameters={
                "snr_sweep_levels": [-5.0, 0.0, 5.0, 10.0, 15.0, 20.0],
                "trials_per_level": 50,
                "modulations": ["BPSK", "QPSK", "16-QAM"],
            },
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "modulation_generation": gen_results,
            "snr_calibration": {
                "overall_mean_absolute_snr_error_db": snr_results["overall_mean_absolute_snr_error_db"],
                "overall_max_absolute_snr_error_db": snr_results["overall_max_absolute_snr_error_db"],
                "records": snr_results["snr_levels"],
            },
            "feature_stability_summary": {
                mod: {
                    "trials": data["trials"],
                    "snr_db": data["snr_db"],
                    "avg_cv": round(float(np.mean([f["coefficient_of_variation"] for f in data["features"]])), 4),
                }
                for mod, data in feature_stability.items()
            },
        }

        # Save machine-readable files
        self.signal_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_data, self.signal_output_dir / "dsp_validation.json")
        save_json(snr_results["snr_levels"], self.signal_output_dir / "snr_accuracy_results.json")
        save_csv(snr_results["snr_levels"], self.signal_output_dir / "snr_accuracy_results.csv")
        save_json(feature_stability, self.signal_output_dir / "feature_stability.json")

        # Generate plots
        raw = snr_results["_raw_for_plots"]
        plot_target_vs_measured_snr(
            target_snrs=raw["target_snrs"],
            measured_means=raw["measured_means"],
            measured_stds=raw["measured_stds"],
            errors=raw["errors_mean"],
            output_target_path=self.plots_dir / "target_vs_measured_snr.png",
            output_error_path=self.plots_dir / "snr_measurement_error.png",
        )

        return output_data

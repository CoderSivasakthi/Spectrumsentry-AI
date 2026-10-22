# SpectrumSentry AI — Scientific Experimentation & Benchmarking Guide

## Overview

Phase 9 equips SpectrumSentry AI with an automated, reproducible scientific evaluation and benchmarking suite. The framework allows engineers and researchers to evaluate AI modulation accuracy, SNR sensitivity, digital signal processing calibration, communication monitoring telemetry, multi-domain decision engine rules, end-to-end pipeline latency, and continuous system stability.

---

## 1. Directory Structure

All experiment modules, runners, reports, and plots are cleanly partitioned:

```
SpectrumSentry-AI/
├── experiments/
│   ├── common/
│   │   ├── config.py         # Standardized ExperimentConfig, metadata, JSON/CSV I/O
│   │   └── plotting.py       # Publication-grade Matplotlib plotting utilities
│   ├── ai/
│   │   ├── evaluator.py      # Baseline AI classification & calibration evaluation
│   │   └── snr_sweep.py      # Systematic 26-level SNR sweep experiment
│   ├── signal/
│   │   └── evaluator.py      # Unit power, AWGN noise calibration, feature stability
│   ├── communication/
│   │   └── evaluator.py      # Packet loss, latency, jitter, interruption/recovery
│   ├── decision/
│   │   └── evaluator.py      # Rule coverage, conflict scenarios, partial evidence
│   ├── system/
│   │   └── end_to_end.py     # 8-stage pipeline latency & lifecycle transitions
│   └── performance/
│       ├── benchmarks.py     # Component micro-benchmarks with percentile distributions
│       └── stability.py      # Continuous soak testing & memory stability tracking
├── scripts/
│   ├── run_phase9_experiments.py   # Central CLI experiment orchestrator
│   └── validate_phase9_results.py  # Automated results validator
└── reports/
    └── phase9/
        ├── ai/               # Machine-readable AI evaluation data
        ├── signal/           # DSP and SNR calibration data
        ├── communication/    # Telemetry and timeout data
        ├── decision/         # Decision Engine rule outputs
        ├── end_to_end/       # Latency breakdowns and state transitions
        ├── performance/      # Benchmarks and throughput summaries
        ├── stability/        # Soak test and memory records
        └── plots/            # High-resolution (300 DPI) publication figures
```

---

## 2. Running Experiments via Central CLI

The primary runner is `scripts/run_phase9_experiments.py`.

### Run All Experiments
To execute the full Phase 9 experimental suite:
```bash
./backend/.venv/bin/python scripts/run_phase9_experiments.py --all
```

### Run Specific Experiment Groups
You can target individual evaluation domains:
```bash
# Run only AI evaluation & SNR sweep
./backend/.venv/bin/python scripts/run_phase9_experiments.py --ai

# Run only DSP signal processing & AWGN calibration
./backend/.venv/bin/python scripts/run_phase9_experiments.py --signal

# Run only communication telemetry experiments
./backend/.venv/bin/python scripts/run_phase9_experiments.py --communication

# Run only Decision Engine rule & conflict evaluation
./backend/.venv/bin/python scripts/run_phase9_experiments.py --decision

# Run only end-to-end pipeline latency profiling
./backend/.venv/bin/python scripts/run_phase9_experiments.py --end-to-end

# Run only performance micro-benchmarks
./backend/.venv/bin/python scripts/run_phase9_experiments.py --performance

# Run only continuous soak/stability testing
./backend/.venv/bin/python scripts/run_phase9_experiments.py --stability
```

### CLI Options
- `--seed <int>`: Set deterministic random seed (default: `42`).
- `--output-dir <path>`: Set destination directory for results (default: `reports/phase9`).

---

## 3. Validating Results

After running experiments, verify the integrity, schema conformance, and non-NaN/Inf validity of all outputs:
```bash
./backend/.venv/bin/python scripts/validate_phase9_results.py
```

The validator checks:
- 17 required machine-readable JSON files.
- 7 required CSV summary files.
- 13 publication plots.
- Zero `NaN` or `Inf` values in floating-point outputs.
- Presence of experiment metadata and environment records.

---

## 4. Experiment Reproducibility

Reproducibility is enforced at the core framework level:
- Default PRNG seed is `42`.
- Every generated JSON result contains a `metadata` block recording:
  - `experiment_id`
  - `experiment_name`
  - `timestamp` (ISO 8601 UTC)
  - `random_seed`
  - `dataset_version` and `model_version`
  - `environment`: OS name, OS release, kernel version, processor architecture, Python version, NumPy version, SciPy version, scikit-learn version, and Matplotlib version.

To verify reproducibility:
```bash
./backend/.venv/bin/pytest backend/tests/test_phase9_experiments.py -k test_seed_reproducibility
```

---

## 5. Performance Measurement Methodology

Micro-benchmarking (`experiments/performance/benchmarks.py`) follows statistical standards:
- **Warmup:** 20 warmup iterations precede measurement to ensure JIT/caching stability.
- **Repetitions:** 200 repeated executions per operation.
- **Reported Percentiles:** Mean, Median (p50), 95th percentile (p95), 99th percentile (p99), Min, Max, and Throughput (ops/sec).
- **Subsystem Isolation:** ML inference is timed strictly around model forward pass, distinct from feature extraction and signal generation.

---

## 6. Interpretation Guidelines

1. **AI Classification Confidence vs Calibration:**
   - Raw softmax probabilities range between 0.0 and 1.0.
   - An Expected Calibration Error (ECE) of **0.0034** indicates model probabilities match empirical frequencies within 0.34%.
2. **Cross-Domain Decision Consistency:**
   - `CONSISTENT`: Both physical layer (SNR/AI) and network layer (loss/latency) indicate agreeing health status.
   - `CONFLICTING`: Physical layer is clean while network layer is degraded (or vice-versa), triggering `REVIEW` status for root cause differentiation.
   - `UNCORRELATED`: Only one domain has active telemetry, or signal evidence is stale ($> 5.0\text{s}$).

---

## 7. Known Limitations

- **Channel Realism:** AWGN channel modeling simulates thermal noise; fading channels (Rayleigh/Rician) and multipath interference are planned for subsequent iterations.
- **Scope of Telemetry:** Communication monitoring tracks safe, application-layer UDP/TCP telemetry. It does not inspect raw Wi-Fi 802.11 frames.
- **Low-SNR Performance:** Under $-1\text{ dB}$ SNR, QPSK and 16-QAM constellation points disperse, reducing classification accuracy to ~77%.

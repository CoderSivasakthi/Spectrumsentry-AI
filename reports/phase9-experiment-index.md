# SpectrumSentry AI — Phase 9 Experiment Index

This document provides a comprehensive index of all scientific experiments, benchmark configurations, result files, and generated publication plots produced during Phase 9.

---

## Experiment Registry

| Experiment ID | Experiment Name | Primary Purpose | Key Configuration | Machine-Readable Results | Associated Plots | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`EXP-AI-01`** | **AI Modulation Classification Baseline** | Full evaluation of Phase 4 MLP classifier on held-out test data | Test samples: 7,800<br>Seed: 42<br>Classes: BPSK, QPSK, 16-QAM | `reports/phase9/ai/classification_metrics.json`<br>`reports/phase9/ai/confusion_matrix.json`<br>`reports/phase9/ai/confidence_analysis.json` | `reports/phase9/plots/confusion_matrix.png` | **PASSED** (94.91% Acc, 0.9491 F1) |
| **`EXP-AI-02`** | **SNR Sweep Modulation Performance** | Accuracy and confidence profiling across 26 discrete SNR levels | SNR range: -5 to +20 dB<br>Step: 1.0 dB<br>300 samples / level | `reports/phase9/ai/snr_sweep_results.json`<br>`reports/phase9/ai/snr_sweep_results.csv` | `reports/phase9/plots/snr_vs_accuracy.png`<br>`reports/phase9/plots/per_class_accuracy_vs_snr.png`<br>`reports/phase9/plots/confidence_vs_snr.png` | **PASSED** (100% in high-SNR region) |
| **`EXP-DSP-01`** | **Signal Processing & AWGN Calibration** | Verification of unit power, AWGN SNR accuracy, and 23-feature stability | Levels: -5, 0, 5, 10, 15, 20 dB<br>Trials: 50 / level<br>Length: 1,024 smp | `reports/phase9/signal/dsp_validation.json`<br>`reports/phase9/signal/snr_accuracy_results.json`<br>`reports/phase9/signal/snr_accuracy_results.csv`<br>`reports/phase9/signal/feature_stability.json` | `reports/phase9/plots/target_vs_measured_snr.png`<br>`reports/phase9/plots/snr_measurement_error.png` | **PASSED** (SNR MAE: 0.0769 dB) |
| **`EXP-COMM-01`**| **Application Telemetry & Loss Profiling** | Verification of packet loss calculation and health degradation | Loss rates: 0%, 5%, 10%, 15%, 25%, 50%<br>Packets: 200 / test | `reports/phase9/communication/communication_evaluation_summary.json`<br>`reports/phase9/communication/packet_loss_results.json`<br>`reports/phase9/communication/packet_loss_results.csv` | `reports/phase9/plots/packet_loss_vs_health.png` | **PASSED** (Monotonic health curve) |
| **`EXP-COMM-02`**| **Latency Sensitivity Profiling** | Characterization of RTT percentiles and warning threshold triggers | Targets: 5, 20, 50, 100, 200 ms<br>Packets: 150 / test | `reports/phase9/communication/latency_results.json`<br>`reports/phase9/communication/latency_results.csv` | `reports/phase9/plots/latency_vs_health.png` | **PASSED** (RTT error $< 0.2\text{ ms}$) |
| **`EXP-COMM-03`**| **Jitter & Variance Evaluation** | RFC 3550 exponential jitter calculation verification | Variance $\sigma$: 0, 2, 5, 10, 20, 40 ms<br>Base RTT: 30 ms | `reports/phase9/communication/jitter_results.json`<br>`reports/phase9/communication/jitter_results.csv` | `reports/phase9/plots/jitter_vs_health.png` | **PASSED** (Jitter error $< 0.3\text{ ms}$) |
| **`EXP-COMM-04`**| **Interruption & Recovery Lifecycle** | Safe timeout silence detection and recovery capture | Silence: 2.5s ($> 2.0\text{s}$ timeout)<br>Recovery packet: seq 11 | `reports/phase9/communication/interruption_recovery_results.json` | N/A (State lifecycle flow) | **PASSED** (Exact state transition) |
| **`EXP-DEC-01`** | **Deterministic Rule Coverage & Conflict**| Evaluation of all 7 Phase 6 rules and cross-domain conflict scenarios | Rules: 7<br>Conflict scenarios: 2<br>Partial scenarios: 3 | `reports/phase9/decision/decision_rule_evaluation.json`<br>`reports/phase9/decision/decision_rule_evaluation.csv` | `reports/phase9/plots/decision_confidence_breakdown.png` | **PASSED** (7/7 rules, 2/2 conflicts) |
| **`EXP-E2E-01`** | **End-to-End Pipeline & State Transitions**| Latency profiling across 8 stages and full lifecycle flow | Iterations: 50<br>Samples: 1,024<br>6 lifecycle states | `reports/phase9/end_to_end/e2e_system_evaluation.json`<br>`reports/phase9/end_to_end/pipeline_latency_breakdown.json`<br>`reports/phase9/end_to_end/state_transitions.json` | `reports/phase9/plots/end_to_end_latency_breakdown.png` | **PASSED** (1.587 ms mean, 630 fps) |
| **`EXP-PERF-01`**| **Component Performance Benchmarking** | Distribution percentiles (mean, med, p95, p99) across 10 operations | Repetitions: 200<br>Warmup: 20<br>Batch sizes: 16, 64, 256 | `reports/phase9/performance/benchmarks_summary.json`<br>`reports/phase9/performance/benchmarks_summary.csv` | `reports/phase9/plots/ml_inference_latency_distribution.png` | **PASSED** (0.084 ms ML single pred) |
| **`EXP-STAB-01`**| **Continuous Telemetry Soak Test** | Memory leak and stability verification under sustained event load | Events: 300<br>Interval: 25<br>Signal updates: every 5 pkts | `reports/phase9/stability/soak_test_results.json` | `reports/phase9/plots/memory_stability_soak.png` | **PASSED** (0.000 MB net growth) |

---

## Directory Organization

```
reports/phase9/
├── ai/
│   ├── classification_metrics.json
│   ├── confusion_matrix.json
│   ├── confidence_analysis.json
│   ├── snr_sweep_results.json
│   └── snr_sweep_results.csv
├── signal/
│   ├── dsp_validation.json
│   ├── snr_accuracy_results.json
│   ├── snr_accuracy_results.csv
│   └── feature_stability.json
├── communication/
│   ├── communication_evaluation_summary.json
│   ├── packet_loss_results.json
│   ├── packet_loss_results.csv
│   ├── latency_results.json
│   ├── latency_results.csv
│   ├── jitter_results.json
│   ├── jitter_results.csv
│   └── interruption_recovery_results.json
├── decision/
│   ├── decision_rule_evaluation.json
│   └── decision_rule_evaluation.csv
├── end_to_end/
│   ├── e2e_system_evaluation.json
│   ├── pipeline_latency_breakdown.json
│   └── state_transitions.json
├── performance/
│   ├── benchmarks_summary.json
│   └── benchmarks_summary.csv
├── stability/
│   └── soak_test_results.json
└── plots/
    ├── confusion_matrix.png
    ├── snr_vs_accuracy.png
    ├── per_class_accuracy_vs_snr.png
    ├── confidence_vs_snr.png
    ├── target_vs_measured_snr.png
    ├── snr_measurement_error.png
    ├── packet_loss_vs_health.png
    ├── latency_vs_health.png
    ├── jitter_vs_health.png
    ├── decision_confidence_breakdown.png
    ├── end_to_end_latency_breakdown.png
    ├── ml_inference_latency_distribution.png
    └── memory_stability_soak.png
```

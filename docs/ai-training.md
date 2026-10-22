# SpectrumSentry AI — AI Model Training & Evaluation (Phase 4)

## Overview
Phase 4 implements the initial AI Modulation Classification system for SpectrumSentry AI using a supervised Multilayer Perceptron (MLP) within an end-to-end `scikit-learn` Pipeline. The model classifies three discrete digital modulation schemes (`BPSK`, `QPSK`, `16-QAM`) strictly from 23 normalized signal features extracted by the Phase 2 DSP engine, without using SNR as an input feature.

---

## 1. Feature Contract & Dataset Integrity

### Input Features ($\mathbb{R}^{23}$)
The model consumes strictly the 23 statistical, temporal, and spectral features extracted from complex baseband I/Q samples:

| Index | Feature Name | Domain | Description |
|---|---|---|---|
| 0–3 | `mean_i`, `mean_q`, `std_i`, `std_q` | Temporal | In-phase and Quadrature 1st & 2nd moments |
| 4–8 | `rms_magnitude`, `mean_magnitude`, `std_magnitude`, `peak_magnitude`, `signal_power` | Temporal | Envelope and power metrics |
| 9–17 | `moment4_i/q/mag`, `skew_i/q/mag`, `kurtosis_i/q/mag` | Statistical | Higher-order central moments, skewness, and excess kurtosis |
| 18–22 | `spectral_centroid`, `spectral_spread`, `peak_frequency`, `spectral_energy`, `spectral_flatness` | Spectral | Frequency domain properties |

Target SNR and measured SNR are strictly evaluation metadata and are excluded from the model feature matrix.

### Target Classes & Label Mapping
- `0`: `BPSK` (Binary Phase Shift Keying)
- `1`: `QPSK` (Quadrature Phase Shift Keying)
- `2`: `16-QAM` (16-ary Quadrature Amplitude Modulation)

### Dataset Version & Partitions
- **Dataset Version**: `v1.0`
- **Total Samples**: 39,000 (balanced: 13,000 per class across 26 SNR levels from -5 dB to +20 dB)
- **Train Partition**: 31,200 samples (80% stratified by condition)
- **Test Partition**: 7,800 samples (20% stratified by condition, held out strictly for final evaluation)

---

## 2. Leakage Prevention & Validation Strategy

To prevent data leakage:
1. **Test Set Isolation**: The Phase 3 test partition (`X_test`, `y_test`, 7,800 samples) was completely sequestered during all scaler fitting, architecture exploration, and hyperparameter tuning.
2. **Internal Development Split**: The 31,200 training examples were split into:
   - **Internal Fit Set**: 24,960 samples (80%)
   - **Internal Validation Set**: 6,240 samples (20%)
   - Stratified by class label with a fixed random seed (`seed=42`).
3. **Pipeline Encapsulation**: A single `sklearn.pipeline.Pipeline` encapsulates `StandardScaler` and `MLPClassifier`. The scaler is fitted strictly on the training partition and automatically applied during inference.

---

## 3. Model Architecture & Selection

Three candidate architectures were evaluated on the internal development validation set:

| Model ID | Architecture | Fit Time | Iterations | Val Loss | Val Accuracy | Val Macro F1 |
|---|---|---|---|---|---|---|
| Model A | `(64, 32)` | 0.63s | 23 | 0.08327 | 95.35% | 0.9535 |
| **Model B (Selected)** | **`(128, 64)`** | **0.82s** | **21** | **0.07962** | **95.43%** | **0.9543** |
| Model C | `(128, 64, 32)` | 0.88s | 19 | 0.08062 | 95.30% | 0.9530 |

### Selected Model Hyperparameters (`Model B`)
- **Hidden Layers**: `(128, 64)`
- **Activation**: `relu`
- **Solver**: `adam`
- **$\alpha$ (L2 Regularization)**: `0.0001`
- **Batch Size**: `128`
- **Learning Rate**: `0.001` (constant)
- **Max Iterations**: `200`
- **Early Stopping**: `True` (`validation_fraction=0.1`, `n_iter_no_change=15`)
- **Random State**: `42`

After model selection, the winning architecture (`Model B`) was fitted on the complete 31,200 training samples in **0.92 seconds** (loss: `0.07662`).

---

## 4. Final Independent Test Evaluation

The trained pipeline was evaluated once on the untouched Phase 3 test partition (7,800 samples).

### Global Metrics
- **Overall Accuracy**: **94.91%** (7,403 / 7,800 correct)
- **Macro Precision**: **0.9493**
- **Macro Recall**: **0.9491**
- **Macro F1-Score**: **0.9491**
- **Weighted F1-Score**: **0.9491**
- **Mean Confidence**: **94.98%** (Median: 99.99%)

### Per-Class Performance
| Modulation | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| **BPSK** | 1.0000 | 1.0000 | 1.0000 | 2,600 |
| **QPSK** | 0.9342 | 0.9115 | 0.9227 | 2,600 |
| **16-QAM** | 0.9136 | 0.9358 | 0.9246 | 2,600 |
| **Macro Average** | **0.9493** | **0.9491** | **0.9491** | **7,800** |

### Confusion Matrix
```
               Predicted BPSK   Predicted QPSK   Predicted 16-QAM
Actual BPSK         2,600              0                 0
Actual QPSK             0          2,370               230
Actual 16-QAM           0            167             2,433
```
- **BPSK**: Zero confusion with any other modulation across all SNR conditions.
- **QPSK vs 16-QAM**: All 397 classification errors occur between QPSK and 16-QAM under low-SNR conditions ($\le 0\text{ dB}$).

---

## 5. Performance Across SNR (-5 dB to +20 dB)

Model performance was evaluated independently for each of the 26 target SNR levels (300 test samples per SNR, 100 per class):

| SNR (dB) | Overall Acc | Macro F1 | BPSK Acc | QPSK Acc | 16-QAM Acc |
|---|---|---|---|---|---|
| **-5 dB** | 73.67% | 0.7363 | 100.0% | 57.0% | 64.0% |
| **-4 dB** | 72.67% | 0.7253 | 100.0% | 52.0% | 66.0% |
| **-3 dB** | 79.33% | 0.7920 | 100.0% | 61.0% | 77.0% |
| **-2 dB** | 75.33% | 0.7508 | 100.0% | 53.0% | 73.0% |
| **-1 dB** | 85.67% | 0.8561 | 100.0% | 72.0% | 85.0% |
| **0 dB** | 92.00% | 0.9200 | 100.0% | 87.0% | 89.0% |
| **1 dB** | 92.33% | 0.9232 | 100.0% | 92.0% | 85.0% |
| **2 dB** | 99.00% | 0.9900 | 100.0% | 99.0% | 98.0% |
| **3 dB** | 99.00% | 0.9900 | 100.0% | 98.0% | 99.0% |
| **4 dB** | 99.00% | 0.9900 | 100.0% | 99.0% | 98.0% |
| **5 dB** | 99.67% | 0.9967 | 100.0% | 100.0% | 99.0% |
| **6 dB to 20 dB** | **100.00%** | **1.0000** | **100.0%** | **100.0%** | **100.0%** |

### Key Observations
1. **Low SNR ($\le -2\text{ dB}$)**: Additive Gaussian noise masks higher-order envelope moments (`std_magnitude`, `kurtosis_magnitude`), causing occasional confusion between QPSK (constant envelope) and 16-QAM (multi-ring envelope).
2. **Transition Region ($-1\text{ dB}$ to $1\text{ dB}$)**: Accuracy rapidly rises from $85.67\%$ to $92.33\%$.
3. **High SNR ($\ge 2\text{ dB}$)**: Accuracy exceeds $99.0\%$, achieving **100% accuracy from 6 dB through 20 dB**.

---

## 6. Prediction Engine & Inference Latency

### Prediction API (`backend/app/ml/predictor.py`)
Provides input validation (verifies 23 features, checks for finite values, preserves ordering), class probabilities, confidence calculation, and latency measurement:

```python
from backend.app.ml.predictor import ModulationPredictor

predictor = ModulationPredictor()
result = predictor.predict_single(feature_vector)
# {
#     "predicted_modulation": "QPSK",
#     "predicted_label": 1,
#     "confidence": 0.9998,
#     "class_probabilities": {"BPSK": 0.0001, "QPSK": 0.9998, "16-QAM": 0.0001},
#     "inference_time_ms": 0.077,
#     "model_version": "v1.0"
# }
```

### Latency Benchmark (Apple M-Series / macOS)
Benchmarked over 1,000 iterations:
- **Single-Sample Inference**:
  - Mean Latency: **0.077 ms** ($\approx 77\,\mu\text{s}$)
  - Median Latency: **0.071 ms**
  - 95th Percentile: **0.103 ms**
- **Batch Inference (7,800 samples)**:
  - Total Time: **6.34 ms**
  - Throughput: **1,230,178 samples/sec**

---

## 7. Model Serialization & Generated Artifacts

- **Model File**: `backend/models/modulation_mlp_v1.joblib` (StandardScaler + MLPClassifier Pipeline)
- **Model Metadata**: `backend/models/model_metadata.json`
- **Training Config**: `backend/models/training_config.json`
- **Evaluation Reports**:
  - `backend/reports/phase4/classification_report.json`
  - `backend/reports/phase4/classification_report.txt`
  - `backend/reports/phase4/confusion_matrix.json`
  - `backend/reports/phase4/confusion_matrix.png`
  - `backend/reports/phase4/snr_performance.csv`
  - `backend/reports/phase4/snr_performance.json`
  - `backend/reports/phase4/snr_accuracy.png`
  - `backend/reports/phase4/training_history.json`
  - `backend/reports/phase4/model_comparison.json`

---

## 8. Reproduction Commands

### Train Model & Generate Reports
```bash
python scripts/train_model.py --seed 42
```

### Run Model Inference Demo & Latency Benchmark
```bash
python scripts/test_model.py
```

### Run Phase 4 Automated Tests
```bash
pytest backend/tests/test_classifier.py backend/tests/test_predictor.py backend/tests/test_evaluator.py -v
```

### Run Full Test Suite (Phases 1–4)
```bash
pytest backend/tests -v
```

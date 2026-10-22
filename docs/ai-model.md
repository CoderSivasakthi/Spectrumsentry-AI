# SpectrumSentry AI - AI Model Specification

## Interface Between DSP Features and AI Engine

Phase 2 establishes the feature contract consumed by the AI Modulation Classification Engine in Phase 3 & 4.

### Feature Vector Specification
The feature extraction pipeline (`backend/app/signal_processing/features.py`) maps any complex baseband signal of arbitrary sample length $N$ into a fixed-length numeric vector:

$$\mathbf{x} \in \mathbb{R}^{23}, \quad \text{dtype} = \text{float32}$$

The vector follows this exact feature order:

| Index | Feature Name | Domain | Description |
|---|---|---|---|
| 0 | `mean_i` | Time | Mean of In-phase component |
| 1 | `mean_q` | Time | Mean of Quadrature component |
| 2 | `std_i` | Time | Standard deviation of In-phase component |
| 3 | `std_q` | Time | Standard deviation of Quadrature component |
| 4 | `rms_magnitude` | Time | Root-Mean-Square signal magnitude $\sqrt{\frac{1}{N}\sum \|x[n]\|^2}$ |
| 5 | `mean_magnitude` | Time | Average envelope magnitude $\frac{1}{N}\sum \|x[n]\|$ |
| 6 | `std_magnitude` | Time | Envelope variance (discriminates constant vs variable amplitude) |
| 7 | `peak_magnitude` | Time | Peak envelope magnitude $\max \|x[n]\|$ |
| 8 | `signal_power` | Time | Average power $P = \frac{1}{N}\sum \|x[n]\|^2$ |
| 9 | `moment4_i` | Statistical | 4th central moment of In-phase component $\mathbb{E}[(I - \mu_I)^4]$ |
| 10 | `moment4_q` | Statistical | 4th central moment of Quadrature component $\mathbb{E}[(Q - \mu_Q)^4]$ |
| 11 | `moment4_magnitude` | Statistical | 4th central moment of magnitude envelope |
| 12 | `skew_i` | Statistical | Sample skewness of In-phase component |
| 13 | `skew_q` | Statistical | Sample skewness of Quadrature component |
| 14 | `skew_magnitude` | Statistical | Sample skewness of envelope |
| 15 | `kurtosis_i` | Statistical | Excess kurtosis of In-phase component |
| 16 | `kurtosis_q` | Statistical | Excess kurtosis of Quadrature component |
| 17 | `kurtosis_magnitude` | Statistical | Excess kurtosis of envelope |
| 18 | `spectral_centroid` | Spectral | Center of mass of power spectrum $\frac{\sum f_k P_k}{\sum P_k}$ |
| 19 | `spectral_spread` | Spectral | Second central moment of power spectrum (bandwidth) |
| 20 | `peak_frequency` | Spectral | Frequency bin corresponding to maximum spectral density |
| 21 | `spectral_energy` | Spectral | Total integrated spectral energy |
| 22 | `spectral_flatness` | Spectral | Ratio of geometric mean to arithmetic mean of PSD |

### Target Classes (Version 1)
1. `BPSK` (Index 0)
2. `QPSK` (Index 1)
3. `16-QAM` (Index 2)

### Implemented Model Pipeline (Phase 4)
- **Pipeline Architecture**: `sklearn.pipeline.Pipeline`
  1. `StandardScaler`: Normalizes 23 features using training statistics only (zero data leakage).
  2. `MLPClassifier`: Multi-Layer Perceptron neural network.
- **Selected Hyperparameters**:
  - Hidden Layers: `(128, 64)` (Model B selected via internal validation F1)
  - Activation: `relu`
  - Solver: `adam`
  - Regularization ($\alpha$): `0.0001`
  - Batch Size: `128`
  - Learning Rate: `0.001`
  - Early Stopping: `True` (`validation_fraction=0.1`, `n_iter_no_change=15`)
  - Random Seed: `42`
- **Model Evaluation Performance**:
  - Test Accuracy: **94.91%**
  - Test Macro F1: **0.9491**
  - Mean Confidence: **94.98%**
  - Latency: **0.077 ms / sample**
  - Performance across SNR: 100% accuracy for SNR $\ge 6\text{ dB}$, $>99\%$ for SNR $\ge 2\text{ dB}$, degrading to $73.7\%$ at $-5\text{ dB}$.
- **Serialization & Prediction**:
  - Saved Model: `backend/models/modulation_mlp_v1.joblib`
  - Predictor: `backend/app/ml/predictor.py` (`predict_single`, `predict_batch`)
  - Detailed Training Documentation: [`docs/ai-training.md`](file:///Users/sivas_mac/projects/SpectrumSentry-AI/docs/ai-training.md)


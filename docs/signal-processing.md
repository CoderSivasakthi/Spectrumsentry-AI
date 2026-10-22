# SpectrumSentry AI - Signal Processing Engine Documentation

## 1. Complex Baseband I/Q Representation

In modern digital communication, radio frequency signals are downconverted to complex baseband equivalents represented as discrete-time complex samples:

$$x[n] = I[n] + j \cdot Q[n]$$

Where:
- $I[n] = \text{Re}\{x[n]\}$ is the In-Phase component.
- $Q[n] = \text{Im}\{x[n]\}$ is the Quadrature component.
- Instantaneous Magnitude: $|x[n]| = \sqrt{I[n]^2 + Q[n]^2}$
- Instantaneous Phase: $\theta[n] = \text{atan2}(Q[n], I[n]) \in [-\pi, \pi]$

---

## 2. Supported Modulation Schemes

All modulations are normalized such that average symbol power $E[|s|^2] \approx 1.0$:

### BPSK (Binary Phase Shift Keying)
- Symbol states: $\{0, 1\}$
- Mapping:
  - $0 \to -1 + 0j$
  - $1 \to +1 + 0j$
- Constellation points: $I \in \{-1, +1\}, Q = 0$
- Normalized average power:
  $$P_{\text{BPSK}} = \frac{1}{2}((-1)^2 + 1^2) = 1.0$$

### QPSK (Quadrature Phase Shift Keying)
- Symbol states: $\{0, 1, 2, 3\}$
- 4 constellation points distributed symmetrically across all 4 quadrants:
  $$s \in \left\{ \frac{\pm 1 \pm j}{\sqrt{2}} \right\}$$
- Normalized average power:
  $$P_{\text{QPSK}} = \frac{1}{4} \sum_{k=1}^4 \left( \left(\frac{\pm 1}{\sqrt{2}}\right)^2 + \left(\frac{\pm 1}{\sqrt{2}}\right)^2 \right) = 1.0$$

### 16-QAM (16-Quadrature Amplitude Modulation)
- Symbol states: $\{0, 1, \dots, 15\}$ (4 bits/symbol)
- Grid: $I \in \{-3, -1, +1, +3\}$, $Q \in \{-3, -1, +1, +3\}$
- Unnormalized average power:
  $$E[I^2 + Q^2] = 2 \cdot \frac{(-3)^2 + (-1)^2 + 1^2 + 3^2}{4} = 2 \cdot \frac{9 + 1 + 1 + 9}{4} = 10.0$$
- Normalization scaling factor: $\frac{1}{\sqrt{10}}$
- Normalized constellation points:
  $$s_{i,q} = \frac{I_i + j \cdot Q_q}{\sqrt{10}}$$

---

## 3. AWGN Channel & SNR Modeling

The communication channel is modeled as Additive White Gaussian Noise (AWGN):

$$r[n] = s[n] + w[n]$$

Where:
- $s[n]$ is the clean transmitted signal.
- $w[n] = n_I[n] + j \cdot n_Q[n]$ is complex circular Gaussian noise.
- $n_I, n_Q \sim \mathcal{N}(0, \sigma^2)$ are independent and identically distributed.

### Power and SNR Calculations
- **Signal Power**:
  $$P_s = \frac{1}{N} \sum_{n=0}^{N-1} |s[n]|^2$$
- **Target Noise Power**:
  $$P_n = \frac{P_s}{10^{\text{SNR}_{\text{dB}} / 10}}$$
- **Variance per dimension**:
  $$\mathbb{E}[|w[n]|^2] = \mathbb{E}[n_I^2 + n_Q^2] = 2\sigma^2 = P_n \implies \sigma = \sqrt{\frac{P_n}{2}}$$
- **Measured Noise Power**:
  $$P_{n,\text{meas}} = \frac{1}{N} \sum_{n=0}^{N-1} |w[n]|^2$$
- **Measured SNR**:
  $$\text{SNR}_{\text{dB,meas}} = 10 \log_{10} \left( \frac{P_s}{P_{n,\text{meas}}} \right)$$

---

## 4. Frequency Domain & Spectral Analysis

### Fast Fourier Transform (FFT)
Computes the centered discrete spectrum using `np.fft.fft` and `np.fft.fftshift`:

$$X[k] = \sum_{n=0}^{N-1} x[n] e^{-j 2\pi k n / N}$$

- Normalized Complex Spectrum: $X_{\text{norm}}[k] = \frac{X[k]}{N}$
- Magnitude Spectrum: $|X_{\text{norm}}[k]|$
- Log Magnitude (dB): $20 \log_{10}(|X_{\text{norm}}[k]|)$
- Power Spectrum: $|X_{\text{norm}}[k]|^2$
- Log Power (dB): $10 \log_{10}(|X_{\text{norm}}[k]|^2)$

### Power Spectral Density (PSD)
Computed using Welch's averaged modified periodogram method (`scipy.signal.welch`) with Hann windowing and 50% overlap. Returns density in $\text{V}^2/\text{Hz}$ and $\text{dB}/\text{Hz}$.

---

## 5. Constellation Processing
Extracts real ($I$) and imaginary ($Q$) vectors for scatter plotting. Includes deterministic uniform decimation (`max_points=5000`) to guarantee high-performance visualization in the frontend without altering signal statistics.

---

## 6. Feature Extraction Pipeline
Transforms raw sample streams into a 23-element vector $\mathbf{x} \in \mathbb{R}^{23}$:

1. **Time-Domain Statistics**:
   - $\mu_I, \mu_Q$: Means of I and Q
   - $\sigma_I, \sigma_Q$: Standard deviations of I and Q
   - RMS Magnitude: $\sqrt{\frac{1}{N}\sum |x[n]|^2}$
   - Mean Magnitude: $\frac{1}{N}\sum |x[n]|$
   - Std Magnitude: $\sqrt{\frac{1}{N}\sum (|x[n]| - \mu_M)^2}$
   - Peak Magnitude: $\max |x[n]|$
   - Average Power: $P_s$
2. **Higher-Order Moments**:
   - 4th central moments: $\mu_4(I), \mu_4(Q), \mu_4(|x|)$
   - Skewness: $\gamma_1(I), \gamma_1(Q), \gamma_1(|x|)$
   - Excess Kurtosis: $\gamma_2(I), \gamma_2(Q), \gamma_2(|x|)$
3. **Spectral Features**:
   - Spectral Centroid: $f_c = \frac{\sum f_k P[k]}{\sum P[k]}$
   - Spectral Spread: $\sigma_f = \sqrt{\frac{\sum (f_k - f_c)^2 P[k]}{\sum P[k]}}$
   - Peak Frequency: $\arg\max_f |X(f)|$
   - Spectral Energy: $\sum P[k]$
   - Spectral Flatness: $\frac{\exp\left(\frac{1}{K}\sum \ln P[k]\right)}{\frac{1}{K}\sum P[k]}$

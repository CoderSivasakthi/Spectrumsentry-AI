# SpectrumSentry AI — Dataset Generation Specification (Phase 3)

## 1. Purpose of Phase 3
Phase 3 leverages the Phase 2 Digital Signal Processing (DSP) engine to synthesize a large-scale, class-balanced, condition-stratified, and deterministic machine learning dataset. This dataset serves as the standard training and evaluation benchmark for the AI modulation classification engine implemented in Phase 4.

---

## 2. Dataset Architecture
The dataset generation pipeline operates strictly through the Phase 2 signal-processing routines without duplicating DSP logic:

```
              DatasetConfig (Modulations, SNR Range, Samples, Seed)
                                        │
                                        ▼
             ┌───────────────────────────────────────────────────────┐
             │            Condition Loop (78 Conditions)             │
             │           Modulation (3) × Target SNR (26)            │
             └──────────────────────────┬────────────────────────────┘
                                        │
                                        ▼
             ┌───────────────────────────────────────────────────────┐
             │       Deterministic Seed Derivation (SeedSequence)    │
             │          Per-Sample Independent Random Seeds          │
             └──────────────────────────┬────────────────────────────┘
                                        │
                     ┌──────────────────┼──────────────────┐
                     ▼                  ▼                  ▼
               Phase 2 DSP         Phase 2 AWGN       Phase 2 FFT &
            Signal Generator      Channel Model      Feature Extractor
              (1024 samples)      (Target SNR)         (23 Features)
                     │                  │                  │
                     └──────────────────┼──────────────────┘
                                        │
                                        ▼
             ┌───────────────────────────────────────────────────────┐
             │            Stratified Train / Test Splitting          │
             │         80% Training (31,200) / 20% Test (7,800)      │
             │      Uniform Condition Stratification (Zero Leakage)  │
             └──────────────────────────┬────────────────────────────┘
                                        │
                                        ▼
             ┌───────────────────────────────────────────────────────┐
             │            Persistent Storage Serialization           │
             │       NPZ Feature Tensors + CSV Metadata + JSON       │
             └───────────────────────────────────────────────────────┘
```

---

## 3. Modulation Classes
The dataset supports three fundamental digital modulation schemes:
- **BPSK** (Binary Phase Shift Keying): Label `0`
- **QPSK** (Quadrature Phase Shift Keying): Label `1`
- **16-QAM** (16-Quadrature Amplitude Modulation): Label `2`

All modulations use complex baseband samples $x[n] = I[n] + j \cdot Q[n]$ with unit average symbol power ($\mathbb{E}[|s|^2] = 1.0$).

---

## 4. Signal-to-Noise Ratio (SNR) Range
- **Minimum Target SNR**: $-5\text{ dB}$
- **Maximum Target SNR**: $+20\text{ dB}$
- **Step Size**: $1\text{ dB}$
- **Total Discrete SNR Levels**: 26 levels:
  $$\{-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20\}\text{ dB}$$

Both target SNR and measured SNR (computed via $10 \log_{10}(P_s / P_{n,\text{meas}})$) are preserved for every example.

---

## 5. Dataset Size
- **Total Conditions**: $3 \text{ modulations} \times 26 \text{ SNR levels} = 78 \text{ conditions}$
- **Default Samples per Condition**: $500$
- **Total Examples ($N$)**: $78 \times 500 = 39,000$ examples
- **Configurability**: Configurable via CLI flags (e.g. `--samples-per-condition 100`, `250`, `1000`).

---

## 6. Feature Contract
Every signal example is mapped into the immutable 23-feature vector specified in Phase 2:
1. `mean_i`: Mean of In-phase component
2. `mean_q`: Mean of Quadrature component
3. `std_i`: Standard deviation of In-phase component
4. `std_q`: Standard deviation of Quadrature component
5. `rms_magnitude`: Root-mean-square signal magnitude
6. `mean_magnitude`: Mean envelope magnitude
7. `std_magnitude`: Envelope magnitude standard deviation
8. `peak_magnitude`: Maximum instantaneous magnitude
9. `signal_power`: Average signal power
10. `moment4_i`: 4th central moment of In-phase component
11. `moment4_q`: 4th central moment of Quadrature component
12. `moment4_magnitude`: 4th central moment of envelope magnitude
13. `skew_i`: Skewness of In-phase component
14. `skew_q`: Skewness of Quadrature component
15. `skew_magnitude`: Skewness of envelope magnitude
16. `kurtosis_i`: Excess kurtosis of In-phase component
17. `kurtosis_q`: Excess kurtosis of Quadrature component
18. `kurtosis_magnitude`: Excess kurtosis of envelope magnitude
19. `spectral_centroid`: Center of mass of power spectrum (Hz)
20. `spectral_spread`: Second central moment / spectral bandwidth (Hz)
21. `peak_frequency`: Frequency bin of peak spectral power (Hz)
22. `spectral_energy`: Integrated power spectrum energy
23. `spectral_flatness`: Ratio of geometric to arithmetic spectral means

---

## 7. Label Mapping
Stored in `backend/data/datasets/label_map.json`:
```json
{
  "class_to_index": {
    "BPSK": 0,
    "QPSK": 1,
    "16-QAM": 2
  },
  "index_to_class": {
    "0": "BPSK",
    "1": "QPSK",
    "2": "16-QAM"
  }
}
```

---

## 8. Random Seed Strategy & Reproducibility
- **Global Seed**: Defaults to `42`.
- **Per-Sample Independence**: NumPy's `np.random.SeedSequence(seed).generate_state(N)` derives 39,000 independent, deterministic 32-bit seeds.
- **Signal & Noise Decoupling**: Each sample seed is spawned into distinct sub-seeds for clean signal generation and Gaussian noise synthesis.
- **Guarantee**: Calling `generate_modulation_dataset(seed=42)` reproduces bit-for-bit identical $X$, $y$, and metadata. Different seeds produce distinct realizations.

---

## 9. Train / Test Split & Leakage Prevention
- **Split Ratio**: 80% Training ($31,200$ samples), 20% Testing ($7,800$ samples).
- **Stratification**: Stratified strictly across all 78 discrete conditions (`modulation_snr`). Exactly $400$ samples per condition enter training, and $100$ samples per condition enter testing.
- **Zero Data Leakage**:
  - Training and testing examples are independently generated signal streams.
  - No signal is duplicated across splits.
  - Disjoint sample IDs: $\text{Train}_{\text{IDs}} \cap \text{Test}_{\text{IDs}} = \emptyset$.
  - Disjoint sample indices: $\text{Train}_{\text{indices}} \cap \text{Test}_{\text{indices}} = \emptyset$.

---

## 10. Dataset File Structure
Saved under `backend/data/datasets/`:
1. `modulation_dataset.npz`: Complete dataset containing arrays:
   - `X`: Shape `(39000, 23)`, `dtype=float32`
   - `y`: Shape `(39000,)`, `dtype=int64`
   - `target_snr`: Shape `(39000,)`, `dtype=float32`
   - `measured_snr`: Shape `(39000,)`, `dtype=float32`
   - `sample_ids`: Shape `(39000,)`, `dtype=U32`
2. `train_test_split.npz`: Pre-partitioned train/test subsets:
   - `X_train`, `X_test`, `y_train`, `y_test`
   - `train_indices`, `test_indices`
   - `target_snr_train`, `target_snr_test`
   - `measured_snr_train`, `measured_snr_test`
3. `metadata.csv`: Tabular metadata per sample:
   - `sample_id,modulation,label,target_snr_db,measured_snr_db,random_seed,sample_count,sample_rate,noise_type,condition,split,dataset_version`
4. `feature_names.json`: List of 23 feature strings.
5. `label_map.json`: Bidirectional class mapping.
6. `dataset_info.json`: Global configuration and split metadata.
7. `dataset_statistics.json`: Computed summary metrics.

---

## 11. Generation Commands
```bash
# Default full dataset generation (39,000 samples)
./backend/.venv/bin/python scripts/generate_dataset.py

# Custom configuration (e.g. fast demo with 50 samples/condition)
./backend/.venv/bin/python scripts/generate_dataset.py \
    --samples-per-condition 50 \
    --snr-min -5 \
    --snr-max 20 \
    --snr-step 1 \
    --seed 42
```

---

## 12. Validation Commands
```bash
./backend/.venv/bin/python scripts/validate_dataset.py --dataset-dir backend/data/datasets
```
Performs 17 comprehensive checks covering file existence, matrix dimensions, class and SNR balance, absence of NaNs/Infs, and zero data leakage.

---

## 13. Known Limitations
- Version 1 features are extracted on mathematically simulated complex I/Q baseband signals with AWGN channels. Multi-path fading, Doppler shifts, and hardware SDR non-linearities are reserved for subsequent versions.

# SpectrumSentry AI - Database Architecture

## Engine
- SQLite (`storage/spectrumsentry.db`) via SQLAlchemy 2.0 and aiosqlite for async support.
- File-based array storage (`storage/experiments/EXP-XXX/`) for heavy numerical data (`.npy`).

## Schema Tables
1. **experiments**:
   - `id`: Primary key (e.g. `EXP-001`)
   - `created_at`: UTC timestamp
   - `modulation`: Target modulation (BPSK, QPSK, 16-QAM)
   - `snr_db`: Signal-to-Noise Ratio (dB)
   - `sample_count`: Total complex samples
   - `sample_rate`: Sampling rate (Hz)
   - `noise_type`: e.g. `AWGN`
   - `signal_power`: Measured signal power
   - `noise_power`: Measured noise power
   - `predicted_modulation`: AI prediction
   - `confidence`: Prediction probability (0.0 - 1.0)
   - `inference_time_ms`: Inference latency (ms)
   - `status`: Review status (`NORMAL`, `DEGRADED`, `INTERRUPTED`, `REVIEW`)
   - `model_version`: e.g. `v1.0.0-mlp`
   - `iq_file_path`: Path to `iq.npy`
   - `spectrum_file_path`: Path to `spectrum.npy`
   - `feature_file_path`: Path to `features.json`

2. **predictions**:
   - Per-inference record tracking batch/real-time predictions, probabilities distribution, and execution metadata.

3. **communication_metrics**:
   - Network/communication session metrics (packets transmitted/received, latency, packet loss, jitter).

4. **alerts**:
   - System and signal threshold alerts (SNR drops, classification anomalies, link degradation).

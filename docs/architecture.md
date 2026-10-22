# SpectrumSentry AI - Architecture

## System Overview
SpectrumSentry AI combines Artificial Intelligence, Digital Signal Processing, synthetic I/Q signal generation, communication monitoring, and experiment tracking into an offline-first, portable platform.

```
                    SpectrumSentry AI
                           |
                    React Dashboard
                           |
                      FastAPI API
                           |
       +-------------------+-------------------+
       |                   |                   |
Communication         Signal Processing      AI/ML
Monitor Engine            Engine             Engine
       |                   |                   |
       +-------------------+-------------------+
                           |
                     Decision Engine
                           |
                 +---------+---------+
                 |                   |
              SQLite             File Storage
                 |                   |
          Metadata/Results      I/Q / datasets
                 |                   |
                 +---------+---------+
                           |
                    Experiment History
```

## Phase 2 & 3 Pipeline: Signal Processing & Dataset Generation
The Digital Signal Processing (DSP) engine converts synthetic configuration parameters into high-fidelity complex baseband signals, applies calibrated physical-layer channel impairments, and extracts 23 statistical/spectral features to construct reproducible ML datasets:

```
             Signal Configuration (Modulation, N, Fs, Seed)
                               │
                               ▼
                        Modulation Engine
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
           BPSK              QPSK              16-QAM
        (±1 + 0j)      (±1±1j)/sqrt(2)   {-3,-1,1,3}/sqrt(10)
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                   Clean Complex I/Q: s[n]
                               │
                               ▼
                        AWGN Noise Engine
                 w[n] = n_I[n] + j * n_Q[n]
                               │
                               ▼
                  Noisy Signal: r[n] = s[n] + w[n]
                               │
             ┌─────────────────┼─────────────────┐
             ▼                 ▼                 ▼
          Waveform            FFT          Constellation
         (I & Q time)      (PSD & Bins)    (X/Y Decimated)
             │                 │                 │
             └─────────────────┼─────────────────┘
                               ▼
                      Feature Extraction
                23 Normalized Numeric Features
                               │
                               ▼
                Phase 3: Dataset Generation
             (78 conditions × 500 samples = 39k)
                               │
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
        X_train, y_train                    X_test, y_test
       (31,200 examples)                   (7,800 examples)
             │                                   │
             └─────────────────┬─────────────────┘
                               ▼
                Phase 4: AI Modulation Classifier
                               │
              ┌────────────────┴────────────────┐
              ▼                                 ▼
        StandardScaler                 MLPClassifier (128, 64)
    (Fitted on Train Only)           (Adam, ReLU, Early Stopping)
              │                                 │
              └────────────────┬────────────────┘
                               ▼
                      Class Probabilities
                  (BPSK, QPSK, 16-QAM) + Confidence
```

## Mathematical Formulations
- **Complex Baseband I/Q**:
  $$x[n] = I[n] + j \cdot Q[n]$$
- **Signal Power**:
  $$P_s = \frac{1}{N} \sum_{n=0}^{N-1} |s[n]|^2$$
- **AWGN Model**:
  $$r[n] = s[n] + w[n], \quad w[n] \sim \mathcal{CN}(0, \sigma^2)$$
  $$\sigma = \sqrt{\frac{P_n}{2}}, \quad P_n = \frac{P_s}{10^{\text{SNR}_{\text{dB}} / 10}}$$
- **Measured SNR**:
  $$\text{SNR}_{\text{dB}} = 10 \log_{10} \left( \frac{P_s}{P_{n,\text{meas}}} \right)$$
- **Discrete Fourier Transform (FFT)**:
  $$X[k] = \sum_{n=0}^{N-1} x[n] e^{-j 2\pi k n / N}$$
- **Power Spectral Density**:
  Welch's averaged periodogram estimator using Hann windowing.
- **Dataset Stratification & Leakage Prevention**:
  Each discrete condition $c = (\text{modulation}, \text{target\_snr})$ is independently sampled and uniformly stratified into $80\%$ training and $20\%$ testing subsets with zero cross-split sample overlap.

## Phase 5 Pipeline: Real Communication Monitoring
Phase 5 introduces application-level network telemetry between a test client and the monitoring server:

```
  Test Client (Device B)                       Monitoring Server (Device A)
 ┌──────────────────────┐                     ┌───────────────────────────────┐
 │ Numbered Packet Gen  │                     │ Packet Ingestion & Validation │
 │ Sequence: 1, 2, ...  │─── HTTP POST ──────►│ Sequence Continuity / Gaps    │
 │ Sender Timestamp     │    /api/communication/│ Latency & Jitter Estimator    │
 │ Payload (1KB default)│    packet           │ Interruption / Recovery Engine│
 └──────────────────────┘                     │ Health Scoring (0–100)        │
            ▲                                 └──────────────┬────────────────┘
            │                                                │
            │                                 ┌──────────────┴────────────────┐
            │                                 ▼                               ▼
            └──────── ACK Response ───────── SQLite DB               WebSocket Stream
                     (Status, Health, RTT)  (Sessions & Events)      (/ws/communication)
```

### Telemetry Formulation:
- **Packet Loss**:
  $$\text{Loss } (\%) = \left(\frac{\text{Expected} - \text{Received}}{\text{Expected}}\right) \times 100$$
- **Round-Trip Time (RTT)**:
  $$\text{RTT}_{\text{ms}} = (T_{\text{recv}} - T_{\text{send}}) \times 1000$$
- **Application Jitter**:
  $$J = \frac{1}{K-1} \sum_{i=2}^K |\text{RTT}_i - \text{RTT}_{i-1}|$$
- **Interruption Detection**:
  $$\text{Timeout Condition}: \Delta t_{\text{silence}} = t_{\text{current}} - t_{\text{last\_packet}} > 2.0\text{ s} \implies \text{INTERRUPTED}$$
- **Health Score**:
  Normalized $0–100$ score penalized by packet loss, latency excess ($>100\text{ ms}$), jitter excess ($>30\text{ ms}$), and interruption state.

## Phase 6 Pipeline: Cross-Domain Decision Engine
Phase 6 implements the explainable, deterministic evidence-correlation layer uniting physical-layer signal classification with application-layer telemetry:

```
          ┌───────────────────────────────────┐     ┌───────────────────────────────────┐
          │     Domain A: Physical / AI       │     │    Domain B: Comm Monitoring      │
          │  - Modulation & Confidence        │     │  - Packet Loss, Latency, Jitter   │
          │  - Measured SNR & Quality Tier    │     │  - Interruption / Recovery State  │
          └─────────────────┬─────────────────┘     └─────────────────┬─────────────────┘
                            │                                         │
                            └────────────────────┬────────────────────┘
                                                 ▼
                                     Phase 6 Decision Engine
                                  (Deterministic Rule Precedence)
                                                 │
                                                 ▼
                                      Evidence Correlation
                                                 │
                        ┌────────────────────────┼────────────────────────┐
                        ▼                        ▼                        ▼
                  Overall Status        Decision Confidence          Consistency
            (NORMAL, DEGRADED, REVIEW)     (0.00 – 1.00)       (CONSISTENT, CONFLICTING)
                        │                        │                        │
                        └────────────────────────┴────────────────────────┘
                                                 │
                                                 ▼
                                           Decision Record
                                      - Primary Reason & Factors
                                      - Rule IDs & Recommendations
                                      - Automated SQLite Alert Generation
```

## Phase 7 Pipeline: Unified Real-Time Integration
Phase 7 creates the unified real-time aggregation and streaming pipeline that continuously correlates asynchronous physical-layer signal evidence and network packet telemetry:

```
        Communication Packet Ingest (Phase 5)         Signal Evidence Update (Phase 4)
                       │                                             │
                       ▼                                             ▼
             PacketMonitor Engine                           Signal Evidence Cache
         (Loss, Latency, Jitter, Health)               (Freshness Check: Max 30.0s Age)
                       │                                             │
                       └──────────────────────┬──────────────────────┘
                                              ▼
                                Phase 7 Unified Manager
                           (Evidence Aggregation & Validation)
                                              │
                                              ▼
                                 Phase 6 Decision Engine
                            (Deterministic Decision Evaluation)
                                              │
                                              ▼
                                 Unified Monitoring Snapshot
                       ┌──────────────────────┴──────────────────────┐
                       ▼                                             ▼
                 REST Status API                           WebSocket Streaming
            GET /api/monitoring/status                       /ws/monitoring
                       │                                             │
                       └──────────────────────┬──────────────────────┘
                                              ▼
                                Phase 8 Real-Time Dashboard UI
```

### Key Integration Architectural Attributes:
1. **Correlation Session**: Unified monitoring sessions track physical signal parameters, communication packet continuity, decision records, and system alerts under a common `monitoring_session_id`.
2. **Signal Freshness Guard**: Signal observations are timestamped and assigned an age. Exceeding `MAX_SIGNAL_EVIDENCE_AGE_SECONDS` flags evidence as `stale=True`, ensuring stale physical data does not distort active real-time operational decisions.
3. **Dual WebSocket Compatibility**: The primary stream `/ws/monitoring` broadcasts rich cross-domain snapshots (`monitoring_snapshot`, `signal_update`, etc.), while `/ws/communication` remains 100% backward-compatible for legacy packet telemetry.
4. **Resilient Non-Blocking Processing**: Packet ingestion in Phase 5 is never blocked by decision evaluation or WebSocket streaming; tasks are dispatched asynchronously.

## Phase 8 Pipeline: Professional Real-Time Dashboard & Signal History
Phase 8 introduces the interactive, responsive user interface built on React 18, TypeScript, Vite, and Tailwind CSS.

```
       Phase 7 Backend (/api/monitoring/* & /ws/monitoring)
                             │
                             ▼
                 Frontend API & WebSocket Client
                   (Axios + Auto-reconnecting WS)
                             │
                             ▼
                    MonitoringContext Store
             (State, Bounded 60-pt History, Timeline)
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    Dashboard View      History View        About View
  - System Status      - SQLite Sessions   - 8-Phase Flow
  - Comm Telemetry     - Duration / Date   - DSP/AI Stack
  - Signal / AI        - Inspection Modal  - SDR Disclaimer
  - Decision Engine
  - Real-time Chart
  - Active Alerts
  - Event Timeline
  - Session Controls
```

### Dashboard Core Guarantees:
1. **Display Fidelity**: UI displays backend decisions (`NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`) and consistency without client-side recalculation.
2. **Bounded Buffer**: Live SVG telemetry maintains a strictly capped 60-point buffer to prevent memory leakage during continuous monitoring sessions.
3. **Responsive Layout**: Reorganizes cleanly across desktop (1440px+), tablet (768px), and mobile (390px) devices.
4. **Zero Fabrication**: Unavailable physical attributes (e.g., raw IQ waveforms without SDR) are displayed as unavailable rather than fabricated.

## Phase 9 Architecture: Scientific Evaluation, Experimentation & Benchmarking

Phase 9 establishes the scientific verification layer evaluating the complete SpectrumSentry AI system across physical signal processing, neural modulation classification, network telemetry monitoring, and cross-domain decision correlation.

```
       Phase 1–8 Production Architecture
                     │
                     ▼
       Phase 9 Experimentation Framework (experiments/)
                     │
      ┌──────────────┼──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼
  AI Evaluator   DSP Evaluator  Comm Evaluator Decision Eval   System/E2E
 (7.8k test split (AWGN sweeps,  (Loss, RTT,    (7 rules,      (8-stage lat,
  ECE, conf)     23-feat CV)     jitter, IR)    conflicts)      lifecycle)
      │              │              │              │              │
      └──────────────┴──────────────┼──────────────┴──────────────┘
                                    ▼
                     Benchmarker & Stability Soak Tester
                   (200 iterations, 300 cycles memory tracking)
                                    │
                                    ▼
                       Experiment Config & Metadata
                         (Pinned seed=42, PRNG logging)
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
        Structured Data Outputs        Publication Plots (300 DPI)
         (17 JSON, 7 CSV files)         (13 matplotlib figures)
                     │                             │
                     └──────────────┬──────────────┘
                                    ▼
                     Automated Results Validator
                   (Zero NaN/Inf, schema conformance)
```

### Key Evaluation Guarantees:
1. **Zero Data Fabrication:** Every reported metric is generated from actual runs over the held-out test split (`7,800` signals) and live software execution.
2. **Strict Determinism:** Experiments utilize a default random seed (`42`), logging full system environment specifications (OS, Python, package versions).
3. **Subsystem Isolation:** Micro-benchmarking cleanly separates pure ML inference (0.084 ms) from statistical feature extraction (1.057 ms) and full pipeline latency (1.587 ms).
4. **Validation Pipeline:** Automated verification (`validate_phase9_results.py`) ensures artifact completeness, bounded distributions, and numerical sanity.


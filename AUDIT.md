# SpectrumSentry AI — Repo Audit vs Corrected Technical Report v1.1

**Scope:** `CoderSivasakthi/Spectrumsentry-AI` backend/frontend code, audited item-by-item against
*SpectrumSentry_AI_Corrected_Report (1).pdf* (Appendix A: 15 corrections; Appendix B: reference code).

**Verdict:** Strong production skeleton (FastAPI + React + SQLite + tests), but it implements the
**original pre-correction science**. The two most important fixes of the corrected report —
phase-robust cumulant features and the novelty (REVIEW) detector — are **missing**.

---

## Correction-by-correction status

| # | Corrected-report fix | Status in repo | Evidence |
|---|---|---|---|
| 1 | Sender must be **phone browser JS** page | ❌ Missing | Only `scripts/communication_client.py` (runs on the laptop). No `/sender` HTML route in FastAPI or sender page in React. Real hotspot test from a phone is impossible. |
| 2 | RTT measured on **sender clock** | ✅ Implemented | `PacketIn.client_rtt_ms` preferred in `packet_monitor.py:200`; Python client sends previous-ack RTT (`communication_client.py:87`). |
| 3 | Message‑loss semantics (TCP hides radio loss) | ✅ Mostly | Sequence‑gap based expected/lost computation in `metrics.py`; still called "packet_loss" everywhere. |
| 4 | One **random stream per dataset** (no repeated defaults) | ✅ Implemented | `dataset.py` uses `SeedSequence` child seeds per sample (reproducible **and** diverse). |
| 5 | **Phase‑robust cumulant features** (6 features) | ❌ Missing | `features.py` has 23 moment/spectral features; word "cumulant" appears nowhere in backend. Report showed this drops accuracy 98%→53.8% under random carrier phase. |
| 6 | **FFT not a classifier input** (flat spectrum at 1 sps) | ❌ Not fixed | Spectral features (centroid, flatness, peak frequency, energy) still in the 23‑feature vector. |
| 7 | **One decision function**, fixed priority | ✅ Implemented (better) | `decision/rules.py`: priority‑ordered rules 100→10, DEGRADED + REVIEW present. Repo adds cross‑domain conflict rules (arguably an upgrade). |
| 8 | **SNR‑aware novelty detector** for unsupported modulations | ❌ Missing | `backend/app/ml/anomaly.py` is a **placeholder stub** — one line, no code. Nothing flags REVIEW for unseen modulations. |
| 9 | Don't use simulated SNR in real‑link decisions | ⚠️ Partial | Rules only apply SNR to experiment/simulated evidence, but there is no real‑link SNR/RSSI substitute either (see #13). |
| 10 | **WAITING state**, monotonic clock, 3‑packet recovery | ⚠️ Mixed | Startup false alert fixed (`interruption.py:56` returns `None` before first packet) ✔. But uses `time.time()` wall clock (`packet_monitor.py:489`) instead of `time.monotonic()` ✗, and recovery opens on the **first packet** (`recovery.py`) instead of N=3 consecutive ✔✗. |
| 11 | Don't overclaim "Anomaly Detection" | ❌ Same overclaim | README + app description still say "Anomaly Detection Platform" while the anomaly module is an empty stub. |
| 12 | Data model: alerts can come from monitor; run is root | ✅ Implemented | `models.py`: `Alert`, `DecisionRecord`, `CommunicationSession`/`CommunicationEvent` independent of `Experiment`. Decision engine creates alerts (`engine.py:114`). |
| 13 | Optional **Wi‑Fi RSSI** stream | ❌ Missing | No RSSI/netsh/iw code anywhere in backend, scripts, or frontend. |
| 14 | Measurable pass/fail criteria | ✅ Implemented | 13+ pytest files under `backend/tests`, `scripts/validate_*`, experiment evaluators. |
| 15 | Single‑HTML dashboard first, React later | ⚠️ Different | Repo went straight to React/Vite — heavier but workable; more moving parts to install. |

## Additional runtime gaps found

1. **No trained model ships with the repo** — `backend/models/` is empty (`.gitkeep` only). The AI
   API cannot respond until the dataset is generated and the model trained (~39,000 samples, 1024
   samples each with default settings).
2. **Test sample length differs from the report** — repo uses 1024 samples/frame vs the report's
   128 symbols; the report's 16‑QAM vs 64‑AM confusion result may not transfer directly.
3. Thresholds differ from the report's starting values (loss 5% vs 10%, latency 100 ms vs 300 ms,
   jitter 30 ms) — legitimate as starting points, but the report requires justification per TC‑09.
4. Installer scripts reference macOS Homebrew paths (`/opt/homebrew/bin/python3.12`) — no true
   Windows testing.

---

## Verification run (done on this machine, Windows 11, Python 3.13, Node 22)

| Check | Result |
|---|---|
| Backend imports (numpy/scipy/sklearn/fastapi/uvicorn/joblib) | ✅ OK |
| Full pytest suite | ✅ **149/149 passed** (was 138 passed + 4 failed before model training; failures were all "no trained model") |
| Backend server boots (`uvicorn backend.app.main:app`) | ✅ 22 API endpoints live (`/openapi.json`) |
| Stream A end-to-end (client → server, injected 3 s pause) | ✅ 26 packets, 0% loss, RTT 6–42 ms, **1 interruption (3.26 s) + 1 recovery detected** — matches corrected report TC‑02/TC‑03 |
| Dataset generation + MLP training | ✅ 94.4% test accuracy (reduced demo set: 200 samples/condition, 15.6k total); 100% accuracy at ≥16 dB, ~70% at −5 dB |
| Live AI classification (demo script) | ✅ 16‑QAM predicted, 99.8% confidence @ 22 dB |
| Decision engine cross-domain test | ✅ Strong SNR + injected 80% loss → **REVIEW / CONFLICTING** with actionable recommendations |
| React dashboard (`vite dev`, port 5173) | ✅ Renders and starts live monitoring sessions |

### Additional Windows issues found while running (add to fix list)

8. **Windows console encoding crash** — `scripts/communication_client.py`, `scripts/generate_dataset.py`
   and the training script all print Unicode symbols (✓/✗/→) and crash on Windows' default
   cp1252 console. Workaround used: `PYTHONIOENCODING=utf-8`. Fix: avoid non-ASCII symbols or
   call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at script start.
9. **Latency fallback explodes on clock mismatch** — if a packet omits `client_rtt_ms`, the server
   computes `(arrival_time - sender_timestamp) * 1000` from two different clocks; sending
   `sender_timestamp=0.0` yields `1,792,664,712,819 ms` and poisons the health score. Fix: the
   fallback should require a sender timestamp within a sane window, else ignore the packet latency.
10. **`backend/app/ml/anomaly.py` stub breaks no tests** — the novelty-detector role is silently
    absent; pytest `test_predictor` skips make it look covered when it is not.

## Score

- **App architecture / engineering: excellent** (structure, tests, DB, persistence, WebSocket).
- **Scientific alignment with the corrected report: ~4/15 fixes present**, with the two
  scientific linchpins (#5 cumulants, #8 novelty detector) absent.

## Recommended fix plan (priority order)

1. Port `features_cumulant()` from report B.1 into `signal_processing/features.py` as an added
   feature set (create a v2 feature contract; keep the 23 features for comparison).
2. Implement `NoveltyDetector` (report 8.2/B.1) in `ml/anomaly.py`; attach `is_outlier` to every
   prediction; let decision rules treat outlier → REVIEW.
3. Phase‑robustness experiment: retrain with random carrier phase, confirm ≥95% at ≥10 dB (TC‑08).
4. Add `/sender` browser page (port of report B.4) + phone‑based hotspot run (TC‑01–TC‑04).
5. `RecoveryDetector`: require 3 consecutive packets; switch tracker clock to `time.monotonic()`.
6. Add optional `rssi.py`/endpoint from report B.5.
7. Tone down "Anomaly Detection" branding to match V1 reality (report #11).

---

## Fix plan implementation results (2026-10-23)

All 7 audit items plus the 3 Windows runtime issues were implemented and tested. Full suite
after all changes: **212/212 passed** (was 149 before the fix plan).

| # | Fix | Status | Where |
|---|---|---|---|
| 1 | Phase-robust cumulant v2 feature contract | ✅ DONE | `backend/app/signal_processing/cumulants.py` — 6 features `m20_abs, c40_abs, c41_abs, c42_real, amplitude_mean, amplitude_std`; exact phase invariance (max diff 0.0 across random rotations, 30-unit-test suite) |
| 2 | Real `NoveltyDetector` + `is_outlier` → REVIEW rule | ✅ DONE | `backend/app/ml/anomaly.py` (IsolationForest, SNR-aware fit ≥10 dB); flag merged into every prediction in `ml/predictor.py`; `decision/rules.py` rule `NOVELTY_OUTLIER` (priority 85) → REVIEW (CONFLICTING / UNCORRELATED) |
| 3 | Phase-robustness retrain (TC-08, ≥95% @ ≥10 dB) | ✅ **PASS** | `scripts/train_cumulant_model.py` + `--with-v1-control`; see experiment table below |
| 4 | `/sender` phone browser page | ✅ DONE | `backend/app/static/sender.html` served at `http://127.0.0.1:8000/sender`; sender-clock RTT (`client_rtt_ms` from previous round trip, fix #2) |
| 5 | 3-consecutive-packet recovery + `time.monotonic()` | ✅ DONE | `backend/app/communication/recovery.py` (`RecoveryDetector(required_consecutive=3)`, gap resets the confirmation window); `packet_monitor.py` clocks all ingest/timeout paths on monotonic time |
| 6 | Optional Wi-Fi RSSI stream | ✅ DONE | `backend/app/communication/rssi.py` + `GET /api/communication/wifi/rssi` (netsh % → dBm estimate `q/2−100`, `iw link` parsimony, graceful `available:false`) |
| 7 | Honest "Novelty/Anomaly" wording | ✅ DONE | `/sender` page and route docs describe the outlier flag as "novelty check", no "anomaly detection" overclaims |
| 8 | cp1252 Unicode console crashes | ✅ DONE | `scripts/_bootstrap.py` forces UTF-8 stdio; injected into all 10 CLI scripts |
| 9 | Latency fallback clock-mismatch explosion | ✅ DONE | one-way fallback only trusted within `COMMUNICATION_LATENCY_FALLBACK_MAX_SECONDS` (30 s) sane window; `sender_timestamp=0.0` now ignored, not `1.7e12 ms` |
| 10 | Stub `ml/anomaly.py` | ✅ DONE | fully implemented + 14 tests + decision-rule integration |

### TC-08 experiment: phase-robustness under random carrier phase

Frames get a uniform random carrier phase `e^{jφ}, φ∈[0,2π)` per frame (report B.3 protocol):

```
Cumulant v2 accuracy @ >= 10 dB : 1.0000  ->  TC-08 PASS (gate 0.95)
Legacy v1 (random phase)        : 0.9924  ->  gap to cumulant: -0.0076
```

Per-SNR: v2 hits 1.000 from +10 dB up; v1 dips to 0.983-0.989 in places.

**Honest nuance — the corrected report's 53.8% v1 collapse did NOT reproduce with this
repo's 23-feature set.** Frame-size sweep under random phase:

| frame | v1 high-SNR acc | v2 high-SNR acc |
|---|---|---|
| 128 | 0.982 | 0.997 |
| 1024 | 0.989 | 1.000 |

Explanation: this repo's v1 feature set includes several phase-invariant envelope/magnitude
features (band power, |x| stats, spectral shape), so per-frame constant random phase is
handled in practice. The report's collapse likely stems from its reference implementation's
smaller/more phase-loaded feature set. The audit verdict stands but is re-framed: v2's
advantage is **robustness by construction** (mathematical invariance of |m20|,|c40|,|c41| to
rotation), not mere empirical survival; it is equal-or-better in every measured cell, and the
6-feature contract also decouples the model from noise-power leakage.

### New artifacts

- `backend/models/modulation_mlp_v2.joblib` + `model_metadata_v2.json` (6-feature contract, TC-08 pass)
- `backend/models/novelty_detector.joblib` (legacy 23-feature contract, SNR-aware ≥10 dB)
- `backend/models/novelty_detector_cumulant.joblib` (6-feature contract, SNR-aware ≥10 dB)
- `backend/data/datasets/cumulant_v2/` (random-phase dataset)
- `backend/models/modulation_mlp_v1.joblib` retrained under random phase as the honest control

### How the live app picks a model (fix #8 wiring)

`settings.py` now prefers the v2 contract with automatic fallback:

- `AI_MODEL_PATH` = `modulation_mlp_v2.joblib` (default), `AI_MODEL_FALLBACK_PATH` = legacy v1
- The unified monitor resolves the model → picks `AI_NOVELTY_DETECTOR_CUMULANT_PATH` for the
  6-feature contract and `AI_NOVELTY_DETECTOR_PATH` for the legacy contract, AND falls back to
  the legacy model when incoming evidence carries 23 features, so v1-era clients keep working.
- Override via `.env` (e.g. `AI_MODEL_PATH=backend/models/modulation_mlp_v1.joblib`) to pin
  the legacy contract.

**Note:** the running backend must be restarted to pick up `/sender`, `wifi/rssi` and the v2
model (uvicorn started without `--reload`).

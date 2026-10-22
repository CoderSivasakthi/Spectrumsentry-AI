# SpectrumSentry AI — Decision Engine Specification (Phase 6)

## 1. Executive Overview
Phase 6 establishes the unified, explainable Decision Engine for SpectrumSentry AI. It deterministically combines physical-layer Digital Signal Processing / AI modulation classification evidence with application-layer network telemetry to generate an authoritative, contextual assessment of communication health.

The Decision Engine answers six core operational questions:
1. **What is the current communication state?** (`NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`).
2. **How confident is the overall decision?** (Normalized probability score between $0.00$ and $1.00$).
3. **What evidence caused the decision?** (Primary explanatory statement).
4. **Which metrics contributed to the decision?** (Granular contributing factors).
5. **Are the signal and communication observations consistent or conflicting?** (`CONSISTENT`, `CONFLICTING`, `UNCORRELATED`).
6. **What corrective actions are recommended?** (Actionable operator guidance).

```
                  INPUT EVIDENCE
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
   SIGNAL / AI EVIDENCE       COMMUNICATION EVIDENCE
  - Predicted Modulation     - Packet Loss (%)
  - AI Confidence            - RTT Latency (ms)
  - Estimated SNR (dB)       - Jitter (ms)
  - Signal Quality Tier      - Throughput (Mbps)
                             - Interruption / Timeout
                             - Recovery State
                             - Communication Health
          │                           │
          └─────────────┬─────────────┘
                        ▼
                 DECISION ENGINE
         (Deterministic Rule Precedence)
                        │
                        ▼
               EVIDENCE CORRELATION
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
       STATUS       CONFIDENCE    CONSISTENCY
    (NORMAL, etc.)   (0.0-1.0)     (CONSISTENT,
                                  CONFLICTING)
          │             │             │
          └─────────────┼─────────────┘
                        ▼
                 DECISION RESULT
          (Explanations & Recommendations)
```

---

## 2. Evidence Input Contracts

### A. Domain A: Signal / AI Evidence (`SignalEvidence`)
- `predicted_modulation`: Classified modulation scheme (`BPSK`, `QPSK`, `16-QAM`) from Phase 4 MLP.
- `confidence`: Maximum softmax class probability ($0.0$ to $1.0$).
- `probabilities`: Complete posterior distribution across all three classes.
- `measured_snr_db`: Calibrated or measured Signal-to-Noise Ratio in dB.
- `signal_quality`: Qualitative tier (`EXCELLENT` $\ge 12\text{ dB}$, `GOOD` $\ge 5\text{ dB}$, `FAIR` $\ge 0\text{ dB}$, `POOR` $< 0\text{ dB}$).
- `signal_power` / `noise_power`: Baseband I/Q power measurements.

### B. Domain B: Communication Evidence (`CommunicationEvidence`)
- `status`: Phase 5 lifecycle state (`STARTING`, `CONNECTED`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `STOPPED`).
- `health_score`: SpectrumSentry Communication Health Score ($0.0$ to $100.0$).
- `packet_loss_percent`: Percentage of missing sequence numbers ($0.0\%$ to $100.0\%$).
- `avg_latency_ms`: Mean round-trip latency in milliseconds.
- `jitter_ms`: Mean variation in consecutive packet latencies.
- `throughput_mbps`: Measured application-level throughput in Mbps.
- `is_interrupted`: Boolean flag indicating active silence timeout ($> 2.0\text{ s}$).
- `interruption_count`: Cumulative number of detected silence timeouts.
- `recovery_count`: Cumulative number of successful recovery resumptions.

---

## 3. Communication States & Consistency Assessment

### Overall Communication Statuses (`OverallStatus`)
1. **`NORMAL`**: Physical signal meets SNR and confidence thresholds, and application-layer transport exhibits zero/negligible loss and nominal latency.
2. **`DEGRADED`**: Link operates under sub-optimal conditions — elevated packet loss ($\ge 5\%$), high latency ($\ge 100\text{ ms}$), elevated jitter ($\ge 30\text{ ms}$), or low SNR ($< 0\text{ dB}$).
3. **`INTERRUPTED`**: Complete link silence exceeding the timeout threshold ($> 2.0\text{ s}$).
4. **`RECOVERING`**: Transient stabilization state immediately following an interruption resolution.
5. **`REVIEW`**: Cross-domain diagnostic divergence requiring human operator inspection.

### Evidence Consistency (`ConsistencyStatus`)
- **`CONSISTENT`**: Physical and application layers corroborate each other (e.g. clean signal with clean packet delivery, or negative SNR with high packet loss).
- **`CONFLICTING`**: Cross-domain mismatch (e.g. pristine $18\text{ dB}$ SNR with severe $25\%$ packet loss, or $100\%$ healthy packet transport with very low AI classification confidence).
- **`UNCORRELATED`**: Evidence available from only one domain, or metrics exhibit orthogonal characteristics.

---

## 4. Deterministic Rule Hierarchy

Rules are evaluated in strict priority order to prevent ambiguous decisions:

| Priority | Rule ID | Category | Trigger Condition | Resulting Status | Consistency |
|---|---|---|---|---|---|
| **100** | `RULE_INTERRUPTED_LINK` | Comm | `is_interrupted == True` or `status == "INTERRUPTED"` | `INTERRUPTED` | `CONSISTENT` / `UNCORRELATED` |
| **90** | `RULE_RECOVERING_LINK` | Comm | `status == "RECOVERING"` | `RECOVERING` | `CONSISTENT` |
| **80** | `RULE_CONFLICT_HIGH_SNR_HIGH_LOSS` | Cross-Domain | `measured_snr_db >= 10.0` and `packet_loss_percent >= 15.0%` | `REVIEW` | `CONFLICTING` |
| **75** | `RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE` | Cross-Domain | `health_score >= 90.0` and `loss == 0%` and `confidence < 0.70` | `REVIEW` | `CONFLICTING` |
| **60** | `RULE_DEGRADED_NETWORK` | Comm | `loss >= 5%` or `latency >= 100ms` or `jitter >= 30ms` or `health < 75` | `DEGRADED` | `CONSISTENT` / `UNCORRELATED` |
| **50** | `RULE_DEGRADED_SIGNAL` | Signal | `measured_snr_db < 0.0 dB` or `signal_quality in ("POOR", "VERY_LOW")` | `DEGRADED` | `CONSISTENT` / `UNCORRELATED` |
| **10** | `RULE_NORMAL_OPERATION` | General | All metrics reside within nominal baseline thresholds | `NORMAL` | `CONSISTENT` |

---

## 5. Decision Confidence Formulation

The Decision Engine computes an explainable confidence value $C \in [0.0, 1.0]$:

1. **Active Interruption**:
   Certainty of active silence is authoritative based on monotonic socket timing:
   $$C = 0.98$$
2. **Conflicting Evidence (`REVIEW`)**:
   Cross-domain divergence reduces diagnostic certainty:
   $$C = 0.65$$
3. **Dual-Domain Consistent Evidence**:
   Confidence is weighted across physical classification confidence $S_{\text{conf}}$ and network health $H_{\text{comm}}$:
   $$C = \text{clip}\left(0.5 \times S_{\text{conf}} + 0.5 \times \frac{H_{\text{comm}}}{100.0}, \ 0.85, \ 0.99\right)$$
4. **Single-Domain Available**:
   Confidence is scaled to reflect single-sided visibility ($0.70 - 0.95$).

---

## 6. Database Schema & Alert Integration

Persisted in SQLite database (`storage/spectrumsentry.db`):
- **Table `decision_records`**:
  - `id`: Primary key.
  - `timestamp`: UTC datetime.
  - `overall_status`: `NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`.
  - `decision_confidence`: Float score.
  - `consistency`: `CONSISTENT`, `CONFLICTING`, `UNCORRELATED`.
  - `primary_reason`: Text summary.
  - `contributing_factors`: JSON array of string metrics.
  - `rules_triggered`: JSON array of rule IDs.
  - `signal_summary` / `communication_summary`: JSON dictionaries.
  - `recommendations`: JSON array of actionable steps.

### Automated Alert Generation:
When an evaluated decision results in `INTERRUPTED`, `DEGRADED`, or `REVIEW`:
- An entry is automatically inserted into the `alerts` table.
- **`INTERRUPTED`**: Dispatches `severity="CRITICAL"`, `category="COMMUNICATION"`.
- **`DEGRADED`**: Dispatches `severity="WARNING"`, `category="COMMUNICATION"`.
- **`REVIEW`**: Dispatches `severity="WARNING"`, `category="SYSTEM"`.

---

## 7. REST API Endpoints

- `POST /api/decision/evaluate`: Evaluates explicit evidence payload (`DecisionInput` $\to$ `DecisionResult`).
- `GET /api/decision/latest`: Gathers latest live communication session and signal experiment to produce real-time decision.
- `GET /api/decision/rules`: Returns full list of active decision rules and priority ordering.
- `GET /api/decision/history`: Returns paginated history of past decision evaluations.

---

## 8. Strictly Maintained Constraints

1. **Zero Retraining**: Phase 4 MLP model pipeline ([`backend/models/modulation_mlp_v1.joblib`](file:///Users/sivas_mac/projects/SpectrumSentry-AI/backend/models/modulation_mlp_v1.joblib)) remains untouched.
2. **Contract Preservation**: Phase 2 23-feature vector contract ($\mathbb{R}^{23}$) is unmodified.
3. **No Root-Cause Fallacies**: The Decision Engine does not claim to detect RF jamming or cyber attacks; it reports observable metric degradation and cross-domain divergence.

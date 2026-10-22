# SpectrumSentry AI — Real-Time Unified Integration Specification (Phase 7)

## 1. Executive Overview

Phase 7 creates the unified, real-time integration layer connecting physical-layer AI classification (Phase 4), application-layer communication monitoring (Phase 5), and the deterministic Decision Engine (Phase 6). It synthesizes cross-domain evidence into unified monitoring snapshots, streamable over WebSockets and pollable via REST APIs, establishing the operational foundation for future dashboard visualization (Phase 8).

```
                      PHYSICAL / AI DOMAIN (Phase 4)
                  [Modulation, Confidence, SNR, Quality]
                                    │
                                    ▼
       ┌────────────────────────────────────────────────────────┐
       │             PHASE 7 UNIFIED AGGREGATOR                 │
       │                                                        │
       │   1. Collect Communication & Signal Evidence           │
       │   2. Validate Freshness (MAX_SIGNAL_EVIDENCE_AGE_SEC)  │
       │   3. Build Unified Evidence Payload                    │
       │   4. Invoke Deterministic Phase 6 Decision Engine      │
       │   5. Construct Unified Monitoring Snapshot             │
       └────────────────────────────┬───────────────────────────┘
                                    │
                                    ▼
                   APPLICATION TELEMETRY (Phase 5)
               [Packet Loss, Latency, Jitter, Health]
                                    │
                                    ▼
                      DECISION ENGINE (Phase 6)
               [Status, Severity, Confidence, Reasons]
                                    │
                     ┌──────────────┴──────────────┐
                     ▼                             ▼
             REST API ENDPOINTS           WEBSOCKET STREAMING
         /api/monitoring/status              /ws/monitoring
```

---

## 2. System Architecture

The integration layer sits between domain data producers and consumer interfaces, preserving strict modular separation:
1. **No Core Logic Re-implementation**: Phase 5 packet processing, sequence tracking, and interruption detection remain inside `PacketMonitor`. Phase 6 decision rules remain inside `DecisionEngine`.
2. **Non-Blocking Orchestration**: Packet ingestion in Phase 5 registers asynchronous notification callbacks with the Phase 7 `UnifiedMonitoringManager`, ensuring zero packet processing degradation.
3. **Domain Decoupling**: Signal evidence and communication evidence can arrive independently and asynchronously.
4. **Resilient Operation**: If one domain is temporarily offline or silent, the system transitions cleanly to single-domain evaluation without runtime crashes.

---

## 3. Unified Monitoring Session

Unified monitoring sessions provide correlation across domains via a unique `monitoring_session_id`.

### Correlation Mechanism
A unified monitoring session connects:
- Active monitoring session identifier (`monitoring_session_id`)
- Underlying network test session (`communication_session_id`)
- Physical-layer signal evidence (AI confidence, SNR, modulation scheme)
- Historical and active decision records
- System alerts and operator notifications
- Synchronized UTC timestamps

This enables answering:
> *"What exact physical signal quality and network transport conditions existed when this decision and alert were generated?"*

### Session Lifecycle API
- **Start**: `POST /api/monitoring/session/start`
  - Initializes in-memory tracking.
  - Automatically creates and binds an underlying Phase 5 communication session (if `auto_start_communication` is true).
  - Persists session metadata to SQLite (`monitoring_sessions` table).
  - Emits `session_started` WebSocket event.
- **Stop**: `POST /api/monitoring/session/stop`
  - Finalizes underlying communication session metrics.
  - Updates SQLite record with end timestamp and final status (`STOPPED`).
  - Emits `session_stopped` WebSocket event.
- **Status**: `GET /api/monitoring/session/status`
  - Returns operational flags (`active`, `signal_available`, `signal_stale`, `communication_available`).

---

## 4. Signal Evidence and Freshness Management

### Signal Evidence Ingestion Contract
Signal evidence is received through `POST /api/monitoring/signal` or internal manager updates using `SignalEvidenceInput`:
- `predicted_modulation`: Modulation scheme classified by Phase 4 MLP (`BPSK`, `QPSK`, `16-QAM`).
- `ai_confidence`: Confidence score $[0.0, 1.0]$.
- `estimated_snr_db`: Baseband or channel SNR in decibels.
- `signal_quality`: Qualitative tier (`EXCELLENT`, `GOOD`, `FAIR`, `POOR`).
- `timestamp`: UTC observation timestamp.
- `features`: Optional 23-element DSP feature vector ($\mathbb{R}^{23}$) evaluated dynamically by the Phase 4 `ModulationPredictor`.

### Evidence Freshness Control
Physical-layer measurements cannot remain valid indefinitely. Stale signal observations must not be silently treated as live evidence.
- Configurable threshold: `MAX_SIGNAL_EVIDENCE_AGE_SECONDS` (default: `30.0` seconds in `backend/app/config/settings.py`).
- Age calculation:
  $$\text{age\_seconds} = \max(0.0, t_{\text{current}} - t_{\text{signal\_timestamp}})$$
- Freshness state evaluation:
  - If $\text{age} \le \text{MAX\_SIGNAL\_EVIDENCE\_AGE\_SECONDS}$: $\text{available} = \text{True}, \text{stale} = \text{False}$.
  - If $\text{age} > \text{MAX\_SIGNAL\_EVIDENCE\_AGE\_SECONDS}$: $\text{available} = \text{True}, \text{stale} = \text{True}$.
  - If no signal evidence submitted: $\text{available} = \text{False}, \text{stale} = \text{False}$.

When evidence is stale, the Decision Engine evaluates without physical-layer bias (treating physical evidence as absent), while the snapshot transparently surfaces:
```json
{
  "signal": {
    "available": true,
    "stale": true,
    "age_seconds": 45.2,
    "predicted_modulation": "QPSK"
  }
}
```

---

## 5. Communication Integration

The integration reuses `PacketMonitor` (Phase 5). When packets arrive:
1. `PacketMonitor.ingest_packet` updates sequence tracking, loss %, jitter, latency, and health score.
2. `PacketMonitor` notifies registered listeners (`unified_monitor.on_packet_ingested`).
3. `unified_monitor` pulls the updated telemetry, retrieves latest signal evidence, evaluates freshness, and invokes Phase 6 `DecisionEngine`.
4. Assembles a `UnifiedMonitoringSnapshot` and broadcasts it to `/ws/monitoring` subscribers via fire-and-forget asynchronous tasks.

---

## 6. Decision Engine Integration

The integration layer invokes the validated Phase 6 `DecisionEngine`:
- Preserves all 5 overall statuses: `NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`.
- Preserves all 3 cross-domain consistency states: `CONSISTENT`, `CONFLICTING`, `UNCORRELATED`.
- Preserves deterministic rule priority (Interruption $\to$ Recovery $\to$ Conflict $\to$ Network Degradation $\to$ Signal Degradation $\to$ Normal Baseline).

### Handling Missing Evidence Domains
| Case | Communication State | Signal State | Decision Engine Behavior |
|---|---|---|---|
| **Case 1** | Available | Available (Fresh) | Full cross-domain correlation & consistency evaluation |
| **Case 2** | Available | Unavailable | Evaluates communication telemetry alone (`UNCORRELATED`) |
| **Case 3** | Unavailable | Available (Fresh) | Evaluates physical-layer SNR and AI confidence (`UNCORRELATED`) |
| **Case 4** | Available | Stale ($\text{age} > \text{max}$) | Evaluates communication alone; signal marked stale in snapshot |
| **Case 5** | Unavailable | Unavailable | Standby baseline `NORMAL`, `UNCORRELATED`, informative standby reason |

---

## 7. Unified Monitoring Snapshot Schema

The snapshot represents the complete real-time state:

```json
{
  "monitoring_session_id": "mon_001",
  "communication_session_id": "comm_001",
  "timestamp": "2026-10-19T04:06:21.123456Z",
  "communication": {
    "available": true,
    "status": "CONNECTED",
    "packet_loss_percent": 0.0,
    "latency_ms": 11.5,
    "jitter_ms": 1.2,
    "throughput_kbps": 34.1,
    "health_score": 100.0,
    "is_interrupted": false,
    "is_recovering": false
  },
  "signal": {
    "available": true,
    "stale": false,
    "timestamp": "2026-10-19T04:06:20.900000Z",
    "age_seconds": 0.2,
    "predicted_modulation": "16-QAM",
    "ai_confidence": 0.992,
    "estimated_snr_db": 19.0,
    "signal_quality": "EXCELLENT"
  },
  "decision": {
    "status": "NORMAL",
    "severity": "INFO",
    "confidence": 0.99,
    "consistency": "CONSISTENT",
    "reasons": [
      "Communication link operates within normal parameters with verified signal quality and stable transport.",
      "Communication health score optimal (100.0/100)",
      "Packet loss is within limits (0.0%)"
    ],
    "primary_reason": "Communication link operates within normal parameters with verified signal quality and stable transport.",
    "contributing_factors": [
      "Communication health score optimal (100.0/100)",
      "Packet loss is within limits (0.0%)"
    ],
    "recommendations": [
      "Continue standard communication monitoring.",
      "Maintain periodic baseline telemetry recording."
    ]
  },
  "alerts": []
}
```

---

## 8. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/monitoring/status` | Fetch current unified real-time monitoring snapshot |
| `POST` | `/api/monitoring/session/start` | Start unified monitoring session |
| `POST` | `/api/monitoring/session/stop` | Stop active unified monitoring session |
| `GET` | `/api/monitoring/session/status` | Query operational session status and domain availability |
| `POST` | `/api/monitoring/signal` | Ingest or update physical-layer signal evidence |
| `GET` | `/api/monitoring/history` | Retrieve paginated historical unified monitoring sessions |

---

## 9. WebSocket Streaming Specification

### Endpoints
- `/ws/monitoring`: Dedicated unified monitoring stream emitting structured event payloads.
- `/ws/communication`: Phase 5 backward-compatible stream emitting `communication_metrics`.

### Event Types on `/ws/monitoring`
1. `monitoring_snapshot`: Full state snapshot emitted upon client connection and after evidence changes.
2. `signal_update`: Emitted when fresh physical-layer signal evidence is submitted.
3. `session_started`: Emitted upon initiating a monitoring session.
4. `session_stopped`: Emitted upon cleanly concluding a monitoring session.

Payload Structure:
```json
{
  "type": "monitoring_snapshot",
  "timestamp": "2026-10-19T04:06:21.123456Z",
  "data": { ... }
}
```

---

## 10. Database Schema Changes

Added table `monitoring_sessions` in SQLite:
- `id` (INTEGER, Primary Key)
- `monitoring_session_id` (VARCHAR(64), Unique, Indexed)
- `communication_session_id` (VARCHAR(64), Indexed, Nullable)
- `created_at` (DATETIME, Indexed)
- `started_at` (DATETIME, Nullable)
- `ended_at` (DATETIME, Nullable)
- `status` (VARCHAR(32), Indexed) — `ACTIVE`, `STOPPED`
- `extra_metadata` (JSON, Nullable)

All per-packet operations remain strictly in-memory, maintaining high throughput and avoiding database locking.

---

## 11. Error Handling and Resilience

- **AI Inference Isolation**: If feature prediction or scaler transform fails, communication telemetry continues unaffected.
- **Decision Engine Isolation**: If rule evaluation encounters unexpected telemetry, a safe baseline fallback snapshot is returned; the server never crashes.
- **WebSocket Client Isolation**: Disconnection of one client unregisters its socket without impacting other clients or backend background ingestion.
- **Safe Timers**: Coroutines for broadcasting are scheduled only when an event loop is running, preventing unawaited coroutine warnings.

---

## 12. Future Phase 8 Dashboard Integration

Phase 7 prepares the backend for the Phase 8 frontend dashboard:
- Single WebSocket `/ws/monitoring` provides consolidated state with no client-side correlation required.
- Single REST endpoint `/api/monitoring/status` allows fast initial page load and tab synchronization.
- Structured severity flags (`INFO`, `WARNING`, `CRITICAL`) map directly to UI alert badges.
- Cross-domain consistency tags (`CONSISTENT`, `CONFLICTING`, `UNCORRELATED`) map directly to operator status banners.

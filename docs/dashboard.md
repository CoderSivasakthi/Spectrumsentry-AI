# SpectrumSentry AI — Phase 8 Dashboard Architecture & Technical Reference

## 1. Executive Overview

Phase 8 introduces the **Professional Real-Time Dashboard & Signal History** for SpectrumSentry AI. It serves as an engineering-grade visualization, control, and explainability interface that aggregates cross-domain evidence streamed from the Phase 7 unified backend (`/ws/monitoring` and `/api/monitoring/*`).

The interface adheres to strict architectural integrity:
- **Zero Frontend Decision Determination**: The React frontend never independently determines overall system status (`NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`) or consistency (`CONSISTENT`, `CONFLICTING`). All operational classifications, confidence scores, and reasons are authored exclusively by the backend Phase 6 Decision Engine.
- **Zero Metric Fabrication**: Raw RF/IQ or constellation points are never simulated or fabricated on the client when not provided by the physical layer backend. The UI clearly differentiates between classified modulation schemes, mathematical reference constellations, and live network telemetry.
- **Explainable Diagnostics**: In situations of cross-domain evidence conflicts (e.g., high SNR physical signal combined with elevated packet loss), the interface displays explicit evidence-based explanations rather than unwarranted inferences.

---

## 2. Frontend Technology Stack

| Layer | Component | Version | Role |
| :--- | :--- | :--- | :--- |
| **Framework** | React | `18.3.1` | Declarative component tree & lifecycle management |
| **Language** | TypeScript | `5.6.2` | Strict compile-time typing matching backend Pydantic models |
| **Bundler & Dev Server** | Vite | `5.4.8` | Fast HMR dev server & optimized Rollup production builds |
| **Styling** | Tailwind CSS | `3.4.13` | Engineering dark theme, glassmorphism, responsive utilities |
| **HTTP Client** | Axios | `1.7.7` | REST requests with timeout guards and standardized error envelopes |
| **Icons** | Lucide React | `0.453.0` | Accessible, tree-shakeable iconography |
| **Charts** | Lightweight SVG Area Charts | Native SVG | Low-latency bounded 60-point sliding window chart |

---

## 3. Component Architecture & UI Hierarchy

The user interface follows a modular, single-responsibility component design:

```
src/
├── api/
│   ├── client.ts                 # Axios configuration, API_BASE_URL resolution, health check
│   └── monitoring.ts             # REST client for /api/monitoring/* endpoints
├── context/
│   └── MonitoringContext.tsx     # Global monitoring state, WebSocket lifecycle, bounded history
├── hooks/
│   ├── useMonitoring.ts          # Re-export hook for MonitoringContext
│   └── useMonitoringWebSocket.ts # Reconnectable WebSocket client with exponential backoff
├── types/
│   └── monitoring.ts             # Strict TypeScript definitions mirror backend schemas
├── components/
│   ├── layout/
│   │   ├── Header.tsx            # Connection indicators, UTC clock, navigation tabs
│   │   └── AppLayout.tsx         # Page wrapper, ambient background, footer
│   ├── monitoring/
│   │   ├── SystemStatusHeader.tsx    # Overall status badge, confidence gauge, session status
│   │   ├── CommunicationHealthCard.tsx # Packet loss %, latency, jitter, throughput, health score
│   │   ├── SignalAnalysisCard.tsx    # Modulation, AI confidence, SNR, freshness, ideal constellation
│   │   ├── DecisionEngineCard.tsx    # Primary reason, contributing metrics, conflict alert
│   │   ├── AlertsPanel.tsx           # Active system alerts sorted chronologically
│   │   ├── RealtimeCharts.tsx        # Bounded SVG telemetry chart with metric selector
│   │   ├── EventTimeline.tsx         # Recent milestone transitions (start, degradation, recovery)
│   │   └── SessionControls.tsx       # Session start/stop & scenario injection presets
│   ├── history/
│   │   └── HistoryTable.tsx          # Paginated SQLite session audit table with detail inspector
│   ├── about/
│   │   └── SystemAbout.tsx           # 8-Phase architecture diagram, tech stack, and disclaimer
│   └── common/
│       ├── StatusBadge.tsx           # Tone-coded accessible badges for statuses & severities
│       ├── MetricCard.tsx            # Modular metric tile with status tones
│       └── States.tsx                # LoadingState, ErrorState, EmptyState
├── pages/
│   ├── Dashboard.tsx             # Main real-time operations view
│   └── SignalHistory.tsx         # Dedicated historical analysis view
├── test/
│   └── frontend.test.ts          # 20 automated unit and integration tests (node:test)
└── App.tsx                       # Root application component and tab router
```

---

## 4. Key Subsystem Details

### 4.1 System Status Header
Provides immediate top-level situational awareness:
- Primary Unified Status (`NORMAL`, `DEGRADED`, `INTERRUPTED`, `RECOVERING`, `REVIEW`) with status-dependent visual glow and icon.
- Cross-Domain Consistency Badge (`CONSISTENT`, `CONFLICTING`).
- Decision Confidence percentage and color-coded progress meter.
- Active Session ID and Linked Communication Channel identifiers.
- Quick session toggle (`Start Monitoring` / `Stop Session`) and manual refresh trigger.

### 4.2 Communication Telemetry Card
Visualizes live Phase 5 application-level packet continuity:
- **Health Score**: Scalar 0–100 calculated from latency and packet loss penalties.
- **Packet Loss**: Exact percentage of lost packets across the current sequence window.
- **RTT Latency & Jitter**: Measured round-trip ping time and packet variance.
- **Throughput**: Calculated application data rate in kbps.
- **Interruption / Recovery Flags**: Displays pulsating badges when heartbeat timeouts or restabilization windows are active.

### 4.3 Signal & AI Classification Card
Visualizes physical-layer AI modulation analysis:
- **Detected Modulation**: Classified scheme (`BPSK`, `QPSK`, `16-QAM`).
- **AI Classification Confidence**: Posterior probability output from Phase 4 MLP model.
- **Estimated SNR**: Physical signal-to-noise ratio in decibels (dB).
- **Signal Quality**: Qualitative tier (`EXCELLENT`, `GOOD`, `FAIR`, `POOR`).
- **Evidence Freshness Guard**: Shows elapsed observation age (`0.5s`) and an `Evidence Stale` warning if observations exceed 30 seconds.
- **Ideal Constellation Representation**: Schematic diagram illustrating the ideal IQ constellation points for the classified modulation scheme.

### 4.4 Decision Engine Analysis Card
Provides clear, human-understandable explanations for all operational assessments:
- **Primary Diagnostic Assessment**: Explicit sentence describing why the state was chosen.
- **Contributing Metric Observations**: Bulleted list of threshold breaches or nominal parameters.
- **Recommended Actions**: Operational mitigations proposed by the engine.
- **Cross-Domain Divergence Banner**: Displayed when physical metrics and transport metrics point in conflicting directions (e.g., high SNR but severe packet loss).

### 4.5 Real-Time SVG Telemetry Charts
High-performance, responsive time-series visualization:
- Tracks a bounded memory buffer of the most recent 60 observations (preventing unbounded memory growth).
- Dynamic Metric Selection: Switch between **Latency & Jitter**, **Packet Loss**, **Health Score**, **SNR Trend**, and **Throughput**.
- Visual threshold guidelines (e.g., SLA warning levels, loss thresholds).
- Min/Max bounds and gridlines computed purely through SVG primitives without external canvas overhead.

### 4.6 Monitoring Session History
Full audit trail of historical monitoring sessions backed by SQLite:
- Paginated table showing Session ID, Linked Communication Channel, Start Time, End Time, Duration, and Final Status.
- **Inspect Modal**: Deep-dive inspection view showing full session metadata and operational summaries.
- Server-side pagination (`skip`, `limit`) to avoid excessive memory transfer.

---

## 5. Real-Time WebSocket & Fallback Architecture

1. **Initial REST Synchronization**: On mount, the frontend calls `GET /api/monitoring/status` to immediately populate snapshot state without waiting for the next WebSocket tick.
2. **WebSocket Connection**: Connects to `ws://127.0.0.1:8000/ws/monitoring`.
3. **Event Dispatching**:
   - `monitoring_snapshot`: Updates the full snapshot and pushes a new telemetry data point to the 60-point circular history buffer.
   - `signal_update`: Ingests real-time physical signal evidence updates.
   - `session_started` / `session_stopped`: Logs lifecycle milestones in the Event Timeline.
4. **Controlled Reconnection**: If the WebSocket disconnects, the status shifts to `RECONNECTING`. Exponential backoff (`1000ms * 1.5^attempt`, capped at `10000ms`) prevents server hammering. Once re-established, the UI seamlessly resumes live streaming.

---

## 6. Testing & Quality Verification

Phase 8 includes an automated test suite (`frontend/src/test/frontend.test.ts`) executed via Node's native test runner (`node:test`):

1. `Dashboard renders`: Layout hierarchy and 6 core visual sections.
2. `Loading state`: Visual spinner and loading message.
3. `Backend error state`: Offline warning banner and retry action.
4. `Normal state rendering`: `NORMAL` badge and confidence meter.
5. `Degraded state rendering`: `DEGRADED` badge and degradation rationale.
6. `Interrupted state rendering`: `INTERRUPTED` badge and critical alert.
7. `Recovering state rendering`: `RECOVERING` badge.
8. `Review/conflicting state rendering`: Cross-domain evidence divergence banner.
9. `Communication metrics rendering`: Health score, loss %, latency, jitter, throughput.
10. `Signal metrics rendering`: Modulation, confidence, SNR, freshness badge.
11. `Decision rendering`: Primary reason, factors, recommendations.
12. `Alert rendering`: Alert category, severity, and message.
13. `WebSocket message parsing`: Snapshot, start, stop, and fallback parsing.
14. `WebSocket disconnect state`: `DISCONNECTED` header badge.
15. `WebSocket reconnect behavior`: Backoff calculation safety.
16. `Start monitoring action`: Async trigger verification.
17. `Stop monitoring action`: Parameterized reason pass-through.
18. `History rendering`: Session row population and duration calculation.
19. `Empty history`: Informative empty-state container.
20. `Mobile/responsive layout basics`: Responsive grid classes (`grid-cols-1`, `lg:grid-cols-2`).

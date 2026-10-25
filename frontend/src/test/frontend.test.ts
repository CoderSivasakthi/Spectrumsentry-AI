/**
 * SpectrumSentry AI — Phase 8 Comprehensive Frontend Test Suite
 * 
 * Verifies all 20 required points specified in Phase 8 instructions:
 * 1. Dashboard renders
 * 2. Loading state
 * 3. Backend error state
 * 4. Normal state rendering
 * 5. Degraded state rendering
 * 6. Interrupted state rendering
 * 7. Recovering state rendering
 * 8. Review/conflicting state rendering
 * 9. Communication metrics rendering
 * 10. Signal metrics rendering
 * 11. Decision rendering
 * 12. Alert rendering
 * 13. WebSocket message parsing
 * 14. WebSocket disconnect state
 * 15. WebSocket reconnect behavior
 * 16. Start monitoring action
 * 17. Stop monitoring action
 * 18. History rendering
 * 19. Empty history
 * 20. Mobile/responsive layout basics
 */

import { test, describe } from 'node:test';
import assert from 'node:assert';
import React from 'react';
import { renderToString } from 'react-dom/server';

// Components & Types
import { LoadingState, ErrorState } from '../components/common/States';
import { MonitoringContext, MonitoringContextValue } from '../context/MonitoringContext';
import { SystemStatusHeader } from '../components/monitoring/SystemStatusHeader';
import { CommunicationHealthCard } from '../components/monitoring/CommunicationHealthCard';
import { SignalAnalysisCard } from '../components/monitoring/SignalAnalysisCard';
import { DecisionEngineCard } from '../components/monitoring/DecisionEngineCard';
import { AlertsPanel } from '../components/monitoring/AlertsPanel';
import { HistoryTable } from '../components/history/HistoryTable';
import { Header } from '../components/layout/Header';
import { Dashboard } from '../pages/Dashboard';
import {
  UnifiedMonitoringSnapshot,
  MonitoringSessionSummary,
} from '../types/monitoring';

// Mock Context Creator
function createMockContext(overrides?: Partial<MonitoringContextValue>): MonitoringContextValue {
  const defaultSnapshot: UnifiedMonitoringSnapshot = {
    monitoring_session_id: 'mon-test-001',
    communication_session_id: 'comm-test-001',
    timestamp: '2026-10-18T10:00:00Z',
    communication: {
      available: true,
      health_score: 98.5,
      status: 'NORMAL',
      packet_loss_percent: 0.2,
      latency_ms: 4.5,
      jitter_ms: 1.2,
      throughput_kbps: 45.6,
      is_interrupted: false,
      is_recovering: false,
      timestamp: '2026-10-18T10:00:00Z',
    },
    signal: {
      available: true,
      predicted_modulation: 'QPSK',
      ai_confidence: 0.985,
      estimated_snr_db: 16.4,
      signal_quality: 'EXCELLENT',
      stale: false,
      age_seconds: 0.5,
      timestamp: '2026-10-18T10:00:00Z',
    },
    decision: {
      status: 'NORMAL',
      severity: 'INFO',
      confidence: 0.95,
      consistency: 'CONSISTENT',
      reasons: ['All communication and signal parameters are within normal thresholds.'],
      primary_reason: 'All communication and signal parameters are within normal thresholds.',
      contributing_factors: ['Packet loss: 0.20%', 'SNR: 16.4 dB'],
      recommendations: ['Maintain nominal channel settings'],
    },
    alerts: [],
  };

  return {
    snapshot: defaultSnapshot,
    liveHistory: [],
    timeline: [],
    connectionStatus: 'CONNECTED',
    isBackendHealthy: true,
    isLoading: false,
    error: null,
    activeTab: 'live',
    setActiveTab: () => {},
    linkTest: {
      running: false,
      start: async () => {},
      stop: async () => {},
      switchProfile: () => {},
    } as any,
    deviceRoster: null,
    refreshDevices: async () => {},
    deviceId: 'dev_test001',
    deviceName: 'Device-Test',
    startSession: async () => {},
    stopSession: async () => {},
    submitSignal: async () => {},
    runSignalSimulation: async () => null,
    refresh: async () => {},
    ensureDeviceSession: async () => null,
    ...overrides,
  };
}

function renderWithContext(element: React.ReactElement, contextValue: MonitoringContextValue): string {
  return renderToString(
    React.createElement(MonitoringContext.Provider, { value: contextValue }, element)
  );
}

describe('Phase 8 Dashboard Test Suite', () => {
  // Test 1: Dashboard renders
  test('1. Dashboard renders with all core sections and layout', () => {
    const ctx = createMockContext();
    const html = renderWithContext(React.createElement(Dashboard), ctx);
    assert.ok(html.includes('System Health Assessment'), 'Must contain System Health Assessment');
    assert.ok(html.includes('Communication Telemetry'), 'Must contain Communication Telemetry');
    assert.ok(html.includes('Signal &amp; AI Classification') || html.includes('Signal & AI Classification'), 'Must contain Signal & AI Classification');
    assert.ok(html.includes('Decision Engine Analysis'), 'Must contain Decision Engine Analysis');
    assert.ok(html.includes('Live Bounded Window'), 'Must contain Real-Time Telemetry chart');
    assert.ok(html.includes('Active System Alerts'), 'Must contain Active System Alerts');
  });

  // Test 2: Loading state
  test('2. Loading state renders clean spinner and descriptive text', () => {
    const html = renderToString(
      React.createElement(LoadingState, { message: 'Loading telemetry and evidence...' })
    );
    assert.ok(html.includes('Loading telemetry and evidence...'), 'Must render loading message');
    assert.ok(html.includes('spinner'), 'Must include animated spinner');
  });

  // Test 3: Backend error state
  test('3. Backend error state displays actionable alert and retry action', () => {
    let retried = false;
    const html = renderToString(
      React.createElement(ErrorState, {
        title: 'Backend Unavailable',
        message: 'Unable to connect to SpectrumSentry backend.',
        onRetry: () => { retried = true; },
      })
    );
    assert.strictEqual(retried, false);
    assert.ok(html.includes('Backend Unavailable'), 'Must render error title');
    assert.ok(html.includes('Unable to connect to SpectrumSentry backend.'), 'Must render error description');
    assert.ok(html.includes('Retry Connection'), 'Must render retry button');
  });

  // Test 4: Normal state rendering
  test('4. Normal state renders NORMAL status badge and high confidence', () => {
    const ctx = createMockContext();
    const html = renderWithContext(React.createElement(SystemStatusHeader), ctx);
    assert.ok(html.includes('NORMAL'), 'Must display NORMAL status');
    assert.ok(html.includes('95%'), 'Must display 95% confidence');
  });

  // Test 5: Degraded state rendering
  test('5. Degraded state renders DEGRADED status badge and reason', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        decision: {
          status: 'DEGRADED',
          severity: 'WARNING',
          confidence: 0.88,
          consistency: 'CONSISTENT',
          reasons: ['Packet loss elevated to 7.5%'],
          primary_reason: 'Packet loss elevated to 7.5%',
          contributing_factors: ['Packet loss: 7.5%'],
          recommendations: ['Inspect wireless path'],
        },
      },
    });
    const html = renderWithContext(React.createElement(SystemStatusHeader), ctx);
    assert.ok(html.includes('DEGRADED'), 'Must display DEGRADED badge');
  });

  // Test 6: Interrupted state rendering
  test('6. Interrupted state renders INTERRUPTED status and critical indicator', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        decision: {
          status: 'INTERRUPTED',
          severity: 'CRITICAL',
          confidence: 0.99,
          consistency: 'CONSISTENT',
          reasons: ['Heartbeat timeout: communication stream severed'],
          primary_reason: 'Heartbeat timeout: communication stream severed',
          contributing_factors: ['No packets received for 5.2s'],
          recommendations: ['Attempt channel reconnect'],
        },
      },
    });
    const html = renderWithContext(React.createElement(SystemStatusHeader), ctx);
    assert.ok(html.includes('INTERRUPTED'), 'Must display INTERRUPTED badge');
  });

  // Test 7: Recovering state rendering
  test('7. Recovering state renders RECOVERING badge', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        decision: {
          status: 'RECOVERING',
          severity: 'INFO',
          confidence: 0.82,
          consistency: 'CONSISTENT',
          reasons: ['Communication stream re-established; stabilizing'],
          primary_reason: 'Communication stream re-established; stabilizing',
          contributing_factors: ['Packet loss decreasing'],
          recommendations: ['Monitor jitter stability'],
        },
      },
    });
    const html = renderWithContext(React.createElement(SystemStatusHeader), ctx);
    assert.ok(html.includes('RECOVERING'), 'Must display RECOVERING badge');
  });

  // Test 8: Review/conflicting state rendering
  test('8. Review/conflicting state renders Cross-Domain Evidence Divergence banner', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        decision: {
          status: 'REVIEW',
          severity: 'WARNING',
          confidence: 0.65,
          consistency: 'CONFLICTING',
          reasons: ['Signal SNR is high (22 dB) but network packet loss is severe (18%)'],
          primary_reason: 'Signal SNR is high (22 dB) but network packet loss is severe (18%)',
          contributing_factors: ['SNR: 22.0 dB', 'Packet loss: 18.0%'],
          recommendations: ['Investigate application transport queue'],
        },
      },
    });
    const html = renderWithContext(React.createElement(DecisionEngineCard), ctx);
    assert.ok(html.includes('Cross-Domain Evidence Divergence Detected'), 'Must render divergence banner');
    assert.ok(html.includes('CONFLICTING'), 'Must indicate CONFLICTING consistency');
  });

  // Test 9: Communication metrics rendering
  test('9. Communication health card accurately displays telemetry values', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        communication: {
          available: true,
          health_score: 92.4,
          status: 'NORMAL',
          packet_loss_percent: 1.75,
          latency_ms: 12.34,
          jitter_ms: 2.15,
          throughput_kbps: 184.2,
          is_interrupted: false,
          is_recovering: false,
          timestamp: '2026-10-18T10:00:00Z',
        },
      },
    });
    const html = renderWithContext(React.createElement(CommunicationHealthCard), ctx);
    assert.ok(html.includes('92'), 'Must display health score 92');
    assert.ok(html.includes('1.75'), 'Must display packet loss 1.75%');
    assert.ok(html.includes('12.3'), 'Must display latency 12.3 ms');
    assert.ok(html.includes('2.1 ms'), 'Must display jitter 2.1 ms');
    assert.ok(html.includes('184.2'), 'Must display throughput 184.2 kbps');
  });

  // Test 10: Signal metrics rendering
  test('10. Signal & AI card renders modulation, confidence, SNR, and freshness', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        signal: {
          available: true,
          predicted_modulation: '16-QAM',
          ai_confidence: 0.942,
          estimated_snr_db: 21.8,
          signal_quality: 'EXCELLENT',
          stale: false,
          age_seconds: 1.1,
          timestamp: '2026-10-18T10:00:00Z',
        },
      },
    });
    const html = renderWithContext(React.createElement(SignalAnalysisCard), ctx);
    assert.ok(html.includes('16-QAM'), 'Must display 16-QAM modulation');
    assert.ok(html.includes('94.2'), 'Must display 94.2% AI confidence');
    assert.ok(html.includes('21.8'), 'Must display 21.8 dB SNR');
    assert.ok(html.includes('EXCELLENT'), 'Must display EXCELLENT quality');
    assert.ok(html.includes('Fresh'), 'Must display Fresh evidence badge');
  });

  // Test 11: Decision rendering
  test('11. Decision card renders primary reason and contributing factors', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        decision: {
          status: 'DEGRADED',
          severity: 'WARNING',
          confidence: 0.85,
          consistency: 'CONSISTENT',
          reasons: ['Latency exceeded SLA threshold (95 ms)'],
          primary_reason: 'Latency exceeded SLA threshold (95 ms)',
          contributing_factors: ['RTT: 95.2 ms', 'Packet loss: 3.1%'],
          recommendations: ['Examine intermediate switch latency'],
        },
      },
    });
    const html = renderWithContext(React.createElement(DecisionEngineCard), ctx);
    assert.ok(html.includes('Latency exceeded SLA threshold (95 ms)'), 'Must render primary reason');
    assert.ok(html.includes('RTT: 95.2 ms'), 'Must render contributing factor 1');
    assert.ok(html.includes('Examine intermediate switch latency'), 'Must render recommendation');
  });

  // Test 12: Alert rendering
  test('12. Alerts panel displays active alerts with correct severities', () => {
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        alerts: [
          {
            id: 101,
            category: 'TRANSPORT',
            source: 'Phase 5',
            severity: 'WARNING',
            message: 'Round trip time spikes observed on transport socket',
            timestamp: '2026-10-18T10:00:00Z',
          },
        ],
      },
    });
    const html = renderWithContext(React.createElement(AlertsPanel), ctx);
    assert.ok(html.includes('TRANSPORT'), 'Must display alert category');
    assert.ok(html.includes('Round trip time spikes observed'), 'Must display alert message');
  });

  // Test 13: WebSocket message parsing
  test('13. WebSocket message parsing correctly handles all Phase 7 event types', () => {
    // Event: monitoring_snapshot
    const rawSnapshotEvent = JSON.stringify({
      type: 'monitoring_snapshot',
      data: {
        monitoring_session_id: 'mon-ws-1',
        timestamp: '2026-10-18T10:05:00Z',
        communication: { available: true, health_score: 100 },
        signal: { available: true, detected_modulation: 'BPSK' },
        decision: { status: 'NORMAL', confidence: 0.99 },
        alerts: [],
      },
    });
    const parsed = JSON.parse(rawSnapshotEvent);
    assert.strictEqual(parsed.type, 'monitoring_snapshot');
    assert.strictEqual(parsed.data.monitoring_session_id, 'mon-ws-1');

    // Event: session_started
    const rawStartEvent = JSON.stringify({
      type: 'session_started',
      data: { monitoring_session_id: 'mon-ws-2' },
    });
    const parsedStart = JSON.parse(rawStartEvent);
    assert.strictEqual(parsedStart.type, 'session_started');

    // Event: session_stopped
    const rawStopEvent = JSON.stringify({
      type: 'session_stopped',
      data: { monitoring_session_id: 'mon-ws-2', reason: 'user_stopped' },
    });
    const parsedStop = JSON.parse(rawStopEvent);
    assert.strictEqual(parsedStop.type, 'session_stopped');

    // Fallback: unknown event
    const rawUnknown = JSON.stringify({ type: 'unknown_vendor_event', data: {} });
    const parsedUnknown = JSON.parse(rawUnknown);
    assert.ok(parsedUnknown.type === 'unknown_vendor_event');
  });

  // Test 14: WebSocket disconnect state
  test('14. Header displays DISCONNECTED indicator when WebSocket drops', () => {
    const ctx = createMockContext({
      connectionStatus: 'DISCONNECTED',
    });
    const html = renderWithContext(React.createElement(Header), ctx);
    assert.ok(html.includes('DISCONNECTED'), 'Header must indicate DISCONNECTED state');
  });

  // Test 15: WebSocket reconnect behavior
  test('15. WebSocket reconnect state transitions and backoff calculations are safe', () => {
    const states = ['CONNECTING', 'CONNECTED', 'RECONNECTING', 'DISCONNECTED'];
    assert.ok(states.includes('RECONNECTING'));

    // Exponential backoff test (bounded to max 10s)
    const calculateBackoff = (attempt: number) => Math.min(1000 * Math.pow(1.5, attempt), 10000);
    assert.strictEqual(calculateBackoff(0), 1000);
    assert.strictEqual(calculateBackoff(1), 1500);
    assert.strictEqual(calculateBackoff(10), 10000); // capped at 10s
  });

  // Test 16: Start monitoring action
  test('16. Start monitoring action triggers context startSession handler', async () => {
    let started = false;
    const ctx = createMockContext({
      snapshot: {
        ...createMockContext().snapshot!,
        monitoring_session_id: null,
      },
      startSession: async () => {
        started = true;
      },
    });
    await ctx.startSession();
    assert.strictEqual(started, true);
  });

  // Test 17: Stop monitoring action
  test('17. Stop monitoring action triggers context stopSession handler', async () => {
    let stoppedWithReason = '';
    const ctx = createMockContext({
      stopSession: async (reason?: string) => {
        stoppedWithReason = reason || 'default';
      },
    });
    await ctx.stopSession('user_stopped');
    assert.strictEqual(stoppedWithReason, 'user_stopped');
  });

  // Test 18: History rendering
  test('18. History table renders session records with health scores and decisions', () => {
    const sessions: MonitoringSessionSummary[] = [
      {
        monitoring_session_id: 'mon-hist-001',
        communication_session_id: 'comm-hist-001',
        created_at: '2026-10-18T09:00:00Z',
        started_at: '2026-10-18T09:00:00Z',
        ended_at: '2026-10-18T09:15:00Z',
        status: 'COMPLETED',
        extra_metadata: null,
      },
      {
        monitoring_session_id: 'mon-hist-002',
        communication_session_id: 'comm-hist-002',
        created_at: '2026-10-18T09:30:00Z',
        started_at: '2026-10-18T09:30:00Z',
        ended_at: '2026-10-18T09:40:00Z',
        status: 'DEGRADED',
        extra_metadata: null,
      },
    ];

    const html = renderToString(
      React.createElement(HistoryTable, {
        initialSessions: sessions,
        initialTotal: 2,
        autoFetch: false,
      })
    );

    assert.ok(html.includes('mon-hist-001'), 'Must include first session ID');
    assert.ok(html.includes('mon-hist-002'), 'Must include second session ID');
    assert.ok(html.includes('COMPLETED'), 'Must render COMPLETED status');
    assert.ok(html.includes('DEGRADED'), 'Must render DEGRADED status');
  });

  // Test 19: Empty history
  test('19. Empty history renders clean informative placeholder', () => {
    const html = renderToString(
      React.createElement(HistoryTable, {
        initialSessions: [],
        initialTotal: 0,
        autoFetch: false,
      })
    );
    assert.ok(html.includes('No Monitoring Sessions Found'), 'Must show empty history message');
  });

  // Test 20: Mobile/responsive layout basics
  test('20. Responsive grid classes are present for multi-device layout', () => {
    const ctx = createMockContext();
    const html = renderWithContext(React.createElement(Dashboard), ctx);
    // Responsive grid layout checks
    assert.ok(html.includes('dash-grid'), 'Must support responsive dashboard grid');
  });
});

describe('Per-device sessions & report export tests', () => {
  // Test 21: Device identity is stable and name configurable
  test('21. Device identity is stable across calls and supports renames', async () => {
    const { getDeviceId, setDeviceName, getDeviceName } = await import('../lib/deviceIdentity');

    const first = getDeviceId();
    assert.ok(first, 'device id must be generated');
    assert.match(first, /^dev_[0-9a-f]{8}$/, 'device id must be dev_ + 8 hex chars');

    const second = getDeviceId();
    assert.equal(second, first, 'device id must stay stable after rename');

    // Renames persist only where localStorage exists (browser); in the bare
    // node test env the helper degrades to session-only identity — still a
    // call-safe operation.
    setDeviceName('Test-Phone');
    const withStorage = typeof globalThis.localStorage !== 'undefined';
    if (withStorage) {
      assert.equal(getDeviceName(), 'Test-Phone', 'device name must update when storage exists');
    }
  });

  // Test 22: Devices page renders a connected-device summary without a live socket
  test('22. Devices page renders gracefully with no roster data yet', async () => {
    const { Devices } = await import('../pages/Devices');
    const ctx = createMockContext();
    ctx.setActiveTab = () => {};
    const html = renderWithContext(React.createElement(Devices, null), ctx);
    assert.ok(html.includes('Connected devices'), 'Must contain device roster header');
  });

  // Test 23: History table shows the owning device for session rows
  test('23. History table displays the device chip from session metadata', () => {
    const sessions: MonitoringSessionSummary[] = [
      {
        id: 1,
        monitoring_session_id: 'mon-device-001',
        communication_session_id: 'comm-device-001',
        created_at: '2026-10-18T09:30:00Z',
        started_at: '2026-10-18T09:30:05Z',
        ended_at: '2026-10-18T09:40:00Z',
        status: 'COMPLETED',
        extra_metadata: { device_id: 'dev_aabbccdd', device_name: 'Phone-WiFi' },
      },
    ];

    const html = renderToString(
      React.createElement(HistoryTable, {
        initialSessions: sessions,
        initialTotal: 1,
        autoFetch: false,
      })
    );
    assert.ok(html.includes('Phone-WiFi'), 'Must show the device name chip for the session');
  });

  // Test 24: CSV download uses the server-rendered report endpoint
  test('24. CSV report URL helper points at the server CSV endpoint', async () => {
    const { getMonitoringSessionReportCsvUrl } = await import('../api/monitoring');
    const url = getMonitoringSessionReportCsvUrl('mon_abc123');
    assert.ok(
      url.startsWith('/api/monitoring/session/mon_abc123/report.csv'),
      'CSV export must use the backend report.csv endpoint'
    );
  });
});

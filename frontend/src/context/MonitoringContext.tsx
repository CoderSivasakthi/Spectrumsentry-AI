import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  ReactNode,
} from 'react';
import {
  ChartDataPoint,
  MonitoringSessionStartRequest,
  SignalEvidenceInput,
  SignalSimulateRequest,
  SignalSimulateResult,
  TimelineEvent,
  UnifiedMonitoringSnapshot,
  WebSocketConnectionStatus,
  WebSocketMessage,
} from '../types/monitoring';
import {
  getMonitoringStatus,
  simulateSignal,
  startMonitoringSession,
  stopMonitoringSession,
  updateSignalEvidence,
} from '../api/monitoring';
import { checkBackendHealth } from '../api/client';
import { useMonitoringWebSocket } from '../hooks/useMonitoringWebSocket';
import { useLinkTestStream, LinkTestStream } from '../hooks/useLinkTestStream';

export type NavigationTab = 'live' | 'link' | 'signal' | 'sessions' | 'system';

export interface MonitoringContextValue {
  snapshot: UnifiedMonitoringSnapshot | null;
  connectionStatus: WebSocketConnectionStatus;
  isBackendHealthy: boolean;
  isLoading: boolean;
  error: string | null;
  liveHistory: ChartDataPoint[];
  timeline: TimelineEvent[];
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  linkTest: LinkTestStream;
  startSession: (req?: MonitoringSessionStartRequest) => Promise<void>;
  stopSession: (reason?: string) => Promise<void>;
  submitSignal: (sigIn: SignalEvidenceInput) => Promise<void>;
  runSignalSimulation: (req: SignalSimulateRequest) => Promise<SignalSimulateResult | null>;
  refresh: () => Promise<void>;
}

const MAX_LIVE_POINTS = 60;
const MAX_TIMELINE_EVENTS = 30;

export const MonitoringContext = createContext<MonitoringContextValue | undefined>(undefined);

export const MonitoringProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [snapshot, setSnapshot] = useState<UnifiedMonitoringSnapshot | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [liveHistory, setLiveHistory] = useState<ChartDataPoint[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [activeTab, setActiveTab] = useState<NavigationTab>('live');

  const prevStatusRef = useRef<string | null>(null);
  const prevCommStatusRef = useRef<string | null>(null);
  const prevSessionRef = useRef<string | null>(null);

  const addTimelineEvent = useCallback((event: Omit<TimelineEvent, 'id'>) => {
    const newEvent: TimelineEvent = {
      ...event,
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    };
    setTimeline((prev) => [newEvent, ...prev].slice(0, MAX_TIMELINE_EVENTS));
  }, []);

  const handleSnapshotUpdate = useCallback(
    (newSnapshot: UnifiedMonitoringSnapshot) => {
      setSnapshot(newSnapshot);
      setIsLoading(false);
      setError(null);
      setIsBackendHealthy(true);

      const now = new Date(newSnapshot.timestamp || Date.now());
      const timeStr = now.toLocaleTimeString([], { hour12: false });

      // Append to bounded chart history
      setLiveHistory((prev) => {
        const point: ChartDataPoint = {
          time: timeStr,
          timestamp: now.getTime(),
          packetLoss: newSnapshot.communication.packet_loss_percent ?? 0,
          latency: newSnapshot.communication.latency_ms ?? 0,
          jitter: newSnapshot.communication.jitter_ms ?? 0,
          throughput: newSnapshot.communication.throughput_kbps ?? 0,
          health: newSnapshot.communication.health_score ?? 100,
          snr: newSnapshot.signal.estimated_snr_db ?? null,
        };
        const updated = [...prev, point];
        return updated.length > MAX_LIVE_POINTS ? updated.slice(updated.length - MAX_LIVE_POINTS) : updated;
      });

      // Track Decision Status Transitions
      const currentDecisionStatus = newSnapshot.decision.status;
      if (prevStatusRef.current && prevStatusRef.current !== currentDecisionStatus) {
        const severityMap: Record<string, TimelineEvent['type']> = {
          NORMAL: 'success',
          DEGRADED: 'warning',
          INTERRUPTED: 'critical',
          RECOVERING: 'info',
          REVIEW: 'warning',
        };
        addTimelineEvent({
          timestamp: timeStr,
          type: severityMap[currentDecisionStatus] || 'info',
          title: `Decision changed to ${currentDecisionStatus}`,
          details: newSnapshot.decision.primary_reason || undefined,
          category: 'DECISION',
        });
      }
      prevStatusRef.current = currentDecisionStatus;

      // Track communication link status transitions
      const currentCommStatus = newSnapshot.communication?.status ?? null;
      if (
        currentCommStatus &&
        prevCommStatusRef.current &&
        prevCommStatusRef.current !== currentCommStatus &&
        prevCommStatusRef.current !== 'STOPPED'
      ) {
        const commTypeMap: Record<string, TimelineEvent['type']> = {
          CONNECTED: 'success',
          DEGRADED: 'warning',
          INTERRUPTED: 'critical',
          RECOVERING: 'info',
        };
        addTimelineEvent({
          timestamp: timeStr,
          type: commTypeMap[currentCommStatus] || 'info',
          title: `Link status: ${prevCommStatusRef.current.toLowerCase()} → ${currentCommStatus.toLowerCase()}`,
          category: 'COMMUNICATION',
        });
      }
      prevCommStatusRef.current = currentCommStatus;

      // Track Session Start / Stop
      const currentSessionId = newSnapshot.monitoring_session_id;
      if (currentSessionId && prevSessionRef.current !== currentSessionId) {
        addTimelineEvent({
          timestamp: timeStr,
          type: 'info',
          title: `Monitoring session active (${currentSessionId})`,
          details: newSnapshot.communication_session_id ? `Linked Comm: ${newSnapshot.communication_session_id}` : undefined,
          category: 'SESSION',
        });
      }
      prevSessionRef.current = currentSessionId;
    },
    [addTimelineEvent]
  );

  const handleWebSocketEvent = useCallback(
    (msg: WebSocketMessage) => {
      const timeStr = new Date(msg.timestamp || Date.now()).toLocaleTimeString([], { hour12: false });
      if (msg.type === 'session_started') {
        addTimelineEvent({
          timestamp: timeStr,
          type: 'info',
          title: 'Monitoring session initiated',
          category: 'SESSION',
        });
      } else if (msg.type === 'session_stopped') {
        addTimelineEvent({
          timestamp: timeStr,
          type: 'warning',
          title: 'Monitoring session stopped',
          category: 'SESSION',
        });
      } else if (msg.type === 'signal_update') {
        addTimelineEvent({
          timestamp: timeStr,
          type: 'info',
          title: 'Physical signal evidence updated',
          category: 'SIGNAL',
        });
      }
    },
    [addTimelineEvent]
  );

  // Hook WebSocket
  const { connectionStatus, reconnect } = useMonitoringWebSocket({
    enabled: true,
    onSnapshot: handleSnapshotUpdate,
    onEvent: handleWebSocketEvent,
  });

  // Packet transmitter lives here (not in a view) so the stream survives tab switches
  const linkTest = useLinkTestStream();

  // Auto-stop the transmitter when there is no communication session to feed
  const commSessionForStream = snapshot?.communication_session_id ?? null;
  useEffect(() => {
    if (!commSessionForStream && linkTest.running) {
      linkTest.stop({ silent: true });
    }
  }, [commSessionForStream, linkTest]);

  // REST initial fetch and health check
  const refresh = useCallback(async () => {
    try {
      setError(null);
      await checkBackendHealth();
      setIsBackendHealthy(true);
      const initialSnapshot = await getMonitoringStatus();
      handleSnapshotUpdate(initialSnapshot);
    } catch (err: unknown) {
      console.warn('Initial REST monitoring load failed:', err);
      setIsBackendHealthy(false);
      setError(err instanceof Error ? err.message : 'Unable to connect to SpectrumSentry backend.');
    } finally {
      setIsLoading(false);
    }
  }, [handleSnapshotUpdate]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const startSession = async (req: MonitoringSessionStartRequest = {}) => {
    try {
      setError(null);
      await startMonitoringSession(req);
      await refresh();
      reconnect();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start monitoring session.');
      throw err;
    }
  };

  const stopSession = async (reason = 'user_requested') => {
    try {
      setError(null);
      await stopMonitoringSession({ reason });
      await refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to stop monitoring session.');
      throw err;
    }
  };

  const submitSignal = async (sigIn: SignalEvidenceInput) => {
    try {
      setError(null);
      const updated = await updateSignalEvidence(sigIn);
      handleSnapshotUpdate(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update signal evidence.');
      throw err;
    }
  };

  const runSignalSimulation = async (
    req: SignalSimulateRequest
  ): Promise<SignalSimulateResult | null> => {
    try {
      setError(null);
      const result = await simulateSignal(req);
      handleSnapshotUpdate(result.snapshot);
      return result;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Signal simulation failed.');
      return null;
    }
  };

  const value: MonitoringContextValue = {
    snapshot,
    connectionStatus,
    isBackendHealthy,
    isLoading,
    error,
    liveHistory,
    timeline,
    activeTab,
    setActiveTab,
    linkTest,
    startSession,
    stopSession,
    submitSignal,
    runSignalSimulation,
    refresh,
  };

  return <MonitoringContext.Provider value={value}>{children}</MonitoringContext.Provider>;
};

export const useMonitoring = (): MonitoringContextValue => {
  const context = useContext(MonitoringContext);
  if (!context) {
    throw new Error('useMonitoring must be used within a MonitoringProvider');
  }
  return context;
};

/**
 * TypeScript type definitions for SpectrumSentry AI Phase 7 & 8 Unified Real-Time Monitoring.
 */

export type OverallStatus = 'NORMAL' | 'DEGRADED' | 'INTERRUPTED' | 'RECOVERING' | 'REVIEW';
export type ConsistencyStatus = 'CONSISTENT' | 'CONFLICTING' | 'UNCORRELATED';
export type SeverityLevel = 'INFO' | 'WARNING' | 'CRITICAL';
export type SignalQualityTier = 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR';
export type WebSocketConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'RECONNECTING' | 'DISCONNECTED';

export interface CommunicationSnapshot {
  available: boolean;
  status: string | null;
  packet_loss_percent: number | null;
  latency_ms: number | null;
  jitter_ms: number | null;
  throughput_kbps: number | null;
  health_score: number | null;
  is_interrupted: boolean;
  is_recovering: boolean;
}

export interface SignalSnapshot {
  available: boolean;
  stale: boolean;
  timestamp: string | null;
  age_seconds: number | null;
  predicted_modulation: string | null;
  ai_confidence: number | null;
  estimated_snr_db: number | null;
  signal_quality: SignalQualityTier | string | null;
}

export interface DecisionSnapshot {
  status: OverallStatus;
  severity: SeverityLevel;
  confidence: number;
  consistency: ConsistencyStatus;
  reasons: string[];
  primary_reason: string | null;
  contributing_factors: string[];
  recommendations: string[];
}

export interface SystemAlert {
  id?: number;
  timestamp: string | null;
  severity: SeverityLevel | string;
  category: string;
  message: string;
  source: string;
}

export interface UnifiedMonitoringSnapshot {
  monitoring_session_id: string | null;
  communication_session_id: string | null;
  timestamp: string;
  communication: CommunicationSnapshot;
  signal: SignalSnapshot;
  decision: DecisionSnapshot;
  alerts: SystemAlert[];
}

export interface MonitoringSessionStartRequest {
  monitoring_session_id?: string;
  communication_session_id?: string;
  auto_start_communication?: boolean;
  expected_packets?: number;
  interval_seconds?: number;
  timeout_seconds?: number;
  extra_metadata?: Record<string, unknown>;
}

export interface MonitoringSessionResponse {
  monitoring_session_id: string;
  communication_session_id: string | null;
  status: string;
  started_at: string;
  message: string;
}

export interface MonitoringSessionStopRequest {
  monitoring_session_id?: string;
  stop_communication?: boolean;
  reason?: string;
}

export interface MonitoringSessionSummary {
  id?: number;
  monitoring_session_id: string;
  communication_session_id: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  status: string;
  extra_metadata: Record<string, unknown> | null;
}

export interface MonitoringHistoryResponse {
  total: number;
  items: MonitoringSessionSummary[];
}

export interface SessionStatusResponse {
  monitoring_session_id: string | null;
  communication_session_id: string | null;
  active: boolean;
  communication_available: boolean;
  signal_available: boolean;
  signal_stale: boolean;
  timestamp: string;
}

export interface SignalEvidenceInput {
  predicted_modulation?: string;
  ai_confidence?: number;
  estimated_snr_db?: number;
  signal_quality?: string;
  timestamp?: string;
  features?: number[];
  signal_power?: number;
  noise_power?: number;
  experiment_id?: string;
  extra_data?: Record<string, unknown>;
}

export interface WebSocketMessage<T = unknown> {
  type: 'monitoring_snapshot' | 'signal_update' | 'session_started' | 'session_stopped' | string;
  timestamp: string;
  data: T;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  type: 'info' | 'warning' | 'critical' | 'success';
  title: string;
  details?: string;
  category: 'COMMUNICATION' | 'SIGNAL' | 'DECISION' | 'SESSION';
}

export interface ChartDataPoint {
  time: string;
  timestamp: number;
  packetLoss: number;
  latency: number;
  jitter: number;
  throughput: number;
  health: number;
  snr?: number | null;
}

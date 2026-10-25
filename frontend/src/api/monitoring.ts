import { apiClient } from './client';
import {
  CommunicationMetricsDetail,
  DeviceRosterResponse,
  MonitoringHistoryResponse,
  MonitoringSessionResponse,
  MonitoringSessionStartRequest,
  MonitoringSessionStopRequest,
  MonitoringSessionSummary,
  SessionStatusResponse,
  SignalEvidenceInput,
  SignalSimulateRequest,
  SignalSimulateResult,
  UnifiedMonitoringSnapshot,
} from '../types/monitoring';

export const getMonitoringStatus = async (
  sessionId?: string,
  deviceId?: string
): Promise<UnifiedMonitoringSnapshot> => {
  const params: Record<string, string> = {};
  if (sessionId) params.session_id = sessionId;
  if (deviceId) params.device_id = deviceId;
  const response = await apiClient.get<UnifiedMonitoringSnapshot>('/api/monitoring/status', {
    params,
  });
  return response.data;
};

export const startMonitoringSession = async (
  request: MonitoringSessionStartRequest = {}
): Promise<MonitoringSessionResponse> => {
  const response = await apiClient.post<MonitoringSessionResponse>(
    '/api/monitoring/session/start',
    request
  );
  return response.data;
};

export const stopMonitoringSession = async (
  request: MonitoringSessionStopRequest = {}
): Promise<MonitoringSessionSummary> => {
  const response = await apiClient.post<MonitoringSessionSummary>(
    '/api/monitoring/session/stop',
    request
  );
  return response.data;
};

export const getSessionStatus = async (
  sessionId?: string
): Promise<SessionStatusResponse> => {
  const params = sessionId ? { session_id: sessionId } : {};
  const response = await apiClient.get<SessionStatusResponse>(
    '/api/monitoring/session/status',
    { params }
  );
  return response.data;
};

export const updateSignalEvidence = async (
  signalInput: SignalEvidenceInput
): Promise<UnifiedMonitoringSnapshot> => {
  const response = await apiClient.post<UnifiedMonitoringSnapshot>(
    '/api/monitoring/signal',
    signalInput
  );
  return response.data;
};

export const simulateSignal = async (
  request: SignalSimulateRequest
): Promise<SignalSimulateResult> => {
  const response = await apiClient.post<SignalSimulateResult>(
    '/api/monitoring/signal/simulate',
    {
      sample_count: 2048,
      ...request,
    }
  );
  return response.data;
};

export const sendTestPacket = async (packet: {
  session_id: string;
  sequence_number: number;
  sender_timestamp: number;
  payload_size: number;
  client_rtt_ms?: number;
}): Promise<{ received_packets: number; status: string; health_score: number }> => {
  const response = await apiClient.post('/api/communication/packet', packet);
  return response.data;
};

export const stopCommunicationSession = async (
  sessionId: string,
  reason = 'completed'
) => {
  const response = await apiClient.post('/api/communication/session/stop', {
    session_id: sessionId,
    reason,
  });
  return response.data;
};

export const getCommunicationMetrics = async (
  sessionId?: string
): Promise<CommunicationMetricsDetail> => {
  const params = sessionId ? { session_id: sessionId } : {};
  const response = await apiClient.get<CommunicationMetricsDetail>(
    '/api/communication/metrics',
    { params }
  );
  return response.data;
};

export const getMonitoringHistory = async (
  skip = 0,
  limit = 20
): Promise<MonitoringHistoryResponse> => {
  const response = await apiClient.get<MonitoringHistoryResponse>(
    '/api/monitoring/history',
    {
      params: { skip, limit },
    }
  );
  return response.data;
};

export const getMonitoringSessionReport = async (
  sessionId: string
): Promise<Record<string, any>> => {
  const response = await apiClient.get<Record<string, any>>(
    `/api/monitoring/session/${encodeURIComponent(sessionId)}/report`
  );
  return response.data;
};

/** Per-device roster: how many devices are connected and how each link is doing. */
export const getDevices = async (): Promise<DeviceRosterResponse> => {
  const response = await apiClient.get<DeviceRosterResponse>('/api/monitoring/devices');
  return response.data;
};

/** URL for the server-rendered Excel-friendly CSV report download. */
export const getMonitoringSessionReportCsvUrl = (sessionId: string): string =>
  `/api/monitoring/session/${encodeURIComponent(sessionId)}/report.csv`;

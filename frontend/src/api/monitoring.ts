import { apiClient } from './client';
import {
  MonitoringHistoryResponse,
  MonitoringSessionResponse,
  MonitoringSessionStartRequest,
  MonitoringSessionStopRequest,
  MonitoringSessionSummary,
  SessionStatusResponse,
  SignalEvidenceInput,
  UnifiedMonitoringSnapshot,
} from '../types/monitoring';

export const getMonitoringStatus = async (
  sessionId?: string
): Promise<UnifiedMonitoringSnapshot> => {
  const params = sessionId ? { session_id: sessionId } : {};
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

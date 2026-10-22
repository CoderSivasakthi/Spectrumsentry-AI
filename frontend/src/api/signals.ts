import { apiClient } from './client';
import { SignalParameters, SignalProcessingData } from '../types/signal';

export const generateSignal = async (params: SignalParameters): Promise<SignalProcessingData> => {
  const response = await apiClient.post('/api/signals/generate', params);
  return response.data;
};

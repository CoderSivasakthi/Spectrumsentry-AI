import { apiClient } from './client';
import { Experiment } from '../types/experiment';

export const getExperiments = async (skip: number = 0, limit: number = 50): Promise<Experiment[]> => {
  const response = await apiClient.get('/api/experiments', { params: { skip, limit } });
  return response.data;
};

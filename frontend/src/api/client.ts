import axios from 'axios';

const env = (typeof import.meta !== 'undefined' && (import.meta as any).env) || {};

export const API_BASE_URL: string =
  env.VITE_API_BASE_URL ||
  env.VITE_API_URL ||
  'http://127.0.0.1:8000';

export const WS_BASE_URL: string = API_BASE_URL.replace(/^http/, 'ws');

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

export const checkBackendHealth = async (): Promise<{ status: string }> => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const getRootStatus = async (): Promise<{ name: string; status: string }> => {
  const response = await apiClient.get('/');
  return response.data;
};

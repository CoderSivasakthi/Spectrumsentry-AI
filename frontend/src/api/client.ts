import axios from 'axios';

const env = (typeof import.meta !== 'undefined' && (import.meta as any).env) || {};

export const API_BASE_URL: string =
  env.VITE_API_BASE_URL ||
  env.VITE_API_URL ||
  '';  // empty = relative, Vite proxy handles cross-host in dev

export const WS_BASE_URL: string = (() => {
  const url = env.VITE_WS_URL || '';
  if (url) return url;
  // In dev (Vite proxy), WebSocket connects to the Vite server origin.
  // In prod, the backend serves WS on the same host as the frontend.
  if (typeof window !== 'undefined') {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${loc.host}`;
  }
  return '';
})();

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

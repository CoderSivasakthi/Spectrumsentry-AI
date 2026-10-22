import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_BASE_URL } from '../api/client';
import {
  UnifiedMonitoringSnapshot,
  WebSocketConnectionStatus,
  WebSocketMessage,
} from '../types/monitoring';

interface UseMonitoringWebSocketOptions {
  enabled?: boolean;
  onSnapshot?: (snapshot: UnifiedMonitoringSnapshot) => void;
  onEvent?: (message: WebSocketMessage) => void;
}

export const useMonitoringWebSocket = (options: UseMonitoringWebSocketOptions = {}) => {
  const { enabled = true, onSnapshot, onEvent } = options;
  const [connectionStatus, setConnectionStatus] = useState<WebSocketConnectionStatus>('CONNECTING');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isUnmountedRef = useRef(false);

  const maxReconnectAttempts = 10;
  const baseDelayMs = 1500;

  const onSnapshotRef = useRef(onSnapshot);
  onSnapshotRef.current = onSnapshot;

  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const connect = useCallback(() => {
    if (!enabled || isUnmountedRef.current) return;

    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/monitoring`;
    setConnectionStatus(reconnectAttemptsRef.current === 0 ? 'CONNECTING' : 'RECONNECTING');

    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        if (isUnmountedRef.current) return;
        setConnectionStatus('CONNECTED');
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        if (isUnmountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(parsed);

          if (parsed.type === 'monitoring_snapshot' && parsed.data) {
            onSnapshotRef.current?.(parsed.data as UnifiedMonitoringSnapshot);
          }
          onEventRef.current?.(parsed);
        } catch (err) {
          console.warn('Failed to parse WebSocket message JSON:', err);
        }
      };

      ws.onerror = (err) => {
        console.debug('WebSocket error encountered:', err);
      };

      ws.onclose = () => {
        if (isUnmountedRef.current) return;
        setConnectionStatus('DISCONNECTED');
        socketRef.current = null;

        // Controlled exponential backoff reconnection
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            baseDelayMs * Math.pow(1.5, reconnectAttemptsRef.current),
            10000
          );
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (err) {
      console.warn('Failed to initiate WebSocket connection:', err);
      setConnectionStatus('DISCONNECTED');
    }
  }, [enabled]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((msg: string | object) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const payload = typeof msg === 'string' ? msg : JSON.stringify(msg);
      socketRef.current.send(payload);
    }
  }, []);

  return {
    connectionStatus,
    lastMessage,
    sendMessage,
    reconnect: connect,
  };
};

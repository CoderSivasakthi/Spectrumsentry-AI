export type CommunicationStatus = 'NORMAL' | 'DEGRADED' | 'INTERRUPTED' | 'REVIEW';

export interface CommunicationMetric {
  sequence_number: number;
  packets_transmitted: number;
  packets_received: number;
  packet_loss_rate: number;
  latency_ms: number;
  jitter_ms?: number;
  state: CommunicationStatus;
  timestamp?: string;
}

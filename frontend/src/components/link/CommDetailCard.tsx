import React, { useEffect, useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { getCommunicationMetrics } from '../../api/monitoring';
import { CommunicationMetricsDetail } from '../../types/monitoring';
import { StatusBadge } from '../common/StatusBadge';

/**
 * Extended, high-resolution communication telemetry for the active link test
 * (latency percentiles, loss counters, interruptions and recoveries).
 */
export const CommDetailCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const commSessionId = snapshot?.communication_session_id ?? null;
  const [metrics, setMetrics] = useState<CommunicationMetricsDetail | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string>('—');

  useEffect(() => {
    let alive = true;

    const poll = async () => {
      try {
        const data = await getCommunicationMetrics(commSessionId ?? undefined);
        if (!alive) return;
        const active = commSessionId != null && data.status !== 'STOPPED' && data.session_id !== 'none';
        setMetrics(active ? data : null);
        setUpdatedAt(new Date().toLocaleTimeString([], { hour12: false }));
      } catch {
        if (alive) setMetrics(null);
      }
    };

    void poll();
    const id = setInterval(poll, 1500);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [commSessionId]);

  if (!metrics) {
    return (
      <section className="card">
        <header className="card__header row--between row">
          <div>
            <h3 className="card__title">Detailed telemetry</h3>
            <p className="card__sub">Latency percentiles · loss counters · interruptions</p>
          </div>
        </header>
        <div className="card__body">
          <div className="pane-state" style={{ padding: 'var(--space-5) var(--space-4)' }}>
            <div className="pane-state__title">No active link session</div>
            <div className="pane-state__hint">
              Start a monitoring session and stream packets to collect percentile-level telemetry.
            </div>
          </div>
        </div>
      </section>
    );
  }

  const rows: Array<[string, string]> = [
    ['Packet loss', `${metrics.packet_loss_percent.toFixed(2)} %`],
    ['Average RTT', `${metrics.avg_latency_ms.toFixed(1)} ms`],
    ['Min RTT', `${metrics.min_latency_ms.toFixed(1)} ms`],
    ['Median RTT', `${metrics.median_latency_ms.toFixed(1)} ms`],
    ['95th percentile', `${metrics.p95_latency_ms.toFixed(1)} ms`],
    ['99th percentile', `${metrics.p99_latency_ms.toFixed(1)} ms`],
    ['Max RTT', `${metrics.max_latency_ms.toFixed(1)} ms`],
    ['Jitter', `${metrics.jitter_ms.toFixed(1)} ms`],
    ['Throughput', `${metrics.throughput_kbps.toFixed(1)} kbps`],
    ['Packets received', `${metrics.packets_received} / ${metrics.packets_sent}`],
    ['Packets lost', `${metrics.packets_lost}`],
    ['Bytes received', `${metrics.bytes_received} B`],
    ['Interruptions', `${metrics.interruption_count} · total ${metrics.total_interruption_duration_ms.toFixed(0)} ms`],
    ['Recoveries', `${metrics.recovery_count}`],
  ];

  return (
    <section className="card">
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Detailed telemetry</h3>
          <p className="card__sub">Session {metrics.session_id}</p>
        </div>
        <div className="row" style={{ gap: 'var(--space-2)' }}>
          <StatusBadge status={metrics.status} size="sm" />
          {metrics.is_interrupted && <span className="badge badge--crit">Timeout interruption</span>}
        </div>
      </header>

      <div className="card__body table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Metric</th>
              <th style={{ textAlign: 'right' }}>Value</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, value]) => (
              <tr key={label}>
                <td>{label}</td>
                <td className="num" style={{ textAlign: 'right' }}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card__footer row--between row">
        <span>Polled every 1.5 s</span>
        <span>Updated {updatedAt}</span>
      </div>
    </section>
  );
};

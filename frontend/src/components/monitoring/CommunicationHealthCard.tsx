import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import {
  Clock,
  ArrowDownUp,
  AlertOctagon,
  HeartPulse,
} from 'lucide-react';

export const CommunicationHealthCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const comm = snapshot?.communication;

  const healthScore = comm?.health_score ?? 100;
  const packetLoss = comm?.packet_loss_percent ?? 0;
  const latency = comm?.latency_ms ?? 0;
  const jitter = comm?.jitter_ms ?? 0;
  const throughput = comm?.throughput_kbps ?? 0;

  const healthTone =
    healthScore >= 90 ? 'ok' : healthScore >= 70 ? 'warn' : 'crit';

  const lossTone =
    packetLoss === 0 ? 'default' : packetLoss < 5 ? 'warn' : 'crit';

  const latencyTone =
    latency < 50 ? 'default' : latency < 100 ? 'warn' : 'crit';

  return (
    <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Communication Telemetry</h3>
          <p className="card__sub">Application-layer packet transport</p>
        </div>
        <div className="row" style={{ gap: 'var(--space-2)' }}>
          {comm?.is_interrupted && (
            <span className="badge badge--crit">
              <AlertOctagon size={11} />
              <span>Timeout interruption</span>
            </span>
          )}
          {comm?.is_recovering && <span className="badge badge--info">Restabilizing</span>}
          <StatusBadge status={comm?.status || 'STOPPED'} size="sm" />
        </div>
      </header>

      <div className="card__body telemetry-grid">
        <MetricCard
          label="Health score"
          value={healthScore.toFixed(0)}
          unit="/100"
          subtext={
            healthScore >= 90
              ? 'Optimal transport'
              : healthScore >= 70
              ? 'Moderate jitter/loss'
              : 'Impaired channel'
          }
          tone={healthTone}
          icon={<HeartPulse size={13} />}
        />

        <MetricCard
          label="Packet loss"
          value={packetLoss.toFixed(2)}
          unit="%"
          subtext={packetLoss === 0 ? 'Zero sequence gaps' : 'Missing packets detected'}
          tone={lossTone}
          icon={<AlertOctagon size={13} />}
        />

        <MetricCard
          label="RTT latency"
          value={latency.toFixed(1)}
          unit="ms"
          subtext={`Jitter: ${jitter.toFixed(1)} ms`}
          tone={latencyTone}
          icon={<Clock size={13} />}
        />

        <MetricCard
          label="Throughput"
          value={throughput.toFixed(1)}
          unit="kbps"
          subtext="Application telemetry rate"
          icon={<ArrowDownUp size={13} />}
        />
      </div>

      <div className="card__footer row--between row">
        <span>Channel: controlled socket ping-ack</span>
        <span className="row" style={{ gap: 6 }}>
          <span className={`dot${comm?.available ? ' dot--ok dot--live' : ''}`} />
          <span style={{ color: 'var(--text-3)' }}>
            {comm?.available ? 'Feed active' : 'Standby'}
          </span>
        </span>
      </div>
    </section>
  );
};

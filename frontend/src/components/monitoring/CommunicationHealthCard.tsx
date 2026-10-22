import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import {
  Network,
  Clock,
  ArrowDownUp,
  AlertOctagon,
  RefreshCw,
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
    healthScore >= 90
      ? 'emerald'
      : healthScore >= 70
      ? 'amber'
      : 'rose';

  const lossTone =
    packetLoss === 0
      ? 'default'
      : packetLoss < 5
      ? 'amber'
      : 'rose';

  const latencyTone =
    latency < 50
      ? 'default'
      : latency < 100
      ? 'amber'
      : 'rose';

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Communication Telemetry
            </h3>
            <p className="text-[11px] text-slate-400">
              Application-Layer Packet Transport (Phase 5)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {comm?.is_interrupted && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-rose-950/80 text-rose-300 border border-rose-500/40 animate-pulse">
              <AlertOctagon className="w-3 h-3 text-rose-400" />
              <span>Timeout Interruption</span>
            </span>
          )}

          {comm?.is_recovering && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-cyan-950/80 text-cyan-300 border border-cyan-500/40">
              <RefreshCw className="w-3 h-3 animate-spin text-cyan-400" />
              <span>Restabilizing</span>
            </span>
          )}

          <StatusBadge status={comm?.status || 'STOPPED'} size="sm" />
        </div>
      </div>

      {/* Main Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
        <MetricCard
          label="Health Score"
          value={healthScore.toFixed(0)}
          unit="/100"
          subtext={
            healthScore >= 90
              ? 'Optimal Transport'
              : healthScore >= 70
              ? 'Moderate Jitter/Loss'
              : 'Impaired Channel'
          }
          tone={healthTone}
          icon={<HeartPulse className="w-4 h-4" />}
        />

        <MetricCard
          label="Packet Loss"
          value={packetLoss.toFixed(2)}
          unit="%"
          subtext={packetLoss === 0 ? 'Zero sequence gaps' : 'Missing packets detected'}
          tone={lossTone}
          icon={<AlertOctagon className="w-4 h-4" />}
        />

        <MetricCard
          label="RTT Latency"
          value={latency.toFixed(1)}
          unit="ms"
          subtext={`Jitter: ${jitter.toFixed(1)} ms`}
          tone={latencyTone}
          icon={<Clock className="w-4 h-4" />}
        />

        <MetricCard
          label="Throughput"
          value={throughput.toFixed(1)}
          unit="kbps"
          subtext="Application telemetry rate"
          icon={<ArrowDownUp className="w-4 h-4" />}
        />
      </div>

      {/* Footer Info */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
        <span>Channel: Controlled Socket Ping-Ack</span>
        <span>
          Feed State:{' '}
          <span className={comm?.available ? 'text-emerald-400' : 'text-slate-500'}>
            {comm?.available ? 'Active Stream' : 'Standby / Inactive'}
          </span>
        </span>
      </div>
    </div>
  );
};

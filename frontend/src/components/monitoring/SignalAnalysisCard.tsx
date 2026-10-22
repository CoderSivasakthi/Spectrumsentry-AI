import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import {
  Radio,
  Cpu,
  Gauge,
  Clock,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';

export const SignalAnalysisCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const sig = snapshot?.signal;

  const isAvailable = sig?.available ?? false;
  const isStale = sig?.stale ?? false;
  const modulation = sig?.predicted_modulation || (sig as any)?.detected_modulation || '—';
  const confidence = sig?.ai_confidence != null ? (sig.ai_confidence * 100).toFixed(1) : '—';
  const snr = sig?.estimated_snr_db != null ? sig.estimated_snr_db.toFixed(1) : '—';
  const quality = sig?.signal_quality || (sig as any)?.quality_assessment || '—';
  const age = sig?.age_seconds != null ? `${sig.age_seconds.toFixed(1)}s` : '—';

  // Constellation Ideal Representation for the detected modulation
  const renderConstellationGraphic = () => {
    const points: [number, number][] = [];
    if (modulation === 'BPSK') {
      points.push([-0.8, 0], [0.8, 0]);
    } else if (modulation === 'QPSK') {
      points.push([-0.6, -0.6], [0.6, -0.6], [-0.6, 0.6], [0.6, 0.6]);
    } else if (modulation === '16-QAM') {
      const levels = [-0.75, -0.25, 0.25, 0.75];
      for (const i of levels) {
        for (const q of levels) {
          points.push([i, q]);
        }
      }
    }

    return (
      <div className="relative w-28 h-28 bg-slate-950/80 rounded-xl border border-slate-800 flex items-center justify-center p-2">
        {/* Axes */}
        <div className="absolute inset-x-2 top-1/2 h-[1px] bg-slate-800" />
        <div className="absolute inset-y-2 left-1/2 w-[1px] bg-slate-800" />
        <span className="absolute top-1 right-1.5 text-[8px] font-mono text-slate-600">Q</span>
        <span className="absolute bottom-1 right-1.5 text-[8px] font-mono text-slate-600">I</span>

        {points.length > 0 ? (
          <div className="relative w-full h-full">
            {points.map(([i, q], idx) => {
              const xPercent = ((i + 1) / 2) * 100;
              const yPercent = ((1 - q) / 2) * 100;
              return (
                <div
                  key={idx}
                  className="absolute w-2 h-2 -ml-1 -mt-1 rounded-full bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]"
                  style={{ left: `${xPercent}%`, top: `${yPercent}%` }}
                />
              );
            })}
          </div>
        ) : (
          <div className="text-[10px] text-slate-600 text-center font-mono">
            No signal classified
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Signal & AI Classification
            </h3>
            <p className="text-[11px] text-slate-400">
              Physical Layer Inference (Phase 4 DSP & MLP)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isStale ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-950/80 text-amber-300 border border-amber-500/40">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              <span>Evidence Stale ({age})</span>
            </span>
          ) : isAvailable ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-emerald-950/60 text-emerald-300 border border-emerald-500/30">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span>Fresh ({age})</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-900 text-slate-500 border border-slate-800">
              Inactive Feed
            </span>
          )}

          {isAvailable && <StatusBadge status={quality} size="sm" />}
        </div>
      </div>

      {/* Main Grid: Visualizer + Metric Cards */}
      <div className="flex flex-col sm:flex-row items-center gap-4 mt-4">
        {/* Constellation Schematic */}
        <div className="flex flex-col items-center shrink-0">
          {renderConstellationGraphic()}
          <span className="text-[10px] text-slate-500 font-mono mt-1.5 uppercase tracking-wider">
            Detected Constellation
          </span>
        </div>

        {/* 4 Metrics Cards */}
        <div className="grid grid-cols-2 gap-2.5 w-full">
          <MetricCard
            label="Modulation"
            value={modulation}
            subtext="Classified scheme"
            icon={<Radio className="w-4 h-4" />}
            tone={modulation !== '—' ? 'cyan' : 'default'}
          />

          <MetricCard
            label="AI Confidence"
            value={confidence}
            unit="%"
            subtext={
              sig?.ai_confidence != null && sig.ai_confidence >= 0.85
                ? 'High certainty'
                : 'Marginal classification'
            }
            tone={
              sig?.ai_confidence != null && sig.ai_confidence >= 0.85
                ? 'emerald'
                : sig?.ai_confidence != null && sig.ai_confidence < 0.7
                ? 'amber'
                : 'default'
            }
            icon={<Sparkles className="w-4 h-4" />}
          />

          <MetricCard
            label="Estimated SNR"
            value={snr}
            unit="dB"
            subtext={
              sig?.estimated_snr_db != null && sig.estimated_snr_db >= 10
                ? 'Clear channel'
                : 'Elevated noise floor'
            }
            tone={
              sig?.estimated_snr_db != null && sig.estimated_snr_db >= 10
                ? 'emerald'
                : sig?.estimated_snr_db != null && sig.estimated_snr_db < 0
                ? 'rose'
                : 'amber'
            }
            icon={<Gauge className="w-4 h-4" />}
          />

          <MetricCard
            label="Signal Age"
            value={age}
            subtext={isStale ? 'Exceeds freshness window' : 'Active valid window'}
            tone={isStale ? 'amber' : 'default'}
            icon={<Clock className="w-4 h-4" />}
          />
        </div>
      </div>

      {/* Disclaimer / Note */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
        <span>Model: MLPClassifier (v1.0 • 23 DSP Features)</span>
        <span className="italic">
          *Note: Constellation displays ideal detected state (No SDR hardware required)
        </span>
      </div>
    </div>
  );
};

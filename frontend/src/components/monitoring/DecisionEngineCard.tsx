import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';
import {
  Brain,
  ShieldAlert,
  Lightbulb,
} from 'lucide-react';

export const DecisionEngineCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const decision = snapshot?.decision;
  const comm = snapshot?.communication;
  const sig = snapshot?.signal;

  const isConflict =
    decision?.status === 'REVIEW' && decision?.consistency === 'CONFLICTING';

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Decision Engine Analysis
            </h3>
            <p className="text-[11px] text-slate-400">
              Deterministic Explainable Correlation (Phase 6)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {decision && <StatusBadge status={decision.status} size="sm" />}
          {decision?.severity && (
            <span
              className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border ${
                decision.severity === 'CRITICAL'
                  ? 'bg-rose-950/80 text-rose-300 border-rose-500/30'
                  : decision.severity === 'WARNING'
                  ? 'bg-amber-950/80 text-amber-300 border-amber-500/30'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              Severity: {decision.severity}
            </span>
          )}
        </div>
      </div>

      {/* Conflict / Review Dedicated Banner */}
      {isConflict && (
        <div className="mt-4 p-3.5 rounded-xl border border-purple-500/40 bg-purple-950/30 text-purple-200">
          <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-wider text-purple-300">
            <ShieldAlert className="w-4 h-4 text-purple-400" />
            <span>Cross-Domain Evidence Divergence Detected</span>
          </div>
          <p className="text-xs text-purple-200/90 mt-1 leading-relaxed">
            The physical layer and network application telemetry report opposing conditions.
            Physical SNR ({sig?.estimated_snr_db?.toFixed(1) ?? '—'} dB) and network packet loss ({comm?.packet_loss_percent?.toFixed(1) ?? '—'}%)
            suggest transport buffer, airtime contention, or host processing bottlenecks rather than physical wireless degradation.
          </p>
        </div>
      )}

      {/* Core Explanation Box */}
      <div className="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
        <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 font-semibold block mb-1">
          Primary Diagnostic Assessment
        </span>
        <p className="text-sm text-slate-100 font-medium leading-relaxed">
          {decision?.primary_reason || 'Standby baseline: Awaiting communication or signal evidence.'}
        </p>

        {/* Contributing Factors */}
        {decision?.contributing_factors && decision.contributing_factors.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-800/60">
            <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-1.5">
              Contributing Metric Observations:
            </span>
            <ul className="space-y-1">
              {decision.contributing_factors.map((factor, idx) => (
                <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                  <span className="text-sky-400 font-bold">•</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recommendations */}
      {decision?.recommendations && decision.recommendations.length > 0 && (
        <div className="mt-3 p-3.5 rounded-xl bg-slate-900/40 border border-slate-800/60">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
            <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
            <span>Recommended Actions</span>
          </div>
          <ul className="space-y-1">
            {decision.recommendations.map((rec, idx) => (
              <li key={idx} className="text-xs text-slate-400 flex items-start gap-1.5">
                <span className="text-amber-400/80 font-mono">→</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer Meta */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500 font-mono">
        <span>Consistency: {decision?.consistency || 'UNCORRELATED'}</span>
        <span>Decision Confidence: {decision ? (decision.confidence * 100).toFixed(0) : 0}%</span>
      </div>
    </div>
  );
};

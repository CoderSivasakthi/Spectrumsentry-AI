import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';
import {
  Activity,
  Play,
  Square,
  RefreshCw,
} from 'lucide-react';

export const SystemStatusHeader: React.FC = () => {
  const {
    snapshot,
    startSession,
    stopSession,
    refresh,
    isLoading,
  } = useMonitoring();

  const decision = snapshot?.decision;
  const comm = snapshot?.communication;
  const sig = snapshot?.signal;
  const sessionId = snapshot?.monitoring_session_id;
  const commSessionId = snapshot?.communication_session_id;

  const handleToggleSession = async () => {
    if (sessionId) {
      await stopSession('user_stopped');
    } else {
      await startSession();
    }
  };

  return (
    <div className="glass-panel p-5 sm:p-6 rounded-2xl border border-slate-800 shadow-xl relative overflow-hidden">
      {/* Background Status Glow */}
      <div
        className={`absolute -right-20 -top-20 w-64 h-64 rounded-full blur-3xl pointer-events-none transition-colors duration-700 opacity-20 ${
          decision?.status === 'NORMAL'
            ? 'bg-emerald-500'
            : decision?.status === 'DEGRADED'
            ? 'bg-amber-500'
            : decision?.status === 'INTERRUPTED'
            ? 'bg-rose-500'
            : decision?.status === 'REVIEW'
            ? 'bg-purple-500'
            : 'bg-sky-500'
        }`}
      />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
        
        {/* Left: Overall Health & Status */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-slate-900 border border-slate-700 flex items-center justify-center text-slate-300">
              <Activity className="w-6 h-6 text-sky-400" />
            </div>

            <div>
              <div className="text-[11px] font-semibold text-slate-400 tracking-wider uppercase flex items-center gap-2">
                <span>System Health Assessment</span>
                {snapshot && (
                  <span className="text-[10px] text-slate-500 font-mono">
                    (Updated {new Date(snapshot.timestamp).toLocaleTimeString()})
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2.5 mt-1">
                <StatusBadge
                  status={decision?.status || 'NORMAL'}
                  size="lg"
                  className="font-bold tracking-wide"
                />

                {decision?.consistency && (
                  <StatusBadge
                    status={decision.consistency}
                    size="md"
                    className="hidden sm:inline-flex"
                  />
                )}
              </div>
            </div>
          </div>

          {/* Decision Confidence Meter */}
          {decision && (
            <div className="border-t sm:border-t-0 sm:border-l border-slate-800 pt-3 sm:pt-0 sm:pl-4 flex flex-col justify-center">
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">
                Confidence
              </span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-xl font-bold font-mono text-white">
                  {(decision.confidence * 100).toFixed(0)}%
                </span>
                <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      decision.confidence >= 0.85
                        ? 'bg-emerald-400'
                        : decision.confidence >= 0.7
                        ? 'bg-amber-400'
                        : 'bg-rose-400'
                    }`}
                    style={{ width: `${Math.min(100, decision.confidence * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Center: Active Session Info */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 border-t lg:border-t-0 lg:border-l border-slate-800 pt-4 lg:pt-0 lg:pl-6">
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">
              Monitoring Session
            </div>
            <div className="text-slate-200 font-semibold mt-0.5">
              {sessionId ? (
                <span className="text-sky-300 font-mono">{sessionId}</span>
              ) : (
                <span className="text-slate-500">Standby Baseline</span>
              )}
            </div>
          </div>

          {commSessionId && (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                Comm Channel
              </div>
              <div className="text-slate-300 font-mono mt-0.5">{commSessionId}</div>
            </div>
          )}

          <div className="hidden xl:block">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">
              Evidence Feeds
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span
                className={`w-2 h-2 rounded-full ${
                  comm?.available ? 'bg-emerald-400' : 'bg-slate-600'
                }`}
                title={comm?.available ? 'Communication feed active' : 'Communication feed inactive'}
              />
              <span className="text-[11px] text-slate-400">Comm</span>
              <span
                className={`w-2 h-2 rounded-full ml-1 ${
                  sig?.available && !sig.stale
                    ? 'bg-emerald-400'
                    : sig?.stale
                    ? 'bg-amber-400'
                    : 'bg-slate-600'
                }`}
                title={
                  sig?.stale
                    ? 'Signal feed stale'
                    : sig?.available
                    ? 'Signal feed fresh'
                    : 'Signal feed inactive'
                }
              />
              <span className="text-[11px] text-slate-400">Signal</span>
            </div>
          </div>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-2 shrink-0 border-t lg:border-t-0 pt-4 lg:pt-0">
          <button
            onClick={refresh}
            disabled={isLoading}
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Refresh state from backend"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleToggleSession}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold tracking-wider uppercase transition-all shadow-lg ${
              sessionId
                ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-rose-950/50'
                : 'bg-sky-600 hover:bg-sky-500 text-white shadow-sky-950/50'
            }`}
          >
            {sessionId ? (
              <>
                <Square className="w-3.5 h-3.5 fill-current" />
                <span>Stop Session</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start Monitoring</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
};

import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  XOctagon,
  Info,
  Calendar,
} from 'lucide-react';

export const EventTimeline: React.FC = () => {
  const { timeline } = useMonitoring();

  const getEventIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'warning':
        return <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />;
      case 'critical':
        return <XOctagon className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Info className="w-3.5 h-3.5 text-sky-400" />;
    }
  };

  const getCategoryBadge = (category: string) => {
    const colors: Record<string, string> = {
      COMMUNICATION: 'text-sky-400 bg-sky-950/40 border-sky-500/20',
      SIGNAL: 'text-purple-400 bg-purple-950/40 border-purple-500/20',
      DECISION: 'text-amber-400 bg-amber-950/40 border-amber-500/20',
      SESSION: 'text-emerald-400 bg-emerald-950/40 border-emerald-500/20',
    };
    return (
      <span
        className={`px-1.5 py-0.2 rounded border text-[9px] font-mono tracking-wider uppercase ${
          colors[category] || 'text-slate-400 bg-slate-900 border-slate-800'
        }`}
      >
        {category}
      </span>
    );
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Clock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Recent Event Timeline
            </h3>
            <p className="text-[11px] text-slate-400">
              State Transitions & Milestone History
            </p>
          </div>
        </div>

        <span className="text-xs font-mono text-slate-500">
          {timeline.length} Events
        </span>
      </div>

      {/* Timeline List */}
      <div className="mt-4 space-y-3 max-h-72 overflow-y-auto pr-1">
        {timeline.length > 0 ? (
          timeline.map((item, idx) => (
            <div key={item.id || idx} className="flex items-start gap-3 text-xs">
              <div className="mt-0.5 shrink-0">{getEventIcon(item.type)}</div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-slate-200 truncate">
                    {item.title}
                  </span>
                  <span className="font-mono text-[10px] text-slate-400 shrink-0">
                    {item.timestamp}
                  </span>
                </div>

                {item.details && (
                  <p className="text-slate-400 text-[11px] mt-0.5 leading-snug">
                    {item.details}
                  </p>
                )}

                <div className="mt-1">{getCategoryBadge(item.category)}</div>
              </div>
            </div>
          ))
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500 font-mono text-xs">
            <Calendar className="w-6 h-6 mb-2 text-slate-600" />
            <span>No events recorded yet</span>
            <span className="text-[10px] text-slate-600 mt-0.5">
              State transitions and alerts will appear in chronological order
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-500 flex items-center justify-between font-mono">
        <span>Timeline Buffer: Last 30 Events</span>
        <span>Auto-synchronized</span>
      </div>
    </div>
  );
};

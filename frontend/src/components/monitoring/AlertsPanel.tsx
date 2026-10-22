import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { Bell, BellOff, AlertTriangle, XOctagon, Info } from 'lucide-react';

export const AlertsPanel: React.FC = () => {
  const { snapshot } = useMonitoring();
  const alerts = snapshot?.alerts || [];

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Bell className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Active System Alerts
            </h3>
            <p className="text-[11px] text-slate-400">
              Correlated Anomalies & Warnings
            </p>
          </div>
        </div>

        <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
          {alerts.length} Active
        </span>
      </div>

      {/* Alerts List */}
      <div className="mt-4 space-y-2.5 max-h-64 overflow-y-auto pr-1">
        {alerts.length > 0 ? (
          alerts.map((alert, idx) => {
            const isCritical = alert.severity === 'CRITICAL';
            const isWarning = alert.severity === 'WARNING';

            const borderClasses = isCritical
              ? 'border-rose-500/40 bg-rose-950/20 text-rose-200'
              : isWarning
              ? 'border-amber-500/40 bg-amber-950/20 text-amber-200'
              : 'border-slate-800 bg-slate-900/40 text-slate-300';

            const Icon = isCritical
              ? XOctagon
              : isWarning
              ? AlertTriangle
              : Info;

            return (
              <div
                key={alert.id || idx}
                className={`p-3 rounded-xl border text-xs flex items-start gap-3 transition-colors ${borderClasses}`}
              >
                <Icon className="w-4 h-4 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold tracking-wide uppercase text-[10px]">
                      {(alert as any).alert_type || alert.category || 'System'}{alert.source ? ` • ${alert.source}` : ''}
                    </span>
                    {alert.timestamp && (
                      <span className="font-mono text-[10px] text-slate-400 shrink-0">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 font-medium leading-relaxed">{alert.message}</p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center text-slate-500">
            <BellOff className="w-6 h-6 mb-2 text-slate-600" />
            <p className="text-xs font-medium text-slate-400">No active system alerts</p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Link telemetry and physical-layer metrics are operating within thresholds
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-500 flex items-center justify-between">
        <span>Alert Thresholds: Phase 6 Rules</span>
        <span>Resolution: Auto-monitored</span>
      </div>
    </div>
  );
};

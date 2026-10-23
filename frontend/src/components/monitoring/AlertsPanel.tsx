import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { BellOff, AlertTriangle, XOctagon, Info, Bell } from 'lucide-react';

export const AlertsPanel: React.FC = () => {
  const { snapshot } = useMonitoring();
  const alerts = snapshot?.alerts || [];

  return (
    <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <header className="card__header row--between row">
        <div>
          <div className="row" style={{ gap: 6 }}>
            <Bell size={14} style={{ color: 'var(--text-3)' }} />
            <h3 className="card__title">Active System Alerts</h3>
          </div>
          <p className="card__sub">Warnings raised on every snapshot</p>
        </div>
        <span className="badge">{alerts.length} active</span>
      </header>

      <div
        className="card__body"
        style={{
          display: 'grid',
          gap: 'var(--space-2)',
          maxHeight: 300,
          overflowY: 'auto',
          paddingRight: 4,
          flex: 1,
          alignContent: 'start',
        }}
      >
        {alerts.length > 0 ? (
          alerts.map((alert, idx) => {
            const exact = alert.severity === 'CRITICAL';
            const warn = alert.severity === 'WARNING';
            const variant = exact ? 'alert-item--crit' : warn ? 'alert-item--warn' : '';
            const iconColor = exact
              ? 'alert-item__icon--crit'
              : warn
              ? 'alert-item__icon--warn'
              : 'alert-item__icon--info';
            const Icon = exact ? XOctagon : warn ? AlertTriangle : Info;

            return (
              <div key={alert.id || idx} className={`alert-item ${variant}`.trim()}>
                <span className={iconColor}>
                  <Icon size={15} />
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="row--between row">
                    <span className="alert-item__meta">
                      {(alert as any).alert_type || alert.category || 'System'}
                      {alert.source ? ` · ${alert.source}` : ''}
                    </span>
                    {alert.timestamp && (
                      <span className="alert-item__meta" style={{ flex: 'none' }}>
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <p className="alert-item__msg">{alert.message}</p>
                </div>
              </div>
            );
          })
        ) : (
          <div className="pane-state" style={{ paddingBlock: 'var(--space-6)' }}>
            <span className="pane-state__icon">
              <BellOff size={18} />
            </span>
            <p className="pane-state__title">No active system alerts</p>
            <p className="pane-state__hint">
              Link telemetry and physical-layer metrics are operating within thresholds.
            </p>
          </div>
        )}
      </div>

      <div className="card__footer row--between row">
        <span>Threshold rules re-evaluated on every snapshot</span>
        <span>Auto-resolved</span>
      </div>
    </section>
  );
};

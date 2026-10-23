import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';
import { ShieldAlert } from 'lucide-react';

export const DecisionEngineCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const decision = snapshot?.decision;
  const comm = snapshot?.communication;
  const sig = snapshot?.signal;

  const isConflict =
    decision?.status === 'REVIEW' && decision?.consistency === 'CONFLICTING';

  const severityVariant =
    decision?.severity === 'CRITICAL'
      ? 'badge--crit'
      : decision?.severity === 'WARNING'
      ? 'badge--warn'
      : '';

  return (
    <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Decision Engine Analysis</h3>
          <p className="card__sub">Explainable cross-domain correlation</p>
        </div>
        <div className="row" style={{ gap: 'var(--space-2)' }}>
          {decision && <StatusBadge status={decision.status} size="sm" />}
          {decision?.severity && (
            <span className={`badge ${severityVariant}`.trim()}>
              {decision.severity}
            </span>
          )}
        </div>
      </header>

      {isConflict && (
        <div
          className="card--inset"
          style={{ marginTop: 'var(--space-4)', background: 'var(--crit-bg)', borderColor: 'var(--crit-border)' }}
        >
          <div className="row" style={{ gap: 'var(--space-2)' }}>
            <ShieldAlert size={15} style={{ color: 'var(--crit-fg)', flex: 'none' }} />
            <span style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--crit-fg)' }}>
              Cross-Domain Evidence Divergence Detected
            </span>
          </div>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-2)', marginTop: 'var(--space-1)' }}>
            The physical layer and network application telemetry report opposing conditions.
            Physical SNR ({sig?.estimated_snr_db?.toFixed(1) ?? '—'} dB) and network packet loss ({comm?.packet_loss_percent?.toFixed(1) ?? '—'}%)
            suggest transport buffer, airtime contention, or host processing bottlenecks rather than physical wireless degradation.
          </p>
        </div>
      )}

      <div className="card__body" style={{ flex: 1 }}>
        <div className="card--inset">
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
            Primary assessment
          </div>
          <p
            style={{
              marginTop: 'var(--space-1)',
              fontSize: 'var(--text-base)',
              color: 'var(--text-1)',
              fontWeight: 500,
              lineHeight: 1.55,
            }}
          >
            {decision?.primary_reason || 'Standby baseline: Awaiting communication or signal evidence.'}
          </p>

          {decision?.contributing_factors && decision.contributing_factors.length > 0 && (
            <div style={{ marginTop: 'var(--space-3)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--border-faint)' }}>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
                Contributing metric observations
              </div>
              <ul style={{ marginTop: 6, display: 'grid', gap: 4 }}>
                {decision.contributing_factors.map((factor, idx) => (
                  <li
                    key={idx}
                    className="row"
                    style={{ alignItems: 'flex-start', fontSize: 'var(--text-sm)', color: 'var(--text-2)' }}
                  >
                    <span style={{ color: 'var(--text-3)' }}>•</span>
                    <span>{factor}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {decision?.recommendations && decision.recommendations.length > 0 && (
          <div style={{ marginTop: 'var(--space-3)' }}>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
              Recommended actions
            </div>
            <ul style={{ marginTop: 6, display: 'grid', gap: 4 }}>
              {decision.recommendations.map((rec, idx) => (
                <li
                  key={idx}
                  className="row"
                  style={{ alignItems: 'flex-start', gap: 8, fontSize: 'var(--text-sm)', color: 'var(--text-2)' }}
                >
                  <span className="num" style={{ color: 'var(--text-3)' }}>→</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="card__footer row--between row">
        <span className="num">Consistency: {decision?.consistency || 'UNCORRELATED'}</span>
        <span className="num">
          Decision confidence: {decision ? (decision.confidence * 100).toFixed(0) : 0}%
        </span>
      </div>
    </section>
  );
};

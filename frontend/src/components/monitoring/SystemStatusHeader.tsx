import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';
import { RefreshCw } from 'lucide-react';

const STATUS_TONE: Record<string, string> = {
  NORMAL: 'var(--ok-fg)',
  DEGRADED: 'var(--warn-fg)',
  INTERRUPTED: 'var(--crit-fg)',
  RECOVERING: 'var(--accent)',
  REVIEW: 'var(--text-2)',
};

const HERO_TONE_CLASS: Record<string, string> = {
  NORMAL: 'k-ok',
  DEGRADED: 'k-warn',
  FAIR: 'k-warn',
  INTERRUPTED: 'k-crit',
  CRITICAL: 'k-crit',
  POOR: 'k-crit',
  RECOVERING: 'k-info',
};

export const SystemStatusHeader: React.FC = () => {
  const { snapshot, refresh, isLoading } =
    useMonitoring();

  const decision = snapshot?.decision;
  const comm = snapshot?.communication;
  const sig = snapshot?.signal;
  const sessionId = snapshot?.monitoring_session_id;
  const commSessionId = snapshot?.communication_session_id;
  const status = decision?.status || 'NORMAL';

  const confidenceTone =
    (decision?.confidence ?? 0) >= 0.85
      ? 'ok'
      : (decision?.confidence ?? 0) >= 0.7
      ? 'warn'
      : 'crit';

  return (
    <section
      className={`card card--hero ${HERO_TONE_CLASS[status] || ''}`.trim()}
    >
      <div
        className="row"
        style={{
          alignItems: 'flex-start',
          gap: 'var(--space-6)',
          flexWrap: 'wrap',
        }}
      >
        {/* Status */}
        <div style={{ minWidth: 220, flex: '1 1 260px' }}>
          <div className="row" style={{ gap: 8 }}>
            <span className="eyebrow">System Health Assessment</span>
            {snapshot && (
              <span className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
                (Updated {new Date(snapshot.timestamp).toLocaleTimeString()})
              </span>
            )}
          </div>

          <div className="row" style={{ gap: 'var(--space-2)', marginTop: 'var(--space-1)' }}>
            <span
              className="num"
              style={{
                fontSize: 'var(--text-2xl)',
                color: STATUS_TONE[status] || 'var(--text-1)',
                fontWeight: 700,
                letterSpacing: '-0.02em',
              }}
            >
              {status}
            </span>
            {decision?.consistency && decision.consistency !== 'CONSISTENT' && (
              <StatusBadge status={decision.consistency} size="md" />
            )}
          </div>

          {decision && (
            <div className="row" style={{ gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
              <span className="num" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
                Confidence
              </span>
              <div className="meter" style={{ width: 100 }}>
                <div
                  className={`meter__fill meter__fill--${confidenceTone}`}
                  style={{ width: `${Math.min(100, decision.confidence * 100)}%` }}
                />
              </div>
              <span className="num" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-2)' }}>
                {(decision.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Session & feeds */}
        <div
          className="row hidden-sm"
          style={{
            gap: 'var(--space-5)',
            flex: '1 1 240px',
            borderLeft: '1px solid var(--border-faint)',
            paddingLeft: 'var(--space-5)',
            minHeight: 64,
            alignItems: 'flex-start',
          }}
        >
          <div>
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
              Monitoring session
            </div>
            <div className="num" style={{ fontSize: 'var(--text-sm)', marginTop: 2 }}>
              {sessionId ? (
                <span style={{ color: 'var(--accent)' }}>{sessionId}</span>
              ) : (
                <span style={{ color: 'var(--text-3)' }}>Standby</span>
              )}
            </div>
          </div>
          {commSessionId && (
            <div>
              <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
                Comm channel
              </div>
              <div className="num" style={{ fontSize: 'var(--text-sm)', marginTop: 2, color: 'var(--text-2)' }}>
                {commSessionId}
              </div>
            </div>
          )}
          <div className="row" style={{ gap: 'var(--space-3)', marginTop: 14 }}>
            <span className="row" style={{ gap: 5, fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
              <span
                className={`dot${comm?.available ? ' dot--ok dot--live' : ''}`}
                title={comm?.available ? 'Communication feed active' : 'Communication feed inactive'}
              />
              Comm
            </span>
            <span className="row" style={{ gap: 5, fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
              <span
                className={`dot${
                  sig?.available && !sig.stale
                    ? ' dot--ok dot--live'
                    : sig?.stale
                    ? ' dot--warn'
                    : ''
                }`}
                title={
                  sig?.stale
                    ? 'Signal feed stale'
                    : sig?.available
                    ? 'Signal feed fresh'
                    : 'Signal feed inactive'
                }
              />
              Signal
            </span>
          </div>
        </div>

        {/* Refresh — session start/stop lives in the sidebar */}
        <div className="row" style={{ gap: 'var(--space-2)', flex: 'none' }}>
          <button
            className="btn btn--ghost"
            onClick={refresh}
            disabled={isLoading}
            title="Refresh state from backend"
            aria-label="Refresh"
            style={{ padding: '9px 10px' }}
          >
            <RefreshCw size={15} style={isLoading ? { animation: 'spin 0.8s linear infinite' } : undefined} />
          </button>
        </div>
      </div>
    </section>
  );
};

import React from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { MetricCard } from '../common/MetricCard';
import { StatusBadge } from '../common/StatusBadge';
import { REFERENCE_POINTS } from '../signal/ConstellationPoints';
import {
  Radio,
  Gauge,
  Clock,
  Sparkles,
  TriangleAlert,
  CheckCircle2,
} from 'lucide-react';

const Constellation: React.FC<{ modulation: string }> = ({ modulation }) => {
  const points = REFERENCE_POINTS[modulation];

  const map = ([i, q]: [number, number]) => ({
    x: 50 + i * 46,
    y: 50 - q * 46,
  });

  return (
    <svg
      viewBox="0 0 120 120"
      width="118"
      height="118"
      role="img"
      aria-label={
        points
          ? `Reference constellation for ${modulation}`
          : 'No signal classified'
      }
      style={{ display: 'block' }}
    >
      {/* axes + quadrant ticks */}
      <line x1="14" y1="60" x2="106" y2="60" stroke="var(--border)" strokeWidth="1" />
      <line x1="60" y1="14" x2="60" y2="106" stroke="var(--border)" strokeWidth="1" />
      <text x="104" y="94" textAnchor="end" fontSize="9" fill="var(--text-4)" fontFamily="var(--font-mono)">I</text>
      <text x="98" y="16" fontSize="9" fill="var(--text-4)" fontFamily="var(--font-mono)">Q</text>
      {[0.25, 0.75].map((r) => (
        <g key={r}>
          <line x1={60 + r * 80} y1="58" x2={60 + r * 80} y2="62" stroke="var(--border-faint)" strokeWidth="1" />
          <line x1="58" y1={60 + r * 80} x2="62" y2={60 + r * 80} stroke="var(--border-faint)" strokeWidth="1" />
          <line
            x1={60 - r * 80} y1="58" x2={60 - r * 80} y2="62"
            stroke="var(--border-faint)" strokeWidth="1" />
          <line x1="58" y1={60 - r * 80} x2="62" y2={60 - r * 80} stroke="var(--border-faint)" strokeWidth="1" />
        </g>
      ))}

      {points ? (
        points.map(([i, q], idx) => {
          const { x, y } = map([i, q]);
          return <circle key={idx} cx={x} cy={y} r="3.5" fill="var(--accent)" opacity="0.9" />;
        })
      ) : (
        <text x="60" y="63" textAnchor="middle" fontSize="9" fill="var(--text-4)">
          No signal classified
        </text>
      )}
    </svg>
  );
};

export const SignalAnalysisCard: React.FC = () => {
  const { snapshot } = useMonitoring();
  const sig = snapshot?.signal;

  const isAvailable = sig?.available ?? false;
  const isStale = sig?.stale ?? false;
  const modulation = sig?.predicted_modulation || '—';
  const confidence = sig?.ai_confidence != null ? (sig.ai_confidence * 100).toFixed(1) : '—';
  const snr = sig?.estimated_snr_db != null ? sig.estimated_snr_db.toFixed(1) : '—';
  const quality = sig?.signal_quality || '—';
  const age = sig?.age_seconds != null ? `${sig.age_seconds.toFixed(1)}s` : '—';

  return (
    <section className="card" style={{ display: 'flex', flexDirection: 'column' }}>
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Signal &amp; AI Classification</h3>
          <p className="card__sub">Physical-layer classification</p>
        </div>
        <div className="row" style={{ gap: 'var(--space-2)' }}>
          {isStale ? (
            <span className="badge badge--warn">
              <TriangleAlert size={11} />
              <span>Evidence stale ({age})</span>
            </span>
          ) : isAvailable ? (
            <span className="badge badge--ok">
              <CheckCircle2 size={11} />
              <span>Fresh</span>
            </span>
          ) : (
            <span className="badge">Inactive feed</span>
          )}
          {isAvailable && <StatusBadge status={quality} size="sm" />}
        </div>
      </header>

      <div className="card__body row" style={{ gap: 'var(--space-3)', alignItems: 'center' }}>
        <div style={{ flex: 'none' }}>
          <Constellation modulation={modulation} />
        </div>

        <div className="telemetry-half" style={{ flex: '1 1 0', minWidth: 0 }}>
          <MetricCard
            label="Modulation"
            value={modulation}
            subtext="Classified scheme"
            icon={<Radio size={13} />}
          />

          <MetricCard
            label="AI confidence"
            value={confidence}
            unit="%"
            subtext={
              sig?.ai_confidence != null && sig.ai_confidence >= 0.85
                ? 'High certainty'
                : 'Marginal classification'
            }
            tone={
              sig?.ai_confidence != null
                ? sig.ai_confidence >= 0.85
                  ? 'ok'
                  : sig.ai_confidence < 0.7
                  ? 'warn'
                  : 'default'
                : 'default'
            }
            icon={<Sparkles size={13} />}
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
              sig?.estimated_snr_db != null
                ? sig.estimated_snr_db >= 10
                  ? 'ok'
                  : sig.estimated_snr_db < 0
                  ? 'crit'
                  : 'warn'
                : 'default'
            }
            icon={<Gauge size={13} />}
          />

          <MetricCard
            label="Signal age"
            value={age}
            subtext={isStale ? 'Exceeds freshness window' : 'Active valid window'}
            tone={isStale ? 'warn' : 'default'}
            icon={<Clock size={13} />}
          />
        </div>
      </div>

      <div className="card__footer row--between row">
        <span>Model: MLPClassifier (23 DSP features)</span>
        <span style={{ color: 'var(--text-4)' }}>Reference constellation (illustrative)</span>
      </div>
    </section>
  );
};

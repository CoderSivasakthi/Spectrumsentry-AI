import React, { useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { SignalSimulateResult } from '../../types/monitoring';
import { Sparkles, Zap } from 'lucide-react';
import { REFERENCE_POINTS } from './ConstellationPoints';

const MODULATIONS = [
  { value: 'BPSK', label: 'BPSK' },
  { value: 'QPSK', label: 'QPSK' },
  { value: '16-QAM', label: '16-QAM' },
];

/**
 * Synthesizes a modulated signal at the requested SNR and classifies it through
 * the real trained MLP + novelty detector on the backend — no hand-fed labels.
 */
export const SignalGeneratorCard: React.FC = () => {
  const { runSignalSimulation } = useMonitoring();

  const [modulation, setModulation] = useState('QPSK');
  const [snr, setSnr] = useState(12.0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<SignalSimulateResult | null>(null);
  const [runs, setRuns] = useState<SignalSimulateResult[]>([]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    try {
      const res = await runSignalSimulation({ modulation, snr_db: Number(snr) });
      if (res) {
        setResult(res);
        setRuns((prev) => [res, ...prev].slice(0, 5));
      }
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <section className="card">
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Signal generator &amp; AI classification</h3>
          <p className="card__sub">
            Synthesize a signal through the full DSP pipeline and let the trained classifier name it
          </p>
        </div>
      </header>

      <div className="card__body">
        <div className="lab-layout">
          <div style={{ flex: '1 1 0', minWidth: 0 }}>
            {/* Controls */}
            <form onSubmit={handleGenerate} className="lab-form">
              <div>
                <label className="field__label" htmlFor="gen-modulation">
                  Modulation to synthesize
                </label>
                <select
                  id="gen-modulation"
                  className="select"
                  value={modulation}
                  onChange={(e) => setModulation(e.target.value)}
                >
                  {MODULATIONS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="field__label" htmlFor="gen-snr">
                  Channel SNR: <span className="num">{Number(snr).toFixed(1)} dB</span>
                </label>
                <input
                  id="gen-snr"
                  type="range"
                  min={-15}
                  max={30}
                  step={0.5}
                  value={snr}
                  onChange={(e) => setSnr(parseFloat(e.target.value))}
                  className="lab-slider"
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button type="submit" className="btn btn--primary" disabled={isGenerating} style={{ width: '100%' }}>
                  {isGenerating ? <Sparkles size={13} style={{ animation: 'spin 0.8s linear infinite' }} /> : <Zap size={13} />}
                  <span>{isGenerating ? 'Classifying…' : 'Generate & classify'}</span>
                </button>
              </div>
            </form>

            {/* Result */}
            {result ? (
              <div className="card--inset lab-result" style={{ marginTop: 'var(--space-3)' }}>
                <div className="row--between row" style={{ alignItems: 'flex-start' }}>
                  <div>
                    <div className="eyebrow" style={{ fontSize: 'var(--text-2xs)' }}>Classifier verdict</div>
                    <div className="row" style={{ gap: 'var(--space-2)', marginTop: 4 }}>
                      <span
                        className="num"
                        style={{
                          fontSize: 'var(--text-xl)',
                          fontWeight: 700,
                          color: result.classification_matches ? 'var(--ok-fg)' : 'var(--warn-fg)',
                        }}
                      >
                        {result.predicted_modulation ?? '—'}
                      </span>
                      <span className={`badge badge--${result.classification_matches ? 'ok' : 'warn'}`}>
                        {result.classification_matches ? 'Match' : 'Mismatch'}
                      </span>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>Confidence</div>
                    <div className="num" style={{ fontSize: 'var(--text-md)', fontWeight: 650 }}>
                      {result.ai_confidence != null ? `${Math.round(result.ai_confidence * 100)}%` : '—'}
                    </div>
                  </div>
                </div>

                <div className="meter" style={{ marginTop: 'var(--space-2)' }}>
                  <div
                    className={`meter__fill meter__fill--${(result.ai_confidence ?? 0) >= 0.85 ? 'ok' : (result.ai_confidence ?? 0) < 0.7 ? 'warn' : ''}`}
                    style={{ width: `${Math.min(100, (result.ai_confidence ?? 0) * 100)}%` }}
                  />
                </div>

                <div className="lab-facts">
                  <div>
                    <span className="lab-fact-label">Requested</span>
                    <span className="num">{result.requested_modulation} @ {result.requested_snr_db.toFixed(1)} dB</span>
                  </div>
                  <div>
                    <span className="lab-fact-label">Measured SNR</span>
                    <span className="num">{result.measured_snr_db.toFixed(1)} dB</span>
                  </div>
                  <div>
                    <span className="lab-fact-label">Quality tier</span>
                    <span>{result.signal_quality ?? '—'}</span>
                  </div>
                  <div>
                    <span className="lab-fact-label">Novelty check</span>
                    <span>
                      {result.is_outlier
                        ? <span className="badge badge--warn">Outlier flagged</span>
                        : <span className="badge badge--ok">In-distribution</span>}
                      <span className="num" style={{ marginLeft: 6, color: 'var(--text-3)' }}>
                        {result.novelty_score != null ? `score ${result.novelty_score.toFixed(2)}` : ''}
                      </span>
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginTop: 'var(--space-3)' }}>
                  At very low SNR the signal leaves the model's training distribution — the novelty
                  detector reports it as an outlier even when the classifier is confident.
                </p>
              </div>
            ) : (
              <div className="pane-state" style={{ padding: 'var(--space-5) 0 0' }}>
                <div className="pane-state__title">No classification run yet</div>
                <div className="pane-state__hint">
                  Pick a modulation and SNR, then generate a noisy signal — the backend runs
                  feature extraction, the MLP classifier and the novelty detector for real.
                </div>
              </div>
            )}
          </div>

          <div style={{ flex: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
            <CompactConstellation modulation={result?.predicted_modulation ?? result?.requested_modulation} caption="Predicted reference constellation" />
          </div>
        </div>

        {/* Recent runs */}
        {runs.length > 1 && (
          <div className="table-wrap" style={{ marginTop: 'var(--space-4)', borderTop: '1px solid var(--border-faint)', paddingTop: 'var(--space-3)' }}>
            <div className="eyebrow" style={{ marginBottom: 6 }}>Recent runs</div>
            <table className="table">
              <thead>
                <tr>
                  <th>Sent</th>
                  <th>Predicted</th>
                  <th>Conf.</th>
                  <th>Outlier</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r, i) => (
                  <tr key={`${r.requested_modulation}-${i}`}>
                    <td>{r.requested_modulation} @ {r.requested_snr_db.toFixed(1)} dB</td>
                    <td className="cell-main">{r.predicted_modulation ?? '—'}</td>
                    <td className="num">{r.ai_confidence != null ? `${Math.round(r.ai_confidence * 100)}%` : '—'}</td>
                    <td>{r.is_outlier ? <span className="badge badge--warn">YES</span> : <span className="badge">NO</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card__footer">
        Pipeline: symbol generator → AWGN noise → 23 statistical/spectral features → MLPClassifier → novelty detector.
      </div>
    </section>
  );
};

const CompactConstellation: React.FC<{ modulation?: string | null; caption: string }> = ({ modulation, caption }) => {
  const points = REFERENCE_POINTS[modulation ?? ''];
  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox="0 0 120 120" width="128" height="128" style={{ display: 'block' }}>
        <line x1="14" y1="60" x2="106" y2="60" stroke="var(--border)" strokeWidth="1" />
        <line x1="60" y1="14" x2="60" y2="106" stroke="var(--border)" strokeWidth="1" />
        {points
          ? points.map(([i, q], idx) => (
              <circle
                key={idx}
                cx={50 + i * 46}
                cy={50 - q * 46}
                r="3.5"
                fill="var(--accent)"
                opacity="0.9"
              />
            ))
          : (
            <text x="60" y="63" textAnchor="middle" fontSize="9" fill="var(--text-4)">
              No prediction
            </text>
          )}
      </svg>
      <figcaption style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)', textAlign: 'center', marginTop: 4 }}>
        {caption}
      </figcaption>
    </figure>
  );
};

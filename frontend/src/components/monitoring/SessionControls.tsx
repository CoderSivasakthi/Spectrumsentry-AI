import React, { useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { Send, SlidersHorizontal } from 'lucide-react';

const PRESETS: Array<{
  label: string;
  detail: string;
  dot: string;
  mod: string;
  snr: number;
  conf: number;
}> = [
  { label: 'Clean QPSK', detail: '16.0 dB SNR · 98% conf', dot: 'dot--ok', mod: 'QPSK', snr: 16.0, conf: 0.98 },
  { label: '16-QAM @ 22 dB', detail: 'Conflict test', dot: 'dot--info', mod: '16-QAM', snr: 22.0, conf: 0.99 },
  { label: 'Degraded noise', detail: '−3.0 dB SNR · poor channel', dot: 'dot--warn', mod: 'BPSK', snr: -3.0, conf: 0.78 },
];

export const SessionControls: React.FC = () => {
  const { submitSignal } = useMonitoring();

  const [modulation, setModulation] = useState<string>('QPSK');
  const [snr, setSnr] = useState<number>(15.0);
  const [confidence, setConfidence] = useState<number>(0.98);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSendCustomSignal = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await submitSignal({
        predicted_modulation: modulation,
        estimated_snr_db: Number(snr),
        ai_confidence: Number(confidence),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const injectPreset = async (preset: (typeof PRESETS)[number]) => {
    setIsSubmitting(true);
    try {
      setModulation(preset.mod);
      setSnr(preset.snr);
      setConfidence(preset.conf);
      await submitSignal({
        predicted_modulation: preset.mod,
        estimated_snr_db: preset.snr,
        ai_confidence: preset.conf,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="card">
      <header className="card__header row">
        <SlidersHorizontal size={14} style={{ color: 'var(--text-3)', marginTop: 1 }} />
        <div>
          <h3 className="card__title">Direct evidence injection</h3>
          <p className="card__sub">
            Skip the pipeline: declare a label by hand and watch the decision engine re-evaluate
          </p>
        </div>
      </header>

      <div className="card__body">
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginBottom: 'var(--space-2)' }}>
          Scenario presets
        </div>
        <div className="telemetry-grid" style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() => injectPreset(p)}
              disabled={isSubmitting}
              className="card--inset"
              style={{ textAlign: 'left', cursor: 'pointer', transition: 'border-color 120ms ease-out' }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-faint)')}
            >
              <div className="row" style={{ gap: 6 }}>
                <span className={`dot ${p.dot}`} />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--text-1)' }}>
                  {p.label}
                </span>
              </div>
              <p className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)', marginTop: 3 }}>
                {p.detail}
              </p>
            </button>
          ))}
        </div>

        <form
          onSubmit={handleSendCustomSignal}
          style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--border-faint)' }}
        >
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginBottom: 'var(--space-2)' }}>
            Manual evidence
          </div>
          <div
            className="telemetry-grid"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))' }}
          >
            <div>
              <label className="field__label" htmlFor="mod-select">
                Modulation
              </label>
              <select
                id="mod-select"
                className="select"
                value={modulation}
                onChange={(e) => setModulation(e.target.value)}
              >
                <option value="BPSK">BPSK</option>
                <option value="QPSK">QPSK</option>
                <option value="16-QAM">16-QAM</option>
              </select>
            </div>

            <div>
              <label className="field__label" htmlFor="snr-input">
                SNR (dB)
              </label>
              <input
                id="snr-input"
                type="number"
                className="input"
                step="0.5"
                value={snr}
                onChange={(e) => setSnr(parseFloat(e.target.value) || 0)}
              />
            </div>

            <div>
              <label className="field__label" htmlFor="conf-input">
                Confidence (0–1)
              </label>
              <input
                id="conf-input"
                type="number"
                className="input"
                step="0.01"
                min="0"
                max="1"
                value={confidence}
                onChange={(e) => setConfidence(parseFloat(e.target.value) || 0)}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button type="submit" className="btn btn--secondary" style={{ width: '100%' }} disabled={isSubmitting}>
                <Send size={13} />
                <span>Inject evidence</span>
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="card__footer">
        The decision engine re-evaluates automatically after every injection.
      </div>
    </section>
  );
};

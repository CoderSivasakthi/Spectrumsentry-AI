import React from 'react';
import {
  Shield,
  Layers,
  Activity,
  Code,
} from 'lucide-react';

/* Pipeline descriptions grouped by engineering domain instead of
   build-phase numbering — the number added nothing for the reader. */
const PIPELINE: Array<{ title: string; body: string; tone?: 'ok' }> = [
  {
    title: 'Platform',
    body: 'FastAPI backend, React frontend, SQLite persistence, and WebSocket infrastructure.',
  },
  {
    title: 'Signal processing',
    body: 'Complex baseband I/Q synthesis (BPSK, QPSK, 16-QAM), AWGN channel, and 23-feature extraction.',
  },
  {
    title: 'Dataset generation',
    body: 'Balanced dataset (39,000 synthetic samples across 78 SNR conditions, 80/20 train/test split).',
  },
  {
    title: 'AI modulation classifier',
    body: 'StandardScaler + MLPClassifier pipeline delivering >97% test accuracy and low-latency inference.',
  },
  {
    title: 'Communication monitoring',
    body: 'Real-time packet loss tracking, RTT latency, jitter, throughput, timeout-based interruption, and recovery.',
  },
  {
    title: 'Decision engine',
    body: 'Deterministic explainable correlation engine evaluating cross-domain consistency and generating alerts.',
  },
  {
    title: 'Real-time integration',
    body: 'Unified evidence aggregation, signal freshness guard, and /ws/monitoring snapshot streaming.',
  },
  {
    title: 'Operator dashboard',
    body: 'Live multi-domain telemetry cards, real-time charts, event timeline, and session history.',
    tone: 'ok',
  },
];

const TECH_STACK: Array<{ name: string; role: string }> = [
  { name: 'Python 3.12', role: 'Backend runtime' },
  { name: 'FastAPI', role: 'REST & WebSockets' },
  { name: 'React 18 & TS', role: 'UI & dashboard' },
  { name: 'Custom CSS design system', role: 'Styling system' },
  { name: 'NumPy & SciPy', role: 'DSP computations' },
  { name: 'scikit-learn', role: 'MLP & scaler' },
  { name: 'SQLite', role: 'Local database' },
  { name: 'Pytest', role: '212 automated tests' },
];

export const SystemAbout: React.FC = () => {
  return (
    <div className="stack" style={{ maxWidth: 920 }}>
      {/* Title */}
      <div>
        <h2
          className="row"
          style={{ fontSize: 'var(--text-2xl)', fontWeight: 600, color: 'var(--text-1)', gap: 'var(--space-2)' }}
        >
          <Shield size={22} style={{ color: 'var(--accent)' }} />
          <span>SpectrumSentry AI system architecture</span>
        </h2>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-3)', marginTop: 'var(--space-1)' }}>
          AI-driven wireless communication monitoring, signal quality analysis, and deterministic decision correlation.
        </p>
      </div>

      {/* Overview */}
      <section className="card">
        <h3 className="card__title row" style={{ gap: 'var(--space-2)' }}>
          <Activity size={16} style={{ color: 'var(--accent)' }} />
          <span>Platform overview</span>
        </h3>
        <p className="card__body" style={{ marginTop: 0, fontSize: 'var(--text-sm)', color: 'var(--text-2)', lineHeight: 1.6 }}>
          SpectrumSentry AI combines physical-layer Digital Signal Processing (DSP) and Machine Learning modulation
          classification with application-layer network packet telemetry to evaluate communication link integrity in
          real time. The platform operates completely offline without external cloud dependencies.
        </p>
      </section>

      {/* Pipeline */}
      <section className="card">
        <h3 className="card__title row" style={{ gap: 'var(--space-2)' }}>
          <Layers size={16} style={{ color: 'var(--accent)' }} />
          <span>End-to-end pipeline</span>
        </h3>
        <div
          className="card__body"
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr',
            gap: 'var(--space-3)',
          }}
        >
          {PIPELINE.map((item) => (
            <div key={item.title} className="card--inset" style={item.tone === 'ok' ? borderOkStyle : undefined}>
              <span
                style={{
                  display: 'block',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  color: item.tone === 'ok' ? 'var(--ok-fg)' : 'var(--accent)',
                  marginBottom: 'var(--space-1)',
                }}
              >
                {item.title}
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', lineHeight: 1.55 }}>
                {item.body}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Technology stack */}
      <section className="card">
        <h3 className="card__title row" style={{ gap: 'var(--space-2)' }}>
          <Code size={16} style={{ color: 'var(--accent)' }} />
          <span>Core technologies</span>
        </h3>
        <div
          className="card__body"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 'var(--space-3)',
          }}
        >
          {TECH_STACK.map((t) => (
            <div key={t.name} className="metric">
              <span style={{ display: 'block', fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-1)' }}>
                {t.name}
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>{t.role}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Scope notice */}
      <section
        style={{
          padding: 'var(--space-4) var(--space-5)',
          border: '1px solid var(--accent-border)',
          background: 'var(--accent-bg)',
          borderRadius: 'var(--radius-lg)',
        }}
      >
        <div className="row" style={{ gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
          <Shield size={15} style={{ color: 'var(--accent)' }} />
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--accent)' }}>
            Operational boundary &amp; research notice
          </span>
        </div>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-2)', lineHeight: 1.6 }}>
          SpectrumSentry AI is designed exclusively for defensive research and educational demonstration.
          The communication monitoring subsystem functions via controlled application-level network telemetry
          (sequence-tracked ping-ack packets). It does not perform physical raw RF spectrum interception,
          packet sniffing, or active radio transmission without dedicated Software Defined Radio (SDR) hardware.
        </p>
      </section>
    </div>
  );
};

const borderOkStyle: React.CSSProperties = {
  borderColor: 'var(--ok-border)',
};

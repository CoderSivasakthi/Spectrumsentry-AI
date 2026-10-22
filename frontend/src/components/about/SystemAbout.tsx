import React from 'react';
import {
  Shield,
  Layers,
  Activity,
  Code,
} from 'lucide-react';

export const SystemAbout: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title */}
      <div className="text-center sm:text-left">
        <h2 className="text-2xl font-extrabold text-white tracking-tight flex items-center justify-center sm:justify-start gap-2.5">
          <Shield className="w-6 h-6 text-sky-400" />
          <span>SpectrumSentry AI System Architecture</span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          AI-driven wireless communication monitoring, signal quality analysis, and deterministic decision correlation.
        </p>
      </div>

      {/* Overview Card */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
          <Activity className="w-4 h-4 text-sky-400" />
          <span>Platform Overview</span>
        </h3>
        <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
          SpectrumSentry AI combines physical-layer Digital Signal Processing (DSP) and Machine Learning modulation classification
          with application-layer network packet telemetry to evaluate communication link integrity in real time.
          The platform operates completely offline without external cloud dependencies.
        </p>
      </div>

      {/* 8-Phase Engineering Pipeline */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
          <Layers className="w-4 h-4 text-sky-400" />
          <span>End-to-End Pipeline</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 1 • Foundation</span>
            <span className="text-slate-400">FastAPI backend, React frontend, SQLite persistence, and WebSocket infrastructure.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 2 • Signal Processing</span>
            <span className="text-slate-400">Complex baseband I/Q synthesis (BPSK, QPSK, 16-QAM), AWGN channel, and 23-feature extraction.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 3 • Dataset Generation</span>
            <span className="text-slate-400">Balanced dataset (39,000 synthetic samples across 78 SNR conditions, 80/20 train/test split).</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 4 • AI Modulation Classifier</span>
            <span className="text-slate-400">Production StandardScaler + MLPClassifier pipeline delivering &gt;97% test accuracy and low-latency inference.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 5 • Communication Monitoring</span>
            <span className="text-slate-400">Real-time packet loss tracking, RTT latency, jitter, throughput, timeout-based interruption, and recovery.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 6 • Decision Engine</span>
            <span className="text-slate-400">Deterministic explainable correlation engine evaluating cross-domain consistency and generating alerts.</span>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-sky-400 font-bold block mb-1">Phase 7 • Real-Time Integration</span>
            <span className="text-slate-400">Unified evidence aggregation, signal freshness guard, and `/ws/monitoring` snapshot streaming.</span>
          </div>

          <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
            <span className="text-emerald-400 font-bold block mb-1">Phase 8 • Professional Dashboard</span>
            <span className="text-slate-300">Live multi-domain telemetry cards, real-time charts, event timeline, and session history.</span>
          </div>
        </div>
      </div>

      {/* Technology Stack */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
          <Code className="w-4 h-4 text-sky-400" />
          <span>Core Technologies</span>
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono text-slate-300">
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">Python 3.12</span>
            <span className="text-slate-500 text-[11px]">Backend Runtime</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">FastAPI</span>
            <span className="text-slate-500 text-[11px]">REST & WebSockets</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">React 18 & TS</span>
            <span className="text-slate-500 text-[11px]">UI & Dashboard</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">Tailwind CSS</span>
            <span className="text-slate-500 text-[11px]">Styling System</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">NumPy & SciPy</span>
            <span className="text-slate-500 text-[11px]">DSP Computations</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">scikit-learn</span>
            <span className="text-slate-500 text-[11px]">MLP & Scaler</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">SQLite</span>
            <span className="text-slate-500 text-[11px]">Local Database</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
            <span className="text-white font-bold block">Pytest</span>
            <span className="text-slate-500 text-[11px]">139 Automated Tests</span>
          </div>
        </div>
      </div>

      {/* Defensive Research Scope & Hardware Boundary Disclaimer */}
      <div className="p-5 rounded-2xl border border-sky-500/30 bg-sky-950/20 text-slate-300 space-y-2">
        <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-wider text-sky-400">
          <Shield className="w-4 h-4 text-sky-400" />
          <span>Operational Boundary & Research Notice</span>
        </div>
        <p className="text-xs leading-relaxed text-slate-300">
          SpectrumSentry AI is designed exclusively for defensive research and educational demonstration.
          The communication monitoring subsystem functions via controlled application-level network telemetry
          (sequence-tracked ping-ack packets). It does not perform physical raw RF spectrum interception, packet sniffing,
          or active radio transmission without dedicated Software Defined Radio (SDR) hardware.
        </p>
      </div>
    </div>
  );
};

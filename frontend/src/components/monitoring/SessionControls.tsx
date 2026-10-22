import React, { useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import {
  Play,
  Square,
  Sliders,
  Send,
  Sparkles,
  AlertTriangle,
  ShieldAlert,
} from 'lucide-react';

export const SessionControls: React.FC = () => {
  const { snapshot, startSession, stopSession, submitSignal } = useMonitoring();
  const sessionId = snapshot?.monitoring_session_id;

  const [modulation, setModulation] = useState<string>('QPSK');
  const [snr, setSnr] = useState<number>(15.0);
  const [confidence, setConfidence] = useState<number>(0.98);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleStart = async () => {
    await startSession();
  };

  const handleStop = async () => {
    await stopSession('operator_stopped');
  };

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

  const injectPreset = async (presetMod: string, presetSnr: number, presetConf: number) => {
    setIsSubmitting(true);
    try {
      setModulation(presetMod);
      setSnr(presetSnr);
      setConfidence(presetConf);
      await submitSignal({
        predicted_modulation: presetMod,
        estimated_snr_db: presetSnr,
        ai_confidence: presetConf,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Monitoring Session & Signal Controls
            </h3>
            <p className="text-[11px] text-slate-400">
              Session Lifecycle & Cross-Domain Evidence Injection
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {sessionId ? (
            <button
              onClick={handleStop}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-rose-600 hover:bg-rose-500 text-white transition-colors"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Stop Session</span>
            </button>
          ) : (
            <button
              onClick={handleStart}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-sky-600 hover:bg-sky-500 text-white transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start Session</span>
            </button>
          )}
        </div>
      </div>

      {/* Preset Ingestion Scenarios */}
      <div className="mt-4">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">
          Interactive Scenario Presets:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <button
            onClick={() => injectPreset('QPSK', 16.0, 0.98)}
            disabled={isSubmitting}
            className="p-2.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 hover:bg-emerald-950/40 text-left transition-colors"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-300">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>Clean QPSK</span>
            </div>
            <p className="text-[10px] text-emerald-400/80 font-mono mt-0.5">
              16.0 dB SNR • 98% Conf
            </p>
          </button>

          <button
            onClick={() => injectPreset('16-QAM', 22.0, 0.99)}
            disabled={isSubmitting}
            className="p-2.5 rounded-xl border border-purple-500/30 bg-purple-950/20 hover:bg-purple-950/40 text-left transition-colors"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold text-purple-300">
              <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
              <span>High SNR 16-QAM</span>
            </div>
            <p className="text-[10px] text-purple-400/80 font-mono mt-0.5">
              22.0 dB SNR • Conflict Test
            </p>
          </button>

          <button
            onClick={() => injectPreset('BPSK', -3.0, 0.78)}
            disabled={isSubmitting}
            className="p-2.5 rounded-xl border border-amber-500/30 bg-amber-950/20 hover:bg-amber-950/40 text-left transition-colors"
          >
            <div className="flex items-center gap-1.5 text-xs font-bold text-amber-300">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
              <span>Degraded Noise</span>
            </div>
            <p className="text-[10px] text-amber-400/80 font-mono mt-0.5">
              -3.0 dB SNR • Poor Channel
            </p>
          </button>
        </div>
      </div>

      {/* Manual Signal Ingestion Form */}
      <form onSubmit={handleSendCustomSignal} className="mt-4 pt-3 border-t border-slate-800/80">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block mb-2">
          Manual Signal Evidence Submission:
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
          <div>
            <label className="text-[10px] text-slate-400 block font-mono mb-1">Modulation</label>
            <select
              value={modulation}
              onChange={(e) => setModulation(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
            >
              <option value="BPSK">BPSK</option>
              <option value="QPSK">QPSK</option>
              <option value="16-QAM">16-QAM</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-slate-400 block font-mono mb-1">SNR (dB)</label>
            <input
              type="number"
              step="0.5"
              value={snr}
              onChange={(e) => setSnr(parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>

          <div>
            <label className="text-[10px] text-slate-400 block font-mono mb-1">Confidence (0-1)</label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={confidence}
              onChange={(e) => setConfidence(parseFloat(e.target.value) || 0)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-slate-800 hover:bg-slate-700 text-sky-400 border border-sky-500/30 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Update Feed</span>
            </button>
          </div>
        </div>
      </form>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-slate-800/60 text-[11px] text-slate-500 flex items-center justify-between font-mono">
        <span>Endpoint: POST /api/monitoring/signal</span>
        <span>Re-evaluates Decision Engine automatically</span>
      </div>
    </div>
  );
};

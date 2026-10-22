import React, { ReactNode } from 'react';
import { Header } from './Header';
import { Shield } from 'lucide-react';

interface AppLayoutProps {
  children: ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-sky-500/30 selection:text-sky-200">
      {/* Background Ambience */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-sky-600/5 rounded-full blur-3xl" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-indigo-600/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-cyan-600/5 rounded-full blur-3xl" />
      </div>

      {/* Top Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 z-10 flex flex-col">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/90 text-slate-500 text-xs py-4 px-4 sm:px-6 lg:px-8 z-10">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-center sm:text-left">
          <div className="flex items-center gap-2 text-slate-400 font-medium">
            <Shield className="w-3.5 h-3.5 text-sky-400" />
            <span>SpectrumSentry AI</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-500 font-mono text-[11px]">v0.1.0 (Phase 8 Verified)</span>
          </div>

          <p className="text-[11px] text-slate-500">
            Defensive Communication Telemetry & AI Evidence Correlation • Non-Intrusive Network Monitoring
          </p>

          <div className="flex items-center gap-3 font-mono text-[11px] text-slate-500">
            <span>FastAPI Backend</span>
            <span className="text-slate-700">|</span>
            <span>React Dashboard</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

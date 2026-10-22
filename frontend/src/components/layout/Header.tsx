import React, { useState, useEffect } from 'react';
import {
  Radio,
  Activity,
  History,
  Info,
  Wifi,
  WifiOff,
  Server,
} from 'lucide-react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';

export const Header: React.FC = () => {
  const {
    connectionStatus,
    isBackendHealthy,
    activeTab,
    setActiveTab,
  } = useMonitoring();

  const [currentTime, setCurrentTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toUTCString().replace('GMT', 'UTC'));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Brand Logo & Name */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <Radio className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-base font-extrabold tracking-tight text-white">
                  SpectrumSentry
                </span>
                <span className="text-xs font-black px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-mono">
                  AI
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium tracking-wider uppercase hidden sm:block">
                Real-Time Communication Monitoring
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-slate-900/80 border border-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'dashboard'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'history'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>History</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'about'
                  ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <Info className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">System</span>
            </button>
          </nav>

          {/* Connection Indicators & UTC Clock */}
          <div className="flex items-center gap-3 shrink-0">
            {/* Backend Indicator */}
            <div
              className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border ${
                isBackendHealthy
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/20'
                  : 'bg-rose-950/40 text-rose-300 border-rose-500/20'
              }`}
              title={isBackendHealthy ? 'Backend REST API online' : 'Backend REST API unreachable'}
            >
              <Server className="w-3 h-3" />
              <span>API {isBackendHealthy ? 'ONLINE' : 'OFFLINE'}</span>
            </div>

            {/* WebSocket Indicator */}
            <div className="flex items-center gap-1.5">
              <StatusBadge
                status={connectionStatus}
                size="sm"
                className="hidden sm:inline-flex"
              />
              <div
                className={`p-1.5 rounded-md border sm:hidden ${
                  connectionStatus === 'CONNECTED'
                    ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                    : 'bg-amber-950/40 text-amber-400 border-amber-500/30'
                }`}
                title={`WebSocket: ${connectionStatus}`}
              >
                {connectionStatus === 'CONNECTED' ? (
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <WifiOff className="w-3.5 h-3.5 text-amber-400" />
                )}
              </div>
            </div>

            {/* UTC Clock */}
            <div className="hidden lg:block text-right font-mono text-[11px] text-slate-400 border-l border-slate-800 pl-3">
              <div>{currentTime || 'Synchronizing...'}</div>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
};

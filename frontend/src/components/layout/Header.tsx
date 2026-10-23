import React, { useState, useEffect } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { StatusBadge } from '../common/StatusBadge';

const VIEW_TITLES: Record<string, string> = {
  live: 'Live monitor',
  link: 'Link test',
  signal: 'AI signal lab',
  sessions: 'Sessions',
  system: 'System',
};

/** UTC clock owned by its own component so the 1 Hz tick never re-renders the header. */
const Clock: React.FC = () => {
  const [time, setTime] = useState<string>('');
  useEffect(() => {
    const update = () =>
      setTime(new Date().toUTCString().replace('GMT', 'UTC'));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span
      className="num hidden-sm"
      style={{ color: 'var(--text-3)', fontSize: 'var(--text-xs)' }}
    >
      {time || 'Synchronizing...'}
    </span>
  );
};

/** Thin top bar of the ops console: current view name + connection indicators. */
export const Header: React.FC = () => {
  const { connectionStatus, isBackendHealthy, activeTab } = useMonitoring();

  return (
    <header
      className="topbar"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 40,
        background: 'rgba(255, 255, 255, 0.85)',
        backdropFilter: 'blur(8px)',
        borderBottom: '1px solid var(--border)',
        height: 54,
        display: 'flex',
        alignItems: 'stretch',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 'var(--space-4)',
          width: '100%',
          paddingInline: 'var(--space-4)',
        }}
      >
        <h1 style={{ fontSize: 'var(--text-md)', fontWeight: 650, color: 'var(--text-1)', letterSpacing: '-0.01em', margin: 0 }}>
          {VIEW_TITLES[activeTab] || 'Live monitor'}
        </h1>

        <div className="row" style={{ flex: 'none', gap: 'var(--space-3)' }}>
          <span className="row hidden-sm" style={{ gap: 6, fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
            <span
              className={`dot dot--${isBackendHealthy ? 'ok' : 'crit'}`}
              title={isBackendHealthy ? 'Backend REST API online' : 'Backend REST API unreachable'}
            />
            <span>API {isBackendHealthy ? 'online' : 'offline'}</span>
          </span>
          <StatusBadge status={connectionStatus} size="sm" />
          <Clock />
        </div>
      </div>
    </header>
  );
};

export default Header;

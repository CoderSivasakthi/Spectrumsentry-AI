import React from 'react';
import { Activity, ArrowDownUp, BrainCircuit, Info, History, Network } from 'lucide-react';
import { useMonitoring, NavigationTab } from '../../context/MonitoringContext';
import { Play, Square } from 'lucide-react';

const NAV: Array<{ id: NavigationTab; label: string; hint: string; Icon: React.ElementType }> = [
  { id: 'live', label: 'Live monitor', hint: 'Real-time overview', Icon: Activity },
  { id: 'link', label: 'Link test', hint: 'Packet transmitter', Icon: ArrowDownUp },
  { id: 'devices', label: 'Devices', hint: 'Connected devices & links', Icon: Network },
  { id: 'signal', label: 'AI signal lab', hint: 'Generate & classify', Icon: BrainCircuit },
  { id: 'sessions', label: 'Sessions', hint: 'Completed history', Icon: History },
  { id: 'system', label: 'System', hint: 'About & pipeline', Icon: Info },
];

export const Sidebar: React.FC = () => {
  const { activeTab, setActiveTab, snapshot, deviceRoster, startSession, stopSession } = useMonitoring();
  const sessionId = snapshot?.monitoring_session_id;
  const commSessionId = snapshot?.communication_session_id;

  const handleSessionToggle = async () => {
    if (sessionId) {
      await stopSession('user_stopped');
    } else {
      await startSession();
    }
  };

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar__brand">
        <span className="sidebar__logo">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
            <path d="M3 17c2-6 4-9 9-9s7 3 9 9" />
            <path d="M3 21c2-4 4-6 9-6s7 2 9 6" opacity="0.55" />
            <circle cx="12" cy="3.5" r="1.6" fill="currentColor" stroke="none" />
          </svg>
        </span>
        <div>
          <div className="sidebar__title">SpectrumSentry</div>
          <div className="sidebar__tagline">Wireless link monitoring</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar__nav" aria-label="Primary">
        {NAV.map(({ id, label, hint, Icon }) => (
          <button
            key={id}
            className={`sidebar__item${activeTab === id ? ' is-active' : ''}`}
            onClick={() => setActiveTab(id)}
            title={hint}
          >
            <Icon size={15} strokeWidth={2} />
            <span className="sidebar__item-text">{label}</span>
          </button>
        ))}
      </nav>

      {/* Session control — per device: sessions are isolated for every connected device */}
      <div className="sidebar__section">
        <div className="sidebar__section-label">This device's session</div>
        <button
          className={`btn ${sessionId ? 'btn--danger' : 'btn--primary'} sidebar__session-btn`}
          onClick={handleSessionToggle}
        >
          {sessionId ? <Square size={13} /> : <Play size={13} />}
          <span>{sessionId ? 'Stop this device’s session' : 'Restart monitoring'}</span>
        </button>
        <div className="sidebar__session-meta">
          {sessionId ? (
            <>
              <div className="row" style={{ gap: 6 }}>
                <span className="dot dot--ok dot--live" />
                <span className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-2)' }}>
                  {sessionId}
                </span>
              </div>
              {commSessionId && (
                <div className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
                  link test {commSessionId}
                </div>
              )}
              {typeof deviceRoster?.total === 'number' && (
                <div className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
                  {deviceRoster.total} device{deviceRoster.total === 1 ? '' : 's'} connected
                </div>
              )}
            </>
          ) : (
            <div style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>Standby — reconnecting starts it again</div>
          )}
        </div>
      </div>

      <div className="spacer" />

      {/* Footer status */}
      <div className="sidebar__foot">
        <span className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
          SpectrumSentry AI · v0.2.0
        </span>
      </div>
    </aside>
  );
};

export default Sidebar;

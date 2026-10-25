import React, { useEffect, useState } from 'react';
import { Play, Square } from 'lucide-react';
import { useMonitoring } from '../../context/MonitoringContext';
import { LINK_PROFILES } from '../../hooks/useLinkTestStream';

/**
 * Packet transmitter controls for the link test: streams numbered test packets
 * to the backend so latency/loss/jitter metrics accumulate in real time. The
 * stream itself lives in MonitoringContext so it keeps running when the user
 * navigates to another view.
 */
export const LinkTestCard: React.FC = () => {
  const { snapshot, linkTest: stream, ensureDeviceSession } = useMonitoring();
  const commSessionId = snapshot?.communication_session_id ?? null;
  const [notice, setNotice] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  // A newly created session invalidates a stream aimed at the old session
  useEffect(() => {
    if (stream.running && commSessionId === null) {
      stream.stop({ silent: true });
      setNotice('Session ended — transmitter stopped.');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commSessionId]);

  const handleStart = async () => {
    if (stream.running) return;
    setStarting(true);
    // The device's session auto-starts on WS connect, but on reload the
    // frontend's first REST status can land before that and resolve to no
    // session (or, before the backend fix, to another device's session).
    // Ensure this device owns its own session before streaming packets into it,
    // so the transmitter never targets a foreign (or null) session.
    let sid = commSessionId;
    if (!sid) {
      sid = await ensureDeviceSession();
    }
    setStarting(false);
    if (!sid) {
      setNotice('No active session for this device — the backend may still be starting up.');
      return;
    }
    setNotice(null);
    stream.start(sid);
  };

  const handleStop = () => {
    stream.stop();
    setNotice('Transmitter stopped; after 2 s of silence the link is flagged as interrupted.');
  };

  const busy = stream.stats.sent > 0 ? `Seq ${stream.stats.sent} streamed` : 'Idle';

  return (
    <section className="card">
      <header className="card__header row--between row">
        <div>
          <h3 className="card__title">Packet transmitter</h3>
          <p className="card__sub">
            {commSessionId
              ? `Streaming to link test ${commSessionId} · measures real HTTP RTT per packet`
              : 'Start a monitoring session to enable the transmitter'}
          </p>
        </div>
        <StatusSummary busy={busy} />
      </header>

      <div className="card__body">
        {/* Network profiles */}
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginBottom: 'var(--space-2)' }}>
          Network profile
        </div>
        <div className="segment segment--wrap">
          {LINK_PROFILES.map((p) => (
            <button
              key={p.key}
              className={`segment__item${stream.profileKey === p.key ? ' is-active' : ''}`}
              onClick={() => stream.setProfile(p.key)}
            >
              <span>{p.label}</span>
            </button>
          ))}
        </div>
        <p className="card__sub" style={{ marginTop: 'var(--space-1)' }}>
          {LINK_PROFILES.find((p) => p.key === stream.profileKey)?.detail}
        </p>

        {/* Stream controls */}
        <div className="row" style={{ gap: 'var(--space-2)', marginTop: 'var(--space-3)' }}>
          {stream.running ? (
            <button className="btn btn--danger" onClick={handleStop}>
              <Square size={13} />
              <span>Stop stream</span>
            </button>
          ) : (
            <button className="btn btn--primary" onClick={handleStart} disabled={starting}>
              <Play size={13} />
              <span>Start stream</span>
            </button>
          )}
          <span className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
            {starting ? 'Acquiring device session…' : stream.running ? 'Streaming…' : busy}
          </span>
        </div>

        {notice && (
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)', marginTop: 'var(--space-2)' }}>
            {notice}
          </p>
        )}

        {/* Live counters */}
        <div className="telemetry-grid" style={{ marginTop: 'var(--space-3)' }}>
          <StreamStat label="Sequences created" value={String(stream.stats.sent)} />
          <StreamStat label="ACKed" value={String(stream.stats.acked)} />
          <StreamStat label="HTTP failures" value={String(stream.stats.failed)} />
          <StreamStat
            label="Measured RTT"
            value={stream.stats.lastRttMs != null ? `${stream.stats.lastRttMs.toFixed(1)}` : '—'}
            unit={stream.stats.lastRttMs != null ? 'ms' : undefined}
          />
        </div>
      </div>

      <div className="card__footer">
        Each packet carries the previous packet's measured round-trip time; dropped sequences
        count as circuit loss and silent gaps exceed 2 s trigger interruption/recovery detection.
      </div>
    </section>
  );
};

const StatusSummary: React.FC<{ busy: string }> = ({ busy }) => (
  <span className="num" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-3)' }}>
    {busy}
  </span>
);

const StreamStat: React.FC<{ label: string; value: string; unit?: string }> = ({ label, value, unit }) => (
  <div className="metric">
    <div className="metric__label">{label}</div>
    <div className="metric__value" style={{ fontSize: 18, lineHeight: '22px' }}>
      {value}
      {unit && <span className="metric__unit">{unit}</span>}
    </div>
  </div>
);

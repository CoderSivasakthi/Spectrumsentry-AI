import React, { useEffect, useMemo, useState } from 'react';
import { useMonitoring } from '../context/MonitoringContext';
import { getDevices } from '../api/monitoring';
import { DeviceStatus } from '../types/monitoring';
import { StatusBadge } from '../components/common/StatusBadge';
import { RefreshCw, Monitor, Server } from 'lucide-react';
import { setDeviceName } from '../lib/deviceIdentity';

const REFRESH_MS = 2000;

interface TopologyDevice extends DeviceStatus {
  isSelf: boolean;
}

/** Hub-and-spoke diagram: each connected device on the left, the backend
 *  server hub on the right, one line per device colored by link health. */
const DeviceTopology: React.FC<{
  devices: TopologyDevice[];
  linkColor: (d: DeviceStatus) => string;
}> = ({ devices, linkColor }) => {
  const visible = devices.filter((d) => d.connection_state !== 'disconnected');
  if (visible.length === 0) {
    return (
      <div className="pane-state">
        <div className="pane-state__icon">
          <Server size={18} />
        </div>
        <div className="pane-state__title">No live device links</div>
        <div className="pane-state__hint">Links appear while device sessions are running.</div>
      </div>
    );
  }

  const DEVICE_Y0 = 34;
  const DEVICE_DY = 78;
  const HUB_X = 620;
  const VIEW_W = 840;
  const VIEW_H = DEVICE_Y0 + visible.length * DEVICE_DY;

  return (
    <svg
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      width="100%"
      height={VIEW_H}
      role="img"
      aria-label="Device to server topology"
    >
      <defs>
        <style>{`
          .topo-name { fill: var(--text-1); font-size: 12px; font-weight: 600; }
          .topo-sub { fill: var(--text-4); font-size: 10px; }
          .topo-line { fill: none; stroke-linecap: round; stroke-width: 2; }
        `}</style>
      </defs>

      {/* server hub node, vertically centered on the links it feeds */}
      <g transform={`translate(${HUB_X}, ${VIEW_H / 2 - 26})`}>
        <rect width="170" height="52" rx="10" fill="var(--surface-3)" stroke="var(--accent)" />
        <circle cx="22" cy="26" r="7" fill="var(--accent)" opacity="0.9" />
        <text x="40" y="23" className="topo-name">
          Backend server
        </text>
        <text x="40" y="38" className="topo-sub">
          packet ingest · decision engine
        </text>
      </g>

      {visible.map((d, i) => {
        const cy = DEVICE_Y0 + i * DEVICE_DY;
        const color = linkColor(d);
        return (
          <g key={d.device_id}>
            {/* link line: device node → server hub */}
            <path
              className="topo-line"
              stroke={color}
              opacity="0.8"
              d={`M 200 ${cy} C 380 ${cy}, 420 ${VIEW_H / 2}, ${HUB_X - 8} ${VIEW_H / 2}`}
            />
            {/* device stats under the name — same numbers as the detail cards */}
            <g transform={`translate(28, ${cy})`}>
              <circle cx="-18" cy="-4" r="4.5" fill={color}>
                {d.connection_state === 'connected' && (
                  <animate attributeName="opacity" values="1;0.45;1" dur="2.4s" repeatCount="indefinite" />
                )}
              </circle>
              <text x="0" y="0" className="topo-name">
                {d.device_name || d.device_id}
                {d.isSelf ? ' (this console)' : ''}
              </text>
              <text x="0" y="14" className="topo-sub">
                {d.ip || 'IP unknown'} · health {d.health_score != null ? Math.round(d.health_score) : '—'} · loss{' '}
                {d.packet_loss_percent != null ? `${d.packet_loss_percent.toFixed(1)}%` : '—'} · rtt{' '}
                {d.avg_latency_ms != null ? `${d.avg_latency_ms.toFixed(0)} ms` : '—'}
              </text>
            </g>
          </g>
        );
      })}
    </svg>
  );
};

/** Devices & network view: who is connected, and what each device's link into the
 *  backend is doing right now. All numbers are measured link stats; the topology
 *  graphic is a presentational hub-and-spoke of the same data (packets from every
 *  device flow through the backend server, so links are device → server). */
export const Devices: React.FC = () => {
  const { deviceId, deviceName, refreshDevices } = useMonitoring();
  const [roster, setRoster] = useState<{ total: number; devices: DeviceStatus[] } | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nameDraft, setNameDraft] = useState(deviceName);

  const fetchRoster = async (showSpinner = false) => {
    if (showSpinner) setIsLoading(true);
    try {
      const data = await getDevices();
      setRoster(data);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch devices.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshDevices();
    fetchRoster(true);
    const id = setInterval(() => fetchRoster(false), REFRESH_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setNameDraft(deviceName);
  }, [deviceName]);

  const devices = roster?.devices ?? [];
  const connectedCount = devices.filter((d) => d.connection_state === 'connected').length;

  const topologyDevices = useMemo(
    () => devices.map((d) => ({ ...d, isSelf: d.device_id === deviceId })),
    [devices, deviceId]
  );

  const linkColor = (d: DeviceStatus): string => {
    if (d.connection_state !== 'connected') return 'var(--text-4)';
    const status = (d.status || '').toUpperCase();
    if (status === 'INTERRUPTED') return 'var(--crit)';
    if (status === 'DEGRADED' || status === 'RECONNECTING' || status === 'CONNECTING') return 'var(--warn)';
    if (status === 'CONNECTED') return 'var(--ok)';
    if ((d.packets_received ?? 0) === 0) return 'var(--warn)';
    return 'var(--ok)';
  };

  const commitName = () => {
    const trimmed = nameDraft.trim();
    if (!trimmed || trimmed === deviceName) {
      setNameDraft(deviceName);
      return;
    }
    setDeviceName(trimmed);
    setNameDraft(trimmed);
    fetchRoster(false);
  };

  return (
    <div className="stack">
      {/* Summary header */}
      <div className="card card--hero k-info">
        <div className="card__header">
          <div>
            <div className="card__title">Connected devices</div>
            <div className="card__sub">
              {roster
                ? `${roster.total} device${roster.total === 1 ? '' : 's'} registered — ${connectedCount} currently connected. Packets from every device flow into the backend server; stats below are measured per device.`
                : 'Reading device roster...'}
            </div>
          </div>
          <button
            className="btn btn--ghost btn--sm"
            onClick={async () => {
              refreshDevices();
              await fetchRoster(true);
            }}
            disabled={isLoading}
          >
            <RefreshCw size={13} className={isLoading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
        <div className="tri-grid" style={{ marginTop: 'var(--space-3)' }}>
          <div className="metric">
            <div className="metric__label">Registered devices</div>
            <div className="metric__value">{roster ? roster.total : '—'}</div>
            <div className="metric__hint">This console: {deviceId}</div>
          </div>
          <div className="metric">
            <div className="metric__label">Connected now</div>
            <div className="metric__value">{roster ? connectedCount : '—'}</div>
            <div className="metric__hint">Live WebSocket connections</div>
          </div>
          <div className="metric">
            <div className="metric__label">This device's name</div>
            <input
              className="input"
              style={{ marginTop: 6 }}
              value={nameDraft}
              onChange={(e) => setNameDraft(e.target.value)}
              onBlur={commitName}
              onKeyDown={(e) => {
                if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
              }}
              aria-label="Device name"
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button className="btn btn--sm btn--ghost" onClick={() => fetchRoster(true)}>
            Retry
          </button>
        </div>
      )}

      {/* Topology: device nodes feeding the backend server hub */}
      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Network topology</div>
            <div className="card__sub">Device → server links, colored by measured link health</div>
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <DeviceTopology devices={topologyDevices} linkColor={linkColor} />
        </div>
      </div>

      {/* Per-device cards */}
      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Device details</div>
            <div className="card__sub">Identity, live link stats, and each device's own session ids</div>
          </div>
          <Monitor size={16} color="var(--text-3)" />
        </div>
        {devices.length === 0 && !isLoading && (
          <div className="pane-state">
            <div className="pane-state__icon">
              <Server size={18} />
            </div>
            <div className="pane-state__title">No devices registered</div>
            <div className="pane-state__hint">
              Devices appear here once a dashboard or sender page connects.
            </div>
          </div>
        )}
        <div
          className="grid-2"
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 'var(--space-3)' }}
        >
          {devices.map((d) => {
            const isSelf = d.device_id === deviceId;
            return (
              <div
                key={d.device_id}
                className="card card--inset"
                style={isSelf ? { outline: '1px solid var(--accent)' } : undefined}
              >
                <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontSize: 'var(--text-md)', fontWeight: 650, color: 'var(--text-1)' }}>
                      {d.device_name || d.device_id}
                    </div>
                    <div className="num" style={{ fontSize: 'var(--text-2xs)', color: 'var(--text-3)' }}>
                      {d.device_id}
                      {isSelf ? ' · this console' : ''} · {d.ip || 'IP unknown'}
                    </div>
                  </div>
                  <StatusBadge status={d.connection_state === 'connected' ? d.status || 'CONNECTING' : 'DISCONNECTED'} size="sm" />
                </div>

                <div className="row" style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', gap: 'var(--space-3)', color: 'var(--text-3)' }}>
                  <span><span className="dot dot--ok" /> Session {d.monitoring_session_id || '—'}</span>
                </div>
                <div className="row" style={{ marginTop: 2, fontSize: 'var(--text-xs)', gap: 'var(--space-3)', color: 'var(--text-3)' }}>
                  <span><span className="dot dot--info" /> Link test {d.communication_session_id || '—'}</span>
                </div>

                <div className="meter" style={{ marginTop: 'var(--space-3)' }}>
                  <div
                    className={`meter__fill meter__fill--${(d.health_score ?? 100) >= 80 ? 'ok' : (d.health_score ?? 100) >= 50 ? 'warn' : 'crit'}`}
                    style={{ width: `${d.health_score ?? 0}%` }}
                  />
                </div>

                <div
                  style={{
                    marginTop: 'var(--space-3)',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))',
                    gap: 'var(--space-2)',
                  }}
                >
                  <div className="metric">
                    <div className="metric__label">Loss</div>
                    <div className="metric__value" style={{ fontSize: 16 }}>
                      {d.packet_loss_percent != null ? d.packet_loss_percent.toFixed(1) : '—'}
                      <span className="metric__unit">%</span>
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric__label">Latency</div>
                    <div className="metric__value" style={{ fontSize: 16 }}>
                      {d.avg_latency_ms != null ? d.avg_latency_ms.toFixed(0) : '—'}
                      <span className="metric__unit">ms</span>
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric__label">Jitter</div>
                    <div className="metric__value" style={{ fontSize: 16 }}>
                      {d.jitter_ms != null ? d.jitter_ms.toFixed(1) : '—'}
                      <span className="metric__unit">ms</span>
                    </div>
                  </div>
                  <div className="metric">
                    <div className="metric__label">Packets</div>
                    <div className="metric__value" style={{ fontSize: 16 }}>
                      {d.packets_received ?? '—'}
                      <span className="metric__unit">/ {d.packets_sent ?? '—'}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default Devices;

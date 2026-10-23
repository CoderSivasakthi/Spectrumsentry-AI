import React, { useState, useEffect, useRef } from 'react';
import { getMonitoringHistory, getMonitoringSessionReport } from '../../api/monitoring';
import { MonitoringSessionSummary } from '../../types/monitoring';
import { StatusBadge } from '../common/StatusBadge';
import { LoadingState, EmptyState } from '../common/States';
import {
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
  X,
  Download,
} from 'lucide-react';

export interface HistoryTableProps {
  initialSessions?: MonitoringSessionSummary[];
  initialTotal?: number;
  autoFetch?: boolean;
}

export const HistoryTable: React.FC<HistoryTableProps> = ({
  initialSessions,
  initialTotal,
  autoFetch = true,
}) => {
  const [sessions, setSessions] = useState<MonitoringSessionSummary[]>(initialSessions || []);
  const [total, setTotal] = useState<number>(initialTotal ?? (initialSessions ? initialSessions.length : 0));
  const [skip, setSkip] = useState<number>(0);
  const [limit] = useState<number>(10);
  const [isLoading, setIsLoading] = useState<boolean>(autoFetch && !initialSessions);
  const [error, setError] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<MonitoringSessionSummary | null>(null);
  const [isDownloading, setIsDownloading] = useState<boolean>(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const escapeCsv = (value: unknown): string => {
    const text = value === null || value === undefined ? '' : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  };

  // Flatten nested report into a two-column CSV: a dotted-path key and its scalar value.
  const flattenObject = (obj: unknown, prefix = ''): Array<[string, string]> => {
    const rows: Array<[string, string]> = [];
    if (obj === null || obj === undefined) {
      rows.push([prefix || 'root', '']);
    } else if (Array.isArray(obj)) {
      if (obj.length === 0) {
        rows.push([`${prefix} (count)`, '0']);
      } else {
        obj.forEach((item, i) => rows.push(...flattenObject(item, `${prefix}.${i}`)));
      }
    } else if (typeof obj === 'object') {
      for (const [k, v] of Object.entries(obj)) {
        const p = prefix ? `${prefix}.${k}` : k;
        rows.push(...flattenObject(v, p));
      }
    } else {
      rows.push([prefix, String(obj)]);
    }
    return rows;
  };

  const handleDownloadReport = async (
    session: MonitoringSessionSummary,
    format: 'json' | 'csv' = 'json'
  ) => {
    const isCsv = format === 'csv';
    if (isCsv) {
      setIsDownloading(true);
    } else {
      setIsDownloading(true);
    }
    try {
      const report = await getMonitoringSessionReport(session.monitoring_session_id);
      const blob = isCsv
        ? (() => {
            const rows = flattenObject(report);
            const csv = ['path,value', ...rows.map(([p, v]) => `${escapeCsv(p)},${escapeCsv(v)}`)].join(
              '\n'
            );
            return new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
          })()
        : new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${session.monitoring_session_id}_report.${isCsv ? 'csv' : 'json'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to download session report.');
    } finally {
      setIsDownloading(false);
    }
  };

  const fetchHistory = async (offset = skip) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getMonitoringHistory(offset, limit);
      setSessions(data.items);
      setTotal(data.total);
      setSkip(offset);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch monitoring history.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (autoFetch) {
      fetchHistory(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoFetch]);

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(skip / limit) + 1;

  const calculateDuration = (startStr?: string | null, endStr?: string | null) => {
    if (!startStr) return '—';
    const start = new Date(startStr).getTime();
    const end = endStr ? new Date(endStr).getTime() : Date.now();
    const diffSec = Math.max(0, Math.floor((end - start) / 1000));
    const mins = Math.floor(diffSec / 60);
    const secs = diffSec % 60;
    return `${mins}m ${secs}s`;
  };

  /* Modal: Escape + backdrop click close; focus moves in on open. */
  useEffect(() => {
    if (!selectedSession) return;
    closeButtonRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSelectedSession(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selectedSession]);

  const em = <>&nbsp;—&nbsp;</>;

  return (
    <div className="stack">
      {/* Page head */}
      <div className="row--between row" style={{ flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--text-1)' }}>
            Session history
          </h2>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-3)', marginTop: 2 }}>
            Completed monitoring sessions persisted by the backend.
          </p>
        </div>
        <button
          className="btn btn--secondary btn--sm"
          onClick={() => fetchHistory(skip)}
          disabled={isLoading}
        >
          <RefreshCw size={13} style={isLoading ? { animation: 'spin 0.8s linear infinite' } : undefined} />
          <span>Refresh</span>
        </button>
      </div>

      <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {isLoading && sessions.length === 0 ? (
          <LoadingState message="Loading historical sessions..." subtext="Querying database records" />
        ) : error ? (
          <div className="pane-state" style={{ color: 'var(--crit-fg)', fontSize: 'var(--text-sm)' }}>{error}</div>
        ) : sessions.length === 0 ? (
          <EmptyState
            title="No Monitoring Sessions Found"
            message="Start and stop a monitoring session from the dashboard to create historical records."
          />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Linked channel</th>
                  <th>Started (UTC)</th>
                  <th>Ended (UTC)</th>
                  <th>Duration</th>
                  <th>Final status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((sess) => (
                  <tr key={sess.monitoring_session_id}>
                    <td className="cell-main num" style={{ color: 'var(--accent)' }}>
                      {sess.monitoring_session_id}
                    </td>
                    <td>{sess.communication_session_id || em}</td>
                    <td>
                      {sess.started_at ? new Date(sess.started_at).toLocaleString() : em}
                    </td>
                    <td>
                      {sess.ended_at ? new Date(sess.ended_at).toLocaleString() : 'In progress'}
                    </td>
                    <td className="num">{calculateDuration(sess.started_at, sess.ended_at)}</td>
                    <td>
                      <StatusBadge status={sess.status} size="sm" />
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div className="row" style={{ justifyContent: 'flex-end', gap: 'var(--space-1)' }}>
                        <button
                          onClick={() => handleDownloadReport(sess, 'json')}
                          className="btn btn--ghost btn--sm"
                          disabled={isDownloading}
                          aria-label={`Download JSON report for ${sess.monitoring_session_id}`}
                        >
                          <Download size={13} />
                          <span>JSON</span>
                        </button>
                        <button
                          onClick={() => handleDownloadReport(sess, 'csv')}
                          className="btn btn--ghost btn--sm"
                          disabled={isDownloading}
                          aria-label={`Download CSV report for ${sess.monitoring_session_id}`}
                        >
                          <Download size={13} />
                          <span>CSV</span>
                        </button>
                        <button
                          onClick={() => setSelectedSession(sess)}
                          className="btn btn--ghost btn--sm"
                        >
                          <Eye size={13} />
                          <span>Inspect</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > 0 && (
          <div
            className="row--between row"
            style={{
              padding: '10px 16px',
              borderTop: '1px solid var(--border-faint)',
              fontSize: 'var(--text-sm)',
              color: 'var(--text-3)',
            }}
          >
            <div className="num">
              Showing {skip + 1}–{Math.min(skip + limit, total)} of {total} sessions
            </div>
            <div className="row" style={{ gap: 'var(--space-2)' }}>
              <button
                className="btn btn--ghost"
                aria-label="Previous page"
                onClick={() => fetchHistory(Math.max(0, skip - limit))}
                disabled={skip === 0 || isLoading}
              >
                <ChevronLeft size={15} />
              </button>
              <span className="num" style={{ fontSize: 'var(--text-xs)' }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn btn--ghost"
                aria-label="Next page"
                onClick={() => fetchHistory(skip + limit)}
                disabled={skip + limit >= total || isLoading}
              >
                <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Inspect modal */}
      {selectedSession && (
        <div className="modal-backdrop" onClick={() => setSelectedSession(null)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={`Session ${selectedSession.monitoring_session_id}`}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              className="row--between row"
              style={{ paddingBottom: 'var(--space-3)', borderBottom: '1px solid var(--border-faint)' }}
            >
              <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-1)' }}>
                Session {selectedSession.monitoring_session_id}
              </h3>
              <button
                ref={closeButtonRef}
                className="btn btn--ghost"
                onClick={() => setSelectedSession(null)}
                aria-label="Close"
              >
                <X size={16} />
              </button>
            </div>

            <div className="card--inset" style={{ marginTop: 'var(--space-4)' }}>
              <div className="telemetry-grid" style={{ gap: 'var(--space-4)' }}>
                <div>
                  <span className="field__label">Status</span>
                  <StatusBadge status={selectedSession.status} size="sm" />
                </div>
                <div>
                  <span className="field__label">Duration</span>
                  <span className="num" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-1)' }}>
                    {calculateDuration(selectedSession.started_at, selectedSession.ended_at)}
                  </span>
                </div>
                <div>
                  <span className="field__label">Started at</span>
                  <span className="num" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-2)' }}>
                    {selectedSession.started_at ? new Date(selectedSession.started_at).toUTCString() : '—'}
                  </span>
                </div>
                <div>
                  <span className="field__label">Ended at</span>
                  <span className="num" style={{ fontSize: 'var(--text-xs)', color: 'var(--text-2)' }}>
                    {selectedSession.ended_at ? new Date(selectedSession.ended_at).toUTCString() : 'Active'}
                  </span>
                </div>
              </div>
            </div>

            {selectedSession.communication_session_id && (
              <div className="card--inset" style={{ marginTop: 'var(--space-3)' }}>
                <span className="field__label">Linked communication session</span>
                <span className="num" style={{ fontSize: 'var(--text-sm)', color: 'var(--accent)' }}>
                  {selectedSession.communication_session_id}
                </span>
              </div>
            )}

            {selectedSession.extra_metadata && (
              <div className="card--inset" style={{ marginTop: 'var(--space-3)' }}>
                <span className="field__label">Session metadata</span>
                <pre
                  className="num"
                  style={{
                    fontSize: 'var(--text-xs)',
                    color: 'var(--text-3)',
                    overflowX: 'auto',
                    background: 'var(--surface-1)',
                    border: '1px solid var(--border-faint)',
                    borderRadius: 'var(--radius-sm)',
                    padding: 'var(--space-2)',
                  }}
                >
                  {JSON.stringify(selectedSession.extra_metadata, null, 2)}
                </pre>
              </div>
            )}

            <div className="row--between row" style={{ marginTop: 'var(--space-4)' }}>
              <button
                className="btn btn--secondary btn--sm"
                onClick={() => selectedSession && handleDownloadReport(selectedSession)}
                disabled={isDownloading}
              >
                <Download size={13} />
                <span>Download JSON</span>
              </button>
              <button
                className="btn btn--secondary btn--sm"
                onClick={() => selectedSession && handleDownloadReport(selectedSession, 'csv')}
                disabled={isDownloading}
              >
                <Download size={13} />
                <span>Download CSV</span>
              </button>
              <button className="btn btn--secondary" onClick={() => setSelectedSession(null)}>
                <span>Close</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

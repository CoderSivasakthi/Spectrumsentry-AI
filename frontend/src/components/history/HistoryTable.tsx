import React, { useState, useEffect } from 'react';
import { getMonitoringHistory } from '../../api/monitoring';
import { MonitoringSessionSummary } from '../../types/monitoring';
import { StatusBadge } from '../common/StatusBadge';
import { LoadingState, EmptyState } from '../common/States';
import {
  History,
  Layers,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  X,
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

  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2.5">
            <History className="w-5 h-5 text-sky-400" />
            <span>Monitoring Session History</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Historical cross-domain monitoring sessions persisted in SQLite
          </p>
        </div>

        <button
          onClick={() => fetchHistory(skip)}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-xs text-slate-300 font-mono transition-colors self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Main Table Card */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
        {isLoading ? (
          <LoadingState message="Loading historical sessions..." subtext="Querying database records" />
        ) : error ? (
          <div className="p-8 text-center text-rose-400 text-sm">{error}</div>
        ) : sessions.length === 0 ? (
          <EmptyState
            title="No Monitoring Sessions Found"
            message="Start and stop a monitoring session from the dashboard to create historical records."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Session ID</th>
                  <th className="py-3 px-4">Linked Channel</th>
                  <th className="py-3 px-4">Started (UTC)</th>
                  <th className="py-3 px-4">Ended (UTC)</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Final Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {sessions.map((sess) => (
                  <tr key={sess.monitoring_session_id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-sky-400">
                      {sess.monitoring_session_id}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {sess.communication_session_id || '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {sess.started_at ? new Date(sess.started_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {sess.ended_at ? new Date(sess.ended_at).toLocaleString() : 'In Progress'}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      {calculateDuration(sess.started_at, sess.ended_at)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={sess.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedSession(sess)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-sans font-medium transition-colors"
                      >
                        <Eye className="w-3 h-3 text-sky-400" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > 0 && (
          <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between text-xs font-mono text-slate-400">
            <div>
              Showing <span className="text-white font-bold">{skip + 1}</span> to{' '}
              <span className="text-white font-bold">{Math.min(skip + limit, total)}</span> of{' '}
              <span className="text-white font-bold">{total}</span> sessions
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => fetchHistory(Math.max(0, skip - limit))}
                disabled={skip === 0 || isLoading}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span className="text-xs">
                Page {currentPage} of {totalPages}
              </span>

              <button
                onClick={() => fetchHistory(skip + limit)}
                disabled={skip + limit >= total || isLoading}
                className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Selected Session Drilldown Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-xl rounded-2xl border border-slate-700 p-6 shadow-2xl relative space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-sky-400" />
                <h3 className="text-base font-bold text-white">
                  Session Inspection: {selectedSession.monitoring_session_id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedSession(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div>
                  <span className="text-slate-500 uppercase text-[10px] block">Status</span>
                  <StatusBadge status={selectedSession.status} size="sm" className="mt-1" />
                </div>
                <div>
                  <span className="text-slate-500 uppercase text-[10px] block">Duration</span>
                  <span className="text-white font-bold mt-1 block">
                    {calculateDuration(selectedSession.started_at, selectedSession.ended_at)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 uppercase text-[10px] block">Started At</span>
                  <span className="text-slate-300 mt-0.5 block">
                    {selectedSession.started_at ? new Date(selectedSession.started_at).toUTCString() : '—'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 uppercase text-[10px] block">Ended At</span>
                  <span className="text-slate-300 mt-0.5 block">
                    {selectedSession.ended_at ? new Date(selectedSession.ended_at).toUTCString() : 'Active'}
                  </span>
                </div>
              </div>

              {selectedSession.communication_session_id && (
                <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
                  <span className="text-slate-500 uppercase text-[10px] block">Linked Communication Session</span>
                  <span className="text-sky-300 font-bold mt-0.5 block">
                    {selectedSession.communication_session_id}
                  </span>
                </div>
              )}

              {selectedSession.extra_metadata && (
                <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800">
                  <span className="text-slate-500 uppercase text-[10px] block mb-1">Session Metadata</span>
                  <pre className="text-[11px] text-slate-400 overflow-x-auto bg-slate-950 p-2 rounded border border-slate-850">
                    {JSON.stringify(selectedSession.extra_metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 text-right">
              <button
                onClick={() => setSelectedSession(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-white uppercase tracking-wider transition-colors"
              >
                Close Inspection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

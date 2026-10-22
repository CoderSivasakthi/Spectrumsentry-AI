import React, { useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { LineChart, Activity } from 'lucide-react';

type ChartMetric = 'latency' | 'loss' | 'health' | 'snr' | 'throughput';

export const RealtimeCharts: React.FC = () => {
  const { liveHistory } = useMonitoring();
  const [selectedMetric, setSelectedMetric] = useState<ChartMetric>('latency');

  const points = liveHistory || [];
  const count = points.length;

  // Chart configuration based on selected metric
  const configs: Record<
    ChartMetric,
    {
      title: string;
      unit: string;
      color: string;
      fillColor: string;
      getValue: (p: (typeof points)[0]) => number;
      minY?: number;
      maxY?: number;
      threshold?: number;
      thresholdLabel?: string;
    }
  > = {
    latency: {
      title: 'Latency & Jitter Telemetry',
      unit: 'ms',
      color: '#38bdf8', // sky-400
      fillColor: 'rgba(56, 189, 248, 0.12)',
      getValue: (p) => p.latency,
      minY: 0,
      threshold: 100,
      thresholdLabel: '100ms Warning',
    },
    loss: {
      title: 'Packet Loss Ratio',
      unit: '%',
      color: '#f43f5e', // rose-500
      fillColor: 'rgba(244, 63, 94, 0.12)',
      getValue: (p) => p.packetLoss,
      minY: 0,
      maxY: 100,
      threshold: 5,
      thresholdLabel: '5% Warning',
    },
    health: {
      title: 'Communication Health Score',
      unit: '/100',
      color: '#10b981', // emerald-500
      fillColor: 'rgba(16, 185, 129, 0.12)',
      getValue: (p) => p.health,
      minY: 0,
      maxY: 100,
      threshold: 75,
      thresholdLabel: '75 Degraded Limit',
    },
    snr: {
      title: 'Physical Signal SNR Trend',
      unit: 'dB',
      color: '#a855f7', // purple-500
      fillColor: 'rgba(168, 85, 247, 0.12)',
      getValue: (p) => (p.snr != null ? p.snr : 0),
      minY: -10,
      maxY: 30,
      threshold: 0,
      thresholdLabel: '0 dB Noise Threshold',
    },
    throughput: {
      title: 'Throughput Rate',
      unit: 'kbps',
      color: '#06b6d4', // cyan-500
      fillColor: 'rgba(6, 182, 212, 0.12)',
      getValue: (p) => p.throughput,
      minY: 0,
    },
  };

  const currentConfig = configs[selectedMetric];

  // Calculate dynamic min/max for scale
  const values = points.map((p) => currentConfig.getValue(p));
  const rawMin = values.length > 0 ? Math.min(...values) : 0;
  const rawMax = values.length > 0 ? Math.max(...values) : 10;

  const minY = currentConfig.minY !== undefined ? currentConfig.minY : Math.min(0, rawMin);
  const maxY = currentConfig.maxY !== undefined ? currentConfig.maxY : Math.max(minY + 10, rawMax * 1.2);
  const rangeY = maxY - minY || 1;

  // Generate SVG path points
  const svgWidth = 800;
  const svgHeight = 220;
  const paddingX = 40;
  const paddingY = 25;
  const chartW = svgWidth - paddingX * 2;
  const chartH = svgHeight - paddingY * 2;

  const coordinates = points.map((p, idx) => {
    const x =
      count > 1
        ? paddingX + (idx / (count - 1)) * chartW
        : paddingX + chartW / 2;
    const val = currentConfig.getValue(p);
    const clamped = Math.max(minY, Math.min(maxY, val));
    const y = paddingY + chartH - ((clamped - minY) / rangeY) * chartH;
    return { x, y, val, time: p.time };
  });

  const pathD =
    coordinates.length > 0
      ? coordinates.reduce(
          (acc, pt, i) => (i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`),
          ''
        )
      : '';

  const areaD =
    coordinates.length > 0
      ? `${pathD} L ${coordinates[coordinates.length - 1].x} ${paddingY + chartH} L ${coordinates[0].x} ${paddingY + chartH} Z`
      : '';

  // Secondary line for Jitter when latency is selected
  const jitterCoordinates =
    selectedMetric === 'latency'
      ? points.map((p, idx) => {
          const x =
            count > 1
              ? paddingX + (idx / (count - 1)) * chartW
              : paddingX + chartW / 2;
          const val = p.jitter;
          const clamped = Math.max(minY, Math.min(maxY, val));
          const y = paddingY + chartH - ((clamped - minY) / rangeY) * chartH;
          return { x, y, val };
        })
      : [];

  const jitterPathD =
    jitterCoordinates.length > 0
      ? jitterCoordinates.reduce(
          (acc, pt, i) => (i === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`),
          ''
        )
      : '';

  return (
    <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
      {/* Header with Metric Selector Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <LineChart className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              {currentConfig.title}
            </h3>
            <p className="text-[11px] text-slate-400 font-mono">
              Live Bounded Window ({count} / 60 points)
            </p>
          </div>
        </div>

        {/* Metric Selector Buttons */}
        <div className="flex flex-wrap items-center gap-1 bg-slate-900/80 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setSelectedMetric('latency')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedMetric === 'latency'
                ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Latency & Jitter
          </button>

          <button
            onClick={() => setSelectedMetric('loss')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedMetric === 'loss'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Packet Loss
          </button>

          <button
            onClick={() => setSelectedMetric('health')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedMetric === 'health'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Health
          </button>

          <button
            onClick={() => setSelectedMetric('snr')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedMetric === 'snr'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            SNR Trend
          </button>

          <button
            onClick={() => setSelectedMetric('throughput')}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
              selectedMetric === 'throughput'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Throughput
          </button>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="mt-4 relative w-full overflow-hidden">
        {count > 0 ? (
          <div className="w-full">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-56 select-none overflow-visible"
            >
              {/* Horizontal Gridlines */}
              {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                const y = paddingY + chartH * ratio;
                const val = maxY - ratio * rangeY;
                return (
                  <g key={i}>
                    <line
                      x1={paddingX}
                      y1={y}
                      x2={svgWidth - paddingX}
                      y2={y}
                      stroke="rgba(51, 65, 85, 0.4)"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={paddingX - 6}
                      y={y + 3}
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="end"
                    >
                      {val.toFixed(val >= 10 || val <= -10 ? 0 : 1)}
                    </text>
                  </g>
                );
              })}

              {/* Threshold Line if configured */}
              {currentConfig.threshold !== undefined &&
                currentConfig.threshold >= minY &&
                currentConfig.threshold <= maxY && (
                  <g>
                    {(() => {
                      const threshY =
                        paddingY +
                        chartH -
                        ((currentConfig.threshold - minY) / rangeY) * chartH;
                      return (
                        <>
                          <line
                            x1={paddingX}
                            y1={threshY}
                            x2={svgWidth - paddingX}
                            y2={threshY}
                            stroke="#f59e0b"
                            strokeWidth="1.5"
                            strokeDasharray="3 3"
                          />
                          <text
                            x={svgWidth - paddingX - 4}
                            y={threshY - 4}
                            fill="#f59e0b"
                            fontSize="9"
                            fontFamily="monospace"
                            textAnchor="end"
                          >
                            {currentConfig.thresholdLabel || 'Threshold'}
                          </text>
                        </>
                      );
                    })()}
                  </g>
                )}

              {/* Area Fill */}
              {areaD && <path d={areaD} fill={currentConfig.fillColor} />}

              {/* Primary Line */}
              {pathD && (
                <path
                  d={pathD}
                  fill="none"
                  stroke={currentConfig.color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Secondary Jitter Line for Latency view */}
              {selectedMetric === 'latency' && jitterPathD && (
                <path
                  d={jitterPathD}
                  fill="none"
                  stroke="#a855f7"
                  strokeWidth="1.5"
                  strokeDasharray="2 2"
                  strokeLinecap="round"
                />
              )}

              {/* Last Point Glow Dot */}
              {coordinates.length > 0 && (
                <g>
                  {(() => {
                    const lastPt = coordinates[coordinates.length - 1];
                    return (
                      <>
                        <circle
                          cx={lastPt.x}
                          cy={lastPt.y}
                          r="4"
                          fill={currentConfig.color}
                        />
                        <circle
                          cx={lastPt.x}
                          cy={lastPt.y}
                          r="8"
                          fill="none"
                          stroke={currentConfig.color}
                          strokeWidth="1.5"
                          opacity="0.5"
                          className="animate-ping"
                        />
                      </>
                    );
                  })()}
                </g>
              )}
            </svg>
          </div>
        ) : (
          <div className="h-56 flex flex-col items-center justify-center text-center text-slate-500 font-mono text-xs">
            <Activity className="w-6 h-6 mb-2 text-slate-600 animate-pulse" />
            <span>Awaiting real-time telemetry stream...</span>
            <span className="text-[10px] text-slate-600 mt-1">
              Start a monitoring session or ingest packets to view live graph
            </span>
          </div>
        )}
      </div>

      {/* Footer Legend */}
      <div className="mt-3 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between text-[11px] text-slate-500 font-mono">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: currentConfig.color }}
            />
            <span>
              {currentConfig.title} ({currentConfig.unit})
            </span>
          </div>

          {selectedMetric === 'latency' && (
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
              <span>Jitter (ms)</span>
            </div>
          )}
        </div>

        <div>
          Latest:{' '}
          <span className="text-white font-bold">
            {values.length > 0 ? values[values.length - 1].toFixed(1) : '—'}{' '}
            {currentConfig.unit}
          </span>
        </div>
      </div>
    </div>
  );
};

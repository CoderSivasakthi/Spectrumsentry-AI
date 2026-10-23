import React, { useMemo, useRef, useState } from 'react';
import { useMonitoring } from '../../context/MonitoringContext';
import { Activity } from 'lucide-react';
import { ChartDataPoint } from '../../types/monitoring';

type ChartMetric = 'latency' | 'loss' | 'health' | 'snr' | 'throughput';

/* ---- Geometry ---- */
const SVG_W = 840;
const SVG_H = 280;
const PAD_L = 52;
const PAD_R = 16;
const PAD_T = 20;
const PAD_B = 30;
const PLOT_W = SVG_W - PAD_L - PAD_R;
const PLOT_H = SVG_H - PAD_T - PAD_B;

const METRIC_TABS: Array<{ id: ChartMetric; label: string; color: string }> = [
  { id: 'latency', label: 'Latency', color: 'var(--chart-latency)' },
  { id: 'loss', label: 'Loss', color: 'var(--chart-loss)' },
  { id: 'health', label: 'Health', color: 'var(--chart-health)' },
  { id: 'snr', label: 'SNR', color: 'var(--chart-snr)' },
  { id: 'throughput', label: 'Throughput', color: 'var(--chart-throughput)' },
];

interface MetricConfig {
  title: string;
  unit: string;
  color: string;
  getValue: (p: ChartDataPoint) => number;
  minY?: number;
  maxY?: number;
  threshold?: number;
  thresholdLabel?: string;
  /** Above the threshold is bad (shade the band). */
  aboveIsBad?: boolean;
}

const CONFIGS: Record<ChartMetric, MetricConfig> = {
  latency: {
    title: 'Latency & Jitter',
    unit: 'ms',
    color: 'var(--chart-latency)',
    getValue: (p) => p.latency,
    minY: 0,
    threshold: 100,
    thresholdLabel: '100 ms warning',
    aboveIsBad: true,
  },
  loss: {
    title: 'Packet loss',
    unit: '%',
    color: 'var(--chart-loss)',
    getValue: (p) => p.packetLoss,
    minY: 0,
    maxY: 100,
    threshold: 5,
    thresholdLabel: '5% warning limit',
    aboveIsBad: true,
  },
  health: {
    title: 'Health score',
    unit: '/100',
    color: 'var(--chart-health)',
    getValue: (p) => p.health,
    minY: 0,
    maxY: 100,
  },
  snr: {
    title: 'SNR trend',
    unit: 'dB',
    color: 'var(--chart-snr)',
    getValue: (p) => (p.snr != null ? p.snr : 0),
    minY: -10,
    maxY: 30,
    threshold: 0,
    thresholdLabel: '0 dB',
  },
  throughput: {
    title: 'Throughput',
    unit: 'kbps',
    color: 'var(--chart-throughput)',
    getValue: (p) => p.throughput,
    minY: 0,
  },
};

/* ---- helpers ---- */

const fmt = (v: number): string => (Math.abs(v) >= 10 ? v.toFixed(0) : v.toFixed(1));

const fmtClock = (ms: number): string => {
  const d = new Date(ms);
  const p = (n: number) => n.toString().padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

/** Evenly stepped "nice" tick step from the {1,2,5}×10^k candidates. */
const niceStep = (range: number): number => {
  const raw = range / 5;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  for (const m of [5, 2, 1]) {
    if (raw >= m * mag * 0.95) return m * mag;
  }
  return 10 * mag;
};

interface Axis {
  ticks: number[];
  toY: (v: number) => number;
}

const buildYAxis = (cfg: MetricConfig, points: ChartDataPoint[]): Axis => {
  const values = points.map((p) => cfg.getValue(p));
  let low = values.length ? Math.min(...values) : 0;
  let high = values.length ? Math.max(...values) : 10;
  if (cfg.minY !== undefined) low = cfg.minY;
  if (cfg.maxY !== undefined) high = cfg.maxY;
  if (high - low <= 0) high = low + 10;

  const step = niceStep(high - low);
  const start = Math.ceil(low / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= high + 1e-9; v += step) ticks.push(v);

  const clamp = (v: number) => Math.max(low, Math.min(high, v));
  return {
    ticks,
    toY: (v: number) => PAD_T + PLOT_H - ((clamp(v) - low) / (high - low)) * PLOT_H,
  };
};

const buildXScale = (points: ChartDataPoint[]) => {
  const times = points.map((p) => p.timestamp);
  const tMin = Math.min(...times);
  const tMax = Math.max(...times);
  if (tMax - tMin < 1) {
    const pad = 30_000; // single point: fake a ±30 s window so it is centered
    return {
      toX: () => PAD_L + PLOT_W / 2,
      tStart: tMin - pad,
      tEnd: tMax + pad,
    };
  }
  const pad = (tMax - tMin) * 0.02;
  const t0 = tMin - pad;
  const t1 = tMax + pad;
  return {
    toX: (t: number) => PAD_L + ((t - t0) / (t1 - t0)) * PLOT_W,
    tStart: t0,
    tEnd: t1,
  };
};

export const RealtimeCharts: React.FC = () => {
  const { liveHistory } = useMonitoring();
  const [selectedMetric, setSelectedMetric] = useState<ChartMetric>('latency');
  const [hover, setHover] = useState<number | null>(null);
  const plotRef = useRef<HTMLDivElement>(null);

  const cfg = CONFIGS[selectedMetric];
  const points = useMemo(() => liveHistory || [], [liveHistory]);

  const axis = useMemo(() => buildYAxis(cfg, points), [cfg, points]);
  const xScale = useMemo(() => buildXScale(points), [points]);

  const coords = useMemo(
    () =>
      points.map((p) => ({
        x: xScale.toX(p.timestamp),
        y: axis.toY(cfg.getValue(p)),
        value: cfg.getValue(p),
        ts: p.timestamp,
        jitter: p.jitter,
      })),
    [points, axis, xScale, cfg],
  );

  const jitterCoords = useMemo(
    () =>
      selectedMetric === 'latency'
        ? points.map((p) => ({ x: xScale.toX(p.timestamp), y: axis.toY(p.jitter) }))
        : [],
    [selectedMetric, points, axis, xScale],
  );

  const pathD = coords.length > 0
    ? coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`).join(' ')
    : '';

  const areaD =
    coords.length > 1
      ? `${pathD} L ${coords[coords.length - 1].x.toFixed(2)} ${PAD_T + PLOT_H} L ${coords[0].x.toFixed(2)} ${PAD_T + PLOT_H} Z`
      : '';

  const jitterPathD = jitterCoords.length > 0
    ? jitterCoords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(2)} ${c.y.toFixed(2)}`).join(' ')
    : '';

  const last = coords.length > 0 ? coords[coords.length - 1] : null;
  const latest = coords.length > 0 ? coords[coords.length - 1].value : null;

  /* Time-axis tick labels — 4 evenly spaced timestamps across the window. */
  const xTicks = useMemo(() => {
    const ticks: Array<{ x: number; label: string }> = [];
    for (let i = 0; i < 4; i++) {
      const t = xScale.tStart + ((xScale.tEnd - xScale.tStart) * i) / 3;
      ticks.push({ x: xScale.toX(t), label: fmtClock(t) });
    }
    return ticks;
  }, [xScale]);

  /* Hover handling */
  const onPointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    if (coords.length < 2) return;
    const rect = plotRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0) return;
    const scale = SVG_W / rect.width;
    const x = (e.clientX - rect.left) * scale;
    // nearest point by x (linear scan is fine for ≤60 points)
    let best = 0;
    for (let i = 1; i < coords.length; i++) {
      if (Math.abs(coords[i].x - x) < Math.abs(coords[best].x - x)) best = i;
    }
    setHover(best);
  };

  const hoverPoint = hover != null ? coords[hover] : null;
  const hoverJitter = hover != null && jitterCoords.length ? jitterCoords[hover] : null;
  const hoverLabel = hover != null && points[hover] ? fmtClock(points[hover].timestamp) : '';

  return (
    <section className="card">
      <header className="card__header row--between row" style={{ flexWrap: 'wrap' }}>
        <div>
          <h3 className="card__title">{cfg.title}</h3>
          <p className="card__sub num">
            Live Bounded Window ({points.length} / 60 points)
          </p>
        </div>
        <div className="segment segment--wrap">
          {METRIC_TABS.map((tab) => (
            <button
              key={tab.id}
              className={`segment__item${selectedMetric === tab.id ? ' is-active' : ''}`}
              onClick={() => {
                setSelectedMetric(tab.id);
                setHover(null);
              }}
            >
              <span className={`dot ${tab.id === 'latency' ? 'dot--info' : ''}`} style={{ background: tab.color }} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
      </header>

      <div className="card__body">
        {points.length === 0 ? (
          <div className="pane-state">
            <span className="pane-state__icon">
              <Activity size={18} />
            </span>
            <p className="pane-state__title">Waiting for telemetry</p>
            <p className="pane-state__hint">
              Start monitoring from the header to stream metrics into this chart.
            </p>
          </div>
        ) : (
          <div ref={plotRef} style={{ position: 'relative' }}>
            <svg
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              style={{ display: 'block', width: '100%', height: 'auto' }}
              onPointerMove={onPointerMove}
              onPointerLeave={() => setHover(null)}
              role="img"
              aria-label={`${cfg.title} over the last ${points.length} samples`}
            >
              {/* Y gridlines + labels */}
              {axis.ticks.map((t) => (
                <g key={`gy-${t}`}>
                  <line
                    x1={PAD_L}
                    y1={axis.toY(t)}
                    x2={PAD_L + PLOT_W}
                    y2={axis.toY(t)}
                    stroke="var(--chart-grid)"
                    strokeWidth="1"
                  />
                  <text
                    x={PAD_L - 6}
                    y={axis.toY(t) + 3}
                    textAnchor="end"
                    fontSize="9"
                    fill="var(--text-3)"
                    fontFamily="var(--font-mono)"
                  >
                    {fmt(t)}
                  </text>
                </g>
              ))}

              {/* X tick labels (time-based) — keyed by slot index; labels can
                  collide when the whole window spans under a second. */}
              {xTicks.map((t, i) => (
                <g key={`gx-${i}`}>
                  <line x1={t.x} y1={PAD_T + PLOT_H} x2={t.x} y2={PAD_T + PLOT_H + 4} stroke="var(--border)" strokeWidth="1" />
                  <text
                    x={t.x}
                    y={SVG_H - 9}
                    textAnchor="middle"
                    fontSize="9.5"
                    fill="var(--text-3)"
                    fontFamily="var(--font-mono)"
                  >
                    {t.label}
                  </text>
                </g>
              ))}

              {/* Threshold + warning band */}
              {cfg.threshold !== undefined &&
                cfg.threshold > Math.min(...axis.ticks, axis.ticks[0]) - 0.001 && (() => {
                  const ty = axis.toY(cfg.threshold);
                  if (ty < PAD_T - 0.5 || ty > PAD_T + PLOT_H + 0.5) return null;
                  return (
                    <g>
                      {cfg.aboveIsBad && (
                        <rect
                          x={PAD_L}
                          y={PAD_T}
                          width={PLOT_W}
                          height={ty - PAD_T}
                          fill="var(--warn)"
                          opacity="0.05"
                        />
                      )}
                      <line x1={PAD_L} y1={ty} x2={PAD_L + PLOT_W} y2={ty}
                            stroke="var(--chart-threshold)" strokeWidth="1.5" strokeDasharray="4 4" />
                      <text
                        x={PAD_L + 4}
                        y={ty - 5}
                        fontSize="9"
                        fill="var(--warn)"
                        fontFamily="var(--font-mono)"
                      >
                        {cfg.thresholdLabel}
                      </text>
                    </g>
                  );
                })()}

              {/* Area + primary line */}
              {areaD && <path d={areaD} fill={cfg.color} fillOpacity="0.08" />}
              {pathD && (
                <path d={pathD} fill="none" stroke={cfg.color} strokeWidth="2"
                      strokeLinecap="round" strokeLinejoin="round" />
              )}

              {/* Jitter secondary line */}
              {jitterPathD && (
                <path d={jitterPathD} fill="none" stroke="var(--chart-jitter)" strokeWidth="1"
                      strokeDasharray="3 3" strokeLinecap="round" opacity="0.8" />
              )}

              {/* Hover crosshair */}
              {hoverPoint && (
                <g pointerEvents="none">
                  <line
                    x1={hoverPoint.x} y1={PAD_T} x2={hoverPoint.x} y2={PAD_T + PLOT_H}
                    stroke="var(--accent)" strokeWidth="1" opacity="0.35" />
                  {hoverJitter && <circle cx={hoverJitter.x} cy={hoverJitter.y} r="3" fill="var(--chart-jitter)" />}
                  <circle cx={hoverPoint.x} cy={hoverPoint.y} r="4" fill={cfg.color} />
                </g>
              )}

              {/* Recent point marker + pulse ring */}
              {last && !(hoverPoint && hover === coords.length - 1) && (
                <g pointerEvents="none">
                  <circle cx={last.x} cy={last.y} r="3.5" fill={cfg.color} />
                  <circle className="pulse-ring" cx={last.x} cy={last.y} r="6"
                          fill="none" stroke={cfg.color} strokeWidth="1.5" />
                </g>
              )}
            </svg>

            {/* Tooltip */}
            {hoverPoint && (
              <div
                className="num"
                style={{
                  position: 'absolute',
                  left: `${Math.max(6, Math.min(94, (hoverPoint.x / SVG_W) * 100))}%`,
                  top: `${(hoverPoint.y / SVG_H) * 100}%`,
                  transform: 'translate(-50%, calc(-100% - 10px))',
                  pointerEvents: 'none',
                  background: 'var(--surface-2)',
                  border: '1px solid var(--border-strong)',
                  borderRadius: 'var(--radius-md)',
                  padding: '6px 9px',
                  fontSize: 11,
                  color: 'var(--text-2)',
                  whiteSpace: 'nowrap',
                  zIndex: 5,
                }}
              >
                <div style={{ color: 'var(--text-3)' }}>{hoverLabel}</div>
                <div>
                  {cfg.title}: <span style={{ color: 'var(--text-1)' }}>{hoverPoint.value.toFixed(1)} {cfg.unit}</span>
                </div>
                {hoverJitter && <div>Jitter: {points[hover!].jitter.toFixed(1)} ms</div>}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card__footer row--between row">
        <div className="row" style={{ gap: 'var(--space-4)' }}>
          <span className="row" style={{ gap: 6 }}>
            <span className="dot" style={{ background: cfg.color }} />
            <span>{cfg.title} ({cfg.unit})</span>
          </span>
          {selectedMetric === 'latency' && (
            <span className="row" style={{ gap: 6 }}>
              <span className="dot" style={{ background: 'var(--chart-jitter)' }} />
              <span>Jitter (ms)</span>
            </span>
          )}
        </div>
        <span className="num">
          Latest: {latest != null ? `${latest.toFixed(1)} ${cfg.unit}` : '—'}
        </span>
      </div>
    </section>
  );
};

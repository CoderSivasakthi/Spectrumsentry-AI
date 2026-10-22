import React, { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  subtext?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  tone?: 'default' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'purple';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subtext,
  icon,
  tone = 'default',
  className = '',
}) => {
  const toneClasses = {
    default: 'border-slate-800 bg-slate-900/60 text-slate-100',
    emerald: 'border-emerald-500/20 bg-emerald-950/20 text-emerald-100',
    amber: 'border-amber-500/20 bg-amber-950/20 text-amber-100',
    rose: 'border-rose-500/20 bg-rose-950/20 text-rose-100',
    cyan: 'border-cyan-500/20 bg-cyan-950/20 text-cyan-100',
    purple: 'border-purple-500/20 bg-purple-950/20 text-purple-100',
  }[tone];

  const valueToneClasses = {
    default: 'text-white',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    rose: 'text-rose-400',
    cyan: 'text-cyan-400',
    purple: 'text-purple-400',
  }[tone];

  return (
    <div className={`p-4 rounded-xl border backdrop-blur-md flex flex-col justify-between transition-all ${toneClasses} ${className}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs uppercase font-medium tracking-wider text-slate-400">
          {label}
        </span>
        {icon && <div className="text-slate-400">{icon}</div>}
      </div>

      <div className="mt-2.5 flex items-baseline gap-1.5">
        <span className={`text-2xl font-bold font-mono tracking-tight ${valueToneClasses}`}>
          {value !== null && value !== undefined ? value : '—'}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>

      {subtext && (
        <div className="mt-2 text-xs text-slate-500 flex items-center gap-1 truncate">
          {subtext}
        </div>
      )}
    </div>
  );
};

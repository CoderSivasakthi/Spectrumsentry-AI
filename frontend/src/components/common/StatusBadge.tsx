import React from 'react';
import { OverallStatus, ConsistencyStatus, SeverityLevel } from '../../types/monitoring';
import {
  CheckCircle2,
  AlertTriangle,
  XOctagon,
  RotateCcw,
  HelpCircle,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';

interface StatusBadgeProps {
  status: OverallStatus | ConsistencyStatus | SeverityLevel | string;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
  className = '',
}) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';
  let Icon = HelpCircle;

  switch (norm) {
    case 'NORMAL':
    case 'CONNECTED':
    case 'CONSISTENT':
    case 'INFO':
    case 'EXCELLENT':
    case 'GOOD':
      colorClasses = 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30';
      Icon = CheckCircle2;
      break;
    case 'DEGRADED':
    case 'WARNING':
    case 'FAIR':
    case 'CONNECTING':
    case 'RECONNECTING':
      colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-500/30';
      Icon = AlertTriangle;
      break;
    case 'INTERRUPTED':
    case 'CRITICAL':
    case 'DISCONNECTED':
    case 'POOR':
      colorClasses = 'bg-rose-950/60 text-rose-300 border-rose-500/30';
      Icon = XOctagon;
      break;
    case 'RECOVERING':
    case 'STARTING':
      colorClasses = 'bg-cyan-950/60 text-cyan-300 border-cyan-500/30';
      Icon = RotateCcw;
      break;
    case 'REVIEW':
    case 'CONFLICTING':
      colorClasses = 'bg-purple-950/60 text-purple-300 border-purple-500/30';
      Icon = ShieldAlert;
      break;
    case 'UNCORRELATED':
      colorClasses = 'bg-slate-800/80 text-slate-300 border-slate-600/30';
      Icon = ShieldCheck;
      break;
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-3.5 h-3.5',
    lg: 'w-4 h-4',
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-md border tracking-wider font-mono uppercase ${sizeClasses} ${colorClasses} ${className}`}
    >
      {showIcon && <Icon className={`${iconSizes} shrink-0`} />}
      <span>{norm}</span>
    </span>
  );
};

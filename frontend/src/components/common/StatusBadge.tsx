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

type Variant = 'ok' | 'warn' | 'crit' | 'info' | 'muted';

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  size = 'md',
  showIcon = true,
  className = '',
}) => {
  const norm = (status || '').toUpperCase();

  let variant: Variant = 'muted';
  let Icon = HelpCircle;

  switch (norm) {
    case 'NORMAL':
    case 'CONNECTED':
    case 'CONSISTENT':
    case 'EXCELLENT':
    case 'GOOD':
      variant = 'ok';
      Icon = CheckCircle2;
      break;
    case 'INFO':
      variant = 'info';
      Icon = CheckCircle2;
      break;
    case 'DEGRADED':
    case 'WARNING':
    case 'FAIR':
    case 'CONNECTING':
    case 'RECONNECTING':
      variant = 'warn';
      Icon = AlertTriangle;
      break;
    case 'INTERRUPTED':
    case 'CRITICAL':
    case 'DISCONNECTED':
    case 'POOR':
      variant = 'crit';
      Icon = XOctagon;
      break;
    case 'RECOVERING':
    case 'STARTING':
      variant = 'info';
      Icon = RotateCcw;
      break;
    case 'REVIEW':
    case 'CONFLICTING':
      variant = 'muted';
      Icon = ShieldAlert;
      break;
    case 'UNCORRELATED':
      variant = 'muted';
      Icon = ShieldCheck;
      break;
  }

  const sizeClass = { sm: 'badge--sm', md: '', lg: 'badge--lg' }[size];

  return (
    <span className={`badge badge--${variant} ${sizeClass} ${className}`.trim()}>
      {showIcon && <Icon size={size === 'lg' ? 13 : 12} strokeWidth={2.2} />}
      <span>{norm}</span>
    </span>
  );
};

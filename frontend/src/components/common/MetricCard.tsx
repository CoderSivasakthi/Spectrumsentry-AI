import React, { ReactNode } from 'react';

interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  subtext?: string;
  icon?: ReactNode;
  tone?: 'default' | 'ok' | 'warn' | 'crit';
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
  const toneClass = tone === 'default' ? '' : ` metric__value--${tone}`;

  return (
    <div className={`metric ${className}`.trim()}>
      <div className="metric__label">
        <span>{label}</span>
        {icon && <span style={{ display: 'inline-flex' }}>{icon}</span>}
      </div>
      <div className={`metric__value${toneClass}`}>
        {value !== null && value !== undefined ? value : '—'}
        {unit && <span className="metric__unit">{unit}</span>}
      </div>
      {subtext && <div className="metric__hint">{subtext}</div>}
    </div>
  );
};

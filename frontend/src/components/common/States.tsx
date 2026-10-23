import React from 'react';
import { AlertCircle, Inbox, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../../api/client';

interface LoadingStateProps {
  message?: string;
  subtext?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Connecting to SpectrumSentry AI...',
  subtext = 'Synchronizing real-time telemetry and decision state',
}) => {
  return (
    <div className="pane-state" style={{ paddingBlock: 80 }}>
      <span className="spinner" />
      <h3 className="pane-state__title">{message}</h3>
      <p className="pane-state__hint">{subtext}</p>
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Backend unreachable',
  message = 'Unable to reach the SpectrumSentry backend service.',
  onRetry,
}) => {
  return (
    <div className="error-banner">
      <span className="error-banner__icon">
        <AlertCircle size={18} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="error-banner__title">{title}</div>
        <p className="error-banner__msg">{message}</p>
        <p className="error-banner__detail">API target: {API_BASE_URL}</p>
      </div>
      {onRetry && (
        <button className="btn btn--secondary" onClick={onRetry}>
          <RefreshCw size={14} />
          <span>Retry Connection</span>
        </button>
      )}
    </div>
  );
};

interface EmptyStateProps {
  title: string;
  message: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  message,
  icon,
  action,
}) => {
  return (
    <div
      className="pane-state"
      style={{
        border: '1px dashed var(--border-strong)',
        borderRadius: 'var(--radius-lg)',
      }}
    >
      <span className="pane-state__icon">{icon || <Inbox size={18} />}</span>
      <h4 className="pane-state__title">{title}</h4>
      <p className="pane-state__hint">{message}</p>
      {action && <div style={{ marginTop: 'var(--space-2)' }}>{action}</div>}
    </div>
  );
};

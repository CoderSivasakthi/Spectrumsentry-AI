import React from 'react';
import { useMonitoring } from '../context/MonitoringContext';
import { LinkTestCard } from '../components/link/LinkTestCard';
import { CommDetailCard } from '../components/link/CommDetailCard';
import { EventTimeline } from '../components/monitoring/EventTimeline';
import { ErrorState, LoadingState } from '../components/common/States';

/** Link test view — transmits packets and inspects detailed link telemetry. */
export const LinkTelemetryView: React.FC = () => {
  const { snapshot, isLoading, error, refresh, isBackendHealthy } = useMonitoring();

  if (isLoading && !snapshot) {
    return <LoadingState message="Connecting to SpectrumSentry AI backend..." />;
  }

  return (
    <div className="stack">
      {(!isBackendHealthy || error) && (
        <ErrorState
          title="Backend unreachable"
          message="Live telemetry is not available right now — retries use the same target."
          onRetry={refresh}
        />
      )}

      <LinkTestCard />

      <div className="dash-grid dash-grid--flat">
        <CommDetailCard />
        <EventTimeline />
      </div>
    </div>
  );
};

export default LinkTelemetryView;

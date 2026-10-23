import React from 'react';
import { useMonitoring } from '../context/MonitoringContext';
import { SystemStatusHeader } from '../components/monitoring/SystemStatusHeader';
import { CommunicationHealthCard } from '../components/monitoring/CommunicationHealthCard';
import { SignalAnalysisCard } from '../components/monitoring/SignalAnalysisCard';
import { DecisionEngineCard } from '../components/monitoring/DecisionEngineCard';
import { AlertsPanel } from '../components/monitoring/AlertsPanel';
import { RealtimeCharts } from '../components/monitoring/RealtimeCharts';
import { EventTimeline } from '../components/monitoring/EventTimeline';
import { ErrorState, LoadingState } from '../components/common/States';

/**
 * Live monitor — the ops console's overview view.
 * Structure: status hero → live chart with alerts rail →
 * three domain boxes (communication | signal/AI | decision) → event timeline.
 */
export const Dashboard: React.FC = () => {
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

      <SystemStatusHeader />

      <div className="dash-grid">
        <RealtimeCharts />
        {/* Right rail: alerts track the chart's height */}
        <div className="dash-grid__rail">
          <AlertsPanel />
        </div>
      </div>

      {/* Three side-by-side domain boxes, each with its details categorized inside */}
      <div className="tri-grid">
        <CommunicationHealthCard />
        <SignalAnalysisCard />
        <DecisionEngineCard />
      </div>

      <EventTimeline />
    </div>
  );
};

export default Dashboard;

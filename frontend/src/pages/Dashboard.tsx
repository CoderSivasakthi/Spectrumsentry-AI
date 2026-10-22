import React from 'react';
import { useMonitoring } from '../context/MonitoringContext';
import { SystemStatusHeader } from '../components/monitoring/SystemStatusHeader';
import { CommunicationHealthCard } from '../components/monitoring/CommunicationHealthCard';
import { SignalAnalysisCard } from '../components/monitoring/SignalAnalysisCard';
import { DecisionEngineCard } from '../components/monitoring/DecisionEngineCard';
import { AlertsPanel } from '../components/monitoring/AlertsPanel';
import { RealtimeCharts } from '../components/monitoring/RealtimeCharts';
import { EventTimeline } from '../components/monitoring/EventTimeline';
import { SessionControls } from '../components/monitoring/SessionControls';
import { ErrorState, LoadingState } from '../components/common/States';

export const Dashboard: React.FC = () => {
  const { snapshot, isLoading, error, refresh, isBackendHealthy } = useMonitoring();

  if (isLoading && !snapshot) {
    return <LoadingState message="Connecting to SpectrumSentry AI backend..." />;
  }

  return (
    <div className="space-y-6">
      {/* Backend Unreachable Alert Banner if applicable */}
      {(!isBackendHealthy || error) && (
        <ErrorState
          title="Backend Service Unreachable"
          message={error || 'Unable to communicate with the SpectrumSentry AI backend service at http://127.0.0.1:8000.'}
          onRetry={refresh}
        />
      )}

      {/* 1. System Status Header */}
      <SystemStatusHeader />

      {/* 2. Top Metric Domain Cards (Communication & Signal) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <CommunicationHealthCard />
        <SignalAnalysisCard />
      </div>

      {/* 3. Decision Engine & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <DecisionEngineCard />
        <AlertsPanel />
      </div>

      {/* 4. Real-Time Telemetry Charts */}
      <RealtimeCharts />

      {/* 5. Event Timeline & Interactive Session Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EventTimeline />
        <SessionControls />
      </div>
    </div>
  );
};

export default Dashboard;

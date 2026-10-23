import React from 'react';
import { useMonitoring } from '../context/MonitoringContext';
import { SignalGeneratorCard } from '../components/signal/SignalGeneratorCard';
import { SessionControls } from '../components/monitoring/SessionControls';
import { SignalAnalysisCard } from '../components/monitoring/SignalAnalysisCard';
import { ErrorState, LoadingState } from '../components/common/States';

/**
 * AI signal lab — synthesize signals and watch the real classification pipeline
 * run, then hand-derive evidence to probe the decision engine directly.
 */
export const SignalLabView: React.FC = () => {
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

      <SignalGeneratorCard />

      <div className="dash-grid dash-grid--flat">
        <SessionControls />
        <SignalAnalysisCard />
      </div>
    </div>
  );
};

export default SignalLabView;

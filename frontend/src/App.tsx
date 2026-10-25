import React from 'react';
import { MonitoringProvider, useMonitoring } from './context/MonitoringContext';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { LinkTelemetryView } from './pages/LinkTelemetryView';
import { Devices } from './pages/Devices';
import { SignalLabView } from './pages/SignalLabView';
import { SignalHistory } from './pages/SignalHistory';
import { SystemAbout } from './components/about/SystemAbout';

const MainContent: React.FC = () => {
  const { activeTab } = useMonitoring();

  switch (activeTab) {
    case 'link':
      return <LinkTelemetryView />;
    case 'devices':
      return <Devices />;
    case 'signal':
      return <SignalLabView />;
    case 'sessions':
      return <SignalHistory />;
    case 'system':
      return <SystemAbout />;
    case 'live':
    default:
      return <Dashboard />;
  }
};

export const App: React.FC = () => {
  return (
    <MonitoringProvider>
      <AppLayout>
        <MainContent />
      </AppLayout>
    </MonitoringProvider>
  );
};

export default App;

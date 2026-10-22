import React from 'react';
import { MonitoringProvider, useMonitoring } from './context/MonitoringContext';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { SignalHistory } from './pages/SignalHistory';
import { SystemAbout } from './components/about/SystemAbout';

const MainContent: React.FC = () => {
  const { activeTab } = useMonitoring();

  switch (activeTab) {
    case 'history':
      return <SignalHistory />;
    case 'about':
      return <SystemAbout />;
    case 'dashboard':
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

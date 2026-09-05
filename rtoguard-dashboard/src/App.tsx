import React, { useEffect, useState } from 'react';
import { Layout } from './components/Layout';
import { ReturnRiskScorer } from './components/ReturnRiskScorer';
import { FraudSpikeDetector } from './components/FraudSpikeDetector';
import { AbuseRingSentinel } from './components/AbuseRingSentinel';
import { ChargebackEvidenceResponder } from './components/ChargebackEvidenceResponder';
import { useStore } from './store/dashboardStore';
import { rtoAPI } from './services/api';
import './styles/globals.css';

function App() {
  const { active_tab } = useStore();
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected'>('connected');

  useEffect(() => {
    // Check API health
    const checkHealth = async () => {
      try {
        await rtoAPI.healthCheck();
        setConnectionStatus('connected');
      } catch (error) {
        console.error('Backend connection failed:', error);
        setConnectionStatus('disconnected');
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const renderContent = () => {
    switch (active_tab) {
      case 'risk-scorer':
        return <ReturnRiskScorer />;
      case 'spike-detector':
        return <FraudSpikeDetector />;
      case 'ring-sentinel':
        return <AbuseRingSentinel />;
      case 'chargeback-responder':
        return <ChargebackEvidenceResponder />;
      default:
        return <ReturnRiskScorer />;
    }
  };

  return (
    <Layout>
      {/* Offline Alert Banner */}
      {connectionStatus === 'disconnected' && (
        <div className="mb-4 p-3 rounded bg-caution-bg text-caution border border-caution/20 text-xs">
          We could not reach the checking service right now. The numbers shown may be from an earlier snapshot. Try again in a moment.
        </div>
      )}

      {/* Main Content */}
      {renderContent()}
    </Layout>
  );
}

export default App;

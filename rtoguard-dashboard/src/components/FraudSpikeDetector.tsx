import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MapPin, AlertTriangle, Activity } from 'lucide-react';
import { motion } from 'framer-motion';
import { PincodeCluster, VelocityMetric } from '../types';
import { rtoAPI } from '../services/api';

export const FraudSpikeDetector: React.FC = () => {
  const MOCK_VELOCITY: VelocityMetric[] = [
    { timestamp: '14:15', tps_value: 12, breach_ceiling: 25, is_breach: false },
    { timestamp: '14:20', tps_value: 14, breach_ceiling: 25, is_breach: false },
    { timestamp: '14:25', tps_value: 18, breach_ceiling: 25, is_breach: false },
    { timestamp: '14:30', tps_value: 21, breach_ceiling: 25, is_breach: false },
    { timestamp: '14:35', tps_value: 36, breach_ceiling: 25, is_breach: true },
    { timestamp: '14:40', tps_value: 41, breach_ceiling: 25, is_breach: true },
    { timestamp: '14:45', tps_value: 32, breach_ceiling: 25, is_breach: true },
  ];

  const MOCK_CLUSTER: PincodeCluster = {
    pincode: '110001',
    city: 'New Delhi',
    cluster_name: 'Delhi Central',
    baseline_tps: 12,
    current_tps: 41,
    spike_percentage: 340,
    spike_start_time: '14:22 IST',
    spike_duration_minutes: 38,
    threat_signature: 'Scripted Checkout Bot Cluster',
    critical: true,
  };

  const [velocityData, setVelocityData] = useState<VelocityMetric[]>(MOCK_VELOCITY);
  const [spikeCluster, setSpikeCluster] = useState<PincodeCluster>(MOCK_CLUSTER);

  useEffect(() => {
    (async () => {
      try {
        const cluster = await rtoAPI.getActiveSpikeCluster();
        if (cluster && cluster.pincode) setSpikeCluster((prev) => ({ ...prev, ...cluster }));
        const metrics = await rtoAPI.getSpikeMetrics(cluster?.pincode || '110001');
        if (metrics?.velocity) setVelocityData(metrics.velocity);
      } catch (e) {
        console.log('Using static area alert data');
      }
    })();
  }, []);

  const isHighSurge = spikeCluster.spike_percentage >= 200;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold text-ink">Return surges by area</h2>
        <p className="text-sm text-ink-muted mt-1">
          If one PIN code is suddenly returning a lot of orders, it might signal a scam cluster. Here is what we are seeing right now.
        </p>
      </div>

      {/* Static Explainer Card */}
      <div className="merchant-card p-4 bg-navy-subtle border-navy/20 flex items-start gap-3">
        <MapPin size={18} className="text-navy shrink-0 mt-0.5" />
        <p className="text-xs text-ink leading-relaxed">
          When many orders from the same area get returned, it can mean a fraud ring is operating there. We watch for these surges automatically and highlight the worst-affected areas below.
        </p>
      </div>

      {/* Active Area Alert Banner */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={`merchant-card p-5 border ${
          isHighSurge ? 'bg-risk-bg border-risk/30 text-risk' : 'bg-caution-bg border-caution/30 text-caution'
        }`}
      >
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <AlertTriangle size={18} />
              <h3 className="text-base font-semibold">
                PIN code: {spikeCluster.pincode} ({spikeCluster.city})
              </h3>
            </div>
            <p className="text-xs font-medium">
              Returns up {spikeCluster.spike_percentage}% vs. normal
            </p>
            <p className="text-xs opacity-80">
              Orders from this area: {(spikeCluster.current_tps * 12).toLocaleString()} total checkouts flagged in last hour
            </p>
          </div>

          <div className="shrink-0">
            <span className={`px-3 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
              isHighSurge ? 'bg-risk text-beige' : 'bg-caution text-beige'
            }`}>
              {isHighSurge ? 'High Surge Risk' : 'Moderate Surge Risk'}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Main Section Heading */}
      <div>
        <h3 className="text-base font-semibold text-ink flex items-center gap-2">
          <Activity size={16} className="text-navy" />
          How bad is it?
        </h3>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="merchant-card p-4 space-y-1">
          <span className="text-xs text-ink-muted block font-medium">Return rate in this area</span>
          <p className="text-2xl font-bold text-ink">
            {Math.min(84, Math.round(spikeCluster.spike_percentage / 4.5))}%
          </p>
          <span className="text-xs text-risk font-medium block">4.2x higher than national baseline</span>
        </div>

        <div className="merchant-card p-4 space-y-1">
          <span className="text-xs text-ink-muted block font-medium">Average order value</span>
          <p className="text-2xl font-bold text-ink">₹3,420</p>
          <span className="text-xs text-ink-muted block">Typical cart size in surge area</span>
        </div>

        <div className="merchant-card p-4 space-y-1">
          <span className="text-xs text-ink-muted block font-medium">Orders we flagged</span>
          <p className="text-2xl font-bold text-navy">
            {(spikeCluster.current_tps * 8).toLocaleString()}
          </p>
          <span className="text-xs text-navy font-medium block">Prepayment requested automatically</span>
        </div>
      </div>

      {/* Velocity Trend Chart */}
      <div className="merchant-card p-5 space-y-4">
        <div>
          <h4 className="text-sm font-semibold text-ink">Order Volume Trend</h4>
          <p className="text-xs text-ink-muted mt-0.5">
            Order placement traffic over time showing baseline vs surge spike.
          </p>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={velocityData}>
              <defs>
                <linearGradient id="colorTps" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#1A3C6E" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#1A3C6E" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#D9D4CB" opacity={0.5} />
              <XAxis dataKey="timestamp" stroke="#3D3D3D" fontSize={12} />
              <YAxis stroke="#3D3D3D" fontSize={12} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#FAF9F6', borderColor: '#D9D4CB', color: '#0D0D0D', fontSize: '12px' }}
              />
              <Area
                type="monotone"
                dataKey="tps_value"
                stroke="#1A3C6E"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#colorTps)"
                name="Orders / min"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

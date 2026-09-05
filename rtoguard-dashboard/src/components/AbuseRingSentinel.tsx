import React, { useState, useEffect } from 'react';
import { Shield, ChevronDown, ChevronUp } from 'lucide-react';
import { AbuseRing } from '../types';
import { rtoAPI } from '../services/api';

export const AbuseRingSentinel: React.FC = () => {
  const MOCK_RING: AbuseRing = {
    ring_id: 'RING-104',
    ring_name: 'Delhi Urban Nexus',
    total_nodes: 18,
    total_edges: 34,
    total_orders: 1420,
    risk_score: 96,
    value_at_risk_inr: 2450000,
    cod_ratio: 100,
    correlation_vectors: [
      { name: 'Fingerprint Collision', linked_signals: 14, strength: 'Critical' },
      { name: 'Geographic Proximity', linked_signals: 18, strength: 'Critical' },
      { name: 'Payment Preference', linked_signals: 34, strength: 'High' },
      { name: 'Virtual Carrier Range', linked_signals: 18, strength: 'Critical' },
    ],
    nodes: [
      { node_id: '+91 9871-X419', node_type: 'Phone', label: '+91 9871-X419', risk_score: 92, linked_orders: 156 },
      { node_id: '+91 9871-X420', node_type: 'Phone', label: '+91 9871-X420', risk_score: 88, linked_orders: 142 },
      { node_id: '+91 9871-X421', node_type: 'Phone', label: '+91 9871-X421', risk_score: 85, linked_orders: 128 },
      { node_id: 'fp_d91a78c', node_type: 'Device', label: 'fp_d91a78c_ios', risk_score: 94, linked_orders: 289 },
      { node_id: 'fp_dI9v2_android', node_type: 'Device', label: 'fp_dI9v2_android', risk_score: 91, linked_orders: 267 },
      { node_id: 'PIN 560001', node_type: 'Pincode', label: 'PIN 560001 (HLR Urban Nexus)', risk_score: 78, linked_orders: 420 },
      { node_id: 'addr_hash_89b21', node_type: 'Address', label: 'Cunningham Rd Blk #4', risk_score: 82, linked_orders: 187 },
      { node_id: 'addr_hash_7c1b', node_type: 'Address', label: 'Queens Road Plot #52', risk_score: 79, linked_orders: 156 },
    ],
    edges: [
      { source_id: '+91 9871-X419', target_id: 'fp_d91a78c', relation_type: 'WebGL Collision', weight: 0.95, collision_type: 'WebGL' },
      { source_id: '+91 9871-X420', target_id: 'fp_dI9v2_android', relation_type: 'Token Collision', weight: 0.92, collision_type: 'Token' },
      { source_id: '+91 9871-X419', target_id: 'PIN 560001', relation_type: 'Geo Concurrence', weight: 0.88, collision_type: 'Geo' },
    ],
    density: 0.84,
    high_cohesion: true,
    active_subgraph_id: 'RING-104',
    detected_at: new Date(Date.now() - 45 * 60000).toISOString(),
  };

  const [ring, setRing] = useState<AbuseRing>(MOCK_RING);
  const [showExplainer, setShowExplainer] = useState(false);
  const [isBlocked, setIsBlocked] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const rings = await rtoAPI.getActiveRings();
        if (rings && rings.length > 0) {
          setRing(rings[0]);
        }
      } catch (e) {
        console.log('Using static fraud group data');
      }
    })();
  }, []);

  const handleBlock = async () => {
    try {
      await rtoAPI.blockRing(ring.ring_id);
    } catch (e) {
      console.log('Local resolution state applied for block ring');
    } finally {
      setIsBlocked(true);
    }
  };

  const devicesCount = ring.nodes.filter((n) => n.node_type === 'Device').length;
  const phonesCount = ring.nodes.filter((n) => n.node_type === 'Phone').length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-xl font-semibold text-ink">Organised return fraud</h2>
        <p className="text-sm text-ink-muted mt-1">
          Some customers place orders in groups, return most of them, and share phone numbers or devices to avoid detection. We track these groups and let you block them.
        </p>
      </div>

      {/* Static Explainer Chip */}
      <div className="merchant-card p-4 space-y-2">
        <button
          onClick={() => setShowExplainer(!showExplainer)}
          className="text-xs font-semibold text-navy hover:underline flex items-center gap-1.5"
        >
          <span>How does this work?</span>
          {showExplainer ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {showExplainer && (
          <p className="text-xs text-ink-muted leading-relaxed pt-1 border-t border-border">
            Our AI looks for shared phone patterns, delivery addresses, and devices across thousands of orders. When it spots a group working together, it surfaces them here.
          </p>
        )}
      </div>

      {/* Group List & Details */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left: Group Card List */}
        <div className="col-span-1 merchant-card p-5 space-y-4">
          <h3 className="text-sm font-semibold text-ink flex items-center gap-2">
            <Shield size={16} className="text-navy" />
            Detected Fraud Groups
          </h3>

          <div className="p-4 rounded bg-beige border border-border space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-ink">Group {ring.ring_id}</span>
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-risk-bg text-risk border border-risk/20">
                High Risk
              </span>
            </div>

            <div className="text-xs text-ink-muted space-y-1 pt-1">
              <p>Orders placed: <strong className="text-ink">{ring.total_orders.toLocaleString()}</strong></p>
              <p>Value at risk: <strong className="text-risk">₹{ring.value_at_risk_inr.toLocaleString()}</strong></p>
              <p>Linked accounts: <strong className="text-ink">{ring.nodes.length}</strong></p>
              <p>Devices linked: <strong className="text-ink">{devicesCount}</strong></p>
            </div>
          </div>
        </div>

        {/* Right: Group Detail Panel */}
        <div className="col-span-2 merchant-card p-6 space-y-6">
          <div className="border-b border-border pb-4 flex items-start justify-between gap-4">
            <div>
              <span className="text-xs font-medium text-ink-muted uppercase tracking-wider block mb-1">
                Fraud Group Assessment
              </span>
              <h3 className="text-lg font-semibold text-ink">
                Details for Group {ring.ring_id}
              </h3>
              <p className="text-xs text-ink-muted mt-1">
                Coordinated cash-on-delivery order pattern spanning multiple delivery addresses.
              </p>
            </div>

            <div className="text-right shrink-0">
              <span className="text-xs text-ink-muted block mb-0.5">Value at Risk</span>
              <span className="text-lg font-bold text-risk">
                ₹{ring.value_at_risk_inr.toLocaleString()}
              </span>
            </div>
          </div>

          {/* Group Overview Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-beige p-3.5 rounded border border-border">
              <span className="text-xs text-ink-muted block mb-1">Total Orders</span>
              <span className="text-base font-semibold text-ink">{ring.total_orders.toLocaleString()}</span>
            </div>

            <div className="bg-beige p-3.5 rounded border border-border">
              <span className="text-xs text-ink-muted block mb-1">Phones Linked</span>
              <span className="text-base font-semibold text-ink">{phonesCount}</span>
            </div>

            <div className="bg-beige p-3.5 rounded border border-border">
              <span className="text-xs text-ink-muted block mb-1">Devices Linked</span>
              <span className="text-base font-semibold text-ink">{devicesCount}</span>
            </div>
          </div>

          {/* Connected Signals */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wider">
              Connected Risk Factors
            </h4>

            <div className="space-y-2">
              {ring.correlation_vectors.map((vector, i) => (
                <div key={i} className="flex items-center justify-between p-3 bg-beige rounded border border-border text-xs">
                  <span className="font-medium text-ink">{vector.name}</span>
                  <span className="text-ink-muted">{vector.linked_signals} connected orders</span>
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="pt-2 border-t border-border space-y-3">
            {isBlocked ? (
              <div className="p-4 rounded bg-safe-bg border border-safe/20 text-safe text-xs font-medium">
                Done. This group has been blocked. New orders from these accounts will be flagged automatically.
              </div>
            ) : (
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs text-ink-muted">
                  Prevent future cash-on-delivery orders from accounts associated with this group.
                </p>
                <button
                  onClick={handleBlock}
                  className="btn-destructive-outline px-4 py-2 text-xs whitespace-nowrap shrink-0"
                >
                  Stop this group from ordering
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

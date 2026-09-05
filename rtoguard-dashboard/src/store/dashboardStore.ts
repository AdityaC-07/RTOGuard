import { create } from 'zustand';
import { DashboardState, RTOOrderResponse, AbuseRing, DisputeCase } from '../types';

interface DashboardStore extends DashboardState {
  setActiveTab: (tab: any) => void;
  selectOrder: (order: RTOOrderResponse) => void;
  selectRing: (ring: AbuseRing) => void;
  selectDispute: (dispute: DisputeCase) => void;
  updateLiveMetrics: (metrics: any) => void;
}

export const useStore = create<DashboardStore>((set) => ({
  active_tab: 'risk-scorer',
  live_metrics: {
    net_inr_saved: 0,
    cod_intercepts: 0,
    chargeback_win_rate: 0,
    fraud_rings_active: 0,
    order_volume_24h: 0,
    processing_timestamp: new Date().toISOString(),
  },
  last_updated: new Date().toISOString(),

  setActiveTab: (tab) => set({ active_tab: tab }),
  selectOrder: (order) => set({ selected_order: order }),
  selectRing: (ring) => set({ selected_ring: ring }),
  selectDispute: (dispute) => set({ selected_dispute: dispute }),
  updateLiveMetrics: (metrics) => set({
    live_metrics: metrics,
    last_updated: new Date().toISOString(),
  }),
}));

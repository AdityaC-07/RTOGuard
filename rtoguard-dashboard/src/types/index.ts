// ============================================================================
// RTOGuard Enterprise - Complete Type Definitions
// ============================================================================

export enum RTODecision {
  APPROVE = "APPROVE",
  REQUIRE_PREPAID = "REQUIRE_PREPAID",
  FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"
}

export enum SpikeRiskLevel {
  NORMAL = "NORMAL",
  MODERATE = "MODERATE",
  HIGH = "HIGH",
  CRITICAL = "CRITICAL"
}

// ============================================================================
// RETURN-RISK SCORER
// ============================================================================

export interface RiskSignal {
  name: string;
  score: number;
  category: string;
  penalty: number;
}

export interface RTOOrderResponse {
  order_id: string;
  risk_score: number; // 0-100
  decision: RTODecision;
  top_risk_factors: string[];
  estimated_financial_risk_inr: number;
  model_confidence: number; // 0-1
  degraded_mode: boolean;
  processing_time_ms: number;
}

export interface FormBehavior {
  phone_paste: boolean;
  address_paste: boolean;
  form_fill_seconds: number;
  field_sequence: string[];
}

export interface OrderPayload {
  order_id: string;
  phone: string;
  address: string;
  pincode: string;
  order_value: number;
  device_id?: string;
  behavior?: FormBehavior;
}

// ============================================================================
// FRAUD-SPIKE DETECTOR & VELOCITY INTELLIGENCE
// ============================================================================

export interface PincodeCluster {
  pincode: string;
  city: string;
  cluster_name: string;
  baseline_tps: number;
  current_tps: number;
  spike_percentage: number;
  spike_start_time: string;
  spike_duration_minutes: number;
  threat_signature: string;
  critical: boolean;
}

export interface SpikeTrafficDecomposition {
  entity_type: string; // "Phone Pool", "Geo/Pin", "WebGL Bot", "Card BIN", "Virtual SIM"
  cluster_id: string;
  category: string;
  share_percentage: number;
  surge_percentage: number;
  attack_vector: string;
  action: string;
}

export interface VelocityMetric {
  timestamp: string;
  tps_value: number;
  breach_ceiling: number;
  is_breach: boolean;
}

// ============================================================================
// ABUSE-RING SENTINEL (CARE-GNN INSPIRED)
// ============================================================================

export interface RingNode {
  node_id: string;
  node_type: "Phone" | "Device" | "Address" | "Pincode" | "BIN"; // Simplified from full CARE-GNN
  label: string;
  risk_score: number;
  linked_orders: number;
}

export interface RingEdge {
  source_id: string;
  target_id: string;
  relation_type: string;
  weight: number;
  collision_type?: "WebGL" | "Token" | "Geo" | "Concurrence";
}

export interface AbuseRing {
  ring_id: string;
  ring_name: string;
  total_nodes: number;
  total_edges: number;
  total_orders: number;
  risk_score: number; // 0-100
  value_at_risk_inr: number;
  cod_ratio: number; // percentage
  correlation_vectors: CorrelationVector[];
  nodes: RingNode[];
  edges: RingEdge[];
  density: number; // 0-1
  high_cohesion: boolean;
  active_subgraph_id?: string;
  detected_at: string;
}

export interface CorrelationVector {
  name: string;
  linked_signals: number;
  strength: "Low" | "Medium" | "High" | "Critical";
}

// ============================================================================
// CHARGEBACK EVIDENCE RESPONDER
// ============================================================================

export enum DisputeStatus {
  AWAITING_ACTION = "AWAITING_ACTION",
  EVIDENCE_COMPILED = "EVIDENCE_COMPILED",
  IN_DRAFT = "IN_DRAFT",
  AWAITING_GATEWAY_SUBMISSION = "AWAITING_GATEWAY_SUBMISSION",
  SUBMITTED = "SUBMITTED"
}

export interface DisputeCase {
  case_id: string;
  dispute_amount_inr: number;
  acquirer_network: string; // "HDFC Bank Ltd", "ICICI Bank Ltd", "Axis Bank Ltd"
  reason_code: string;
  reason_description: string;
  time_remaining_hours: number;
  status: DisputeStatus;
  pipeline_status: string;
  dossier_action?: string;
}

export interface EvidenceArtifact {
  artifact_id: string;
  artifact_name: string;
  artifact_type: string; // "PDF", "Image", "Hash", "Signature"
  verified: boolean;
  verification_method?: string;
}

export interface ChargebackEvidenceResponse {
  case_id: string;
  gateway_latency_ms: number;
  active_disputes_count: number;
  recovered_mtd_inr: number;
  highest_priority_case: DisputeCase;
  evidence_artifacts: EvidenceArtifact[];
  auto_generate_status: string;
  win_probability: number; // 0-1
}

// ============================================================================
// LIVE METRICS & MONITORING
// ============================================================================

export interface LiveMetrics {
  net_inr_saved: number;
  cod_intercepts: number;
  chargeback_win_rate: number; // percentage
  fraud_rings_active: number;
  order_volume_24h: number;
  processing_timestamp: string;
}

export interface DashboardState {
  selected_order?: RTOOrderResponse;
  selected_ring?: AbuseRing;
  selected_dispute?: DisputeCase;
  active_tab: "risk-scorer" | "spike-detector" | "ring-sentinel" | "chargeback-responder";
  live_metrics: LiveMetrics;
  last_updated: string;
}

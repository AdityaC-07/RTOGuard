import { RTODecision, DisputeStatus } from '../types';

const RISK_FACTOR_COPY: Record<string, string> = {
  pincode_rto_ratio:               "This PIN code has a high history of returned orders.",
  phone_is_ring_prefix:            "This phone number matches patterns seen in repeated returns.",
  is_high_value_suspicious:        "High order value from an address with a returns history.",
  device_multi_address_count:      "This device has placed orders to many different addresses.",
  order_value_vs_pincode_avg_ratio:"Order value is unusually high for this delivery area.",
  char_len:                        "The delivery address is too short to be valid.",
  completeness_score:              "The delivery address looks incomplete.",
  has_house_num:                   "No house or flat number in the address.",
  // Phase 2 history signals arrive as full sentences from the backend;
  // map them to themselves so they render verbatim in the verdict card.
  "This device has been used with many different phone numbers recently.":
    "This device has been used with many different phone numbers recently.",
  "Most orders from this device were previously flagged.":
    "Most orders from this device were previously flagged.",
  "This delivery address has been used in orders we flagged before.":
    "This delivery address has been used in orders we flagged before.",
  "Multiple orders were placed from this device within minutes of each other.":
    "Multiple orders were placed from this device within minutes of each other.",
  "This account placed small, safe-looking orders recently and is now ordering a much higher value — a known fraud pattern.":
    "This account placed small, safe-looking orders recently and is now ordering a much higher value — a known fraud pattern.",
};

export function humanizeRiskFactor(key: string): string {
  // If string contains extra details in parens, strip key or match exact substring
  const rawKey = key.split(' (')[0].trim();
  return RISK_FACTOR_COPY[rawKey] ?? RISK_FACTOR_COPY[key] ?? "Unusual pattern detected in this order.";
}

export function getVerdictDetails(decision: RTODecision): {
  label: string;
  badgeClass: string;
  actionText: string;
} {
  switch (decision) {
    case RTODecision.APPROVE:
      return {
        label: "Safe to ship",
        badgeClass: "bg-navy-subtle text-navy border-navy/20",
        actionText: "You can ship this order.",
      };
    case RTODecision.REQUIRE_PREPAID:
      return {
        label: "Ask for prepayment",
        badgeClass: "bg-caution-bg text-caution border-caution/20",
        actionText: "Contact the customer and request payment before shipping.",
      };
    case RTODecision.FLAG_FOR_REVIEW:
      return {
        label: "Hold this order",
        badgeClass: "bg-risk-bg text-risk border-risk/20",
        actionText: "Do not ship yet. Review the order details or contact support.",
      };
    default:
      return {
        label: "Safe to ship",
        badgeClass: "bg-navy-subtle text-navy border-navy/20",
        actionText: "You can ship this order.",
      };
  }
}

export function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.75) return "High confidence";
  if (confidence >= 0.50) return "Moderate confidence";
  return "Low confidence — use your judgment";
}

export function scoreLabel(score: number): string {
  if (score < 20) return "Very low risk";
  if (score < 40) return "Low risk";
  if (score < 60) return "Moderate risk";
  if (score < 80) return "High risk";
  return "Very high risk";
}

export function scoreColor(score: number): string {
  if (score < 40) return "#1A3C6E"; // safe — navy
  if (score < 70) return "#7A5C00"; // caution — amber
  return "#5C1A1A";                 // risk — dark red
}

export function scoreBg(score: number): string {
  if (score < 40) return "#E8EEF7";
  if (score < 70) return "#FDF5DC";
  return "#FAEAEA";
}

export function factorImpact(key: string): "High" | "Medium" | "Low" {
  const HIGH = ["pincode_rto_ratio", "phone_is_ring_prefix", "is_high_value_suspicious"];
  const MEDIUM = ["device_multi_address_count", "order_value_vs_pincode_avg_ratio"];
  return HIGH.includes(key) ? "High" : MEDIUM.includes(key) ? "Medium" : "Low";
}

export function getDisputeStatusLabel(status: DisputeStatus | string): string {
  switch (status) {
    case DisputeStatus.AWAITING_ACTION:
    case DisputeStatus.IN_DRAFT:
    case 'open':
      return "Needs your response";
    case DisputeStatus.SUBMITTED:
    case DisputeStatus.AWAITING_GATEWAY_SUBMISSION:
    case DisputeStatus.EVIDENCE_COMPILED:
    case 'submitted':
      return "Response sent";
    default:
      return "Resolved";
  }
}

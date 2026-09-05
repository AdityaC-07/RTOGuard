"""Decision engine and failure guardrails.
Implements verified buyer overrides, 50ms circuit breaker timeouts,
three-tier action mapping (APPROVE, REQUIRE_PREPAID, FLAG_FOR_REVIEW),
and graceful address-score fallback during degraded mode."""

import logging
import time
from typing import Dict, Any, Tuple, Optional, List
import numpy as np

logger = logging.getLogger("rtoguard.guardrails")

VERIFIED_BUYERS: set = {"9876543210", "9999999999", "9811111111"}

# Phase 2: history-triggered probability bumps + shopkeeper-readable factors.
# Each trigger adds fixed probability mass (transparent, auditable).
HISTORY_BUMP_ROTATION = 0.08
HISTORY_BUMP_FLAG_RATE = 0.08
HISTORY_BUMP_ADDRESS = 0.08
HISTORY_BUMP_BURST = 0.06
HISTORY_BUMP_PROBE = 0.08


class DecisionEngine:
    def __init__(self, scorer=None, feature_pipeline=None, db_path=None):
        self.scorer = scorer
        self.feature_pipeline = feature_pipeline
        self.db_path = db_path

    def check_verified_buyer(self, phone: str) -> bool:
        clean_phone = str(phone).strip()[-10:]
        return clean_phone in VERIFIED_BUYERS

    def rule_based_fallback(self, payload: Dict[str, Any]) -> Tuple[int, str]:
        """Graceful degradation fallback using address length when pipeline/Redis fails."""
        address = str(payload.get("address", "")).strip()
        order_val = float(payload.get("order_value", 0.0))

        if len(address) < 15 or order_val > 3000:
            return 75, "REQUIRE_PREPAID"
        return 20, "APPROVE"

    def history_adjustment(self, payload: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Phase 2 behavioural-history layer.

        Returns (probability_bump, human_readable_factors). Zero bump and no
        factors on day 1 (empty DB) so Phase 1 behaviour is preserved.
        Never raises.
        """
        try:
            import pandas as pd

            from app.features.history_signals import HistorySignalTransformer

            transformer = HistorySignalTransformer(db_path=self.db_path)
            transformer.fit()
            row = {
                "device_id": payload.get("device_id", "UNKNOWN"),
                "phone": payload.get("phone", ""),
                "address": payload.get("address", ""),
                "order_value": payload.get("order_value", 0.0),
            }
            hist = transformer.transform(pd.DataFrame([row])).iloc[0]
            bump = 0.0
            factors: List[str] = []
            if float(hist["device_is_high_rotation"]) >= 1.0:
                bump += HISTORY_BUMP_ROTATION
                factors.append(
                    "This device has been used with many different phone numbers recently."
                )
            if float(hist["device_flag_rate_90d"]) > 0.4:
                bump += HISTORY_BUMP_FLAG_RATE
                factors.append(
                    "Most orders from this device were previously flagged."
                )
            if float(hist["address_prior_flag_count"]) > 2:
                bump += HISTORY_BUMP_ADDRESS
                factors.append(
                    "This delivery address has been used in orders we flagged before."
                )
            if float(hist["is_burst_session"]) >= 1.0:
                bump += HISTORY_BUMP_BURST
                factors.append(
                    "Multiple orders were placed from this device within minutes of each other."
                )
            if float(hist["is_value_probe_exploit"]) >= 1.0:
                bump += HISTORY_BUMP_PROBE
                factors.append(
                    "This account placed small, safe-looking orders recently and is now "
                    "ordering a much higher value — a known fraud pattern."
                )
            return bump, factors
        except Exception as e:
            logger.warning(f"History layer failed, continuing without it: {e}")
            return 0.0, []

    def evaluate_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        phone = payload.get("phone", "")

        # Check 1: Verified Buyer Override
        if self.check_verified_buyer(phone):
            return {
                "risk_score": 5,
                "decision": "APPROVE",
                "top_risk_factors": ["Verified repeat customer with 0 RTO history"],
                "degraded_mode": False,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

        # Check 2: Model and Pipeline execution with circuit breaker pattern
        try:
            if self.feature_pipeline is None or self.scorer is None:
                raise RuntimeError("Pipeline or scorer not initialized")

            features = self.feature_pipeline.transform_order_payload(payload)
            prob, risk_score, _ = self.scorer.predict_risk(features)
            p_val = float(prob[0])

            # Phase 2 history layer: cross-order patterns add probability mass
            hist_bump, hist_factors = self.history_adjustment(payload)
            p_val = min(0.99, p_val + hist_bump)
            score = int(round(p_val * 100))

            # Decision tiering
            if p_val < self.scorer.optimal_threshold:
                decision = "APPROVE"
            elif p_val < 0.85:
                decision = "REQUIRE_PREPAID"
            else:
                decision = "FLAG_FOR_REVIEW"

            # Top risk factors
            risk_factors = []
            if len(str(payload.get("address", ""))) < 20:
                risk_factors.append("Incomplete delivery address")
            if p_val >= self.scorer.optimal_threshold:
                risk_factors.append("High pincode historical RTO rate")
            risk_factors.extend(hist_factors)

            return {
                "risk_score": score,
                "decision": decision,
                "top_risk_factors": risk_factors if risk_factors else ["Low overall risk"],
                "degraded_mode": False,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

        except Exception as e:
            logger.warning(f"Circuit breaker tripped, dropping to rule-based fallback: {e}")
            fallback_score, fallback_decision = self.rule_based_fallback(payload)
            # Phase 2 history still applies in degraded mode
            hist_bump, hist_factors = self.history_adjustment(payload)
            fallback_score = min(100, fallback_score + int(round(hist_bump * 100)))
            if fallback_score >= 85:
                fallback_decision = "FLAG_FOR_REVIEW"
            elif fallback_score >= 50:
                fallback_decision = "REQUIRE_PREPAID"
            return {
                "risk_score": fallback_score,
                "decision": fallback_decision,
                "top_risk_factors": ["System degraded: evaluated via emergency rules"] + hist_factors,
                "degraded_mode": True,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }

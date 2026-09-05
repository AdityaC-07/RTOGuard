"""FastAPI REST API endpoint routes with zero-exception guarantee."""

import json
import logging
import os
import pickle

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.schemas import RTORequest, RTOResponse, DecisionEnum
from app.api.extended import router as extended_router
from app.api.confirm import router as confirm_router
from app.api.verification import router as verification_router
from app.core.guardrails import DecisionEngine

logger = logging.getLogger("rtoguard.routes")

_MODEL_PATH = os.environ.get("RTOGUARD_MODEL_PATH", "data/model.pkl")


def _load_model_bundle():
    if not os.path.exists(_MODEL_PATH):
        return None
    try:
        with open(_MODEL_PATH, "rb") as handle:
            bundle = pickle.load(handle)
        logger.info(
            "[RTOGuard] Loaded model from %s (dim=%s, threshold=%.2f)",
            _MODEL_PATH, bundle.get("feature_dim"), bundle.get("threshold", 0.5),
        )
        return bundle
    except Exception as exc:
        logger.warning("[RTOGuard] model.pkl load failed (%s), using rule fallback", exc)
        return None


_MODEL_BUNDLE = _load_model_bundle()

app = FastAPI(
    title="RTOGuard API",
    description="Pre-Checkout Return & RTO Risk Scorer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global DecisionEngine instance
decision_engine = DecisionEngine()

# Live operational endpoints (spike / rings / disputes / threshold sweep)
app.include_router(extended_router)

# Phase 2 ground-truth confirmations
app.include_router(confirm_router)
app.include_router(verification_router)


def _persist_scored_order(payload: RTORequest, result: dict, ip_address: str = "") -> None:
    """Write-through of every scored order into the history store.

    Best-effort: storage failures are logged and never fail the request.
    """
    try:
        from app.db import queries
        from app.db.connection import insert_order

        behavior = payload.model_dump().get("behavior")
        insert_order(
            {
                "order_id": payload.order_id,
                "device_id": queries.resolve_device_key(
                    payload.device_id, payload.phone
                ),
                "phone": payload.phone,
                "pincode": payload.pincode,
                "address_token": queries.canonicalise_address(payload.address),
                "order_value": payload.order_value,
                "risk_score": result.get("risk_score", 0),
                "decision": result.get("decision", "APPROVE"),
                "behavior_json": json.dumps(behavior) if behavior else None,
                "ip_address": ip_address,
            }
        )
    except Exception as e:
        logger.warning(f"Order write-through failed: {e}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/v1/score/rto", response_model=RTOResponse)
async def score_rto_endpoint(payload: RTORequest, request: Request):
    try:
        data = payload.model_dump()
        client_ip = request.client.host if request.client else ""
        data["ip_address"] = client_ip
        if decision_engine.check_verified_buyer(payload.phone):
            result = decision_engine.evaluate_order(data)
        elif _MODEL_BUNDLE is not None:
            bundle = _MODEL_BUNDLE
            features = bundle["pipeline"].transform_order_payload(data, ip=client_ip)
            probability = float(bundle["ensemble"].predict(
                features[:, bundle["addr_slice"]],
                features[:, bundle["identity_slice"]],
                features[:, bundle["network_slice"]],
            )[0])
            threshold = float(bundle["threshold"])
            decision = (
                "APPROVE" if probability < threshold
                else "REQUIRE_PREPAID" if probability < 0.85
                else "FLAG_FOR_REVIEW"
            )
            result = {
                "risk_score": int(round(probability * 100)),
                "decision": decision,
                "top_risk_factors": ["Model ensemble assessment"],
                "degraded_mode": False,
                "latency_ms": 0.0,
            }
        else:
            result = decision_engine.evaluate_order(data)
        _persist_scored_order(payload, result, data["ip_address"])

        # Calculate estimated financial risk in INR
        est_risk = round((result["risk_score"] / 100.0) * 1200.0, 2)

        return RTOResponse(
            order_id=payload.order_id,
            risk_score=result["risk_score"],
            decision=DecisionEnum(result["decision"]),
            top_risk_factors=result["top_risk_factors"],
            estimated_financial_risk_inr=est_risk,
            degraded_mode=result["degraded_mode"],
            latency_ms=result["latency_ms"],
            model_confidence=round(result["risk_score"] / 100.0, 4),
            processing_time_ms=result["latency_ms"],
            otp_verified=False,
        )
    except Exception as e:
        # Ultimate fallback guarantee — never throw 500
        return RTOResponse(
            order_id=payload.order_id,
            risk_score=20,
            decision=DecisionEnum.APPROVE,
            top_risk_factors=["Global exception fallback triggered"],
            estimated_financial_risk_inr=240.0,
            degraded_mode=True,
            latency_ms=0.0,
            model_confidence=0.2,
            processing_time_ms=0.0
        )

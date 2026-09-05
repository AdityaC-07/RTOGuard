"""FastAPI REST API endpoint routes with zero-exception guarantee."""

import json
import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.schemas import RTORequest, RTOResponse, DecisionEnum
from app.api.extended import router as extended_router
from app.api.confirm import router as confirm_router
from app.core.guardrails import DecisionEngine

logger = logging.getLogger("rtoguard.routes")

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


def _persist_scored_order(payload: RTORequest, result: dict) -> None:
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
            }
        )
    except Exception as e:
        logger.warning(f"Order write-through failed: {e}")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/v1/score/rto", response_model=RTOResponse)
async def score_rto_endpoint(payload: RTORequest):
    try:
        data = payload.model_dump()
        result = decision_engine.evaluate_order(data)
        _persist_scored_order(payload, result)

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
            processing_time_ms=result["latency_ms"]
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

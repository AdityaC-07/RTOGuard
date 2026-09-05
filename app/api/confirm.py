"""Phase 2 RTO confirmation endpoint.

POST /v1/confirm-rto marks a previously scored order as a confirmed return,
so the device/address history layer learns from ground truth instead of
only from the model's own flags.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import queries
from app.db.connection import update_confirmation

logger = logging.getLogger("rtoguard.confirm")

router = APIRouter()


class ConfirmRTORequest(BaseModel):
    order_id: str
    confirmed: bool = True


@router.post("/v1/confirm-rto")
async def confirm_rto(payload: ConfirmRTORequest) -> Dict[str, Any]:
    try:
        row = update_confirmation(payload.order_id, payload.confirmed)
        if row is None:
            return {
                "order_id": payload.order_id,
                "confirmed": False,
                "message": "Order not found in history store",
            }
        flag_rate = 0.0
        try:
            hist = queries.device_history_features(
                row.get("device_id", ""), row.get("phone", "")
            )
            flag_rate = float(hist.get("device_flag_rate_90d", 0.0))
        except Exception:
            pass
        return {
            "order_id": payload.order_id,
            "confirmed": bool(payload.confirmed),
            "device_flag_rate_90d": round(flag_rate, 4),
            "message": "Order marked as confirmed RTO"
            if payload.confirmed
            else "Confirmation cleared",
        }
    except Exception as e:
        logger.warning(f"confirm-rto failed: {e}")
        return {
            "order_id": payload.order_id,
            "confirmed": False,
            "message": "Confirmation store unavailable",
        }

"""Development OTP flow for high-risk COD orders."""

import secrets
import time
from typing import Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
OTP_STORE: Dict[str, Dict[str, object]] = {}
CONSUMED_OTPS: set[str] = set()


class OTPRequest(BaseModel):
    phone: str


class OTPConfirmRequest(BaseModel):
    phone: str
    otp: str


@router.post("/v1/verify/send-otp")
async def send_otp(payload: OTPRequest):
    otp = str(secrets.randbelow(9000) + 1000)
    OTP_STORE[payload.phone] = {"otp": otp, "expires": time.time() + 300}
    return {"sent": True, "dev_otp": otp}


@router.post("/v1/verify/confirm-otp")
async def confirm_otp(payload: OTPConfirmRequest):
    replay_key = f"{payload.phone}:{payload.otp}"
    if replay_key in CONSUMED_OTPS:
        return {
            "verified": False,
            "reason": "consumed",
            "detail": "This code was already used.",
        }
    record = OTP_STORE.get(payload.phone)
    if not record or time.time() > float(record["expires"]):
        return {
            "verified": False,
            "reason": "expired",
            "detail": "No active code for this number. Request a new one.",
        }
    if not secrets.compare_digest(str(record["otp"]), payload.otp):
        return {
            "verified": False,
            "reason": "wrong",
            "detail": "Incorrect code. Please try again.",
        }
    OTP_STORE.pop(payload.phone, None)
    CONSUMED_OTPS.add(replay_key)
    if len(CONSUMED_OTPS) > 10_000:
        CONSUMED_OTPS.clear()
    return {"verified": True}
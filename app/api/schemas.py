"""Pydantic v2 schemas for RTOGuard REST API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class DecisionEnum(str, Enum):
    APPROVE = "APPROVE"
    REQUIRE_PREPAID = "REQUIRE_PREPAID"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW"


class FormBehavior(BaseModel):
    """Phase 2 behavioural biometrics captured on the checkout form.
    All fields optional — older clients simply omit the block."""

    phone_paste: bool = False
    address_paste: bool = False
    form_fill_seconds: float = 0.0
    field_sequence: List[str] = []


class RTORequest(BaseModel):
    order_id: str = Field(..., example="ORD_000123")
    phone: str = Field(..., min_length=10, max_length=16, example="9876543210")
    address: str = Field(..., example="Flat 4B, Sunrise Apt, Koramangala")
    pincode: str = Field(..., min_length=6, max_length=6, example="560001")
    order_value: float = Field(..., gt=0, example=1499.00)
    device_id: Optional[str] = Field(default="UNKNOWN", example="DEV_8F9A12")
    behavior: Optional[FormBehavior] = None

    model_config = {"extra": "ignore"}


class RTOResponse(BaseModel):
    order_id: str
    risk_score: int = Field(..., ge=0, le=100)
    decision: DecisionEnum
    top_risk_factors: List[str]
    estimated_financial_risk_inr: float
    degraded_mode: bool
    latency_ms: float
    # Aliases expected by rtoguard-dashboard (RTOOrderResponse)
    model_confidence: float = 0.0
    processing_time_ms: float = 0.0
    otp_verified: bool = False

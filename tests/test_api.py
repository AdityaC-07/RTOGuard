"""API tests for POST /v1/score/rto with zero-500 guarantee."""

from fastapi.testclient import TestClient

from app.api.routes import app

client = TestClient(app)


def _valid_payload(**overrides):
    payload = {
        "order_id": "ORD_000123",
        "phone": "9000000001",
        "address": "Flat 4B, Sunrise Apt, Koramangala, Bangalore",
        "pincode": "560001",
        "order_value": 1499.0,
        "device_id": "DEV_TEST01",
    }
    payload.update(overrides)
    return payload


def test_score_valid_payload_schema():
    resp = client.post("/v1/score/rto", json=_valid_payload())
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "order_id",
        "risk_score",
        "decision",
        "top_risk_factors",
        "estimated_financial_risk_inr",
        "degraded_mode",
        "latency_ms",
    ):
        assert key in body
    assert 0 <= body["risk_score"] <= 100
    assert body["decision"] in ("APPROVE", "REQUIRE_PREPAID", "FLAG_FOR_REVIEW")


def test_verified_buyer_instant_approve():
    resp = client.post("/v1/score/rto", json=_valid_payload(phone="9876543210"))
    assert resp.status_code == 200
    body = resp.json()
    assert body["decision"] == "APPROVE"
    assert body["risk_score"] <= 10


def test_incomplete_payload_422():
    # Missing required pincode -> Pydantic validation error, backend stays alive
    payload = _valid_payload()
    del payload["pincode"]
    resp = client.post("/v1/score/rto", json=payload)
    assert resp.status_code == 422
    # Backend still healthy afterwards
    resp2 = client.post("/v1/score/rto", json=_valid_payload())
    assert resp2.status_code == 200

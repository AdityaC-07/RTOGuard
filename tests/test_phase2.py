"""Phase 2 tests: history store, canonicalisation, confirmations, score lift."""

import numpy as np
import pandas as pd

from app.core.guardrails import DecisionEngine
from app.db import queries
from app.db.connection import init_db, insert_order, update_confirmation
from app.features.history_signals import HistorySignalTransformer


def _use_tmp_db(monkeypatch, tmp_path):
    monkeypatch.setenv("RTOGUARD_DB_PATH", str(tmp_path / "orders.db"))
    init_db()


def test_canonicalise_groups_variants():
    a = queries.canonicalise_address("Plot 14, MG Road")
    b = queries.canonicalise_address("14, M.G. Road")
    assert "14 mg road" in a
    assert "14 mg road" in b
    assert queries.canonicalise_address("") == ""
    assert queries.canonicalise_address(None) == ""


def test_empty_db_returns_zeros(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    t = HistorySignalTransformer()
    t.fit(None)
    out = t.transform(pd.DataFrame([{
        "device_id": "DEV_NEW", "phone": "9000000001",
        "address": "Some Fresh Address", "order_value": 1500.0,
    }]))
    assert out.shape == (1, 11)
    assert (out.values == 0.0).all()


def _seed_flagged_device(dev="DEV_RINGTEST", n_phones=6):
    for i in range(n_phones):
        insert_order({
            "order_id": f"ORD_SEED_{i}",
            "device_id": dev,
            "phone": f"90000000{i:02d}",
            "pincode": "110001",
            "address_token": queries.canonicalise_address("Plot 14 MG Road"),
            "order_value": 1200.0,
            "risk_score": 90,
            "decision": "FLAG_FOR_REVIEW",
        })


def test_history_repeated_device_scores_higher(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    engine = DecisionEngine()
    payload = {
        "order_id": "ORD_FRESH",
        "phone": "9000000099",
        "address": "Flat 9C, Long Complete Address, Koramangala, Bangalore",
        "pincode": "560034",
        "order_value": 1500.0,
        "device_id": "DEV_HISTORY_X",
    }
    fresh = engine.evaluate_order(dict(payload))
    _seed_flagged_device(dev="DEV_HISTORY_X")
    repeat = engine.evaluate_order(dict(payload, order_id="ORD_REPEAT"))
    assert repeat["risk_score"] > fresh["risk_score"]
    assert any("phone numbers" in f for f in repeat["top_risk_factors"])


def test_confirm_rto_raises_flag_rate(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    insert_order({
        "order_id": "ORD_CONF1", "device_id": "DEV_CONF", "phone": "9111111111",
        "pincode": "560001",
        "address_token": queries.canonicalise_address("Flat 1 Test Address"),
        "order_value": 900.0, "risk_score": 30, "decision": "APPROVE",
    })
    before = queries.device_history_features("DEV_CONF", "9111111111")
    assert before["device_flag_rate_90d"] == 0.0
    row = update_confirmation("ORD_CONF1", True)
    assert row is not None
    after = queries.device_history_features("DEV_CONF", "9111111111")
    assert after["device_flag_rate_90d"] == 1.0


def test_burst_and_probe_signals(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    for i in range(2):
        insert_order({
            "order_id": f"ORD_BURST_{i}", "device_id": "DEV_BURST",
            "phone": "9222222222", "pincode": "560001",
            "address_token": queries.canonicalise_address("Burst Address Lane"),
            "order_value": 700.0, "risk_score": 20, "decision": "APPROVE",
        })
    burst = queries.session_burst_features("DEV_BURST", "9222222222")
    assert burst["is_burst_session"] == 1.0

    for i in range(3):
        insert_order({
            "order_id": f"ORD_PROBE_{i}", "device_id": "DEV_PROBE",
            "phone": "9333333333", "pincode": "560001",
            "address_token": queries.canonicalise_address("Probe Address Lane"),
            "order_value": 500.0, "risk_score": 20, "decision": "APPROVE",
        })
    traj = queries.value_trajectory_features("DEV_PROBE", 2500.0, "9333333333")
    assert traj["is_value_probe_exploit"] == 1.0


def test_api_write_through_persists_order(monkeypatch, tmp_path):
    _use_tmp_db(monkeypatch, tmp_path)
    from fastapi.testclient import TestClient

    from app.api.routes import app

    client = TestClient(app)
    resp = client.post("/v1/score/rto", json={
        "order_id": "ORD_WRITE1", "phone": "9444444444",
        "address": "Flat 2 Write Through Address, Bangalore",
        "pincode": "560001", "order_value": 1200.0,
        "device_id": "DEV_WRITE",
    })
    assert resp.status_code == 200
    hist = queries.device_history_features("DEV_WRITE", "9444444444")
    assert hist["device_total_orders_90d"] == 1.0

    resp = client.post("/v1/confirm-rto", json={"order_id": "ORD_WRITE1", "confirmed": True})
    assert resp.status_code == 200
    assert resp.json()["confirmed"] is True

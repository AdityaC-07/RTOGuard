"""Tests for address, ring-signal, and pipeline feature transformers."""

import numpy as np
import pandas as pd

from app.features.address import AddressCompletenessTransformer
from app.features.ring_signals import RingSignalTransformer
from app.features.pipeline import FeaturePipeline


def test_address_valid_empty_none():
    t = AddressCompletenessTransformer()
    t.fit(None)
    df = pd.DataFrame({
        "address": [
            "Flat 4B, 2nd Floor, Sunrise Apt, Near City Mall, Koramangala",
            "",
            None,
        ]
    })
    out = t.transform(df)
    assert list(out.columns) == t.feature_names_out_
    assert out.shape == (3, 6)
    # Valid address should score higher than empty/None
    assert out.iloc[0]["addr_char_len"] > 0
    assert out.iloc[0]["addr_completeness_score"] > 0
    # Empty and None degrade gracefully to zeros
    assert (out.iloc[1].values == 0.0).all()
    assert (out.iloc[2].values == 0.0).all()
    assert out.dtypes.apply(lambda d: d == np.float64).all()


def test_ring_signal_shape_and_defaults():
    t = RingSignalTransformer()
    t.fit(None)
    df = pd.DataFrame({
        "pincode": ["110001", "400001"],
        "address": ["test addr one", "test addr two"],
        "device_id": ["DEV_A", "DEV_B"],
        "order_value": [1000.0, 2000.0],
    })
    out = t.transform(df)
    assert out.shape == (2, 5)
    assert list(out.columns) == t.feature_names_out_
    # No historical stats -> neutral prior
    assert (out["pincode_rto_historical_ratio"] == 0.28).all()

    # Missing columns / NaNs must degrade gracefully, never raise
    df_bad = pd.DataFrame({
        "pincode": [None, "110001"],
        "address": [None, ""],
        "device_id": [None, "DEV_X"],
        "order_value": [None, 500.0],
    })
    out_bad = t.transform(df_bad)
    assert out_bad.shape == (2, 5)
    assert np.isfinite(out_bad.values.astype(float)).all()


def test_pipeline_single_payload():
    p = FeaturePipeline()
    p.fit(pd.DataFrame({
        "address": ["Flat 4B test"],
        "pincode": ["110001"],
        "device_id": ["DEV1"],
        "order_value": [1500.0],
        "phone": ["9876543210"],
    }))
    payload = {
        "address": "Flat 4B, Sunrise Apt",
        "pincode": "110001",
        "device_id": "DEV1",
        "order_value": 1500.0,
        "phone": "9876543210",
    }
    result = p.transform_order_payload(payload)
    assert result.shape == (1, 47)
    assert np.isfinite(result).all()
    assert len(p.feature_names_) == 47

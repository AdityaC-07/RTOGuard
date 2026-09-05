"""CARE-GNN inspired ring signal feature extractor.
Instead of a full graph neural network, this transformer computes
graph-structural camouflage signals as tabular features.
Concept: fraudsters form rings by sharing pincodes, device IDs,
and address tokens — we measure the density of these shared
attributes as fraud signals."""

import hashlib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Dict, Optional
from collections import defaultdict

GLOBAL_RTO_PRIOR: float = 0.28
DEFAULT_PINCODE_RISK: float = 0.28
HIGH_RISK_ORDER_VALUE_THRESHOLD: float = 1500.0


class RingSignalTransformer(BaseEstimator, TransformerMixin):
    def __init__(self,
        pincode_rto_map: Optional[Dict[str, float]] = None,
        historical_orders: Optional[pd.DataFrame] = None):
        self.pincode_rto_map = pincode_rto_map or {}
        self.historical_orders = historical_orders
        self.feature_names_out_ = []
        self._pincode_stats = {}

    def fit(self, X, y=None) -> "RingSignalTransformer":
        self.feature_names_out_ = [
            "pincode_rto_historical_ratio",
            "pincode_addr_phone_count",
            "device_multi_address_count",
            "order_value_vs_pincode_avg_ratio",
            "is_high_value_suspicious"
        ]

        # If historical orders provided, compute stats
        if self.historical_orders is not None and len(self.historical_orders) > 0:
            for pincode in self.historical_orders['pincode'].unique():
                subset = self.historical_orders[self.historical_orders['pincode'] == pincode]
                self._pincode_stats[pincode] = {
                    "rto_rate": subset['is_rto'].mean() if 'is_rto' in subset.columns else GLOBAL_RTO_PRIOR,
                    "avg_order_value": subset['order_value'].mean() if 'order_value' in subset.columns else 1000.0
                }

        return self

    def _hash_address(self, address: str) -> str:
        if address is None:
            address = ""
        address_str = str(address).strip().lower()
        return hashlib.md5(address_str.encode()).hexdigest()[:8]

    def _get_pincode_rto(self, pincode: str) -> float:
        if pincode in self.pincode_rto_map:
            return float(self.pincode_rto_map[pincode])
        if pincode in self._pincode_stats:
            return float(self._pincode_stats[pincode]["rto_rate"])
        return GLOBAL_RTO_PRIOR

    def _compute_ring_features(self, df: pd.DataFrame) -> pd.DataFrame:
        n = len(df)

        # Feature 1: pincode_rto_historical_ratio
        feature_1 = np.array([self._get_pincode_rto(str(p)) for p in df['pincode']], dtype=np.float64)

        # Feature 2: pincode_addr_phone_count
        composite_keys = df['pincode'].astype(str) + "|" + df['address'].apply(self._hash_address)
        composite_counts = composite_keys.value_counts().to_dict()
        feature_2 = np.array([np.log1p(composite_counts.get(k, 1)) for k in composite_keys], dtype=np.float64)

        # Feature 3: device_multi_address_count
        device_addresses = {}
        for i, (device, addr) in enumerate(zip(df['device_id'], df['address'])):
            device_str = str(device)
            addr_hash = self._hash_address(addr)
            if device_str not in device_addresses:
                device_addresses[device_str] = set()
            device_addresses[device_str].add(addr_hash)
        feature_3 = np.array([np.log1p(len(device_addresses.get(str(d), {1}))) for d in df['device_id']], dtype=np.float64)

        # Feature 4: order_value_vs_pincode_avg_ratio
        feature_4 = np.zeros(n, dtype=np.float64)
        for i, (ov, pincode) in enumerate(zip(df['order_value'], df['pincode'])):
            pincode_str = str(pincode)
            if pincode_str in self._pincode_stats:
                avg = self._pincode_stats[pincode_str].get("avg_order_value", 1000.0)
                ratio = float(ov) / avg if avg > 0 else 1.0
                feature_4[i] = np.clip(ratio, 0.1, 10.0)
            else:
                feature_4[i] = 1.0

        # Feature 5: is_high_value_suspicious
        feature_5 = np.zeros(n, dtype=np.float64)
        for i, (ov, pincode) in enumerate(zip(df['order_value'], df['pincode'])):
            if float(ov) > HIGH_RISK_ORDER_VALUE_THRESHOLD and self._get_pincode_rto(str(pincode)) > 0.35:
                feature_5[i] = 1.0

        return pd.DataFrame({
            "pincode_rto_historical_ratio": feature_1,
            "pincode_addr_phone_count": feature_2,
            "device_multi_address_count": feature_3,
            "order_value_vs_pincode_avg_ratio": feature_4,
            "is_high_value_suspicious": feature_5
        })

    def transform(self, X, y=None) -> pd.DataFrame:
        # Fill missing values (graceful defaults for missing/malformed data)
        if isinstance(X, pd.DataFrame):
            X = X.copy()
            defaults = {
                'pincode': '000000',
                'address': '',
                'phone': '0000000000',
                'device_id': 'UNKNOWN',
                'order_value': 0.0,
            }
            for col, default in defaults.items():
                if col not in X.columns:
                    X[col] = default
                else:
                    try:
                        X[col] = X[col].fillna(default)
                    except Exception:
                        X[col] = default
        else:
            return pd.DataFrame(np.zeros((X.shape[0], 5), dtype=np.float64))

        return self._compute_ring_features(X).astype(np.float64)

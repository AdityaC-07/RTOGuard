"""Phase 2 behavioural-history transformer (sklearn-compatible).

Wraps app.db.queries into the same BaseEstimator/TransformerMixin interface
as the Phase 1 transformers. Emits 11 cross-order features; all zeros when
there is no history (day-1 cold start) or the DB is unreachable.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Any, Dict, List, Optional

from app.db import queries

HISTORY_FEATURE_NAMES: List[str] = [
    "device_unique_phones_90d",
    "device_total_orders_90d",
    "device_flag_rate_90d",
    "device_is_high_rotation",
    "address_seen_before",
    "address_prior_flag_count",
    "address_flag_rate",
    "orders_last_10min",
    "is_burst_session",
    "value_spike_vs_history",
    "is_value_probe_exploit",
]


class HistorySignalTransformer(BaseEstimator, TransformerMixin):
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.feature_names_out_: List[str] = []

    def fit(self, X: Any = None, y: Any = None) -> "HistorySignalTransformer":
        self.feature_names_out_ = list(HISTORY_FEATURE_NAMES)
        return self

    def _extract_single(self, row: Dict[str, Any]) -> List[float]:
        try:
            device_id = row.get("device_id", "UNKNOWN")
            phone = row.get("phone", "")
            address = row.get("address", "")
            try:
                order_value = float(row.get("order_value", 0.0) or 0.0)
            except Exception:
                order_value = 0.0

            dev = queries.device_history_features(device_id, phone, self.db_path)
            addr = queries.address_cluster_score(address, self.db_path)
            burst = queries.session_burst_features(device_id, phone, self.db_path)
            traj = queries.value_trajectory_features(
                device_id, order_value, phone, self.db_path
            )
            return [
                float(dev["device_unique_phones_90d"]),
                float(dev["device_total_orders_90d"]),
                float(dev["device_flag_rate_90d"]),
                float(dev["device_is_high_rotation"]),
                float(addr["address_seen_before"]),
                float(addr["address_prior_flag_count"]),
                float(addr["address_flag_rate"]),
                float(burst["orders_last_10min"]),
                float(burst["is_burst_session"]),
                float(traj["value_spike_vs_history"]),
                float(traj["is_value_probe_exploit"]),
            ]
        except Exception:
            return [0.0] * len(HISTORY_FEATURE_NAMES)

    def transform(self, X: Any, y: Any = None) -> pd.DataFrame:
        if not self.feature_names_out_:
            self.fit()
        try:
            if isinstance(X, pd.DataFrame):
                records = X.to_dict(orient="records")
            elif isinstance(X, dict):
                records = [X]
            else:
                records = list(X)
        except Exception:
            n = 0
            try:
                n = len(X)
            except Exception:
                n = 1
            return pd.DataFrame(
                np.zeros((n, len(HISTORY_FEATURE_NAMES))),
                columns=self.feature_names_out_,
            ).astype(np.float64)
        features = [self._extract_single(r) for r in records]
        return pd.DataFrame(features, columns=self.feature_names_out_).astype(
            np.float64
        )

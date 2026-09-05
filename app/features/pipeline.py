"""Unified feature pipeline combining address completeness,
ring signal, and behavioural-history transformers. Exposes a single
transform_order_payload method for real-time single-order inference
in the API layer."""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from app.features.address import AddressCompletenessTransformer
from app.features.ring_signals import RingSignalTransformer
from app.features.history_signals import HistorySignalTransformer


class FeaturePipeline:
    def __init__(self,
        pincode_rto_map: Optional[Dict[str, float]] = None,
        historical_orders: Optional[pd.DataFrame] = None,
        db_path: Optional[str] = None,
        include_history: bool = True):
        self.address_transformer = AddressCompletenessTransformer()
        self.ring_transformer = RingSignalTransformer(
            pincode_rto_map=pincode_rto_map,
            historical_orders=historical_orders
        )
        self.history_transformer = HistorySignalTransformer(db_path=db_path)
        self.include_history = include_history
        self.db_path = db_path
        self.is_fitted = False
        self.feature_names_ = []

    def fit(self, X: pd.DataFrame, y=None) -> "FeaturePipeline":
        self.address_transformer.fit(X)
        self.ring_transformer.fit(X)
        self.history_transformer.fit(X)
        self.feature_names_ = (
            list(self.address_transformer.feature_names_out_) +
            list(self.ring_transformer.feature_names_out_) +
            (list(self.history_transformer.feature_names_out_) if self.include_history else [])
        )
        self.is_fitted = True
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        addr_features = self.address_transformer.transform(X)
        ring_features = self.ring_transformer.transform(X)
        if self.include_history:
            hist_features = self.history_transformer.transform(X)
            combined = pd.concat([addr_features, ring_features, hist_features], axis=1)
        else:
            combined = pd.concat([addr_features, ring_features], axis=1)
        return combined.values.astype(np.float64)

    def transform_order_payload(self,
        payload: Dict[str, Any]) -> np.ndarray:
        try:
            # Convert dict to single-row DataFrame
            df = pd.DataFrame([payload])
            result = self.transform(df)
            return result.astype(np.float64)
        except Exception as e:
            # Safe degradation: return zeros (dim follows fitted pipeline)
            print(f"Warning: Feature extraction failed: {e}")
            dim = len(self.feature_names_) if self.feature_names_ else 22
            return np.zeros((1, dim), dtype=np.float64)

    def get_feature_importance_map(self,
        feature_importances: np.ndarray) -> Dict[str, float]:
        importance_dict = dict(zip(self.feature_names_, feature_importances))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

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
from app.features.ip_signals import IP_FEATURE_NAMES, ip_features
from app.features.phone_signals import PHONE_FEATURE_NAMES, phone_features
from app.features.time_signals import TIME_FEATURE_NAMES, time_features
from app.features.address_intelligence import ADDRESS_INTELLIGENCE_FEATURE_NAMES, address_intelligence_features


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
            + list(ADDRESS_INTELLIGENCE_FEATURE_NAMES) + list(PHONE_FEATURE_NAMES)
            + list(IP_FEATURE_NAMES) + list(TIME_FEATURE_NAMES)
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
        enriched = []
        for row in X.to_dict(orient="records"):
            enriched.append(
                list(address_intelligence_features(row.get("address", "")).values())
                + list(phone_features(row.get("phone", "")).values())
                + list(ip_features(row.get("ip_address", ""), self.db_path).values())
                + list(time_features().values())
            )
        enrichment = pd.DataFrame(enriched, columns=(
            ADDRESS_INTELLIGENCE_FEATURE_NAMES + PHONE_FEATURE_NAMES
            + IP_FEATURE_NAMES + TIME_FEATURE_NAMES
        ), index=combined.index)
        combined = pd.concat([combined, enrichment], axis=1)
        return combined.values.astype(np.float64)

    def fit_transform(self, X: pd.DataFrame, y=None) -> np.ndarray:
        self.fit(X, y)
        return self.transform(X)

    def transform_order_payload(self, payload: Dict[str, Any], ip: str = "") -> np.ndarray:
        try:
            # Convert dict to single-row DataFrame
            row = dict(payload)
            if ip:
                row["ip_address"] = ip
            df = pd.DataFrame([row])
            result = self.transform(df)
            return result.astype(np.float64)
        except Exception as e:
            # Safe degradation: return zeros (dim follows fitted pipeline)
            print(f"Warning: Feature extraction failed: {e}")
            dim = len(self.feature_names_) if self.feature_names_ else 47
            return np.zeros((1, dim), dtype=np.float64)

    def get_feature_importance_map(self,
        feature_importances: np.ndarray) -> Dict[str, float]:
        importance_dict = dict(zip(self.feature_names_, feature_importances))
        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))

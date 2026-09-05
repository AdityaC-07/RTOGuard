"""Three-branch stacked RTO risk model."""

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.models.scorer import RTOScorer


class RTOEnsemble:
    def __init__(self, model_params=None):
        self.addr_scorer = RTOScorer(model_params)
        self.identity_scorer = RTOScorer(model_params)
        self.network_scorer = RTOScorer(model_params)
        self.meta = LogisticRegression(C=1.0, random_state=42)
        self.is_trained = False

    def fit(self, X_addr, X_identity, X_network, y, X_addr_val, X_identity_val, X_network_val, y_val):
        self.addr_scorer.fit(X_addr, y, X_addr_val, y_val)
        self.identity_scorer.fit(X_identity, y, X_identity_val, y_val)
        self.network_scorer.fit(X_network, y, X_network_val, y_val)
        meta = np.column_stack([
            self.addr_scorer.predict_proba(X_addr_val),
            self.identity_scorer.predict_proba(X_identity_val),
            self.network_scorer.predict_proba(X_network_val),
        ])
        self.meta.fit(meta, y_val)
        self.is_trained = True
        return self

    def predict(self, X_addr, X_identity, X_network) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Ensemble is not trained yet.")
        meta = np.column_stack([
            self.addr_scorer.predict_proba(X_addr),
            self.identity_scorer.predict_proba(X_identity),
            self.network_scorer.predict_proba(X_network),
        ])
        return self.meta.predict_proba(meta)[:, 1]
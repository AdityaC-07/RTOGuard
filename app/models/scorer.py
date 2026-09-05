"""Cost-sensitive XGBoost model wrapper with CSL-OCRL threshold optimization.
Evaluates validation performance across decision thresholds (0.25 to 0.75) to directly
maximize Net Financial Saved Value (NFSV) in Indian Rupees."""

import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Dict, Tuple, Any, Optional
from app.models.custom_obj import asymmetric_inr_cost_obj
from eval.metrics import calculate_nfsv


class RTOScorer:
    def __init__(self, model_params: Optional[Dict[str, Any]] = None):
        default_params = {
            "max_depth": 5,
            "learning_rate": 0.05,
            "n_estimators": 150,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42
        }
        if model_params:
            default_params.update(model_params)
        self.params = default_params
        self.model: Optional[xgb.XGBClassifier] = None
        self.optimal_threshold: float = 0.50
        self.is_trained: bool = False

    def fit(self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray) -> "RTOScorer":

        # Initialize XGBClassifier with custom objective
        self.model = xgb.XGBClassifier(
            objective=asymmetric_inr_cost_obj,
            **self.params
        )

        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )

        # Run CSL-OCRL threshold optimization on validation set
        self.optimize_threshold_csl_ocrl(X_val, y_val)
        self.is_trained = True
        return self

    def optimize_threshold_csl_ocrl(self,
        X_val: np.ndarray,
        y_val: np.ndarray) -> float:

        # Predict raw probabilities
        val_probs = self.model.predict_proba(X_val)[:, 1]

        best_nfsv = -float("inf")
        best_thresh = 0.50

        # Sweep thresholds from 0.25 to 0.75 in steps of 0.02
        for t in np.arange(0.25, 0.76, 0.02):
            y_pred = (val_probs >= t).astype(int)
            metrics = calculate_nfsv(y_val, y_pred)
            if metrics["total_nfsv_inr"] > best_nfsv:
                best_nfsv = metrics["total_nfsv_inr"]
                best_thresh = float(t)

        self.optimal_threshold = best_thresh
        return self.optimal_threshold

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained or self.model is None:
            raise ValueError("Model is not trained yet.")
        return self.model.predict_proba(X)[:, 1]

    def predict_risk(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        probs = self.predict_proba(X)
        risk_scores = np.round(probs * 100).astype(int)
        decisions = (probs >= self.optimal_threshold).astype(int)
        return probs, risk_scores, decisions

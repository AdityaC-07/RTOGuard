"""Asymmetric INR cost-sensitive objective function for XGBoost.
Implements custom first and second-order derivatives (gradient and Hessian)
where False Negatives (missed RTO fraud) carry a 3.0x penalty multiplier relative
to False Positives (customer friction), directly translating the ₹1,200 vs ₹400 INR cost matrix."""

import numpy as np
import xgboost as xgb
from typing import Tuple

COST_WEIGHT_FN: float = 3.0  # C_FN (1200) / C_FP (400)
COST_WEIGHT_FP: float = 1.0
EPSILON: float = 1e-7


def asymmetric_inr_cost_obj(
    preds: np.ndarray,
    dtrain: xgb.DMatrix
) -> Tuple[np.ndarray, np.ndarray]:
    # Compatible with both native (preds, DMatrix) and sklearn (y_true, y_pred) APIs.
    # XGBoost >= 1.6 sklearn wrapper calls objective(y_true, y_pred) with ndarrays.
    if hasattr(dtrain, "get_label"):
        y = dtrain.get_label()
        raw = preds
    else:
        y = np.asarray(preds)
        raw = np.asarray(dtrain)
    p = 1.0 / (1.0 + np.exp(-raw))
    p = np.clip(p, EPSILON, 1.0 - EPSILON)
    w = np.where(y == 1.0, COST_WEIGHT_FN, COST_WEIGHT_FP)
    g = p * (w * y + 1.0 - y) - w * y
    h = p * (1.0 - p) * (w * y + 1.0 - y)
    return g.astype(np.float32), h.astype(np.float32)


def asymmetric_inr_eval_metric(
    preds: np.ndarray,
    dtrain: xgb.DMatrix
) -> Tuple[str, float]:
    if hasattr(dtrain, "get_label"):
        y = dtrain.get_label()
        raw = preds
    else:
        y = np.asarray(preds)
        raw = np.asarray(dtrain)
    p = 1.0 / (1.0 + np.exp(-raw))
    y_pred = (p >= 0.5).astype(float)

    # Compute total cost loss in INR
    fn = np.sum((y == 1.0) & (y_pred == 0.0))
    fp = np.sum((y == 0.0) & (y_pred == 1.0))
    total_cost = (fn * 1200.0) + (fp * 400.0)

    return "inr_cost", float(total_cost)


if __name__ == "__main__":
    # Smoke test gradient calculation
    dummy_preds = np.array([-1.0, 0.0, 2.0])
    dummy_labels = np.array([1.0, 0.0, 1.0])
    dtrain = xgb.DMatrix(np.zeros((3, 2)), label=dummy_labels)
    g, h = asymmetric_inr_cost_obj(dummy_preds, dtrain)
    print(f"Gradients: {g}")
    print(f"Hessians: {h}")

"""Tests for asymmetric objective and cost-sensitive XGBoost scorer."""

import numpy as np
import xgboost as xgb

from app.models.custom_obj import asymmetric_inr_cost_obj
from app.models.scorer import RTOScorer
from app.features.pipeline import FeaturePipeline
from eval.generate_data import generate_synthetic_orders


def test_asymmetric_objective_shape():
    preds = np.array([-1.0, 0.0, 2.0])
    labels = np.array([1.0, 0.0, 1.0])
    dtrain = xgb.DMatrix(np.zeros((3, 2)), label=labels)
    g, h = asymmetric_inr_cost_obj(preds, dtrain)
    assert g.shape == (3,)
    assert h.shape == (3,)
    assert np.isfinite(g).all()
    assert np.isfinite(h).all()
    # FN sample with low score should have stronger gradient magnitude
    assert abs(float(g[0])) > abs(float(g[1]))


def test_training_and_threshold_convergence():
    df = generate_synthetic_orders(300, random_seed=7)
    pipe = FeaturePipeline()
    pipe.fit(df)
    X = pipe.transform(df)
    y = df["is_rto"].values
    scorer = RTOScorer({"n_estimators": 20})
    scorer.fit(X[:200], y[:200], X[200:], y[200:])
    assert scorer.is_trained is True
    assert 0.25 <= scorer.optimal_threshold <= 0.75


def test_predict_risk_bounds():
    df = generate_synthetic_orders(300, random_seed=11)
    pipe = FeaturePipeline()
    pipe.fit(df)
    X = pipe.transform(df)
    y = df["is_rto"].values
    scorer = RTOScorer({"n_estimators": 20})
    scorer.fit(X[:200], y[:200], X[200:], y[200:])
    probs, scores, decisions = scorer.predict_risk(X[200:210])
    assert ((probs >= 0.0) & (probs <= 1.0)).all()
    assert ((scores >= 0) & (scores <= 100)).all()
    assert set(np.unique(decisions)).issubset({0, 1})

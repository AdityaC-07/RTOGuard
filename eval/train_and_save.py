"""Train the Phase 3 ensemble on V2 synthetic data and save its bundle."""

import os
import tempfile

import numpy as np

from app.features.pipeline import FeaturePipeline
from app.models.ensemble import RTOEnsemble
from app.models.trainer import save_model
from eval.generate_data_v2 import generate_synthetic_orders_v2
from eval.metrics import calculate_nfsv


ADDR_SLICE = slice(0, 6)
NETWORK_SLICE = slice(6, 22)
IDENTITY_SLICE = slice(22, None)


def main():
    print("Generating V2 synthetic data (5000 rows)...")
    data = generate_synthetic_orders_v2(num_samples=5000, random_seed=42)
    print("Fitting feature pipeline...")
    training_db = os.path.join(tempfile.gettempdir(), "rtoguard-training-orders.db")
    pipeline = FeaturePipeline(db_path=training_db)
    features = pipeline.fit_transform(data)
    labels = data["is_rto"].values
    split = int(len(features) * 0.70)
    X_train, X_val = features[:split], features[split:]
    y_train, y_val = labels[:split], labels[split:]

    print("Training ensemble (3 sub-models + meta)...")
    ensemble = RTOEnsemble({"n_estimators": 40})
    ensemble.fit(
        X_train[:, ADDR_SLICE], X_train[:, IDENTITY_SLICE], X_train[:, NETWORK_SLICE], y_train,
        X_val[:, ADDR_SLICE], X_val[:, IDENTITY_SLICE], X_val[:, NETWORK_SLICE], y_val,
    )

    probabilities = ensemble.predict(
        X_val[:, ADDR_SLICE], X_val[:, IDENTITY_SLICE], X_val[:, NETWORK_SLICE]
    )
    best_threshold, best_nfsv = 0.35, -float("inf")
    for threshold in np.arange(0.25, 0.75, 0.02):
        result = calculate_nfsv(y_val, (probabilities >= threshold).astype(int))
        if result["total_nfsv_inr"] > best_nfsv:
            best_nfsv, best_threshold = result["total_nfsv_inr"], float(threshold)
    result = calculate_nfsv(y_val, (probabilities >= best_threshold).astype(int))
    print(f"Optimal threshold: {best_threshold:.2f}")
    print(f"F1: {result['f1_score']:.3f}  Precision: {result['precision']:.3f}  Recall: {result['recall']:.3f}")
    print(f"NFSV: INR {result['total_nfsv_inr']:,.0f}")

    bundle = {
        "ensemble": ensemble,
        "pipeline": pipeline,
        "threshold": best_threshold,
        "addr_slice": ADDR_SLICE,
        "identity_slice": IDENTITY_SLICE,
        "network_slice": NETWORK_SLICE,
        "trained_on": "synthetic_v2_5000",
        "feature_dim": features.shape[1],
    }
    os.makedirs("data", exist_ok=True)
    save_model(bundle, "data/model.pkl")
    print("Saved -> data/model.pkl")


if __name__ == "__main__":
    main()
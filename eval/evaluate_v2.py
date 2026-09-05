"""Print a merchant-readable held-out evaluation report."""

import os
import pickle

import numpy as np
from sklearn.metrics import f1_score

from eval.generate_data_v2 import generate_synthetic_orders_v2
from eval.metrics import calculate_nfsv


def evaluate():
    model_path = "data/model.pkl"
    if not os.path.exists(model_path):
        raise SystemExit("ERROR: data/model.pkl not found. Run python -m eval.train_and_save first.")
    with open(model_path, "rb") as handle:
        bundle = pickle.load(handle)
    data = generate_synthetic_orders_v2(num_samples=2000, random_seed=99)
    features = bundle["pipeline"].transform(data)
    labels = data["is_rto"].values
    probabilities = bundle["ensemble"].predict(
        features[:, bundle["addr_slice"]],
        features[:, bundle["identity_slice"]],
        features[:, bundle["network_slice"]],
    )
    predictions = (probabilities >= bundle["threshold"]).astype(int)
    metrics = calculate_nfsv(labels, predictions)
    total = len(labels)
    legit = int((labels == 0).sum())
    fraud = int((labels == 1).sum())
    print("\n" + "=" * 54)
    print("  RTOGuard Accuracy Report")
    print("=" * 54)
    print(f"\nOut of {total} test orders:")
    print(f"  - {legit} legitimate orders -> {int(metrics['tn'])} correctly allowed ({metrics['tn'] / max(legit, 1) * 100:.0f}% accuracy)")
    print(f"  - {fraud} fraud orders      -> {int(metrics['tp'])} correctly caught ({metrics['tp'] / max(fraud, 1) * 100:.0f}% catch rate)")
    print(f"\nOrders we missed:      {int(metrics['fn'])} fraud orders shipped (cost: INR {metrics['fn'] * 1200:,.0f})")
    print(f"False alarms:          {int(metrics['fp'])} real orders blocked (cost: INR {metrics['fp'] * 400:,.0f})")
    print(f"Net savings vs no AI:  INR {metrics['total_nfsv_inr']:,.0f} across {total} orders")
    print(f"\nF1 Score:     {metrics['f1_score']:.2f}")
    print(f"Precision:    {metrics['precision']:.2f}")
    print(f"Recall:       {metrics['recall']:.2f}")
    print("\nPer-archetype breakdown:")
    for archetype in sorted(data["archetype"].unique()):
        mask = data["archetype"] == archetype
        archetype_f1 = float("nan") if len(np.unique(labels[mask])) < 2 else f1_score(labels[mask], predictions[mask], zero_division=0)
        marker = "OK" if archetype_f1 >= 0.80 else "~" if archetype_f1 >= 0.65 else "X"
        value = "N/A" if np.isnan(archetype_f1) else f"{archetype_f1:.2f}"
        print(f"  {archetype:<25} F1 = {value}  {marker}  (n={int(mask.sum())})")
    print("=" * 54)


if __name__ == "__main__":
    evaluate()
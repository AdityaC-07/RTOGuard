"""Financial evaluation engine for RTOGuard.
Implements the Net Financial Saved Value (NFSV) formula and the
CSL-OCRL threshold sweep from Thai-Nghe et al. cost-sensitive learning.
All metrics are denominated in Indian Rupees (INR)."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from sklearn.metrics import confusion_matrix, classification_report

C_FN: float = 1200.0
C_FP: float = 400.0


def calculate_nfsv(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    c_fn: float = C_FN,
    c_fp: float = C_FP
) -> Dict[str, float]:
    # Compute confusion matrix
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

    # Compute metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # NFSV formula
    total_nfsv = (tp * c_fn) - (fp * c_fp) - (fn * c_fn)
    savings_per_order = total_nfsv / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "tp": float(tp),
        "fp": float(fp),
        "tn": float(tn),
        "fn": float(fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "total_nfsv_inr": float(total_nfsv),
        "savings_per_order_inr": float(savings_per_order)
    }


def compare_models(
    y_true: np.ndarray,
    model_predictions: Dict[str, np.ndarray]
) -> pd.DataFrame:
    results = []
    for model_name, y_pred in model_predictions.items():
        metrics = calculate_nfsv(y_true, y_pred)
        metrics["model"] = model_name
        results.append(metrics)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("total_nfsv_inr", ascending=False)
    return df_results


def print_evaluation_report(
    model_name: str,
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> None:
    metrics = calculate_nfsv(y_true, y_pred)
    print(f"\n{'='*60}")
    print(f"Model: {model_name}")
    print(f"{'='*60}")
    print(f"True Positives: {int(metrics['tp'])}")
    print(f"False Positives: {int(metrics['fp'])}")
    print(f"True Negatives: {int(metrics['tn'])}")
    print(f"False Negatives: {int(metrics['fn'])}")
    print(f"\nPrecision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1 Score: {metrics['f1_score']:.4f}")
    print(f"\nTotal NFSV (INR): ₹{metrics['total_nfsv_inr']:,.2f}")
    print(f"Savings per Order (INR): ₹{metrics['savings_per_order_inr']:.2f}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    from eval.generate_data import generate_synthetic_orders

    # Generate synthetic data
    df = generate_synthetic_orders(1000)
    y_true = df['is_rto'].values

    # Create three model predictions for comparison
    model_predictions = {
        "Naive Baseline (value > 1000)": (df['order_value'] > 1000).astype(int).values,
        "Random Classifier": np.random.binomial(1, 0.28, size=len(df)),
        "Perfect Oracle": y_true
    }

    # Compare models
    comparison_df = compare_models(y_true, model_predictions)

    print("\n" + "="*80)
    print("MODEL COMPARISON - FINANCIAL PERSPECTIVE")
    print("="*80)
    print(comparison_df[["model", "precision", "recall", "f1_score", "total_nfsv_inr", "savings_per_order_inr"]].to_string(index=False))
    print("="*80)
    print(f"\nMaximum Possible NFSV on this dataset: ₹{comparison_df['total_nfsv_inr'].max():,.2f}")
    print(f"Naive Baseline NFSV: ₹{comparison_df[comparison_df['model']=='Naive Baseline (value > 1000)']['total_nfsv_inr'].values[0]:,.2f}")

    # Print detailed report for the naive baseline
    y_pred_naive = (df['order_value'] > 1000).astype(int).values
    print_evaluation_report("Naive Baseline", y_true, y_pred_naive)

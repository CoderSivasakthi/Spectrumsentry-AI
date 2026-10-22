"""Model evaluation module for modulation classification.

Provides comprehensive classification metrics, confusion matrix computation,
SNR-stratified performance analysis, and publication-ready visualization generation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from backend.app.ml.dataset import INVERSE_LABEL_MAP, LABEL_MAP


def evaluate_predictions(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute overall and per-class classification metrics.
    
    Args:
        y_true: Ground truth integer class labels of shape (N,).
        y_pred: Predicted integer class labels of shape (N,).
        y_prob: Optional predicted class probabilities of shape (N, C).
        class_names: List of class names ordered by integer label.

    Returns:
        Structured evaluation dictionary containing overall and per-class metrics.
    """
    if class_names is None:
        class_names = [INVERSE_LABEL_MAP[i] for i in range(len(LABEL_MAP))]

    n_classes = len(class_names)
    labels = list(range(n_classes))

    # Overall Metrics
    acc = float(accuracy_score(y_true, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="macro", zero_division=0
    )
    p_weighted, r_weighted, f1_weighted, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average="weighted", zero_division=0
    )

    # Per-Class Metrics
    p_per_class, r_per_class, f1_per_class, support_per_class = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )

    per_class_metrics = {}
    for idx, name in enumerate(class_names):
        per_class_metrics[name] = {
            "precision": round(float(p_per_class[idx]), 4),
            "recall": round(float(r_per_class[idx]), 4),
            "f1_score": round(float(f1_per_class[idx]), 4),
            "support": int(support_per_class[idx]),
        }

    # Confidence Metrics (if probabilities are available)
    confidence_stats = {}
    if y_prob is not None:
        confidences = np.max(y_prob, axis=1)
        confidence_stats = {
            "mean_confidence": round(float(np.mean(confidences)), 4),
            "median_confidence": round(float(np.median(confidences)), 4),
            "min_confidence": round(float(np.min(confidences)), 4),
            "max_confidence": round(float(np.max(confidences)), 4),
            "std_confidence": round(float(np.std(confidences)), 4),
        }

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "weighted_f1": round(float(f1_weighted), 4),
        "total_samples": len(y_true),
        "per_class": per_class_metrics,
        "confidence": confidence_stats,
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
    }


def compute_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute raw count and normalized confusion matrices."""
    if class_names is None:
        class_names = [INVERSE_LABEL_MAP[i] for i in range(len(LABEL_MAP))]

    labels = list(range(len(class_names)))
    cm_raw = confusion_matrix(y_true, y_pred, labels=labels)

    # Normalize by true class row sums (with division-by-zero guard)
    row_sums = cm_raw.sum(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        cm_norm = np.where(row_sums > 0, cm_raw / row_sums, 0.0)

    return {
        "class_names": class_names,
        "raw_matrix": cm_raw.tolist(),
        "normalized_matrix": [[round(float(val), 4) for val in row] for row in cm_norm],
    }


def plot_confusion_matrix(
    cm_dict: Dict[str, Any],
    output_path: Path,
    title: str = "Modulation Classification Confusion Matrix",
) -> None:
    """Render and save a high-contrast confusion matrix heatmap visualization."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    class_names = cm_dict["class_names"]
    cm_raw = np.array(cm_dict["raw_matrix"])
    cm_norm = np.array(cm_dict["normalized_matrix"])
    n = len(class_names)

    fig, ax = plt.subplots(figsize=(6.5, 5.5), dpi=300)
    im = ax.imshow(cm_norm, interpolation="nearest", cmap="Blues", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Normalized Proportion", rotation=270, labelpad=15, fontsize=10)

    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels(class_names, fontsize=10, fontweight="medium")
    ax.set_yticklabels(class_names, fontsize=10, fontweight="medium")

    # Annotate cells with both count and percentage
    thresh = 0.5
    for i in range(n):
        for j in range(n):
            val_pct = cm_norm[i, j] * 100.0
            val_count = cm_raw[i, j]
            text_color = "white" if cm_norm[i, j] > thresh else "black"
            ax.text(
                j, i,
                f"{val_pct:.1f}%\n({val_count:,})",
                ha="center", va="center",
                color=text_color, fontsize=9, fontweight="bold",
            )

    ax.set_title(title, fontsize=12, fontweight="bold", pad=15)
    ax.set_xlabel("Predicted Modulation", fontsize=11, labelpad=8)
    ax.set_ylabel("True Modulation", fontsize=11, labelpad=8)
    fig.tight_layout()

    plt.savefig(output_path, dpi=300)
    plt.close(fig)


def evaluate_performance_across_snr(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    target_snrs: np.ndarray,
    class_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluate classification accuracy and F1 independently across all SNR levels.
    
    Args:
        y_true: Ground truth labels (N,).
        y_pred: Predicted labels (N,).
        target_snrs: Target SNR in dB (N,).
        class_names: List of class names.

    Returns:
        Dictionary mapping SNR levels to detailed performance records.
    """
    if class_names is None:
        class_names = [INVERSE_LABEL_MAP[i] for i in range(len(LABEL_MAP))]

    unique_snrs = sorted([int(round(s)) for s in np.unique(target_snrs)])
    snr_records = []

    for snr in unique_snrs:
        mask = np.isclose(target_snrs, snr)
        snr_true = y_true[mask]
        snr_pred = y_pred[mask]
        total = len(snr_true)

        if total == 0:
            continue

        acc = float(accuracy_score(snr_true, snr_pred))
        p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
            snr_true, snr_pred, average="macro", zero_division=0
        )

        # Per-class accuracy at this SNR
        per_class_acc = {}
        for idx, name in enumerate(class_names):
            class_mask = (snr_true == idx)
            class_total = int(np.sum(class_mask))
            if class_total > 0:
                class_correct = int(np.sum((snr_true == idx) & (snr_pred == idx)))
                per_class_acc[f"{name}_acc"] = round(class_correct / class_total, 4)
                per_class_acc[f"{name}_total"] = class_total
            else:
                per_class_acc[f"{name}_acc"] = 0.0
                per_class_acc[f"{name}_total"] = 0

        record = {
            "snr_db": snr,
            "sample_count": total,
            "accuracy": round(acc, 4),
            "macro_precision": round(float(p_macro), 4),
            "macro_recall": round(float(r_macro), 4),
            "macro_f1": round(float(f1_macro), 4),
            **per_class_acc,
        }
        snr_records.append(record)

    return {
        "snr_levels": unique_snrs,
        "records": snr_records,
    }


def plot_snr_accuracy(
    snr_eval: Dict[str, Any],
    output_path: Path,
    title: str = "Modulation Classification Accuracy vs SNR",
) -> None:
    """Plot and save classification accuracy as a function of SNR."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = snr_eval["records"]
    snrs = [r["snr_db"] for r in records]
    overall_acc = [r["accuracy"] * 100.0 for r in records]
    bpsk_acc = [r.get("BPSK_acc", 0.0) * 100.0 for r in records]
    qpsk_acc = [r.get("QPSK_acc", 0.0) * 100.0 for r in records]
    qam16_acc = [r.get("16-QAM_acc", 0.0) * 100.0 for r in records]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    # Plot curves
    ax.plot(snrs, overall_acc, "k-o", linewidth=2.5, markersize=5, label="Overall Accuracy")
    ax.plot(snrs, bpsk_acc, "r--s", linewidth=1.5, markersize=4, label="BPSK")
    ax.plot(snrs, qpsk_acc, "g--^", linewidth=1.5, markersize=4, label="QPSK")
    ax.plot(snrs, qam16_acc, "b--d", linewidth=1.5, markersize=4, label="16-QAM")

    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Target SNR (dB)", fontsize=11, labelpad=8)
    ax.set_ylabel("Classification Accuracy (%)", fontsize=11, labelpad=8)
    ax.set_ylim(-2, 103)
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower right", frameon=True, fontsize=10)

    # Reference threshold lines
    ax.axhline(85.0, color="gray", linestyle=":", alpha=0.5, label="85% Target")

    fig.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close(fig)


def generate_classification_report_text(eval_result: Dict[str, Any]) -> str:
    """Format evaluation results into a clean, human-readable text report."""
    lines = []
    lines.append("=====================================================================")
    lines.append("           SPECTRUMSENTRY AI — CLASSIFICATION REPORT")
    lines.append("=====================================================================")
    lines.append(f"Total Test Samples : {eval_result['total_samples']:,}")
    lines.append(f"Overall Accuracy   : {eval_result['accuracy'] * 100:.2f}%")
    lines.append(f"Macro F1-Score     : {eval_result['macro_f1']:.4f}")
    lines.append(f"Weighted F1-Score  : {eval_result['weighted_f1']:.4f}")
    lines.append("---------------------------------------------------------------------")
    lines.append(f"{'Class':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    lines.append("---------------------------------------------------------------------")

    for name, metrics in eval_result["per_class"].items():
        lines.append(
            f"{name:<12} {metrics['precision']:<12.4f} {metrics['recall']:<12.4f} "
            f"{metrics['f1_score']:<12.4f} {metrics['support']:<10,}"
        )

    lines.append("---------------------------------------------------------------------")
    lines.append(
        f"{'Macro Avg':<12} {eval_result['macro_precision']:<12.4f} "
        f"{eval_result['macro_recall']:<12.4f} {eval_result['macro_f1']:<12.4f} "
        f"{eval_result['total_samples']:<10,}"
    )

    if eval_result.get("confidence"):
        conf = eval_result["confidence"]
        lines.append("---------------------------------------------------------------------")
        lines.append("Prediction Confidence Distribution:")
        lines.append(f"  Mean Confidence  : {conf['mean_confidence'] * 100:.2f}%")
        lines.append(f"  Median Confidence: {conf['median_confidence'] * 100:.2f}%")
        lines.append(f"  Min / Max Conf   : {conf['min_confidence'] * 100:.2f}% / {conf['max_confidence'] * 100:.2f}%")
    lines.append("=====================================================================")
    return "\n".join(lines)

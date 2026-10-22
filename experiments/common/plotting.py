"""Standardized publication-grade plotting utilities for Phase 9 scientific evaluation."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import matplotlib
matplotlib.use("Agg")  # Non-interactive headless backend
import matplotlib.pyplot as plt
import numpy as np

# Professional engineering color palette
COLOR_PRIMARY = "#0284c7"    # Sky 600
COLOR_SECONDARY = "#6366f1"  # Indigo 500
COLOR_SUCCESS = "#10b981"    # Emerald 500
COLOR_WARNING = "#f59e0b"    # Amber 500
COLOR_DANGER = "#ef4444"     # Rose 500
COLOR_DARK = "#0f172a"       # Slate 900
COLOR_GRID = "#e2e8f0"       # Slate 200

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "axes.labelweight": "medium",
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "axes.grid": True,
    "grid.alpha": 0.5,
    "grid.linestyle": "--",
})


def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: List[str],
    output_path: Union[str, Path],
    title: str = "Modulation Classification Confusion Matrix",
    normalize: bool = True,
) -> Path:
    """Generate and save a confusion matrix plot."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if normalize:
        cm_sum = cm.sum(axis=1)[:, np.newaxis]
        cm_norm = np.divide(cm.astype(float), cm_sum, out=np.zeros_like(cm, dtype=float), where=cm_sum != 0)
        display_data = cm_norm
    else:
        display_data = cm

    fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
    im = ax.imshow(display_data, interpolation="nearest", cmap="Blues")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Fraction of True Class" if normalize else "Sample Count")

    tick_marks = np.arange(len(class_names))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(class_names)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(class_names)

    ax.set_ylabel("True Class")
    ax.set_xlabel("Predicted Class")
    ax.set_title(title, pad=12)

    thresh = display_data.max() / 2.0
    for i in range(display_data.shape[0]):
        for j in range(display_data.shape[1]):
            val = display_data[i, j]
            count_val = cm[i, j]
            text = f"{val:.1%}\n(N={count_val})" if normalize else f"{count_val}"
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                color="white" if val > thresh else "black",
                fontsize=9,
            )

    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_snr_vs_accuracy(
    snr_levels: List[float],
    overall_accuracy: List[float],
    per_class_accuracy: Dict[str, List[float]],
    output_path: Union[str, Path],
    title: str = "Modulation Classification Accuracy vs SNR",
) -> Path:
    """Plot overall and per-class classification accuracy across SNR sweep."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    # Plot overall accuracy
    ax.plot(
        snr_levels,
        [acc * 100 for acc in overall_accuracy],
        marker="o",
        linewidth=2.5,
        color=COLOR_PRIMARY,
        label="Overall Accuracy",
        zorder=5,
    )

    # Class colors and line styles
    palette = [COLOR_SUCCESS, COLOR_WARNING, COLOR_SECONDARY]
    markers = ["s", "^", "D"]
    for idx, (cls_name, accs) in enumerate(per_class_accuracy.items()):
        color = palette[idx % len(palette)]
        marker = markers[idx % len(markers)]
        ax.plot(
            snr_levels,
            [acc * 100 for acc in accs],
            marker=marker,
            linestyle="--",
            linewidth=1.5,
            color=color,
            label=f"{cls_name}",
            alpha=0.85,
        )

    # Reference threshold lines
    ax.axhline(90.0, color="gray", linestyle=":", alpha=0.7, label="90% Target")

    # Annotate operating regions
    ax.axvspan(-5, 0, alpha=0.08, color="red", label="Low-SNR Region (<0 dB)")
    ax.axvspan(0, 5, alpha=0.08, color="orange", label="Transition Region (0-5 dB)")
    ax.axvspan(5, 20, alpha=0.08, color="green", label="High-Confidence Region (>5 dB)")

    ax.set_xlabel("Signal-to-Noise Ratio (SNR) [dB]")
    ax.set_ylabel("Classification Accuracy [%]")
    ax.set_title(title, pad=12)
    ax.set_ylim(-2, 105)
    ax.set_xlim(min(snr_levels) - 0.5, max(snr_levels) + 0.5)
    ax.legend(loc="lower right", framealpha=0.9)

    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_confidence_vs_snr(
    snr_levels: List[float],
    mean_confidence: List[float],
    std_confidence: List[float],
    output_path: Union[str, Path],
) -> Path:
    """Plot mean AI model confidence with variance bands across SNR range."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    means = np.array(mean_confidence) * 100
    stds = np.array(std_confidence) * 100

    ax.plot(snr_levels, means, marker="o", color=COLOR_SECONDARY, linewidth=2, label="Mean AI Confidence")
    ax.fill_between(snr_levels, np.clip(means - stds, 0, 100), np.clip(means + stds, 0, 100), color=COLOR_SECONDARY, alpha=0.2, label="±1σ Confidence Range")

    ax.set_xlabel("Signal-to-Noise Ratio (SNR) [dB]")
    ax.set_ylabel("Classification Confidence [%]")
    ax.set_title("AI Confidence vs Signal-to-Noise Ratio", pad=12)
    ax.set_ylim(0, 105)
    ax.legend(loc="lower right")

    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_target_vs_measured_snr(
    target_snrs: List[float],
    measured_means: List[float],
    measured_stds: List[float],
    errors: List[float],
    output_target_path: Union[str, Path],
    output_error_path: Union[str, Path],
) -> Tuple[Path, Path]:
    """Plot Target SNR vs Measured SNR and SNR Calibration Error."""
    target_p = Path(output_target_path)
    error_p = Path(output_error_path)
    target_p.parent.mkdir(parents=True, exist_ok=True)
    error_p.parent.mkdir(parents=True, exist_ok=True)

    # 1. Target vs Measured SNR
    fig1, ax1 = plt.subplots(figsize=(6, 5), dpi=300)
    ax1.plot(target_snrs, target_snrs, "k--", alpha=0.7, label="Ideal 1:1 Identity")
    ax1.errorbar(
        target_snrs,
        measured_means,
        yerr=measured_stds,
        fmt="o",
        color=COLOR_PRIMARY,
        ecolor=COLOR_SECONDARY,
        elinewidth=1.5,
        capsize=3,
        label="Measured SNR (Mean ± Std)",
    )
    ax1.set_xlabel("Configured Target SNR [dB]")
    ax1.set_ylabel("Measured SNR [dB]")
    ax1.set_title("AWGN Channel Calibration: Target vs Measured SNR", pad=12)
    ax1.legend(loc="upper left")
    plt.tight_layout()
    plt.savefig(target_p, dpi=300, bbox_inches="tight")
    plt.close(fig1)

    # 2. SNR Error
    fig2, ax2 = plt.subplots(figsize=(6, 4.5), dpi=300)
    ax2.axhline(0.0, color="k", linestyle="--", alpha=0.5)
    ax2.plot(target_snrs, errors, marker="s", color=COLOR_DANGER, linewidth=1.8, label="Mean SNR Error (dB)")
    ax2.set_xlabel("Target SNR [dB]")
    ax2.set_ylabel("Error: Measured - Target [dB]")
    ax2.set_title("SNR Measurement Discrepancy Across Dynamic Range", pad=12)
    ax2.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(error_p, dpi=300, bbox_inches="tight")
    plt.close(fig2)

    return target_p, error_p


def plot_communication_curves(
    loss_levels: List[float],
    loss_health_scores: List[float],
    latency_levels: List[float],
    latency_health_scores: List[float],
    jitter_levels: List[float],
    jitter_health_scores: List[float],
    output_dir: Union[str, Path],
) -> List[Path]:
    """Generate communication telemetry degradation curves."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    paths = []

    # 1. Packet Loss vs Health
    p1 = out / "packet_loss_vs_health.png"
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)
    ax.plot(loss_levels, loss_health_scores, marker="o", color=COLOR_DANGER, linewidth=2, label="Health Score")
    ax.axhline(90.0, color="green", linestyle=":", label="Normal Threshold (≥90)")
    ax.axhline(70.0, color="orange", linestyle=":", label="Degraded Threshold (≥70)")
    ax.set_xlabel("Configured Packet Loss [%]")
    ax.set_ylabel("Communication Health Score (/100)")
    ax.set_title("Packet Loss vs Health Score Degradation", pad=12)
    ax.set_ylim(-2, 105)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(p1, dpi=300, bbox_inches="tight")
    plt.close(fig)
    paths.append(p1)

    # 2. Latency vs Health
    p2 = out / "latency_vs_health.png"
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)
    ax.plot(latency_levels, latency_health_scores, marker="s", color=COLOR_PRIMARY, linewidth=2, label="Health Score")
    ax.set_xlabel("Measured RTT Latency [ms]")
    ax.set_ylabel("Communication Health Score (/100)")
    ax.set_title("RTT Latency vs Communication Health Score", pad=12)
    ax.set_ylim(-2, 105)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(p2, dpi=300, bbox_inches="tight")
    plt.close(fig)
    paths.append(p2)

    # 3. Jitter vs Health
    p3 = out / "jitter_vs_health.png"
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)
    ax.plot(jitter_levels, jitter_health_scores, marker="^", color=COLOR_WARNING, linewidth=2, label="Health Score")
    ax.set_xlabel("Measured Jitter [ms]")
    ax.set_ylabel("Communication Health Score (/100)")
    ax.set_title("Packet Jitter vs Communication Health Score", pad=12)
    ax.set_ylim(-2, 105)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(p3, dpi=300, bbox_inches="tight")
    plt.close(fig)
    paths.append(p3)

    return paths


def plot_pipeline_latency_breakdown(
    stages: List[str],
    durations_ms: List[float],
    output_path: Union[str, Path],
) -> Path:
    """Generate horizontal bar chart showing end-to-end processing latency breakdown."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    y_pos = np.arange(len(stages))
    bars = ax.barh(y_pos, durations_ms, color=COLOR_PRIMARY, edgecolor=COLOR_DARK, alpha=0.85)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(stages)
    ax.invert_yaxis()
    ax.set_xlabel("Processing Duration [milliseconds]")
    ax.set_title("End-to-End SpectrumSentry AI Pipeline Latency Breakdown", pad=12)

    for bar, val in zip(bars, durations_ms):
        ax.text(
            bar.get_width() + 0.02 * max(durations_ms),
            bar.get_y() + bar.get_height() / 2,
            f"{val:.3f} ms",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_xlim(0, max(durations_ms) * 1.25)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_memory_soak(
    timestamps_sec: List[float],
    memory_mb: List[float],
    output_path: Union[str, Path],
) -> Path:
    """Plot resident set memory usage during continuous soak testing."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
    ax.plot(timestamps_sec, memory_mb, color=COLOR_SECONDARY, linewidth=1.8, label="Resident Memory (RSS)")
    ax.set_xlabel("Elapsed Time [seconds]")
    ax.set_ylabel("Process Memory [MB]")
    ax.set_title("System Stability: Memory Usage Under Continuous Operation", pad=12)
    ax.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path

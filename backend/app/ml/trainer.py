"""Model training, validation splitting, model selection, and serialization pipeline.

Trains an sklearn Pipeline comprising StandardScaler and MLPClassifier.
Enforces zero data leakage by keeping the original test partition untouched
and conducting hyperparameter selection strictly on a development validation split.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import sklearn
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.app.ml.dataset import INVERSE_LABEL_MAP, LABEL_MAP
from backend.app.ml.evaluator import evaluate_predictions
from backend.app.signal_processing import FEATURE_COUNT, FEATURE_NAMES

DEFAULT_MODELS_DIR = Path("backend/models")
DEFAULT_DATASET_DIR = Path("backend/data/datasets")


@dataclass
class TrainingConfig:
    """Hyperparameter and execution configuration for MLPClassifier."""
    hidden_layer_sizes: Tuple[int, ...] = (64, 32)
    activation: str = "relu"
    solver: str = "adam"
    alpha: float = 0.0001
    batch_size: int = 128
    learning_rate_init: float = 0.001
    max_iter: int = 200
    early_stopping: bool = True
    validation_fraction: float = 0.1
    n_iter_no_change: int = 15
    random_state: int = 42
    val_ratio: float = 0.2  # Development validation split ratio

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass configuration to dictionary."""
        d = asdict(self)
        d["hidden_layer_sizes"] = list(self.hidden_layer_sizes)
        return d


def load_training_dataset(
    dataset_dir: Path = DEFAULT_DATASET_DIR,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
    """Load and verify the saved Phase 3 train/test partitions.
    
    Args:
        dataset_dir: Directory containing train_test_split.npz and dataset_info.json.

    Returns:
        Tuple of:
            X_train: (31200, 23) float32
            y_train: (31200,) int64
            target_snr_train: (31200,) float32
            X_test: (7800, 23) float32
            y_test: (7800,) int64
            target_snr_test: (7800,) float32
            dataset_info: Metadata dictionary

    Raises:
        FileNotFoundError: If dataset files are missing.
        ValueError: If array dimensions or feature count violate the Phase 3 contract.
    """
    dataset_dir = Path(dataset_dir)
    split_file = dataset_dir / "train_test_split.npz"
    info_file = dataset_dir / "dataset_info.json"

    if not split_file.exists():
        raise FileNotFoundError(f"Missing train_test_split file: {split_file}")
    if not info_file.exists():
        raise FileNotFoundError(f"Missing dataset_info file: {info_file}")

    with open(info_file, "r", encoding="utf-8") as f:
        dataset_info = json.load(f)

    data = np.load(split_file)
    X_train = data["X_train"]
    y_train = data["y_train"]
    target_snr_train = data["target_snr_train"]

    X_test = data["X_test"]
    y_test = data["y_test"]
    target_snr_test = data["target_snr_test"]

    # Verify input feature dimensions and numerical health
    if X_train.ndim != 2 or X_train.shape[1] != FEATURE_COUNT:
        raise ValueError(f"X_train feature count mismatch: expected {FEATURE_COUNT}, got {X_train.shape[1]}")
    if X_test.ndim != 2 or X_test.shape[1] != FEATURE_COUNT:
        raise ValueError(f"X_test feature count mismatch: expected {FEATURE_COUNT}, got {X_test.shape[1]}")

    if not np.all(np.isfinite(X_train)) or not np.all(np.isfinite(X_test)):
        raise ValueError("Dataset features contain NaN or Infinite values")

    return (
        X_train,
        y_train,
        target_snr_train,
        X_test,
        y_test,
        target_snr_test,
        dataset_info,
    )


def create_development_split(
    X_train: np.ndarray,
    y_train: np.ndarray,
    target_snrs_train: np.ndarray,
    val_ratio: float = 0.2,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create a stratified development validation split from the training partition.
    
    Prevents leakage by stratifying on the composite condition key (class and SNR).
    
    Args:
        X_train: Full training feature matrix.
        y_train: Full training label array.
        target_snrs_train: Full training SNR metadata.
        val_ratio: Proportion of training examples for model selection validation (default: 0.2).
        seed: Random seed for split reproducibility.

    Returns:
        (X_fit, y_fit, snr_fit, X_val, y_val, snr_val)
    """
    condition_keys = [
        f"{lbl}_{int(round(snr))}"
        for lbl, snr in zip(y_train, target_snrs_train)
    ]
    indices = np.arange(len(y_train))

    fit_idx, val_idx = train_test_split(
        indices,
        test_size=val_ratio,
        random_state=seed,
        stratify=condition_keys,
    )

    fit_idx = np.sort(fit_idx)
    val_idx = np.sort(val_idx)

    return (
        X_train[fit_idx],
        y_train[fit_idx],
        target_snrs_train[fit_idx],
        X_train[val_idx],
        y_train[val_idx],
        target_snrs_train[val_idx],
    )


def build_model_pipeline(config: TrainingConfig) -> Pipeline:
    """Construct an sklearn Pipeline with StandardScaler and MLPClassifier.
    
    Args:
        config: TrainingConfig parameters.

    Returns:
        Unfitted sklearn Pipeline instance.
    """
    scaler = StandardScaler()
    classifier = MLPClassifier(
        hidden_layer_sizes=config.hidden_layer_sizes,
        activation=config.activation,
        solver=config.solver,
        alpha=config.alpha,
        batch_size=config.batch_size,
        learning_rate_init=config.learning_rate_init,
        max_iter=config.max_iter,
        early_stopping=config.early_stopping,
        validation_fraction=config.validation_fraction,
        n_iter_no_change=config.n_iter_no_change,
        random_state=config.random_state,
    )
    return Pipeline([("scaler", scaler), ("classifier", classifier)])


def compare_model_architectures(
    X_fit: np.ndarray,
    y_fit: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    seed: int = 42,
    max_iter: int = 200,
) -> Tuple[str, TrainingConfig, Dict[str, Any]]:
    """Compare predefined MLP candidate configurations on the validation split.
    
    Candidates:
    - Model A: (64, 32)
    - Model B: (128, 64)
    - Model C: (128, 64, 32)

    Selects the winning configuration based on Validation Macro F1 score.

    Returns:
        (best_name, best_config, comparison_results)
    """
    candidates = {
        "Model A (64, 32)": (64, 32),
        "Model B (128, 64)": (128, 64),
        "Model C (128, 64, 32)": (128, 64, 32),
    }

    results = {}
    best_f1 = -1.0
    best_name = "Model A (64, 32)"
    best_config = TrainingConfig(
        hidden_layer_sizes=candidates[best_name],
        random_state=seed,
        max_iter=max_iter,
    )

    for name, hidden_layers in candidates.items():
        cfg = TrainingConfig(
            hidden_layer_sizes=hidden_layers,
            random_state=seed,
            max_iter=max_iter,
        )
        pipe = build_model_pipeline(cfg)

        t_start = time.perf_counter()
        pipe.fit(X_fit, y_fit)
        train_time = time.perf_counter() - t_start

        y_val_pred = pipe.predict(X_val)
        y_val_prob = pipe.predict_proba(X_val)
        val_eval = evaluate_predictions(y_val, y_val_pred, y_val_prob)

        mlp = pipe.named_steps["classifier"]
        loss_curve = [round(float(l), 5) for l in getattr(mlp, "loss_curve_", [])]

        results[name] = {
            "hidden_layer_sizes": list(hidden_layers),
            "training_time_sec": round(train_time, 2),
            "iterations": int(getattr(mlp, "n_iter_", 0)),
            "validation_accuracy": val_eval["accuracy"],
            "validation_macro_f1": val_eval["macro_f1"],
            "validation_weighted_f1": val_eval["weighted_f1"],
            "final_loss": round(float(getattr(mlp, "loss_", 0.0)), 5),
            "loss_curve": loss_curve,
        }

        if val_eval["macro_f1"] > best_f1:
            best_f1 = val_eval["macro_f1"]
            best_name = name
            best_config = cfg

    return best_name, best_config, results


def train_model(
    config: Optional[TrainingConfig] = None,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    perform_model_selection: bool = True,
) -> Tuple[Pipeline, Dict[str, Any], Dict[str, Any]]:
    """Execute complete model training and validation workflow.
    
    Args:
        config: TrainingConfig parameters (if None, default is used).
        dataset_dir: Path to dataset files.
        perform_model_selection: If True, evaluates Model A, B, and C on validation set.

    Returns:
        (trained_pipeline, validation_metrics, comparison_summary)
    """
    if config is None:
        config = TrainingConfig()

    # 1. Load dataset partitions
    (
        X_train,
        y_train,
        snr_train,
        X_test,
        y_test,
        snr_test,
        dataset_info,
    ) = load_training_dataset(dataset_dir)

    # 2. Partition training data into internal fit and validation subsets
    (
        X_fit,
        y_fit,
        snr_fit,
        X_val,
        y_val,
        snr_val,
    ) = create_development_split(
        X_train, y_train, snr_train, val_ratio=config.val_ratio, seed=config.random_state
    )

    comparison_results: Dict[str, Any] = {}
    selected_name = f"Custom MLP {list(config.hidden_layer_sizes)}"
    selected_config = config

    # 3. Model Selection across predefined architectures
    if perform_model_selection:
        selected_name, selected_config, comparison_results = compare_model_architectures(
            X_fit, y_fit, X_val, y_val, seed=config.random_state, max_iter=config.max_iter
        )

    # 4. Train selected model pipeline on full training set (31,200 examples)
    pipeline = build_model_pipeline(selected_config)
    t_start = time.perf_counter()
    pipeline.fit(X_train, y_train)
    total_train_time = time.perf_counter() - t_start

    # Evaluate on development validation set
    y_val_pred = pipeline.predict(X_val)
    y_val_prob = pipeline.predict_proba(X_val)
    val_metrics = evaluate_predictions(y_val, y_val_pred, y_val_prob)

    mlp = pipeline.named_steps["classifier"]
    loss_curve = [round(float(l), 5) for l in getattr(mlp, "loss_curve_", [])]

    val_summary = {
        "selected_architecture": selected_name,
        "training_time_sec": round(total_train_time, 2),
        "total_iterations": int(getattr(mlp, "n_iter_", 0)),
        "final_loss": round(float(getattr(mlp, "loss_", 0.0)), 5),
        "loss_curve": loss_curve,
        "metrics": val_metrics,
        "fit_samples": len(X_train),
        "val_samples": len(X_val),
    }

    return pipeline, val_summary, comparison_results


def save_trained_model(
    pipeline: Pipeline,
    output_dir: Path,
    model_name: str = "modulation_mlp_v1",
    model_metadata: Optional[Dict[str, Any]] = None,
    training_config: Optional[TrainingConfig] = None,
) -> Dict[str, str]:
    """Serialize fitted sklearn pipeline and associated metadata to disk.
    
    Args:
        pipeline: Trained sklearn Pipeline.
        output_dir: Destination directory path (e.g. backend/models/).
        model_name: Base file name without extension.
        model_metadata: Evaluation metrics and environment metadata.
        training_config: Configuration used during training.

    Returns:
        Dict of paths to saved artifacts.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    joblib_path = output_dir / f"{model_name}.joblib"
    metadata_path = output_dir / "model_metadata.json"
    config_path = output_dir / "training_config.json"

    # Save fitted pipeline
    joblib.dump(pipeline, joblib_path)

    # Save config
    cfg_dict = training_config.to_dict() if training_config else {}
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg_dict, f, indent=2)

    # Save metadata
    meta = model_metadata or {}
    meta["model_filename"] = joblib_path.name
    meta["sklearn_version"] = sklearn.__version__
    meta["numpy_version"] = np.__version__
    meta["joblib_version"] = joblib.__version__
    meta["feature_count"] = FEATURE_COUNT
    meta["feature_names"] = list(FEATURE_NAMES)
    meta["label_mapping"] = {str(k): v for k, v in INVERSE_LABEL_MAP.items()}

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    return {
        "model_file": str(joblib_path),
        "metadata_file": str(metadata_path),
        "config_file": str(config_path),
    }


def load_trained_model(model_path: Path) -> Pipeline:
    """Load a previously serialized sklearn pipeline.
    
    Args:
        model_path: Path to the .joblib model file.

    Returns:
        Loaded sklearn Pipeline.

    Raises:
        FileNotFoundError: If model file does not exist.
        ValueError: If file is not a valid Pipeline.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    loaded = joblib.load(model_path)
    if not isinstance(loaded, Pipeline):
        raise ValueError(f"Loaded object is not an sklearn Pipeline, got {type(loaded).__name__}")
    return loaded

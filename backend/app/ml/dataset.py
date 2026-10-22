"""Dataset generation, splitting, serialization, and validation for modulation classification.

Uses the Phase 2 DSP engine (generator, AWGN noise, feature extraction) to create
a balanced, stratified, deterministic, and fully reproducible dataset across:
- Modulations: BPSK (0), QPSK (1), 16-QAM (2)
- Target SNR range: -5 dB to +20 dB in 1 dB increments (26 levels)
- Default size: 78 conditions x 500 samples/condition = 39,000 examples
- Exact 23-feature vector contract preserved from Phase 2
"""

from dataclasses import asdict, dataclass
import csv
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
from sklearn.model_selection import train_test_split

from backend.app.signal_processing import (
    FEATURE_COUNT,
    FEATURE_NAMES,
    SUPPORTED_MODULATIONS,
    add_awgn,
    extract_features,
    generate_signal,
)

LABEL_MAP: Dict[str, int] = {
    "BPSK": 0,
    "QPSK": 1,
    "16-QAM": 2,
}

INVERSE_LABEL_MAP: Dict[int, str] = {
    0: "BPSK",
    1: "QPSK",
    2: "16-QAM",
}


@dataclass
class DatasetConfig:
    """Configuration parameters for dataset generation."""
    dataset_version: str = "v1.0"
    modulations: Tuple[str, ...] = ("BPSK", "QPSK", "16-QAM")
    snr_min_db: int = -5
    snr_max_db: int = 20
    snr_step_db: int = 1
    samples_per_condition: int = 500
    sample_count: int = 1024
    sample_rate: float = 1e6
    seed: int = 42
    train_ratio: float = 0.8
    test_ratio: float = 0.2
    noise_type: str = "AWGN"
    save_raw: bool = False

    @property
    def snr_levels(self) -> List[int]:
        """List of integer SNR levels in dB from min to max inclusive."""
        return list(range(self.snr_min_db, self.snr_max_db + 1, self.snr_step_db))

    @property
    def total_conditions(self) -> int:
        """Total number of unique modulation x SNR conditions."""
        return len(self.modulations) * len(self.snr_levels)

    @property
    def total_samples(self) -> int:
        """Total number of samples across all conditions."""
        return self.total_conditions * self.samples_per_condition


@dataclass
class DatasetResult:
    """In-memory representation of a generated dataset with train/test splits."""
    config: DatasetConfig
    X: np.ndarray             # (N, 23) float32
    y: np.ndarray             # (N,) int64
    sample_ids: np.ndarray    # (N,) str
    target_snr: np.ndarray    # (N,) float32
    measured_snr: np.ndarray  # (N,) float32
    metadata: List[Dict[str, Any]]
    X_train: np.ndarray
    X_test: np.ndarray
    y_train: np.ndarray
    y_test: np.ndarray
    train_indices: np.ndarray
    test_indices: np.ndarray
    statistics: Dict[str, Any]


def calculate_dataset_statistics(
    X: np.ndarray,
    y: np.ndarray,
    target_snr: np.ndarray,
    measured_snr: np.ndarray,
    config: DatasetConfig,
    train_indices: np.ndarray,
    test_indices: np.ndarray,
) -> Dict[str, Any]:
    """Calculate descriptive statistics for the generated dataset."""
    total_examples = len(y)
    
    # Class counts
    class_counts = {}
    for mod_name, label_idx in LABEL_MAP.items():
        if mod_name in config.modulations:
            class_counts[mod_name] = int(np.sum(y == label_idx))

    # Samples per SNR
    samples_per_snr = {}
    for snr in config.snr_levels:
        samples_per_snr[str(snr)] = int(np.sum(np.isclose(target_snr, snr)))

    # Measured SNR statistics
    min_measured = float(np.min(measured_snr)) if total_examples > 0 else 0.0
    max_measured = float(np.max(measured_snr)) if total_examples > 0 else 0.0
    mean_measured = float(np.mean(measured_snr)) if total_examples > 0 else 0.0
    std_measured = float(np.std(measured_snr)) if total_examples > 0 else 0.0

    # Numerical integrity
    nan_count = int(np.sum(np.isnan(X)))
    inf_count = int(np.sum(np.isinf(X)))

    return {
        "dataset_version": config.dataset_version,
        "seed": config.seed,
        "total_examples": total_examples,
        "feature_count": X.shape[1] if X.ndim == 2 else 0,
        "train_examples": len(train_indices),
        "test_examples": len(test_indices),
        "class_counts": class_counts,
        "samples_per_snr": samples_per_snr,
        "total_conditions": config.total_conditions,
        "samples_per_condition": config.samples_per_condition,
        "measured_snr": {
            "min_db": round(min_measured, 3),
            "max_db": round(max_measured, 3),
            "mean_db": round(mean_measured, 3),
            "std_db": round(std_measured, 3),
        },
        "integrity": {
            "nan_count": nan_count,
            "inf_count": inf_count,
            "is_clean": (nan_count == 0 and inf_count == 0),
        },
    }


def generate_modulation_dataset(
    config: Optional[DatasetConfig] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> DatasetResult:
    """Generate a clean, balanced, reproducible dataset for modulation classification.
    
    Args:
        config: DatasetConfig instance. If None, default configuration is used.
        progress_callback: Optional callable(completed_samples, total_samples) for progress reporting.

    Returns:
        DatasetResult containing full arrays, train/test splits, metadata, and statistics.
    """
    if config is None:
        config = DatasetConfig()

    total_samples = config.total_samples
    if total_samples <= 0:
        raise ValueError(f"Total samples must be positive, got {total_samples}")

    # Initialize feature matrix and target arrays
    X = np.empty((total_samples, FEATURE_COUNT), dtype=np.float32)
    y = np.empty(total_samples, dtype=np.int64)
    target_snrs = np.empty(total_samples, dtype=np.float32)
    measured_snrs = np.empty(total_samples, dtype=np.float32)
    sample_ids = []
    metadata: List[Dict[str, Any]] = []

    # Deterministic seed derivation via SeedSequence
    root_seed_seq = np.random.SeedSequence(config.seed)
    child_seeds = root_seed_seq.generate_state(total_samples)

    sample_idx = 0
    raw_dir: Optional[Path] = None
    if config.save_raw:
        raw_dir = Path("backend/data/raw/signals")
        raw_dir.mkdir(parents=True, exist_ok=True)

    for mod in config.modulations:
        mod_label = LABEL_MAP[mod]
        for snr in config.snr_levels:
            condition_name = f"{mod}_{snr:+d}dB"

            for c_idx in range(config.samples_per_condition):
                # Derive independent sub-seeds for clean signal and noise
                current_seed = int(child_seeds[sample_idx])
                sub_seq = np.random.SeedSequence(current_seed)
                sig_seed, noise_seed = [int(s) for s in sub_seq.generate_state(2)]

                # 1. Generate clean signal using Phase 2 DSP generator
                clean_gen = generate_signal(
                    modulation=mod,
                    num_samples=config.sample_count,
                    sample_rate=config.sample_rate,
                    seed=sig_seed,
                )

                # 2. Add AWGN noise using Phase 2 noise engine
                awgn_res = add_awgn(
                    signal=clean_gen.signal,
                    snr_db=float(snr),
                    seed=noise_seed,
                )

                # 3. Extract 23 features using Phase 2 feature extractor
                feat_vec, _ = extract_features(
                    signal=awgn_res.noisy_signal,
                    sample_rate=config.sample_rate,
                )

                # Store in preallocated arrays
                X[sample_idx] = feat_vec
                y[sample_idx] = mod_label
                target_snrs[sample_idx] = float(snr)
                measured_snrs[sample_idx] = awgn_res.measured_snr_db

                sample_id = f"SMP-{sample_idx + 1:06d}"
                sample_ids.append(sample_id)

                # Optional raw I/Q storage (disabled by default for compact storage)
                if config.save_raw and raw_dir is not None:
                    np.save(raw_dir / f"{sample_id}_noisy.npy", awgn_res.noisy_signal)

                metadata.append({
                    "sample_id": sample_id,
                    "modulation": mod,
                    "label": mod_label,
                    "target_snr_db": float(snr),
                    "measured_snr_db": round(float(awgn_res.measured_snr_db), 4),
                    "random_seed": current_seed,
                    "sample_count": config.sample_count,
                    "sample_rate": config.sample_rate,
                    "noise_type": config.noise_type,
                    "condition": condition_name,
                    "split": "",  # Populated during train/test split
                    "dataset_version": config.dataset_version,
                })

                sample_idx += 1
                if progress_callback is not None and (sample_idx % 250 == 0 or sample_idx == total_samples):
                    progress_callback(sample_idx, total_samples)

    sample_ids_arr = np.array(sample_ids, dtype="U32")

    # 4. Stratified Train / Test Split
    # Stratify by condition (modulation x target_snr) to guarantee uniform distribution across train and test
    condition_keys = [item["condition"] for item in metadata]
    indices = np.arange(total_samples)

    train_indices, test_indices = train_test_split(
        indices,
        test_size=config.test_ratio,
        random_state=config.seed,
        stratify=condition_keys,
    )

    # Sort indices for predictable indexing
    train_indices = np.sort(train_indices)
    test_indices = np.sort(test_indices)

    # Mark split in metadata
    train_idx_set = set(train_indices)
    for idx, item in enumerate(metadata):
        item["split"] = "train" if idx in train_idx_set else "test"

    # Slice train and test subsets
    X_train = X[train_indices]
    y_train = y[train_indices]
    X_test = X[test_indices]
    y_test = y[test_indices]

    # Calculate statistics
    stats = calculate_dataset_statistics(
        X=X,
        y=y,
        target_snr=target_snrs,
        measured_snr=measured_snrs,
        config=config,
        train_indices=train_indices,
        test_indices=test_indices,
    )

    return DatasetResult(
        config=config,
        X=X,
        y=y,
        sample_ids=sample_ids_arr,
        target_snr=target_snrs,
        measured_snr=measured_snrs,
        metadata=metadata,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        train_indices=train_indices,
        test_indices=test_indices,
        statistics=stats,
    )


def save_dataset_artifacts(dataset: DatasetResult, output_dir: Path) -> Dict[str, str]:
    """Save all dataset artifacts into the target directory.
    
    Artifacts:
    - modulation_dataset.npz: Full numerical dataset (X, y, target_snr, measured_snr, sample_ids)
    - train_test_split.npz: Train and test splits (X_train, X_test, y_train, y_test, indices, SNRs)
    - metadata.csv: Tabular example-level metadata
    - feature_names.json: Ordered list of 23 feature names
    - label_map.json: Class-to-index and index-to-class mappings
    - dataset_info.json: High-level dataset configuration and metadata
    - dataset_statistics.json: Computed descriptive statistics

    Args:
        dataset: DatasetResult instance.
        output_dir: Destination directory path.

    Returns:
        Dict mapping artifact keys to their absolute string file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. modulation_dataset.npz
    dataset_npz_path = output_dir / "modulation_dataset.npz"
    np.savez_compressed(
        dataset_npz_path,
        X=dataset.X,
        y=dataset.y,
        target_snr=dataset.target_snr,
        measured_snr=dataset.measured_snr,
        sample_ids=dataset.sample_ids,
    )

    # 2. train_test_split.npz
    split_npz_path = output_dir / "train_test_split.npz"
    np.savez_compressed(
        split_npz_path,
        X_train=dataset.X_train,
        X_test=dataset.X_test,
        y_train=dataset.y_train,
        y_test=dataset.y_test,
        train_indices=dataset.train_indices,
        test_indices=dataset.test_indices,
        target_snr_train=dataset.target_snr[dataset.train_indices],
        target_snr_test=dataset.target_snr[dataset.test_indices],
        measured_snr_train=dataset.measured_snr[dataset.train_indices],
        measured_snr_test=dataset.measured_snr[dataset.test_indices],
    )

    # 3. metadata.csv
    metadata_csv_path = output_dir / "metadata.csv"
    if dataset.metadata:
        fieldnames = list(dataset.metadata[0].keys())
        with open(metadata_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(dataset.metadata)

    # 4. feature_names.json
    feature_names_path = output_dir / "feature_names.json"
    with open(feature_names_path, "w", encoding="utf-8") as f:
        json.dump(list(FEATURE_NAMES), f, indent=2)

    # 5. label_map.json
    label_map_path = output_dir / "label_map.json"
    label_map_content = {
        "class_to_index": LABEL_MAP,
        "index_to_class": {str(k): v for k, v in INVERSE_LABEL_MAP.items()},
    }
    with open(label_map_path, "w", encoding="utf-8") as f:
        json.dump(label_map_content, f, indent=2)

    # 6. dataset_info.json
    dataset_info_path = output_dir / "dataset_info.json"
    info_content = {
        "dataset_version": dataset.config.dataset_version,
        "seed": dataset.config.seed,
        "modulations": list(dataset.config.modulations),
        "snr_min_db": dataset.config.snr_min_db,
        "snr_max_db": dataset.config.snr_max_db,
        "snr_step_db": dataset.config.snr_step_db,
        "samples_per_condition": dataset.config.samples_per_condition,
        "total_conditions": dataset.config.total_conditions,
        "total_examples": dataset.config.total_samples,
        "sample_count": dataset.config.sample_count,
        "sample_rate": dataset.config.sample_rate,
        "feature_count": FEATURE_COUNT,
        "train_ratio": dataset.config.train_ratio,
        "test_ratio": dataset.config.test_ratio,
        "noise_type": dataset.config.noise_type,
        "label_mapping": {str(k): v for k, v in INVERSE_LABEL_MAP.items()},
        "feature_names": list(FEATURE_NAMES),
    }
    with open(dataset_info_path, "w", encoding="utf-8") as f:
        json.dump(info_content, f, indent=2)

    # 7. dataset_statistics.json
    stats_path = output_dir / "dataset_statistics.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(dataset.statistics, f, indent=2)

    return {
        "modulation_dataset_npz": str(dataset_npz_path),
        "train_test_split_npz": str(split_npz_path),
        "metadata_csv": str(metadata_csv_path),
        "feature_names_json": str(feature_names_path),
        "label_map_json": str(label_map_path),
        "dataset_info_json": str(dataset_info_path),
        "dataset_statistics_json": str(stats_path),
    }


def validate_dataset_directory(dataset_dir: Path) -> Tuple[bool, List[str]]:
    """Validate all 17 dataset criteria from Section 13 of the specification.
    
    Args:
        dataset_dir: Path to directory containing saved dataset files.

    Returns:
        Tuple of (is_valid: bool, issues: List[str]).
    """
    dataset_dir = Path(dataset_dir)
    issues: List[str] = []

    # 1. Dataset files exist
    required_files = [
        "modulation_dataset.npz",
        "train_test_split.npz",
        "metadata.csv",
        "feature_names.json",
        "label_map.json",
        "dataset_info.json",
        "dataset_statistics.json",
    ]
    for rf in required_files:
        if not (dataset_dir / rf).exists():
            issues.append(f"Missing required file: {rf}")

    if issues:
        return False, issues

    # Load arrays and info
    try:
        data_npz = np.load(dataset_dir / "modulation_dataset.npz")
        split_npz = np.load(dataset_dir / "train_test_split.npz")
        with open(dataset_dir / "dataset_info.json", "r", encoding="utf-8") as f:
            info = json.load(f)
        with open(dataset_dir / "feature_names.json", "r", encoding="utf-8") as f:
            feat_names = json.load(f)
        with open(dataset_dir / "label_map.json", "r", encoding="utf-8") as f:
            label_map = json.load(f)
    except Exception as e:
        return False, [f"Failed to load dataset files: {str(e)}"]

    X = data_npz["X"]
    y = data_npz["y"]
    target_snr = data_npz["target_snr"]
    sample_ids = data_npz["sample_ids"]

    X_train = split_npz["X_train"]
    X_test = split_npz["X_test"]
    y_train = split_npz["y_train"]
    y_test = split_npz["y_test"]
    train_idx = split_npz["train_indices"]
    test_idx = split_npz["test_indices"]

    n_samples = len(y)

    # 2. X and y shapes are correct
    if X.ndim != 2 or X.shape[0] != n_samples:
        issues.append(f"X shape mismatch: expected ({n_samples}, 23), got {X.shape}")
    if y.ndim != 1 or y.shape[0] != n_samples:
        issues.append(f"y shape mismatch: expected ({n_samples},), got {y.shape}")

    # 3. Feature count = 23
    if X.shape[1] != FEATURE_COUNT:
        issues.append(f"Feature count mismatch: expected {FEATURE_COUNT}, got {X.shape[1]}")

    # 4. No NaN values
    nan_count = int(np.sum(np.isnan(X)))
    if nan_count > 0:
        issues.append(f"Found {nan_count} NaN values in feature matrix X")

    # 5. No infinite values
    inf_count = int(np.sum(np.isinf(X)))
    if inf_count > 0:
        issues.append(f"Found {inf_count} infinite values in feature matrix X")

    # 6. All expected labels exist
    unique_labels = sorted(list(np.unique(y)))
    expected_labels = sorted([LABEL_MAP[m] for m in info["modulations"]])
    if unique_labels != expected_labels:
        issues.append(f"Unique labels {unique_labels} do not match expected {expected_labels}")

    # 7. Class balance is correct
    expected_samples_per_class = n_samples // len(expected_labels)
    for lbl in expected_labels:
        count = int(np.sum(y == lbl))
        if count != expected_samples_per_class:
            issues.append(f"Class {lbl} is not balanced: expected {expected_samples_per_class}, got {count}")

    # 8. Every SNR level exists
    expected_snrs = list(range(info["snr_min_db"], info["snr_max_db"] + 1, info["snr_step_db"]))
    actual_snrs = sorted([int(round(s)) for s in np.unique(target_snr)])
    if actual_snrs != expected_snrs:
        issues.append(f"SNR levels mismatch: expected {len(expected_snrs)} levels, found {len(actual_snrs)}")

    # 9. Every modulation x SNR combination exists
    # 10. Expected samples per condition are present
    samples_per_cond = info["samples_per_condition"]
    for lbl in expected_labels:
        for snr in expected_snrs:
            cond_count = int(np.sum((y == lbl) & np.isclose(target_snr, snr)))
            if cond_count != samples_per_cond:
                issues.append(
                    f"Condition (label={lbl}, snr={snr}dB) has {cond_count} samples, expected {samples_per_cond}"
                )

    # 11. Metadata row count matches X/y
    metadata_rows = 0
    with open(dataset_dir / "metadata.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for _ in reader:
            metadata_rows += 1
    if metadata_rows != n_samples:
        issues.append(f"Metadata rows ({metadata_rows}) does not match sample count ({n_samples})")

    # 12. Feature names match Phase 2 contract
    if feat_names != list(FEATURE_NAMES):
        issues.append("Feature names do not match Phase 2 FEATURE_NAMES contract")

    # 13. Label mapping is correct
    if label_map.get("class_to_index") != LABEL_MAP:
        issues.append("class_to_index mapping is incorrect")

    # 14. Train/test split sizes are correct
    expected_test_len = int(round(n_samples * info["test_ratio"]))
    expected_train_len = n_samples - expected_test_len
    if len(train_idx) != expected_train_len or len(test_idx) != expected_test_len:
        issues.append(
            f"Train/test size mismatch: expected {expected_train_len}/{expected_test_len}, got {len(train_idx)}/{len(test_idx)}"
        )

    # 15. Train/test contain all modulation classes
    train_classes = set(np.unique(y_train))
    test_classes = set(np.unique(y_test))
    if train_classes != set(expected_labels) or test_classes != set(expected_labels):
        issues.append("Train or test split is missing modulation classes")

    # 16. Train/test contain the expected SNR range
    train_snrs = set(np.round(split_npz["target_snr_train"]).astype(int))
    test_snrs = set(np.round(split_npz["target_snr_test"]).astype(int))
    if train_snrs != set(expected_snrs) or test_snrs != set(expected_snrs):
        issues.append("Train or test split is missing SNR levels")

    # 17. No duplicate examples cross the train/test split (Zero data leakage)
    train_id_set = set(sample_ids[train_idx])
    test_id_set = set(sample_ids[test_idx])
    overlap = train_id_set.intersection(test_id_set)
    if len(overlap) > 0:
        issues.append(f"Data leakage detected! {len(overlap)} sample IDs exist in both train and test splits")

    return (len(issues) == 0), issues

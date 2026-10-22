"""Experiment configuration, metadata extraction, and serialization utilities for Phase 9."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
from typing import Any, Dict, List, Optional, Union
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports" / "phase9"
DEFAULT_DATASET_DIR = PROJECT_ROOT / "backend" / "data" / "datasets"
DEFAULT_MODEL_PATH = PROJECT_ROOT / "backend" / "models" / "modulation_mlp_v1.joblib"


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder converting NumPy types to standard Python primitives."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def get_environment_metadata() -> Dict[str, Any]:
    """Capture hardware and software runtime environment details for scientific reproducibility."""
    import sklearn
    import scipy
    import matplotlib

    return {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "machine_architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "sklearn_version": sklearn.__version__,
        "matplotlib_version": matplotlib.__version__,
        "pid": os.getpid(),
    }


@dataclass
class ExperimentConfig:
    """Standardized metadata container ensuring complete experiment reproducibility."""

    experiment_id: str
    experiment_name: str
    description: str
    random_seed: int = 42
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dataset_version: str = "v1.0"
    model_version: str = "v1.0"
    model_path: str = str(DEFAULT_MODEL_PATH)
    dataset_dir: str = str(DEFAULT_DATASET_DIR)
    output_dir: str = str(DEFAULT_REPORTS_DIR)
    parameters: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=get_environment_metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dataclass to dictionary with ISO-formatted fields."""
        data = asdict(self)
        return data


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists and return Path object."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_json(data: Any, filepath: Union[str, Path], indent: int = 2) -> Path:
    """Save serializable data to JSON using NumpyJSONEncoder."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, cls=NumpyJSONEncoder)
    return path


def save_csv(rows: List[Dict[str, Any]], filepath: Union[str, Path], fieldnames: Optional[List[str]] = None) -> Path:
    """Save list of dictionaries as standard CSV."""
    import csv

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return path

    keys = fieldnames or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            # Format float values cleanly
            clean_row = {}
            for k in keys:
                v = row.get(k)
                if isinstance(v, (np.floating, float)):
                    clean_row[k] = round(float(v), 6)
                else:
                    clean_row[k] = v
            writer.writerow(clean_row)
    return path

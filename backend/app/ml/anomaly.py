"""SNR-aware novelty detection for unsupported/unseen modulations (corrected report fix #8).

Replaces the previous placeholder stub. Wraps an sklearn ``IsolationForest`` trained on
the classifier's *known-modulation* feature vectors so inference can attach an
``is_outlier`` flag and a continuous novelty score to every prediction. The decision
engine maps ``is_outlier=True`` to a REVIEW state (see
``backend.app.decision.rules.RULE_NOVELTY_OUTLIER``).

SNR-awareness: the detector should be fit only on feature vectors captured at usable
SNRs (e.g. >= 10 dB in training or live sessions), where each supported modulation has
a clean, well-separated signature. At low SNR noise dominates and *all* classes drift,
so flagging there would conflate "unseen modulation" with "noisy link" — the low SNR
itself already triggers ``RULE_DEGRADED_SIGNAL``. The fitting corpus is the caller's
responsibility; use :meth:`NoveltyDetector.fit` (or the high-SNR filter in
``scripts/train_cumulant_model.py``) to enforce it.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

DEFAULT_NOVELTY_DETECTOR_PATH = Path("backend/models/novelty_detector.joblib")


class NoveltyDetector:
    """Out-of-distribution detector over feature vectors of supported modulations.

    Uses a scikit-learn ``IsolationForest`` with a fixed random state so results are
    reproducible. ``fit`` expects a 2D array of feature vectors from *supported*
    modulations; ``predict`` returns ``True`` (= novel / unsupported signal) or
    ``False``. ``score_novelty`` exposes a continuous [0, 1] novelty score.
    """

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
        n_estimators: int = 200,
    ):
        self.contamination = contamination
        self.random_state = random_state
        self.n_estimators = n_estimators
        self.forest: Optional[IsolationForest] = None
        self.feature_count: Optional[int] = None
        self.n_training_samples: int = 0

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------
    def fit(self, X: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> "NoveltyDetector":
        """Fit the detector on known-modulation feature vectors.

        Args:
            X: 2D array (n_samples, n_features) of in-distribution features.
            metadata: Optional descriptive fields stored with the model (feature
                set name, SNR range of the fitting corpus, model version, ...).

        Returns:
            Self (enables chaining).

        Raises:
            ValueError: If the matrix is empty, not 2D, or contains non-finite values.
        """
        arr = np.asarray(X, dtype=np.float32)
        if arr.ndim != 2 or arr.shape[0] < 2:
            raise ValueError(
                f"NoveltyDetector.fit expects a 2D matrix with >= 2 rows, got shape {arr.shape}"
            )
        if not np.all(np.isfinite(arr)):
            raise ValueError("NoveltyDetector.fit received NaN or Infinity values")

        self.feature_count = int(arr.shape[1])
        self.n_training_samples = int(arr.shape[0])
        self.forest = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=self.n_estimators,
        )
        self.forest.fit(arr)
        self.fit_metadata = dict(metadata) if metadata else {}
        return self

    @property
    def is_trained(self) -> bool:
        """Whether the detector has been fit."""
        return self.forest is not None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def _validate_vector(self, X: np.ndarray) -> np.ndarray:
        arr = np.asarray(X, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.ndim != 2:
            raise ValueError(f"Feature array must be 1D or 2D, got dimension {arr.ndim}")
        if self.feature_count is not None and arr.shape[1] != self.feature_count:
            raise ValueError(
                f"Expected {self.feature_count} features, got {arr.shape[1]}"
            )
        if arr.shape[0] == 0:
            raise ValueError("Feature matrix cannot be empty")
        if not np.all(np.isfinite(arr)):
            raise ValueError("NoveltyDetector input contains NaN or Infinite values")
        return arr

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return boolean outlier flags per row (True = novel / out-of-distribution).

        Args:
            X: 1D feature vector or 2D feature matrix.

        Returns:
            1D boolean array of length n_samples.
        """
        if self.forest is None:
            raise RuntimeError("NoveltyDetector is not trained. Call fit() first.")
        arr = self._validate_vector(X)
        return self.forest.predict(arr) == -1

    def score_novelty(self, X: np.ndarray) -> np.ndarray:
        """Continuous novelty score in [0, 1] per row (0 = typical, 1 = extreme outlier).

        Maps the IsolationForest decision function, monotonically, from its natural
        range onto [0, 1] via a logistic squashing on the standard normal CDF.

        Args:
            X: 1D feature vector or 2D feature matrix.

        Returns:
            1D float array of length n_samples.
        """
        if self.forest is None:
            raise RuntimeError("NoveltyDetector is not trained. Call fit() first.")
        arr = self._validate_vector(X)
        from scipy.stats import norm

        decision = self.forest.decision_function(arr)  # >0 in-distribution, <0 outlier
        return norm.cdf(-decision)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: Union[str, Path]) -> Path:
        """Serialize the detector (state + forest) to disk.

        Args:
            path: Output path (default: backend/models/novelty_detector.joblib).

        Returns:
            The resolved output path.
        """
        if self.forest is None:
            raise RuntimeError("Cannot save an untrained NoveltyDetector.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        state: Dict[str, Any] = {
            "contamination": self.contamination,
            "random_state": self.random_state,
            "n_estimators": self.n_estimators,
            "feature_count": self.feature_count,
            "n_training_samples": self.n_training_samples,
            "fit_metadata": getattr(self, "fit_metadata", {}),
            "forest": self.forest,
        }
        joblib.dump(state, path)
        return path

    @classmethod
    def load(cls, path: Union[str, Path]) -> "NoveltyDetector":
        """Load a previously saved detector.

        Args:
            path: Path written by :meth:`save`.

        Returns:
            Restored NoveltyDetector instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the payload is not a serialized detector.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Novelty detector file not found: {path}")
        state = joblib.load(path)
        if not isinstance(state, dict) or not isinstance(state.get("forest"), IsolationForest):
            raise ValueError(f"File is not a saved NoveltyDetector: {path}")
        detector = cls(
            contamination=state.get("contamination", 0.05),
            random_state=state.get("random_state", 42),
            n_estimators=state.get("n_estimators", 200),
        )
        detector.forest = state["forest"]
        detector.feature_count = state.get("feature_count")
        detector.n_training_samples = state.get("n_training_samples", 0)
        detector.fit_metadata = state.get("fit_metadata", {})
        return detector


# ----------------------------------------------------------------------
# Module-level convenience
# ----------------------------------------------------------------------
def novelty_check(
    feature_vector: np.ndarray,
    detector_path: Union[str, Path] = DEFAULT_NOVELTY_DETECTOR_PATH,
) -> Optional[Dict[str, Any]]:
    """Attach novelty verdicts to a prediction when a trained detector exists.

    Args:
        feature_vector: 1D feature vector (same contract the classifier consumed).
        detector_path: Where the serialized detector lives.

    Returns:
        None if no trained detector exists at ``detector_path`` (novelty monitoring
        silently absent, as before this fix), otherwise::

            {"is_outlier": bool, "novelty_score": float, "detector_metadata": dict}
    """
    path = Path(detector_path)
    if not path.exists():
        return None
    detector = NoveltyDetector.load(path)
    if detector.feature_count is not None and len(feature_vector) != detector.feature_count:
        return None
    return {
        "is_outlier": bool(detector.predict(feature_vector)[0]),
        "novelty_score": round(float(detector.score_novelty(feature_vector)[0]), 4),
        "detector_metadata": getattr(detector, "fit_metadata", {}),
    }

"""Machine Learning package for SpectrumSentry AI."""

from .dataset import (
    INVERSE_LABEL_MAP,
    LABEL_MAP,
    DatasetConfig,
    DatasetResult,
    calculate_dataset_statistics,
    generate_modulation_dataset,
    save_dataset_artifacts,
    validate_dataset_directory,
)
from .evaluator import (
    compute_confusion_matrix,
    evaluate_performance_across_snr,
    evaluate_predictions,
    generate_classification_report_text,
    plot_confusion_matrix,
    plot_snr_accuracy,
)
from .predictor import (
    ModulationPredictor,
    get_predictor,
    predict_batch,
    predict_single,
)
from .trainer import (
    TrainingConfig,
    build_model_pipeline,
    compare_model_architectures,
    create_development_split,
    load_trained_model,
    load_training_dataset,
    save_trained_model,
    train_model,
)

__all__ = [
    # Dataset
    "LABEL_MAP",
    "INVERSE_LABEL_MAP",
    "DatasetConfig",
    "DatasetResult",
    "calculate_dataset_statistics",
    "generate_modulation_dataset",
    "save_dataset_artifacts",
    "validate_dataset_directory",
    # Evaluator
    "evaluate_predictions",
    "compute_confusion_matrix",
    "plot_confusion_matrix",
    "evaluate_performance_across_snr",
    "plot_snr_accuracy",
    "generate_classification_report_text",
    # Trainer
    "TrainingConfig",
    "load_training_dataset",
    "create_development_split",
    "build_model_pipeline",
    "compare_model_architectures",
    "train_model",
    "save_trained_model",
    "load_trained_model",
    # Predictor
    "ModulationPredictor",
    "get_predictor",
    "predict_single",
    "predict_batch",
]

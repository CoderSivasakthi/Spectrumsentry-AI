"""Decision Engine module (Phase 6).

Correlates physical-layer signal classification with application-layer network telemetry
to produce unified, deterministic, explainable communication assessments.
"""

from .correlator import (
    build_communication_summary,
    build_signal_summary,
    compute_decision_confidence,
)
from .engine import DecisionEngine, decision_engine
from .rules import evaluate_rules, get_all_rules_info

__all__ = [
    "DecisionEngine",
    "decision_engine",
    "evaluate_rules",
    "get_all_rules_info",
    "compute_decision_confidence",
    "build_signal_summary",
    "build_communication_summary",
]

"""Decision Engine Scientific Evaluation Module for Phase 9.

Tests the deterministic Phase 6 Decision Engine across all rule categories:
1. Complete rule coverage (7 production rules).
2. Cross-domain conflict scenarios (Scenario A: High SNR + High Loss; Scenario B: Clean Comm + Low Conf).
3. Partial/Uncorrelated evidence (Comm only, Signal only, neither available).
4. Deterministic confidence scoring and explainable reason formulation.
"""

from pathlib import Path
from typing import Any, Dict, List
import matplotlib.pyplot as plt
import numpy as np

from backend.app.decision.engine import DecisionEngine
from backend.app.schemas.decision import (
    CommunicationEvidence,
    ConsistencyStatus,
    DecisionInput,
    OverallStatus,
    SignalEvidence,
)
from experiments.common.config import (
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_csv,
    save_json,
)
from experiments.common.plotting import COLOR_DANGER, COLOR_PRIMARY, COLOR_SECONDARY, COLOR_SUCCESS, COLOR_WARNING


class DecisionEngineEvaluator:
    """Scientific evaluation suite for Phase 6 multi-domain evidence correlation."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.decision_output_dir = self.output_dir / "decision"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed
        self.engine = DecisionEngine()

    def evaluate_rule_coverage(self) -> List[Dict[str, Any]]:
        """Verify each production rule executes deterministically and maps to expected status."""
        scenarios = [
            # 1. Interrupted Link
            {
                "rule_id": "RULE_INTERRUPTED_LINK",
                "scenario_name": "Active Communication Timeout",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.95, measured_snr_db=15.0),
                "comm": CommunicationEvidence(is_interrupted=True, packet_loss_percent=100.0, health_score=0.0),
                "expected_status": OverallStatus.INTERRUPTED,
                "expected_consistency": ConsistencyStatus.UNCORRELATED,
            },
            # 2. Recovering Link
            {
                "rule_id": "RULE_RECOVERING_LINK",
                "scenario_name": "Link Recovery Restabilization",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.96, measured_snr_db=14.0),
                "comm": CommunicationEvidence(status="RECOVERING", is_recovering=True, packet_loss_percent=5.0, health_score=75.0),
                "expected_status": OverallStatus.RECOVERING,
                "expected_consistency": ConsistencyStatus.CONSISTENT,
            },
            # 3. Conflict Scenario A
            {
                "rule_id": "RULE_CONFLICT_HIGH_SNR_HIGH_LOSS",
                "scenario_name": "Conflict A: High SNR with Severe Loss",
                "signal": SignalEvidence(predicted_modulation="16-QAM", confidence=0.98, measured_snr_db=22.0),
                "comm": CommunicationEvidence(packet_loss_percent=20.0, avg_latency_ms=45.0, health_score=40.0),
                "expected_status": OverallStatus.REVIEW,
                "expected_consistency": ConsistencyStatus.CONFLICTING,
            },
            # 4. Conflict Scenario B
            {
                "rule_id": "RULE_CONFLICT_CLEAN_COMM_LOW_CONFIDENCE",
                "scenario_name": "Conflict B: Clean Comm with Low AI Confidence",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.45, measured_snr_db=12.0),
                "comm": CommunicationEvidence(packet_loss_percent=0.0, avg_latency_ms=8.0, health_score=98.0),
                "expected_status": OverallStatus.REVIEW,
                "expected_consistency": ConsistencyStatus.CONFLICTING,
            },
            # 5. Degraded Network
            {
                "rule_id": "RULE_DEGRADED_NETWORK",
                "scenario_name": "Elevated Packet Loss Network Degradation",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.92, measured_snr_db=3.0),
                "comm": CommunicationEvidence(status="DEGRADED", packet_loss_percent=8.5, avg_latency_ms=25.0, health_score=68.0),
                "expected_status": OverallStatus.DEGRADED,
                "expected_consistency": ConsistencyStatus.CONSISTENT,
            },
            # 6. Degraded Signal
            {
                "rule_id": "RULE_DEGRADED_SIGNAL",
                "scenario_name": "Sub-zero Negative SNR Degradation",
                "signal": SignalEvidence(predicted_modulation="BPSK", confidence=0.65, measured_snr_db=-3.0),
                "comm": CommunicationEvidence(packet_loss_percent=2.0, avg_latency_ms=15.0, health_score=85.0),
                "expected_status": OverallStatus.DEGRADED,
                "expected_consistency": ConsistencyStatus.CONSISTENT,
            },
            # 7. Normal Operation
            {
                "rule_id": "RULE_NORMAL_OPERATION",
                "scenario_name": "Nominal Wireless & Network Operation",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.99, measured_snr_db=18.0),
                "comm": CommunicationEvidence(packet_loss_percent=0.0, avg_latency_ms=6.0, health_score=100.0),
                "expected_status": OverallStatus.NORMAL,
                "expected_consistency": ConsistencyStatus.CONSISTENT,
            },
        ]

        results = []
        for s in scenarios:
            inp = DecisionInput(signal_evidence=s["signal"], communication_evidence=s["comm"])
            out = self.engine.evaluate(inp)

            status_matched = out.overall_status == s["expected_status"]
            consistency_matched = out.consistency == s["expected_consistency"]
            rule_matched = s["rule_id"] in out.rules_triggered
            passed = status_matched and consistency_matched and rule_matched

            results.append({
                "rule_id": s["rule_id"],
                "scenario_name": s["scenario_name"],
                "expected_status": s["expected_status"].value,
                "actual_status": out.overall_status.value,
                "expected_consistency": s["expected_consistency"].value,
                "actual_consistency": out.consistency.value,
                "decision_confidence": round(out.decision_confidence, 4),
                "primary_reason": out.primary_reason,
                "rules_triggered": out.rules_triggered,
                "recommendations_count": len(out.recommendations),
                "status_matched": status_matched,
                "consistency_matched": consistency_matched,
                "rule_matched": rule_matched,
                "passed": passed,
            })

        return results

    def evaluate_partial_evidence(self) -> List[Dict[str, Any]]:
        """Evaluate handling of partial, single-domain, or missing evidence."""
        partial_scenarios = [
            # Communication only
            {
                "scenario": "Communication Evidence Only (No Signal)",
                "signal": None,
                "comm": CommunicationEvidence(packet_loss_percent=0.0, avg_latency_ms=10.0, health_score=95.0),
                "expected_status": OverallStatus.NORMAL,
                "expected_consistency": ConsistencyStatus.UNCORRELATED,
            },
            # Signal only
            {
                "scenario": "Signal Evidence Only (No Comm)",
                "signal": SignalEvidence(predicted_modulation="QPSK", confidence=0.95, measured_snr_db=15.0),
                "comm": None,
                "expected_status": OverallStatus.NORMAL,
                "expected_consistency": ConsistencyStatus.UNCORRELATED,
            },
            # Neither available
            {
                "scenario": "Neither Evidence Domain Available",
                "signal": None,
                "comm": None,
                "expected_status": OverallStatus.NORMAL,
                "expected_consistency": ConsistencyStatus.UNCORRELATED,
            },
        ]

        results = []
        for ps in partial_scenarios:
            inp = DecisionInput(signal_evidence=ps["signal"], communication_evidence=ps["comm"])
            out = self.engine.evaluate(inp)

            passed = (
                out.overall_status == ps["expected_status"]
                and out.consistency == ps["expected_consistency"]
            )
            results.append({
                "scenario": ps["scenario"],
                "expected_status": ps["expected_status"].value,
                "actual_status": out.overall_status.value,
                "expected_consistency": ps["expected_consistency"].value,
                "actual_consistency": out.consistency.value,
                "decision_confidence": round(out.decision_confidence, 4),
                "passed": passed,
            })

        return results

    def plot_rule_evaluation(self, results: List[Dict[str, Any]]) -> Path:
        """Plot decision confidence across all 7 evaluated rules."""
        plot_p = self.plots_dir / "decision_confidence_breakdown.png"
        plot_p.parent.mkdir(parents=True, exist_ok=True)

        rule_names = [r["rule_id"].replace("RULE_", "") for r in results]
        confidences = [r["decision_confidence"] * 100 for r in results]
        statuses = [r["actual_status"] for r in results]

        color_map = {
            "NORMAL": COLOR_SUCCESS,
            "DEGRADED": COLOR_WARNING,
            "INTERRUPTED": COLOR_DANGER,
            "RECOVERING": COLOR_PRIMARY,
            "REVIEW": COLOR_SECONDARY,
        }
        bar_colors = [color_map.get(st, COLOR_PRIMARY) for st in statuses]

        fig, ax = plt.subplots(figsize=(9, 4.8), dpi=300)
        bars = ax.bar(rule_names, confidences, color=bar_colors, edgecolor="#1e293b", width=0.6)

        ax.set_ylabel("Decision Confidence [%]")
        ax.set_title("Decision Engine Rule Confidence and Assessment Mapping", pad=12)
        ax.set_ylim(0, 110)
        plt.xticks(rotation=25, ha="right", fontsize=9)

        for bar, conf, st in zip(bars, confidences, statuses):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 2,
                f"{conf:.0f}%\n({st})",
                ha="center",
                va="bottom",
                fontsize=8,
                fontweight="bold",
            )

        plt.tight_layout()
        plt.savefig(plot_p, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return plot_p

    def run_all(self) -> Dict[str, Any]:
        """Execute full Decision Engine evaluation suite."""
        rule_results = self.evaluate_rule_coverage()
        partial_results = self.evaluate_partial_evidence()

        all_rules_passed = all(r["passed"] for r in rule_results)
        all_partial_passed = all(r["passed"] for r in partial_results)

        cfg = ExperimentConfig(
            experiment_id="EXP-DEC-01",
            experiment_name="decision_engine_evaluation",
            description="Verification of all 7 Phase 6 decision rules, cross-domain conflict scenarios, and partial evidence.",
            random_seed=self.random_seed,
            parameters={
                "rules_tested": len(rule_results),
                "partial_scenarios_tested": len(partial_results),
            },
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "summary": {
                "total_rules_evaluated": len(rule_results),
                "all_rules_passed": all_rules_passed,
                "partial_evidence_scenarios_evaluated": len(partial_results),
                "all_partial_passed": all_partial_passed,
            },
            "rule_coverage": rule_results,
            "partial_evidence": partial_results,
        }

        # Save files
        self.decision_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_data, self.decision_output_dir / "decision_rule_evaluation.json")
        save_csv(rule_results, self.decision_output_dir / "decision_rule_evaluation.csv")

        # Plot
        self.plot_rule_evaluation(rule_results)

        return output_data

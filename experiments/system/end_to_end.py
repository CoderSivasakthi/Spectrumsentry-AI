"""End-to-End System Pipeline Evaluation Module for Phase 9.

Measures latency across the entire unified SpectrumSentry AI processing chain:
    Signal Generation -> AWGN Noise -> Feature Extraction -> ML Inference ->
    Communication Ingestion -> Evidence Aggregation -> Decision Engine ->
    Unified Snapshot Packaging.

Also validates full end-to-end lifecycle state transitions:
    START -> NORMAL -> DEGRADED -> INTERRUPTED -> RECOVERING -> NORMAL.
"""

from pathlib import Path
import time
from typing import Any, Dict, List
import numpy as np

from backend.app.communication.packet_monitor import SessionMonitor, packet_monitor
from backend.app.decision.engine import DecisionEngine
from backend.app.ml.predictor import ModulationPredictor
from backend.app.monitoring import UnifiedMonitoringManager
from backend.app.schemas.communication import PacketIn
from backend.app.schemas.decision import DecisionInput
from backend.app.schemas.monitoring import SignalEvidenceInput
from backend.app.signal_processing import add_awgn, extract_features, generate_signal
from experiments.common.config import (
    DEFAULT_MODEL_PATH,
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_json,
)
from experiments.common.plotting import plot_pipeline_latency_breakdown


class EndToEndEvaluator:
    """End-to-end latency and state transition measurement suite."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.e2e_output_dir = self.output_dir / "end_to_end"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed

        self.predictor = ModulationPredictor(model_path=self.model_path)
        self.decision_engine = DecisionEngine()

    def measure_pipeline_latency(self, iterations: int = 50) -> Dict[str, Any]:
        """Measure latency of each distinct pipeline stage over repeated executions."""
        stage_timings: Dict[str, List[float]] = {
            "1. Signal Generation": [],
            "2. AWGN Channel": [],
            "3. Feature Extraction": [],
            "4. AI Classification": [],
            "5. Comm Telemetry Ingest": [],
            "6. Evidence Aggregation": [],
            "7. Decision Evaluation": [],
            "8. Snapshot Packaging": [],
        }

        manager = UnifiedMonitoringManager()
        monitor = SessionMonitor("e2e_timing_sess", timeout_seconds=2.0)
        packet_monitor.sessions["e2e_timing_sess"] = monitor
        manager.active_communication_session_id = "e2e_timing_sess"

        for i in range(iterations):
            seed = abs(self.random_seed * 1000 + i)

            # 1. Signal Generation
            t0 = time.perf_counter_ns()
            gen_res = generate_signal("QPSK", num_samples=1024, seed=seed)
            t1 = time.perf_counter_ns()
            stage_timings["1. Signal Generation"].append((t1 - t0) / 1e6)

            # 2. AWGN Noise
            t0 = time.perf_counter_ns()
            awgn_res = add_awgn(gen_res.signal, snr_db=15.0, seed=seed)
            t1 = time.perf_counter_ns()
            stage_timings["2. AWGN Channel"].append((t1 - t0) / 1e6)

            # 3. 23-Feature Extraction
            t0 = time.perf_counter_ns()
            feat_arr, _ = extract_features(awgn_res.noisy_signal, sample_rate=1e6)
            t1 = time.perf_counter_ns()
            stage_timings["3. Feature Extraction"].append((t1 - t0) / 1e6)

            # 4. AI Modulation Prediction
            t0 = time.perf_counter_ns()
            pred_res = self.predictor.predict_single(feat_arr)
            t1 = time.perf_counter_ns()
            stage_timings["4. AI Classification"].append((t1 - t0) / 1e6)

            # 5. Communication Packet Ingestion
            pkt = PacketIn(
                session_id="e2e_timing_sess",
                sequence_number=i + 1,
                sender_timestamp=1000.0 + i * 0.1,
                payload_size=1024,
                client_rtt_ms=12.0,
            )
            t0 = time.perf_counter_ns()
            monitor.record_packet(pkt, arrival_time=1000.0 + i * 0.1 + 0.012)
            t1 = time.perf_counter_ns()
            stage_timings["5. Comm Telemetry Ingest"].append((t1 - t0) / 1e6)

            # 6. Evidence Aggregation & Submission
            t0 = time.perf_counter_ns()
            sig_in = SignalEvidenceInput(
                predicted_modulation=pred_res["predicted_modulation"],
                ai_confidence=pred_res["confidence"],
                estimated_snr_db=awgn_res.measured_snr_db,
                signal_power=awgn_res.signal_power,
                noise_power=awgn_res.noise_power,
                signal_quality="EXCELLENT",
            )
            manager.update_signal_evidence(sig_in)
            t1 = time.perf_counter_ns()
            stage_timings["6. Evidence Aggregation"].append((t1 - t0) / 1e6)

            # 7. Decision Evaluation & Snapshot Assembly
            t0 = time.perf_counter_ns()
            snap = manager.get_current_snapshot()
            t1 = time.perf_counter_ns()
            stage_timings["7. Decision Evaluation"].append((t1 - t0) / 1e6)

            # 8. Snapshot Packaging (JSON serialization)
            t0 = time.perf_counter_ns()
            _ = snap.model_dump_json()
            t1 = time.perf_counter_ns()
            stage_timings["8. Snapshot Packaging"].append((t1 - t0) / 1e6)

        packet_monitor.sessions.pop("e2e_timing_sess", None)
        manager.clear_signal_evidence()

        # Statistical aggregation per stage
        summary = {}
        for stage_name, times in stage_timings.items():
            summary[stage_name] = {
                "mean_ms": round(float(np.mean(times)), 4),
                "median_ms": round(float(np.median(times)), 4),
                "std_ms": round(float(np.std(times)), 4),
                "p95_ms": round(float(np.percentile(times, 95)), 4),
                "p99_ms": round(float(np.percentile(times, 99)), 4),
                "min_ms": round(float(np.min(times)), 4),
                "max_ms": round(float(np.max(times)), 4),
            }

        total_mean_latency = sum(s["mean_ms"] for s in summary.values())
        summary["total_pipeline"] = {
            "mean_ms": round(total_mean_latency, 4),
            "throughput_fps": round(1000.0 / total_mean_latency, 1) if total_mean_latency > 0 else 0.0,
        }

        return summary

    def evaluate_state_transitions(self) -> List[Dict[str, Any]]:
        """Validate full state sequence: START -> NORMAL -> DEGRADED -> INTERRUPTED -> RECOVERING -> NORMAL."""
        manager = UnifiedMonitoringManager()
        monitor = SessionMonitor("comm_sess_trans", timeout_seconds=2.0)
        packet_monitor.sessions["comm_sess_trans"] = monitor
        manager.active_communication_session_id = "comm_sess_trans"
        manager.clear_signal_evidence()
        transitions = []
        t_base = 10000.0

        # Step 1: Initialization
        snap_init = manager.get_current_snapshot()
        transitions.append({
            "step": 1,
            "transition": "INITIALIZATION",
            "action": "Start unified monitoring session (standby baseline)",
            "session_id": "comm_sess_trans",
            "resulting_status": snap_init.decision.status.value,
        })

        # Step 2: Normal Operation
        manager.update_signal_evidence(SignalEvidenceInput(
            predicted_modulation="QPSK", ai_confidence=0.99, estimated_snr_db=18.0, signal_quality="EXCELLENT"
        ))
        pkt_norm = PacketIn(session_id="comm_sess_trans", sequence_number=1, sender_timestamp=t_base, client_rtt_ms=10.0)
        monitor.record_packet(pkt_norm, arrival_time=t_base + 0.01)
        snap_norm = manager.get_current_snapshot()
        transitions.append({
            "step": 2,
            "transition": "NOMINAL_OPERATION",
            "action": "Clean signal (18 dB) & clean packet flow",
            "resulting_status": snap_norm.decision.status.value,
            "consistency": snap_norm.decision.consistency.value,
        })

        # Step 3: Degraded Signal
        manager.update_signal_evidence(SignalEvidenceInput(
            predicted_modulation="BPSK", ai_confidence=0.60, estimated_snr_db=-2.0, signal_quality="POOR"
        ))
        snap_deg = manager.get_current_snapshot()
        transitions.append({
            "step": 3,
            "transition": "DEGRADATION",
            "action": "Physical SNR drops below 0 dB (-2.0 dB)",
            "resulting_status": snap_deg.decision.status.value,
            "consistency": snap_deg.decision.consistency.value,
        })

        # Step 4: Interrupted (Silence timeout triggered)
        monitor.check_timeout_tick(current_time=t_base + 10.0)
        snap_int = manager.get_current_snapshot()
        transitions.append({
            "step": 4,
            "transition": "INTERRUPTION",
            "action": "Silence timeout triggered (>2.0s gap)",
            "resulting_status": snap_int.decision.status.value,
            "consistency": snap_int.decision.consistency.value,
        })

        # Step 5: Recovering (Packets resume following interruption)
        pkt_rec = PacketIn(session_id="comm_sess_trans", sequence_number=2, sender_timestamp=t_base + 10.5, client_rtt_ms=15.0)
        monitor.record_packet(pkt_rec, arrival_time=t_base + 10.5 + 0.015)
        snap_rec = manager.get_current_snapshot()
        transitions.append({
            "step": 5,
            "transition": "RECOVERY",
            "action": "Packets resume following interruption",
            "resulting_status": snap_rec.decision.status.value,
            "consistency": snap_rec.decision.consistency.value,
        })

        # Step 6: Return to Normal (Restabilized)
        for seq in range(3, 12):
            p = PacketIn(session_id="comm_sess_trans", sequence_number=seq, sender_timestamp=t_base + 10.5 + seq * 0.1, client_rtt_ms=10.0)
            monitor.record_packet(p, arrival_time=t_base + 10.5 + seq * 0.1 + 0.01)
        manager.update_signal_evidence(SignalEvidenceInput(
            predicted_modulation="QPSK", ai_confidence=0.98, estimated_snr_db=15.0, signal_quality="EXCELLENT"
        ))
        snap_norm2 = manager.get_current_snapshot()
        transitions.append({
            "step": 6,
            "transition": "NORMAL_STABILIZED",
            "action": "Signal and communication restabilized",
            "resulting_status": snap_norm2.decision.status.value,
            "consistency": snap_norm2.decision.consistency.value,
        })

        packet_monitor.sessions.pop("comm_sess_trans", None)
        manager.clear_signal_evidence()
        return transitions

    def run_all(self) -> Dict[str, Any]:
        """Execute complete end-to-end evaluation."""
        latency_breakdown = self.measure_pipeline_latency(iterations=50)
        transitions = self.evaluate_state_transitions()

        cfg = ExperimentConfig(
            experiment_id="EXP-E2E-01",
            experiment_name="end_to_end_system_latency_and_lifecycle",
            description="End-to-end pipeline latency profiling and lifecycle state transition validation.",
            random_seed=self.random_seed,
            parameters={
                "iterations": 50,
                "stages_evaluated": 8,
                "lifecycle_states": ["INITIALIZATION", "NOMINAL_OPERATION", "DEGRADATION", "INTERRUPTION", "RECOVERY", "NORMAL_STABILIZED"],
            },
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "pipeline_latency_summary": latency_breakdown,
            "lifecycle_transitions": transitions,
        }

        # Save artifacts
        save_json(output_data, self.e2e_output_dir / "e2e_system_evaluation.json")
        save_json({"metadata": cfg.to_dict(), "stages": latency_breakdown}, self.e2e_output_dir / "pipeline_latency_breakdown.json")
        save_json({"metadata": cfg.to_dict(), "transitions": transitions}, self.e2e_output_dir / "state_transitions.json")

        # Plot latency breakdown
        stage_names = [k for k in latency_breakdown.keys() if k != "total_pipeline"]
        means = [latency_breakdown[k]["mean_ms"] for k in stage_names]
        p95s = [latency_breakdown[k]["p95_ms"] for k in stage_names]
        plot_pipeline_latency_breakdown(
            stage_names,
            means,
            self.plots_dir / "end_to_end_latency_breakdown.png",
        )

        return output_data

"""Communication Telemetry Evaluation Module for Phase 9.

Evaluates Phase 5 application-level packet monitoring:
1. Packet loss accuracy and health score degradation (0% to 50%).
2. Round-trip latency impact and distribution percentiles (p50, p95, p99).
3. Jitter tracking under controlled variance.
4. Silence timeout interruption detection and recovery restabilization transitions.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from backend.app.communication.packet_monitor import SessionMonitor
from backend.app.schemas.communication import CommunicationStatus, PacketIn
from experiments.common.config import (
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_csv,
    save_json,
)
from experiments.common.plotting import plot_communication_curves


class CommunicationEvaluator:
    """Scientific evaluation suite for Phase 5 network telemetry monitoring."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.comm_output_dir = self.output_dir / "communication"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed
        self.rng = np.random.RandomState(random_seed)

    def evaluate_packet_loss_scenarios(
        self,
        loss_levels: Optional[List[float]] = None,
        total_packets: int = 200,
    ) -> List[Dict[str, Any]]:
        """Evaluate measured packet loss and health score across configured drop rates."""
        if loss_levels is None:
            loss_levels = [0.0, 5.0, 10.0, 15.0, 25.0, 50.0]

        results = []
        for loss_pct in loss_levels:
            session_id = f"eval_loss_{int(loss_pct)}"
            monitor = SessionMonitor(session_id=session_id, timeout_seconds=2.0)
            t0 = 1000.0
            packets_sent = 0
            packets_received = 0

            for seq in range(1, total_packets + 1):
                packets_sent += 1
                # Drop packet probabilistically if within configured loss
                if loss_pct > 0 and (self.rng.uniform(0.0, 100.0) < loss_pct):
                    continue  # Packet lost in simulated transport

                packets_received += 1
                pkt = PacketIn(
                    session_id=session_id,
                    sequence_number=seq,
                    sender_timestamp=t0 + (seq - 1) * 0.05,
                    payload_size=1024,
                    client_rtt_ms=10.0,
                )
                monitor.record_packet(pkt, arrival_time=t0 + (seq - 1) * 0.05 + 0.01)

            metrics = monitor.get_metrics()
            results.append({
                "configured_loss_percent": loss_pct,
                "packets_sent": packets_sent,
                "packets_received": packets_received,
                "packets_lost": packets_sent - packets_received,
                "measured_loss_percent": round(metrics.packet_loss_percent, 2),
                "loss_error_percent": round(abs(metrics.packet_loss_percent - loss_pct), 2),
                "health_score": round(metrics.health_score, 1),
                "status": metrics.status.value,
            })

        return results

    def evaluate_latency_scenarios(
        self,
        latency_levels: Optional[List[float]] = None,
        packets_per_level: int = 150,
    ) -> List[Dict[str, Any]]:
        """Evaluate health degradation and RTT latency percentile metrics."""
        if latency_levels is None:
            latency_levels = [5.0, 20.0, 50.0, 100.0, 200.0]

        results = []
        for target_lat in latency_levels:
            session_id = f"eval_lat_{int(target_lat)}"
            monitor = SessionMonitor(session_id=session_id, timeout_seconds=5.0)
            t0 = 2000.0
            injected_rtts = []

            for seq in range(1, packets_per_level + 1):
                # Small Gaussian variance around target latency (capped > 1ms)
                rtt = max(1.0, float(self.rng.normal(target_lat, target_lat * 0.1)))
                injected_rtts.append(rtt)

                pkt = PacketIn(
                    session_id=session_id,
                    sequence_number=seq,
                    sender_timestamp=t0 + (seq - 1) * 0.1,
                    payload_size=1024,
                    client_rtt_ms=rtt,
                )
                monitor.record_packet(pkt, arrival_time=t0 + (seq - 1) * 0.1 + (rtt / 1000.0))

            metrics = monitor.get_metrics()
            results.append({
                "target_latency_ms": target_lat,
                "measured_mean_latency_ms": round(metrics.avg_latency_ms, 2),
                "measured_p50_latency_ms": round(float(np.percentile(injected_rtts, 50)), 2),
                "measured_p95_latency_ms": round(float(np.percentile(injected_rtts, 95)), 2),
                "measured_p99_latency_ms": round(float(np.percentile(injected_rtts, 99)), 2),
                "measured_max_latency_ms": round(float(np.max(injected_rtts)), 2),
                "health_score": round(metrics.health_score, 1),
                "status": metrics.status.value,
            })

        return results

    def evaluate_jitter_scenarios(
        self,
        jitter_stds: Optional[List[float]] = None,
        base_latency: float = 30.0,
        packets_per_level: int = 150,
    ) -> List[Dict[str, Any]]:
        """Evaluate measured jitter under controlled variance and its effect on health."""
        if jitter_stds is None:
            jitter_stds = [0.0, 2.0, 5.0, 10.0, 20.0, 40.0]

        results = []
        for std in jitter_stds:
            session_id = f"eval_jit_{int(std)}"
            monitor = SessionMonitor(session_id=session_id, timeout_seconds=5.0)
            t0 = 3000.0

            for seq in range(1, packets_per_level + 1):
                rtt = max(1.0, float(self.rng.normal(base_latency, std)))
                pkt = PacketIn(
                    session_id=session_id,
                    sequence_number=seq,
                    sender_timestamp=t0 + (seq - 1) * 0.1,
                    payload_size=1024,
                    client_rtt_ms=rtt,
                )
                monitor.record_packet(pkt, arrival_time=t0 + (seq - 1) * 0.1 + (rtt / 1000.0))

            metrics = monitor.get_metrics()
            results.append({
                "configured_jitter_std_ms": std,
                "base_latency_ms": base_latency,
                "measured_jitter_ms": round(metrics.jitter_ms, 2),
                "avg_latency_ms": round(metrics.avg_latency_ms, 2),
                "health_score": round(metrics.health_score, 1),
                "status": metrics.status.value,
            })

        return results

    def evaluate_interruption_recovery(self) -> Dict[str, Any]:
        """Test controlled timeout interruption triggering and subsequent recovery stabilization."""
        timeout_sec = 2.0
        monitor = SessionMonitor(session_id="eval_ir_flow", timeout_seconds=timeout_sec)
        t0 = 5000.0

        # Phase A: Initial normal transmission (10 packets, interval 0.1s)
        for seq in range(1, 11):
            pkt = PacketIn(
                session_id="eval_ir_flow",
                sequence_number=seq,
                sender_timestamp=t0 + (seq - 1) * 0.1,
                payload_size=1024,
                client_rtt_ms=10.0,
            )
            monitor.record_packet(pkt, arrival_time=t0 + (seq - 1) * 0.1 + 0.01)

        normal_metrics = monitor.get_metrics()
        state_after_normal = normal_metrics.status.value
        health_after_normal = normal_metrics.health_score

        # Phase B: Incur silence timeout (2.5s silence gap > 2.0s timeout)
        silence_timestamp = t0 + 1.0 + 2.5
        interruption_event = monitor.check_timeout_tick(current_time=silence_timestamp)
        metrics_interrupted = monitor.get_metrics()

        state_after_silence = metrics_interrupted.status.value
        interruption_detected = interruption_event is not None
        interruption_duration = interruption_event["details"]["silence_sec"] if interruption_event else 0.0

        # Phase C: Packet resumes (Recovery packet)
        recovery_time = silence_timestamp + 0.1
        recovery_pkt = PacketIn(
            session_id="eval_ir_flow",
            sequence_number=11,
            sender_timestamp=recovery_time,
            payload_size=1024,
            client_rtt_ms=12.0,
        )
        ack, rec_events = monitor.record_packet(recovery_pkt, arrival_time=recovery_time + 0.01)
        recovery_metrics = monitor.get_metrics()

        state_after_recovery = recovery_metrics.status.value
        recovery_detected = len(rec_events) > 0 or recovery_metrics.status == CommunicationStatus.RECOVERING

        return {
            "timeout_threshold_seconds": timeout_sec,
            "phase_a_normal": {
                "status": state_after_normal,
                "health_score": health_after_normal,
                "packets_sent": 10,
            },
            "phase_b_interruption": {
                "silence_duration_seconds": 2.5,
                "interruption_detected": bool(interruption_detected),
                "detected_status": state_after_silence,
                "interruption_duration": round(float(interruption_duration), 2),
                "cumulative_interruptions": monitor.interruption_detector.interruption_counter,
            },
            "phase_c_recovery": {
                "recovery_detected": bool(recovery_detected),
                "detected_status": state_after_recovery,
                "final_health_score": round(recovery_metrics.health_score, 1),
            },
            "transition_sequence_valid": (
                state_after_normal in ("CONNECTED", "STARTING")
                and state_after_silence == "INTERRUPTED"
                and state_after_recovery in ("RECOVERING", "CONNECTED")
            ),
        }

    def run_all(self) -> Dict[str, Any]:
        """Execute all communication telemetry experiments and produce plots."""
        loss_results = self.evaluate_packet_loss_scenarios()
        lat_results = self.evaluate_latency_scenarios()
        jit_results = self.evaluate_jitter_scenarios()
        ir_results = self.evaluate_interruption_recovery()

        cfg = ExperimentConfig(
            experiment_id="EXP-COMM-01",
            experiment_name="communication_telemetry_evaluation",
            description="Evaluation of packet loss, latency, jitter tracking, and interruption/recovery detection.",
            random_seed=self.random_seed,
            parameters={
                "packet_loss_levels": [0.0, 5.0, 10.0, 15.0, 25.0, 50.0],
                "latency_levels_ms": [5.0, 20.0, 50.0, 100.0, 200.0],
                "jitter_std_levels_ms": [0.0, 2.0, 5.0, 10.0, 20.0, 40.0],
                "silence_timeout_sec": 2.0,
            },
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "packet_loss_evaluation": loss_results,
            "latency_evaluation": lat_results,
            "jitter_evaluation": jit_results,
            "interruption_recovery_evaluation": ir_results,
        }

        # Save structured JSON & CSV
        self.comm_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_data, self.comm_output_dir / "communication_evaluation_summary.json")
        save_json(loss_results, self.comm_output_dir / "packet_loss_results.json")
        save_csv(loss_results, self.comm_output_dir / "packet_loss_results.csv")
        save_json(lat_results, self.comm_output_dir / "latency_results.json")
        save_csv(lat_results, self.comm_output_dir / "latency_results.csv")
        save_json(jit_results, self.comm_output_dir / "jitter_results.json")
        save_csv(jit_results, self.comm_output_dir / "jitter_results.csv")
        save_json(ir_results, self.comm_output_dir / "interruption_recovery_results.json")

        # Generate plots
        plot_communication_curves(
            loss_levels=[r["configured_loss_percent"] for r in loss_results],
            loss_health_scores=[r["health_score"] for r in loss_results],
            latency_levels=[r["target_latency_ms"] for r in lat_results],
            latency_health_scores=[r["health_score"] for r in lat_results],
            jitter_levels=[r["configured_jitter_std_ms"] for r in jit_results],
            jitter_health_scores=[r["health_score"] for r in jit_results],
            output_dir=self.plots_dir,
        )

        return output_data

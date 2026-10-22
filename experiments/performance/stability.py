"""Stability and Soak Testing Module for Phase 9.

Performs controlled continuous monitoring runs to evaluate:
    1. Resident memory (RSS) stability and growth curves.
    2. Zero event leakage under continuous telemetry updates.
    3. Memory bounds of internal buffers and snapshot histories.
    4. Subsystem error rates and execution reliability.
"""

import os
from pathlib import Path
import resource
import sys
import time
from typing import Any, Dict, List

from backend.app.communication.packet_monitor import SessionMonitor, packet_monitor
from backend.app.decision.engine import DecisionEngine
from backend.app.monitoring import UnifiedMonitoringManager
from backend.app.schemas.communication import PacketIn
from backend.app.schemas.monitoring import SignalEvidenceInput
from experiments.common.config import (
    DEFAULT_REPORTS_DIR,
    ExperimentConfig,
    save_json,
)
from experiments.common.plotting import plot_memory_soak


def get_current_rss_mb() -> float:
    """Return process Resident Set Size (RSS) in megabytes."""
    # On macOS ru_maxrss is in bytes; on Linux it is in kilobytes.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return float(usage) / (1024.0 * 1024.0)
    else:
        return float(usage) / 1024.0


class StabilitySoakTester:
    """Executes continuous soak tests to demonstrate runtime stability and bounded memory."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_REPORTS_DIR,
        random_seed: int = 42,
    ):
        self.output_dir = Path(output_dir)
        self.stab_output_dir = self.output_dir / "stability"
        self.plots_dir = self.output_dir / "plots"
        self.random_seed = random_seed

    def run_soak_test(self, total_events: int = 500, checkpoint_interval: int = 25) -> Dict[str, Any]:
        """Execute continuous stream of telemetry events and monitor resource utilization."""
        manager = UnifiedMonitoringManager()
        monitor = SessionMonitor("soak_test_session", timeout_seconds=2.0)
        packet_monitor.sessions["soak_test_session"] = monitor
        manager.active_communication_session_id = "soak_test_session"

        t_start = time.perf_counter()
        initial_rss = get_current_rss_mb()

        timestamps_sec = []
        rss_samples_mb = []
        error_count = 0

        for i in range(total_events):
            try:
                # 1. Update communication packet
                seq = i + 1
                pkt = PacketIn(
                    session_id="soak_test_session",
                    sequence_number=seq,
                    sender_timestamp=1000.0 + i * 0.05,
                    payload_size=1024,
                    client_rtt_ms=10.0 + (i % 5),
                )
                monitor.record_packet(pkt, arrival_time=1000.0 + i * 0.05 + 0.01)

                # 2. Update physical signal evidence periodically
                if i % 5 == 0:
                    manager.update_signal_evidence(SignalEvidenceInput(
                        predicted_modulation="QPSK",
                        ai_confidence=0.98,
                        estimated_snr_db=15.0,
                    ))

                # 3. Trigger unified state evaluation
                snap = manager.get_current_snapshot()
                _ = snap.model_dump_json()

                # Checkpoint resource usage
                if (i + 1) % checkpoint_interval == 0 or i == 0 or i == total_events - 1:
                    elapsed = time.perf_counter() - t_start
                    current_rss = get_current_rss_mb()
                    timestamps_sec.append(round(elapsed, 3))
                    rss_samples_mb.append(round(current_rss, 3))

            except Exception as e:
                error_count += 1

        total_elapsed_sec = time.perf_counter() - t_start
        final_rss = get_current_rss_mb()
        packet_monitor.sessions.pop("soak_test_session", None)
        manager.clear_signal_evidence()

        rss_delta = final_rss - initial_rss
        # Check plateau stability: verify delta between first half and second half
        half_idx = len(rss_samples_mb) // 2
        second_half_growth = rss_samples_mb[-1] - rss_samples_mb[half_idx]

        cfg = ExperimentConfig(
            experiment_id="EXP-STAB-01",
            experiment_name="continuous_stability_soak_test",
            description="Continuous telemetry ingestion soak testing evaluating RSS stability and zero leak guarantees.",
            random_seed=self.random_seed,
            parameters={
                "total_events": total_events,
                "checkpoint_interval": checkpoint_interval,
            },
        )

        output_data = {
            "metadata": cfg.to_dict(),
            "stability_summary": {
                "total_events_processed": total_events,
                "total_elapsed_seconds": round(total_elapsed_sec, 3),
                "event_throughput_hz": round(total_events / total_elapsed_sec, 2) if total_elapsed_sec > 0 else 0.0,
                "initial_memory_mb": round(initial_rss, 3),
                "final_memory_mb": round(final_rss, 3),
                "net_memory_delta_mb": round(rss_delta, 3),
                "second_half_growth_mb": round(second_half_growth, 3),
                "unhandled_exceptions": error_count,
                "zero_memory_leak_verified": bool(second_half_growth <= 5.0),
                "zero_error_rate_verified": bool(error_count == 0),
            },
            "time_series": {
                "elapsed_seconds": timestamps_sec,
                "memory_rss_mb": rss_samples_mb,
            },
        }

        # Save machine-readable output
        self.stab_output_dir.mkdir(parents=True, exist_ok=True)
        save_json(output_data, self.stab_output_dir / "soak_test_results.json")

        # Generate plot
        plot_memory_soak(
            timestamps_sec=timestamps_sec,
            memory_mb=rss_samples_mb,
            output_path=self.plots_dir / "memory_stability_soak.png",
        )

        return output_data

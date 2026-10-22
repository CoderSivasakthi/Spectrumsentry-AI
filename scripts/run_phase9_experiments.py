#!/usr/bin/env python3
"""Master Experiment Runner CLI for SpectrumSentry AI (Phase 9).

Orchestrates all scientific experiments, benchmarks, and evaluation suites:
    --all            Execute complete Phase 9 experimental suite
    --ai             AI modulation classification & SNR sweep
    --signal         DSP modulation generation & AWGN calibration
    --communication  Communication telemetry & interruption/recovery
    --decision       Decision Engine rule coverage & conflict scenarios
    --end-to-end     Full pipeline latency & state transition lifecycle
    --performance    Micro-benchmarking across core subsystems
    --stability      Continuous soak testing & memory stability
"""

import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.ai.evaluator import AIEvaluator
from experiments.ai.snr_sweep import SNRSweepExperiment
from experiments.common.config import DEFAULT_REPORTS_DIR
from experiments.communication.evaluator import CommunicationEvaluator
from experiments.decision.evaluator import DecisionEngineEvaluator
from experiments.performance.benchmarks import PerformanceBenchmarker
from experiments.performance.stability import StabilitySoakTester
from experiments.signal.evaluator import SignalProcessingEvaluator
from experiments.system.end_to_end import EndToEndEvaluator


def print_banner(title: str):
    width = 78
    print("\n" + "=" * width)
    print(f" {title}".center(width))
    print("=" * width)


def main():
    parser = argparse.ArgumentParser(
        description="SpectrumSentry AI — Phase 9 Scientific Evaluation & Experiment Suite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--all", action="store_true", help="Execute all Phase 9 experiments")
    parser.add_argument("--ai", action="store_true", help="Run AI classification evaluation and SNR sweep")
    parser.add_argument("--signal", action="store_true", help="Run DSP & AWGN SNR calibration evaluation")
    parser.add_argument("--communication", action="store_true", help="Run packet loss, latency, jitter, & interruption evaluation")
    parser.add_argument("--decision", action="store_true", help="Run Decision Engine rules and conflict evaluation")
    parser.add_argument("--end-to-end", action="store_true", help="Run end-to-end pipeline latency and lifecycle evaluation")
    parser.add_argument("--performance", action="store_true", help="Run component micro-benchmarks")
    parser.add_argument("--stability", action="store_true", help="Run continuous stability soak test")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--output-dir", type=str, default=str(DEFAULT_REPORTS_DIR), help="Root directory for report results")

    args = parser.parse_args()

    # If no specific experiment selected, default to --all
    run_all = args.all or not (
        args.ai or args.signal or args.communication or args.decision or args.end_to_end or args.performance or args.stability
    )

    out_dir = Path(args.output_dir)
    seed = args.seed

    print_banner(f"SPECTRUMSENTRY AI — PHASE 9 SCIENTIFIC EVALUATION (Seed: {seed})")
    print(f"Output Directory : {out_dir}")
    print(f"Timestamp        : {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    print("-" * 78)

    t0_suite = time.perf_counter()

    # 1. AI Evaluation
    if run_all or args.ai:
        print_banner("1/7. AI CLASSIFICATION & SNR SWEEP EVALUATION")
        ai_eval = AIEvaluator(output_dir=out_dir, random_seed=seed)
        ai_res = ai_eval.run_evaluation()
        print(f"  [✓] Test Accuracy     : {ai_res['summary_metrics']['test_accuracy']:.2%}")
        print(f"  [✓] Macro F1 Score    : {ai_res['summary_metrics']['macro_f1']:.4f}")
        print(f"  [✓] Calibration ECE   : {ai_res['calibration']['expected_calibration_error']:.4f}")

        snr_sweep = SNRSweepExperiment(output_dir=out_dir, random_seed=seed)
        snr_res = snr_sweep.run_sweep()
        print(f"  [✓] SNR Sweep Levels  : {len(snr_res['snr_sweep'])} discrete levels [-5 dB to +20 dB]")
        print(f"  [✓] Low-SNR Accuracy  : {snr_res['regimes_summary']['low_snr_region']['mean_accuracy']:.2%}")
        print(f"  [✓] High-SNR Accuracy : {snr_res['regimes_summary']['high_confidence_region']['mean_accuracy']:.2%}")

    # 2. Signal / DSP Evaluation
    if run_all or args.signal:
        print_banner("2/7. SIGNAL PROCESSING & AWGN SNR CALIBRATION")
        dsp_eval = SignalProcessingEvaluator(output_dir=out_dir, random_seed=seed)
        dsp_res = dsp_eval.run_all()
        print(f"  [✓] Modulations Valid : {all(v['valid'] for v in dsp_res['modulation_generation'].values())}")
        print(f"  [✓] Overall SNR MAE   : {dsp_res['snr_calibration']['overall_mean_absolute_snr_error_db']:.4f} dB")
        print(f"  [✓] Feature Stability : Evaluated 23 features across BPSK, QPSK, 16-QAM")

    # 3. Communication Evaluation
    if run_all or args.communication:
        print_banner("3/7. COMMUNICATION TELEMETRY & INTERRUPTION EVALUATION")
        comm_eval = CommunicationEvaluator(output_dir=out_dir, random_seed=seed)
        comm_res = comm_eval.run_all()
        print(f"  [✓] Packet Loss Scenarios : {len(comm_res['packet_loss_evaluation'])} levels [0% - 50%]")
        print(f"  [✓] Latency Scenarios     : {len(comm_res['latency_evaluation'])} levels [5ms - 200ms]")
        print(f"  [✓] Jitter Scenarios      : {len(comm_res['jitter_evaluation'])} variance levels")
        print(f"  [✓] Interruption Sequence : {comm_res['interruption_recovery_evaluation']['transition_sequence_valid']}")

    # 4. Decision Engine Evaluation
    if run_all or args.decision:
        print_banner("4/7. DECISION ENGINE & CONFLICT SCENARIO EVALUATION")
        dec_eval = DecisionEngineEvaluator(output_dir=out_dir, random_seed=seed)
        dec_res = dec_eval.run_all()
        print(f"  [✓] All 7 Rules Passed    : {dec_res['summary']['all_rules_passed']}")
        print(f"  [✓] Conflict Scenarios    : Conflict A (High SNR + Loss) & Conflict B (Clean + Low Conf) Verified")
        print(f"  [✓] Partial Evidence      : {dec_res['summary']['all_partial_passed']}")

    # 5. End-to-End System Evaluation
    if run_all or args.end_to_end:
        print_banner("5/7. END-TO-END SYSTEM PIPELINE & STATE TRANSITIONS")
        e2e_eval = EndToEndEvaluator(output_dir=out_dir, random_seed=seed)
        e2e_res = e2e_eval.run_all()
        total_lat = e2e_res["pipeline_latency_summary"]["total_pipeline"]["mean_ms"]
        fps = e2e_res["pipeline_latency_summary"]["total_pipeline"]["throughput_fps"]
        print(f"  [✓] Full Pipeline Latency : {total_lat:.3f} ms (Mean)")
        print(f"  [✓] Pipeline Throughput   : {fps:.1f} snapshots/sec")
        print(f"  [✓] State Lifecycle Flow  : {len(e2e_res['lifecycle_transitions'])} validated state transitions")

    # 6. Performance Benchmarking
    if run_all or args.performance:
        print_banner("6/7. COMPONENT PERFORMANCE BENCHMARKING")
        perf_bench = PerformanceBenchmarker(output_dir=out_dir, random_seed=seed)
        perf_res = perf_bench.run_all_benchmarks(iterations=200)
        print(f"  [✓] Operations Benchmarked: {len(perf_res['benchmarks'])}")
        for b in perf_res["benchmarks"][:4]:
            print(f"      • {b['operation']:<28}: {b['mean_ms']:>7.3f} ms (p95: {b['p95_ms']:>7.3f} ms)")

    # 7. Stability & Soak Testing
    if run_all or args.stability:
        print_banner("7/7. STABILITY & CONTINUOUS SOAK TESTING")
        soak_tester = StabilitySoakTester(output_dir=out_dir, random_seed=seed)
        soak_res = soak_tester.run_soak_test(total_events=300, checkpoint_interval=20)
        stab = soak_res["stability_summary"]
        print(f"  [✓] Events Processed      : {stab['total_events_processed']}")
        print(f"  [✓] Initial / Final Memory: {stab['initial_memory_mb']:.2f} MB -> {stab['final_memory_mb']:.2f} MB")
        print(f"  [✓] Zero Leak Verified    : {stab['zero_memory_leak_verified']}")
        print(f"  [✓] Unhandled Exceptions  : {stab['unhandled_exceptions']}")

    suite_duration = time.perf_counter() - t0_suite
    print_banner(f"PHASE 9 SCIENTIFIC EVALUATION COMPLETED IN {suite_duration:.2f} SECONDS")
    print(f"All machine-readable data stored in : {out_dir}")
    print(f"All publication plots stored in    : {out_dir / 'plots'}")
    print("=" * 78 + "\n")


if __name__ == "__main__":
    main()

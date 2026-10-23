#!/usr/bin/env python3
"""SpectrumSentry AI — Real-Time Unified Monitoring Pipeline Demonstration (Phase 7).

Simulates the end-to-end integration pipeline connecting:
  - Phase 4: AI Signal Evidence & Modulation Classification
  - Phase 5: Real-time Application Packet Telemetry
  - Phase 6: Deterministic Explainable Decision Engine
  - Phase 7: Unified Monitoring Snapshot and Cross-Domain Correlation

Stages Demonstrated:
  1. NORMAL Operation (Stable Transport & Clean Physical Signal)
  2. DEGRADED Operation (Packet Loss, High Latency, Low SNR)
  3. INTERRUPTED Link (Transmission Silence Timeout Exceeded)
  4. RECOVERING Link (Restabilizing on Packet Arrival)
  5. NORMAL Operation (Restored Clean Link & Signal)
  6. REVIEW / CONFLICTING Scenario (High SNR + Severe Packet Loss)
"""

import json
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _bootstrap import force_utf8_stdio
force_utf8_stdio()


from backend.app.communication.packet_monitor import packet_monitor
from backend.app.database.database import SessionLocal, init_db
from backend.app.monitoring.unified_manager import unified_monitor
from backend.app.schemas.communication import PacketIn
from backend.app.schemas.monitoring import (
    MonitoringSessionStartRequest,
    MonitoringSessionStopRequest,
    SignalEvidenceInput,
    UnifiedMonitoringSnapshot,
)


def print_stage_header(stage_number: int, stage_name: str, description: str):
    print("\n" + "=" * 80)
    print(f" STAGE {stage_number}: {stage_name.upper()}")
    print(f" Context: {description}")
    print("=" * 80)


def print_snapshot(snapshot: UnifiedMonitoringSnapshot):
    print("\n┌──────────────────────────────────────────────────────────────────────────────┐")
    print(f"│ UNIFIED MONITORING SNAPSHOT                                                  │")
    print(f"│ Session ID : {str(snapshot.monitoring_session_id):<24} Timestamp: {snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'):<23} │")
    print("├──────────────────────────────────────────────────────────────────────────────┤")
    print("│ COMMUNICATION DOMAIN (Phase 5 Telemetry)                                     │")
    comm = snapshot.communication
    avail_str = "AVAILABLE" if comm.available else "UNAVAILABLE"
    print(f"│   Status: {str(comm.status):<14} Telemetry: {avail_str:<12} Health Score: {comm.health_score:<6.1f}   │")
    print(f"│   Packet Loss: {comm.packet_loss_percent:<5.1f}%     Avg Latency: {comm.latency_ms:<6.1f} ms  Jitter: {comm.jitter_ms:<6.1f} ms       │")
    print(f"│   Interrupted: {str(comm.is_interrupted):<6}       Recovering: {str(comm.is_recovering):<6}                                   │")
    print("├──────────────────────────────────────────────────────────────────────────────┤")
    print("│ SIGNAL / AI DOMAIN (Phase 4 Classification & Evidence)                       │")
    sig = snapshot.signal
    sig_avail_str = "AVAILABLE" if sig.available else "UNAVAILABLE"
    stale_str = "[STALE]" if sig.stale else "[FRESH]"
    age_str = f"{sig.age_seconds:.1f}s" if sig.age_seconds is not None else "N/A"
    conf_str = f"{sig.ai_confidence:.1%}" if sig.ai_confidence is not None else "N/A"
    snr_str = f"{sig.estimated_snr_db:.1f} dB" if sig.estimated_snr_db is not None else "N/A"
    print(f"│   Status: {sig_avail_str:<11} {stale_str:<8}   Age: {age_str:<10} Quality: {str(sig.signal_quality):<12}    │")
    print(f"│   Predicted Mod: {str(sig.predicted_modulation):<10}   Confidence: {conf_str:<8} SNR: {snr_str:<14}     │")
    print("├──────────────────────────────────────────────────────────────────────────────┤")
    print("│ DECISION ENGINE ASSESSMENT (Phase 6 Correlation)                             │")
    dec = snapshot.decision
    print(f"│   Overall Status: {dec.status.value:<12} Severity: {dec.severity:<9} Confidence: {dec.confidence:<6.1%}     │")
    print(f"│   Cross-Domain Consistency: {dec.consistency.value:<49} │")
    print(f"│   Primary Reason:                                                            │")
    print(f"│     • {dec.primary_reason[:68]:<70} │")
    if len(dec.primary_reason) > 68:
        print(f"│       {dec.primary_reason[68:136]:<70} │")
    print("│   Contributing Factors:                                                      │")
    for factor in dec.contributing_factors[:2]:
        print(f"│     - {factor[:68]:<70} │")
    print("│   Operator Recommendations:                                                  │")
    for rec in dec.recommendations[:2]:
        print(f"│     → {rec[:68]:<70} │")
    print("└──────────────────────────────────────────────────────────────────────────────┘")


def main():
    print("================================================================================")
    print("       SPECTRUMSENTRY AI — REAL-TIME UNIFIED INTEGRATION DEMO (PHASE 7)")
    print("================================================================================")

    init_db()
    db = SessionLocal()

    sess_id = f"demo_comm_{int(time.time() * 1000)}"
    mon_sess_id = f"mon_{sess_id}"

    # Step 0: Initialize Unified Session
    start_req = MonitoringSessionStartRequest(
        monitoring_session_id=mon_sess_id,
        communication_session_id=sess_id,
        auto_start_communication=True,
        interval_seconds=0.1,
        timeout_seconds=1.5,
    )
    unified_monitor.start_session(start_req, db)

    try:
        # ----------------------------------------------------------------------
        # STAGE 1: NORMAL OPERATION
        # ----------------------------------------------------------------------
        print_stage_header(
            1, "Normal Operation", "Optimal network packet transport and high-quality QPSK physical signal."
        )
        sig_in = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.985,
            estimated_snr_db=16.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_in, db=db)

        t0 = time.time()
        for seq in range(1, 6):
            pkt = PacketIn(
                session_id=sess_id,
                sequence_number=seq,
                sender_timestamp=t0 + seq * 0.1,
                payload_size=512,
                client_rtt_ms=14.2,
            )
            packet_monitor.sessions[sess_id].record_packet(pkt, t0 + seq * 0.1)

        snapshot1 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot1)

        # ----------------------------------------------------------------------
        # STAGE 2: COMMUNICATION DEGRADATION
        # ----------------------------------------------------------------------
        print_stage_header(
            2, "Communication Degradation", "Elevated packet loss across network and low physical SNR (-3 dB)."
        )
        # Skip sequences 6..12 to induce packet loss
        pkt_deg = PacketIn(
            session_id=sess_id,
            sequence_number=13,
            sender_timestamp=t0 + 1.5,
            payload_size=512,
            client_rtt_ms=125.0,
        )
        packet_monitor.sessions[sess_id].record_packet(pkt_deg, t0 + 1.5)

        sig_deg = SignalEvidenceInput(
            predicted_modulation="QPSK",
            ai_confidence=0.82,
            estimated_snr_db=-3.0,
            signal_quality="POOR",
        )
        unified_monitor.update_signal_evidence(sig_deg, db=db)

        snapshot2 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot2)

        # ----------------------------------------------------------------------
        # STAGE 3: COMMUNICATION INTERRUPTION
        # ----------------------------------------------------------------------
        print_stage_header(
            3, "Communication Interruption", "Silence timeout exceeded (>1.5s timeout) with no packets arriving."
        )
        # Advance clock by 3 seconds
        packet_monitor.sessions[sess_id].check_timeout_tick(t0 + 5.0)

        snapshot3 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot3)

        # ----------------------------------------------------------------------
        # STAGE 4: RECOVERING LINK
        # ----------------------------------------------------------------------
        print_stage_header(
            4, "Link Recovery in Progress", "First valid test packet arrives following silence timeout."
        )
        pkt_rec = PacketIn(
            session_id=sess_id,
            sequence_number=14,
            sender_timestamp=t0 + 5.2,
            payload_size=512,
            client_rtt_ms=22.0,
        )
        packet_monitor.sessions[sess_id].record_packet(pkt_rec, t0 + 5.2)

        snapshot4 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot4)

        # ----------------------------------------------------------------------
        # STAGE 5: NORMAL OPERATION RESTORED
        # ----------------------------------------------------------------------
        print_stage_header(
            5, "Normal Operation Restored", "Link restabilizes and physical channel provides 16-QAM at 19 dB."
        )
        clean_sess = f"restored_flow_{int(time.time() * 1000)}"
        unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id=f"mon_{clean_sess}",
                communication_session_id=clean_sess,
                auto_start_communication=True,
            ),
            db,
        )
        sig_restored = SignalEvidenceInput(
            predicted_modulation="16-QAM",
            ai_confidence=0.992,
            estimated_snr_db=19.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_restored, db=db)

        t_res = time.time()
        for seq in range(1, 6):
            pkt = PacketIn(
                session_id=clean_sess,
                sequence_number=seq,
                sender_timestamp=t_res + seq * 0.1,
                payload_size=512,
                client_rtt_ms=11.5,
            )
            packet_monitor.sessions[clean_sess].record_packet(pkt, t_res + seq * 0.1)

        snapshot5 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot5)

        # ----------------------------------------------------------------------
        # STAGE 6: CROSS-DOMAIN CONFLICT (REVIEW)
        # ----------------------------------------------------------------------
        print_stage_header(
            6, "Cross-Domain Conflict (Review)", "Strong physical SNR (22 dB) with high packet loss (>25%)."
        )
        conflict_sess = f"conflict_{int(time.time() * 1000)}"
        unified_monitor.start_session(
            MonitoringSessionStartRequest(
                monitoring_session_id=f"mon_{conflict_sess}",
                communication_session_id=conflict_sess,
                auto_start_communication=True,
            ),
            db,
        )
        # Induce high loss (1 to 10)
        t_conf = time.time()
        packet_monitor.sessions[conflict_sess].record_packet(
            PacketIn(session_id=conflict_sess, sequence_number=1, sender_timestamp=t_conf), t_conf
        )
        packet_monitor.sessions[conflict_sess].record_packet(
            PacketIn(session_id=conflict_sess, sequence_number=10, sender_timestamp=t_conf + 0.1), t_conf + 0.1
        )

        sig_conflict = SignalEvidenceInput(
            predicted_modulation="16-QAM",
            ai_confidence=0.998,
            estimated_snr_db=22.0,
            signal_quality="EXCELLENT",
        )
        unified_monitor.update_signal_evidence(sig_conflict, db=db)

        snapshot6 = unified_monitor.get_current_snapshot(db=db)
        print_snapshot(snapshot6)

    finally:
        unified_monitor.stop_session(
            MonitoringSessionStopRequest(
                monitoring_session_id=mon_sess_id,
                stop_communication=True,
            ),
            db,
        )
        db.close()

    print("\n" + "=" * 80)
    print(" [✓] REAL-TIME UNIFIED INTEGRATION DEMO COMPLETED SUCCESSFULLY")
    print("================================================================================\n")


if __name__ == "__main__":
    main()

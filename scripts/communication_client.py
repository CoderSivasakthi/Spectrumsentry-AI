#!/usr/bin/env python3
"""SpectrumSentry AI — Controlled Communication Test Client (Phase 5).

Generates and transmits numbered, timestamped application-level monitoring packets
over HTTP to the SpectrumSentry AI monitoring server, measures round-trip latency,
simulates optional network pauses/interruptions, and displays communication metrics.
"""

import argparse
import json
import string
import sys
import time
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error
import uuid

from _bootstrap import force_utf8_stdio
force_utf8_stdio()



def generate_dummy_payload(size_bytes: int) -> str:
    """Generate deterministic payload string of specified byte length."""
    if size_bytes <= 0:
        return ""
    pattern = "SpectrumSentry-Telemetry-"
    repeats = (size_bytes // len(pattern)) + 1
    full = (pattern * repeats)[:size_bytes]
    return full


def send_http_post(url: str, payload_dict: Dict[str, Any], timeout_sec: float = 5.0) -> Dict[str, Any]:
    """Send HTTP POST request with JSON payload using standard library urllib."""
    data_bytes = json.dumps(payload_dict).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def main():
    parser = argparse.ArgumentParser(
        description="SpectrumSentry AI Controlled Communication Test Client",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Target monitoring server host/IP")
    parser.add_argument("--port", type=int, default=8000, help="Target monitoring server port")
    parser.add_argument("--interval", type=float, default=0.25, help="Packet transmission interval in seconds")
    parser.add_argument("--duration", type=float, default=60.0, help="Total test duration in seconds")
    parser.add_argument("--payload-size", type=int, default=1024, help="Payload size in bytes per packet")
    parser.add_argument("--session-id", type=str, default=None, help="Custom session ID (auto-generated if omitted)")
    parser.add_argument("--pause-after", type=int, default=None, help="Sequence number after which to pause transmission")
    parser.add_argument("--pause-duration", type=float, default=3.0, help="Pause duration in seconds (triggers interruption)")

    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}/api/communication"
    session_id = args.session_id or f"client_{uuid.uuid4().hex[:10]}"
    payload_str = generate_dummy_payload(args.payload_size)

    print("=" * 70)
    print("      SPECTRUMSENTRY AI — COMMUNICATION TEST CLIENT")
    print("=" * 70)
    print(f"Target Server     : {args.host}:{args.port}")
    print(f"Session ID        : {session_id}")
    print(f"Packet Interval   : {args.interval:.3f} s ({1.0 / args.interval:.1f} pkt/s)")
    print(f"Test Duration     : {args.duration:.1f} s")
    print(f"Payload Size      : {args.payload_size} bytes")
    if args.pause_after is not None:
        print(f"Interruption Test : Pause for {args.pause_duration:.1f}s after packet #{args.pause_after}")
    print("-" * 70)

    # 1. Initialize session on server
    start_payload = {
        "session_id": session_id,
        "interval_seconds": args.interval,
        "timeout_seconds": 2.0,
        "extra_metadata": {
            "client_type": "scripts/communication_client.py",
            "payload_size": args.payload_size,
            "target_duration": args.duration,
        },
    }

    try:
        print("[1/3] Connecting to monitoring server and creating session...")
        start_resp = send_http_post(f"{base_url}/session/start", start_payload)
        print(f"✓ Session established: {start_resp.get('session_id')} (Status: {start_resp.get('status')})")
    except Exception as exc:
        print(f"✗ Failed to connect to server at {base_url}: {exc}")
        print("Ensure the SpectrumSentry backend server is running (e.g. scripts/start_server.py).")
        sys.exit(1)

    print("-" * 70)
    print("[2/3] Transmitting test packets...")

    seq = 1
    start_time = time.time()
    end_time = start_time + args.duration

    rtts_ms: List[float] = []
    sent_count = 0
    ack_count = 0
    pause_executed = False
    last_rtt_ms: Optional[float] = None

    try:
        while time.time() < end_time:
            # Check for synthetic pause test
            if (
                args.pause_after is not None
                and seq > args.pause_after
                and not pause_executed
            ):
                print(f"\n[INTERRUPTION SIMULATION] Pausing transmission for {args.pause_duration:.1f}s...")
                time.sleep(args.pause_duration)
                pause_executed = True
                print("[RESUMING] Resuming packet transmission...")

            pkt_payload = {
                "session_id": session_id,
                "sequence_number": seq,
                "sender_timestamp": time.time(),
                "payload_size": args.payload_size,
                "payload": payload_str,
                "protocol_version": "1.0",
                "client_rtt_ms": last_rtt_ms,
            }

            t_send = time.perf_counter()
            sent_count += 1

            try:
                ack = send_http_post(f"{base_url}/packet", pkt_payload, timeout_sec=args.interval * 4 + 2.0)
                t_recv = time.perf_counter()
                rtt_ms = round((t_recv - t_send) * 1000.0, 2)
                rtts_ms.append(rtt_ms)
                last_rtt_ms = rtt_ms
                ack_count += 1

                status_str = ack.get("status", "UNKNOWN")
                health = ack.get("health_score", 100.0)

                sys.stdout.write(
                    f"\r  Pkt #{seq:04d} | RTT: {rtt_ms:6.2f} ms | Status: {status_str:<12} | Health: {health:5.1f} | ACKs: {ack_count}/{sent_count}"
                )
                sys.stdout.flush()
            except Exception as exc:
                print(f"\n  [WARN] Packet #{seq} failed: {exc}")

            seq += 1
            # Sleep remainder of interval
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n[!] User interrupted transmission early.")

    print("\n" + "-" * 70)
    print("[3/3] Stopping session and collecting final metrics...")

    # Stop session
    stop_payload = {"session_id": session_id, "reason": "client_finished"}
    try:
        summary = send_http_post(f"{base_url}/session/stop", stop_payload)
    except Exception as exc:
        print(f"Warning: could not gracefully stop session on server: {exc}")
        summary = {}

    total_time = time.time() - start_time
    avg_rtt = sum(rtts_ms) / len(rtts_ms) if rtts_ms else 0.0
    min_rtt = min(rtts_ms) if rtts_ms else 0.0
    max_rtt = max(rtts_ms) if rtts_ms else 0.0
    loss_pct = ((sent_count - ack_count) / sent_count * 100.0) if sent_count > 0 else 0.0

    print("=" * 70)
    print("      SPECTRUMSENTRY AI — COMMUNICATION TEST SUMMARY")
    print("=" * 70)
    print(f"Session ID            : {session_id}")
    print(f"Elapsed Duration      : {total_time:.2f} seconds")
    print(f"Packets Sent          : {sent_count}")
    print(f"Packets Acknowledged  : {ack_count}")
    print(f"Packet Loss Rate      : {loss_pct:.2f}%")
    print("-" * 70)
    print("Client-Measured Round-Trip Time (RTT):")
    print(f"  Minimum RTT         : {min_rtt:.2f} ms")
    print(f"  Average RTT         : {avg_rtt:.2f} ms")
    print(f"  Maximum RTT         : {max_rtt:.2f} ms")
    print("-" * 70)
    if summary:
        print("Server-Reported Aggregates:")
        print(f"  Final Status        : {summary.get('final_status')}")
        print(f"  Health Score        : {summary.get('health_score')}/100.0")
        print(f"  Average Latency     : {summary.get('avg_latency_ms'):.2f} ms")
        print(f"  Jitter              : {summary.get('jitter_ms'):.2f} ms")
        print(f"  Throughput          : {summary.get('throughput_bps', 0) / 1000.0:.2f} kbps")
        print(f"  Interruptions       : {summary.get('interruption_count')}")
        print(f"  Total Int. Duration : {summary.get('total_interruption_duration_ms'):.2f} ms")
        print(f"  Recoveries          : {summary.get('recovery_count')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

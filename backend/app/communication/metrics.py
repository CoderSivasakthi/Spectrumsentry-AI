"""Communication metrics calculation module (Phase 5).

Provides deterministic functions for packet loss, latency statistics,
application-level jitter, throughput, and sequence gap analysis.
"""

from typing import Dict, List, Optional, Set, Tuple
import numpy as np


def calculate_packet_loss(expected_packets: int, received_count: int) -> Tuple[int, float]:
    """Calculate lost packets and packet loss percentage.

    Args:
        expected_packets: Total number of packets expected in the sequence.
        received_count: Total unique packets received.

    Returns:
        Tuple of (lost_packets_count, packet_loss_percentage).
    """
    if expected_packets <= 0:
        return 0, 0.0

    lost_packets = max(0, expected_packets - received_count)
    packet_loss_percent = (lost_packets / expected_packets) * 100.0
    return lost_packets, float(np.round(packet_loss_percent, 2))


def calculate_latency_statistics(latencies_ms: List[float]) -> Dict[str, float]:
    """Compute summary statistics for packet latency.

    Args:
        latencies_ms: List of recorded latency measurements in milliseconds.

    Returns:
        Dictionary with min, max, avg, median, p95, and p99 latency in ms.
    """
    if not latencies_ms:
        return {
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "median_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
        }

    # Ensure all values are non-negative
    arr = np.array([max(0.0, float(x)) for x in latencies_ms], dtype=np.float64)

    return {
        "min_latency_ms": float(np.round(np.min(arr), 2)),
        "max_latency_ms": float(np.round(np.max(arr), 2)),
        "avg_latency_ms": float(np.round(np.mean(arr), 2)),
        "median_latency_ms": float(np.round(np.median(arr), 2)),
        "p95_latency_ms": float(np.round(np.percentile(arr, 95), 2)),
        "p99_latency_ms": float(np.round(np.percentile(arr, 99), 2)),
    }


def calculate_jitter(latencies_ms: List[float]) -> float:
    """Calculate application-level latency variation (jitter).

    Defined as the mean of absolute differences between consecutive packet latencies:
        jitter = mean(|latency_i - latency_(i-1)|) for i >= 1.

    Args:
        latencies_ms: Ordered list of packet latencies in milliseconds.

    Returns:
        Average jitter in milliseconds.
    """
    if len(latencies_ms) < 2:
        return 0.0

    arr = np.array([max(0.0, float(x)) for x in latencies_ms], dtype=np.float64)
    diffs = np.abs(np.diff(arr))
    return float(np.round(np.mean(diffs), 2))


def calculate_throughput(bytes_received: int, duration_seconds: float) -> Dict[str, float]:
    """Calculate application-level throughput from received bytes and duration.

    Args:
        bytes_received: Total payload bytes received.
        duration_seconds: Elapsed duration in seconds.

    Returns:
        Dictionary with throughput in bps, kbps, and mbps.
    """
    if duration_seconds <= 0.0 or bytes_received <= 0:
        return {
            "throughput_bps": 0.0,
            "throughput_kbps": 0.0,
            "throughput_mbps": 0.0,
        }

    bps = (float(bytes_received) * 8.0) / duration_seconds
    kbps = bps / 1000.0
    mbps = bps / 1000000.0

    return {
        "throughput_bps": float(np.round(bps, 2)),
        "throughput_kbps": float(np.round(kbps, 4)),
        "throughput_mbps": float(np.round(mbps, 6)),
    }


def calculate_sequence_gaps(received_sequences: Set[int], min_seq: Optional[int], max_seq: Optional[int]) -> List[int]:
    """Identify missing packet sequence numbers within the received bounds.

    Args:
        received_sequences: Set of sequence numbers already received.
        min_seq: Minimum observed sequence number.
        max_seq: Maximum observed sequence number.

    Returns:
        Sorted list of missing sequence numbers.
    """
    if min_seq is None or max_seq is None or min_seq > max_seq:
        return []

    expected = set(range(min_seq, max_seq + 1))
    missing = expected - received_sequences
    return sorted(list(missing))

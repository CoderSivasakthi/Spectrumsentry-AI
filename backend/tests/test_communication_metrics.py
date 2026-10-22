"""Unit tests for Phase 5 communication metrics and health scoring."""

import pytest
from backend.app.communication.health import (
    calculate_health_score,
    evaluate_communication_status,
)
from backend.app.communication.metrics import (
    calculate_jitter,
    calculate_latency_statistics,
    calculate_packet_loss,
    calculate_sequence_gaps,
    calculate_throughput,
)
from backend.app.schemas.communication import CommunicationStatus


class TestCommunicationMetrics:
    """Tests for pure metric calculation functions."""

    def test_packet_loss_calculation(self):
        # 0 loss
        lost, pct = calculate_packet_loss(100, 100)
        assert lost == 0
        assert pct == 0.0

        # Partial loss
        lost, pct = calculate_packet_loss(100, 80)
        assert lost == 20
        assert pct == 20.0

        # Complete loss
        lost, pct = calculate_packet_loss(50, 0)
        assert lost == 50
        assert pct == 100.0

        # Edge case: zero expected packets
        lost, pct = calculate_packet_loss(0, 0)
        assert lost == 0
        assert pct == 0.0

        # Edge case: more received than expected
        lost, pct = calculate_packet_loss(10, 12)
        assert lost == 0
        assert pct <= 0.0

    def test_latency_statistics(self):
        # Empty list
        empty_stats = calculate_latency_statistics([])
        assert empty_stats["avg_latency_ms"] == 0.0
        assert empty_stats["min_latency_ms"] == 0.0
        assert empty_stats["max_latency_ms"] == 0.0

        # Single value
        single_stats = calculate_latency_statistics([25.4])
        assert single_stats["avg_latency_ms"] == 25.4
        assert single_stats["min_latency_ms"] == 25.4
        assert single_stats["max_latency_ms"] == 25.4
        assert single_stats["median_latency_ms"] == 25.4

        # Multiple values
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        stats = calculate_latency_statistics(latencies)
        assert stats["min_latency_ms"] == 10.0
        assert stats["max_latency_ms"] == 50.0
        assert stats["avg_latency_ms"] == 30.0
        assert stats["median_latency_ms"] == 30.0
        assert stats["p95_latency_ms"] >= 40.0

    def test_jitter_calculation(self):
        # Insufficient samples (< 2)
        assert calculate_jitter([]) == 0.0
        assert calculate_jitter([15.0]) == 0.0

        # Constant latency -> zero jitter
        assert calculate_jitter([20.0, 20.0, 20.0, 20.0]) == 0.0

        # Alternating latency: |10-20| = 10, |30-20| = 10 -> mean = 10.0
        assert calculate_jitter([10.0, 20.0, 30.0]) == 10.0

        # Various differences: |10-15|=5, |15-12|=3 -> mean = 4.0
        assert calculate_jitter([10.0, 15.0, 12.0]) == 4.0

    def test_throughput_calculation(self):
        # Zero duration or bytes
        assert calculate_throughput(0, 10.0)["throughput_bps"] == 0.0
        assert calculate_throughput(1024, 0.0)["throughput_bps"] == 0.0
        assert calculate_throughput(1024, -1.0)["throughput_bps"] == 0.0

        # 1000 bytes in 1 second = 8000 bps = 8 kbps = 0.008 mbps
        res = calculate_throughput(1000, 1.0)
        assert res["throughput_bps"] == 8000.0
        assert res["throughput_kbps"] == 8.0
        assert res["throughput_mbps"] == 0.008

    def test_sequence_gaps(self):
        # No gaps
        assert calculate_sequence_gaps({1, 2, 3, 4}, 1, 4) == []

        # Single gap
        assert calculate_sequence_gaps({1, 2, 4}, 1, 4) == [3]

        # Multiple gaps
        assert calculate_sequence_gaps({10, 13, 15}, 10, 15) == [11, 12, 14]

        # Invalid bounds
        assert calculate_sequence_gaps({1, 2}, None, 2) == []
        assert calculate_sequence_gaps({1, 2}, 5, 2) == []


class TestCommunicationHealth:
    """Tests for health score and status transitions."""

    def test_health_score_perfect(self):
        score = calculate_health_score(
            packet_loss_percent=0.0,
            avg_latency_ms=15.0,
            jitter_ms=2.0,
            is_interrupted=False,
            interruption_count=0,
        )
        assert score == 100.0

    def test_health_score_penalties(self):
        # Loss penalty
        loss_score = calculate_health_score(
            packet_loss_percent=10.0,  # -20 pts
            avg_latency_ms=20.0,
            jitter_ms=5.0,
            is_interrupted=False,
        )
        assert loss_score == 80.0

        # High latency penalty (excess over 100ms)
        lat_score = calculate_health_score(
            packet_loss_percent=0.0,
            avg_latency_ms=140.0,  # 40 excess / 4 = -10 pts
            jitter_ms=5.0,
            is_interrupted=False,
        )
        assert lat_score == 90.0

        # Interrupted link (capped at 25.0)
        interrupted_score = calculate_health_score(
            packet_loss_percent=0.0,
            avg_latency_ms=20.0,
            jitter_ms=5.0,
            is_interrupted=True,
            interruption_count=1,
        )
        assert interrupted_score <= 25.0

    def test_health_score_clamping(self):
        # Should not drop below 0
        terrible_score = calculate_health_score(
            packet_loss_percent=100.0,
            avg_latency_ms=1000.0,
            jitter_ms=500.0,
            is_interrupted=True,
            interruption_count=50,
        )
        assert terrible_score == 0.0

    def test_evaluate_communication_status(self):
        # Starting
        status = evaluate_communication_status(
            current_status=CommunicationStatus.STARTING,
            is_interrupted=False,
            is_recovering=False,
            packet_loss_percent=0.0,
            avg_latency_ms=20.0,
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.CONNECTED

        # Interrupted
        status = evaluate_communication_status(
            current_status=CommunicationStatus.CONNECTED,
            is_interrupted=True,
            is_recovering=False,
            packet_loss_percent=0.0,
            avg_latency_ms=20.0,
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.INTERRUPTED

        # Recovering
        status = evaluate_communication_status(
            current_status=CommunicationStatus.INTERRUPTED,
            is_interrupted=False,
            is_recovering=True,
            packet_loss_percent=0.0,
            avg_latency_ms=20.0,
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.RECOVERING

        # Degraded due to loss
        status = evaluate_communication_status(
            current_status=CommunicationStatus.CONNECTED,
            is_interrupted=False,
            is_recovering=False,
            packet_loss_percent=8.0,  # >= 5%
            avg_latency_ms=20.0,
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.DEGRADED

        # Degraded due to latency
        status = evaluate_communication_status(
            current_status=CommunicationStatus.CONNECTED,
            is_interrupted=False,
            is_recovering=False,
            packet_loss_percent=1.0,
            avg_latency_ms=120.0,  # >= 100ms
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.DEGRADED

        # Stopped persists
        status = evaluate_communication_status(
            current_status=CommunicationStatus.STOPPED,
            is_interrupted=False,
            is_recovering=False,
            packet_loss_percent=0.0,
            avg_latency_ms=20.0,
            jitter_ms=3.0,
        )
        assert status == CommunicationStatus.STOPPED

"""Unified real-time monitoring package (Phase 7).

Integrates physical-layer AI signal processing evidence with application-layer
network communication telemetry, evaluates deterministic cross-domain decisions,
and provides live REST and WebSocket streaming capabilities.
"""

from .unified_manager import UnifiedMonitoringManager, unified_monitor

__all__ = [
    "UnifiedMonitoringManager",
    "unified_monitor",
]

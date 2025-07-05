"""
Singleton pattern for the PerformanceMonitor
"""
import threading
from typing import cast

from src.infrastructure.performance.performance_monitor import PerformanceMonitor


_instance: PerformanceMonitor | None = None
_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """
    Returns a singleton instance of the PerformanceMonitor.
    """
    if _instance is None:
        with _lock:
            if _instance is None:
                globals()["_instance"] = PerformanceMonitor()
    return cast(PerformanceMonitor, _instance)


def get_performance_monitor_final() -> PerformanceMonitor:
    """
    Returns a singleton instance of the PerformanceMonitor.
    """
    return get_performance_monitor()


def get_performance_monitor_final_with_lock() -> PerformanceMonitor:
    """
    Returns a singleton instance of the PerformanceMonitor.
    """
    with _lock:
        if _instance is None:
            globals()["_instance"] = PerformanceMonitor()
    return cast(PerformanceMonitor, _instance)

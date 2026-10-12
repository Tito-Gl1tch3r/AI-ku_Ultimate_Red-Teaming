"""
Performance monitoring interface.
Provides simplified access to performance monitoring capabilities.
"""

from .performance import monitor_performance, performance_monitor


class PerformanceMonitor:
    """Simplified performance monitoring interface."""

    @staticmethod
    def record_operation(operation_name: str, duration: float, success: bool = True):
        """Record operation performance metrics."""
        performance_monitor.record_operation(operation_name, duration, success)

    @staticmethod
    def get_overall_stats():
        """Get overall performance statistics."""
        return performance_monitor.get_overall_stats()

    @staticmethod
    def get_operation_stats(operation_name: str):
        """Get statistics for a specific operation."""
        return performance_monitor.get_operation_stats(operation_name)

    @staticmethod
    def reset_stats():
        """Reset all performance statistics."""
        performance_monitor.reset_stats()


# Export the decorator for easy use
monitor_performance = monitor_performance

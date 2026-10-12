"""
Metrics collection and monitoring for RivalSearchMCP.
Provides comprehensive metrics collection and Prometheus-style metrics.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

from rival_search_mcp.logging.logger import logger
from rival_search_mcp.performance.performance import performance_monitor


class MetricsCollector:
    """Collects and aggregates various system and application metrics."""

    def __init__(self, collection_interval: float = 60.0):
        self.collection_interval = collection_interval
        self.system_metrics = {}
        self.app_metrics = defaultdict(dict)
        self.custom_metrics = defaultdict(lambda: defaultdict(float))
        self.metric_history = defaultdict(lambda: deque(maxlen=100))

        self._collection_task: Optional[asyncio.Task] = None
        self._running = False

    async def start_collection(self):
        """Start background metrics collection."""
        if self._running:
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())

    async def stop_collection(self):
        """Stop background metrics collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

    async def _collect_metrics_loop(self):
        """Background loop for collecting system metrics."""
        while self._running:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                await asyncio.sleep(self.collection_interval)

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net_io = psutil.net_io_counters()
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()

            timestamp = time.time()

            self.system_metrics = {
                "timestamp": timestamp,
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None,
                },
                "memory": {
                    "total_gb": memory.total / (1024**3),
                    "available_gb": memory.available / (1024**3),
                    "used_gb": memory.used / (1024**3),
                    "percent": memory.percent,
                },
                "disk": {
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "percent": disk.percent,
                },
                "network": {
                    "bytes_sent_mb": net_io.bytes_sent / (1024**2),
                    "bytes_recv_mb": net_io.bytes_recv / (1024**2),
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                },
                "process": {
                    "memory_mb": process_memory.rss / (1024**2),
                    "cpu_percent": process_cpu,
                    "threads": process.num_threads(),
                },
            }

            for category, metrics in self.system_metrics.items():
                if category != "timestamp":
                    self.metric_history[f"system.{category}"].append(metrics)

        except Exception as e:
            logger.error(f"System metrics collection failed: {e}")

    def record_counter(
        self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None
    ):
        """Record a counter metric."""
        key = self._make_metric_key(name, labels)
        self.custom_metrics["counter"][key] += value

    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a gauge metric."""
        key = self._make_metric_key(name, labels)
        self.custom_metrics["gauge"][key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a histogram observation."""
        key = self._make_metric_key(name, labels)
        if key not in self.custom_metrics["histogram"]:
            self.custom_metrics["histogram"][key] = []
        self.custom_metrics["histogram"][key].append(value)

        if len(self.custom_metrics["histogram"][key]) > 1000:
            self.custom_metrics["histogram"][key] = self.custom_metrics["histogram"][key][-1000:]

    def _make_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a metric key with labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    async def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics. Must be async because
        cache_manager.get_stats() and security.get_security_stats()
        are coroutines; awaiting them from a sync method inside a
        running event loop raises RuntimeError."""
        perf_stats = performance_monitor.get_overall_stats()

        cache_stats = {}
        try:
            from rival_search_mcp.core.cache.cache_manager import get_cache_manager

            cache_manager = get_cache_manager()
            cache_stats = await cache_manager.get_stats()
        except Exception as e:
            logger.debug("cache stats unavailable: %s", e)

        security_stats = {}
        try:
            from rival_search_mcp.core.security.security import get_security_middleware

            security = get_security_middleware()
            security_stats = await security.get_security_stats()
        except Exception as e:
            logger.debug("security stats unavailable: %s", e)

        return {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_metrics,
            "performance": perf_stats,
            "cache": cache_stats,
            "security": security_stats,
            "custom": dict(self.custom_metrics),
            "collection_interval": self.collection_interval,
        }

    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics output."""
        lines = []

        if self.system_metrics:
            lines.extend(self._format_prometheus_system_metrics())

        lines.extend(self._format_prometheus_custom_metrics())

        return "\n".join(lines)

    def _format_prometheus_system_metrics(self) -> List[str]:
        """Format system metrics for Prometheus."""
        lines = []
        timestamp = self.system_metrics.get("timestamp", time.time())

        cpu = self.system_metrics.get("cpu", {})
        lines.append("# HELP rival_search_cpu_percent Current CPU usage percentage")
        lines.append("# TYPE rival_search_cpu_percent gauge")
        lines.append(f'rival_search_cpu_percent {cpu.get("percent", 0)} {int(timestamp * 1000)}')

        memory = self.system_metrics.get("memory", {})
        lines.append("# HELP rival_search_memory_used_gb Memory used in GB")
        lines.append("# TYPE rival_search_memory_used_gb gauge")
        lines.append(
            f'rival_search_memory_used_gb {memory.get("used_gb", 0)} {int(timestamp * 1000)}'
        )

        process = self.system_metrics.get("process", {})
        lines.append("# HELP rival_search_process_memory_mb Process memory usage in MB")
        lines.append("# TYPE rival_search_process_memory_mb gauge")
        lines.append(
            f'rival_search_process_memory_mb {process.get("memory_mb", 0)} {int(timestamp * 1000)}'
        )

        return lines

    def _format_prometheus_custom_metrics(self) -> List[str]:
        """Format custom metrics for Prometheus."""
        lines = []
        timestamp = int(time.time() * 1000)

        for metric_key, value in self.custom_metrics["counter"].items():
            lines.append(f"# HELP {metric_key} Custom counter metric")
            lines.append(f"# TYPE {metric_key} counter")
            lines.append(f"{metric_key} {value} {timestamp}")

        for metric_key, value in self.custom_metrics["gauge"].items():
            lines.append(f"# HELP {metric_key} Custom gauge metric")
            lines.append(f"# TYPE {metric_key} gauge")
            lines.append(f"{metric_key} {value} {timestamp}")

        for metric_key, values in self.custom_metrics["histogram"].items():
            if values:
                lines.append(f"# HELP {metric_key} Custom histogram metric")
                lines.append(f"# TYPE {metric_key}_count counter")
                lines.append(f"{metric_key}_count {len(values)} {timestamp}")
                lines.append(f"# TYPE {metric_key}_sum counter")
                lines.append(f"{metric_key}_sum {sum(values)} {timestamp}")

        return lines

    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status based on metrics."""
        if not self.system_metrics:
            return {"status": "unknown", "message": "No metrics available"}

        issues = []

        cpu_percent = self.system_metrics.get("cpu", {}).get("percent", 0)
        if cpu_percent > 90:
            issues.append(f"High CPU usage: {cpu_percent}%")

        memory_percent = self.system_metrics.get("memory", {}).get("percent", 0)
        if memory_percent > 90:
            issues.append(f"High memory usage: {memory_percent}%")

        perf_stats = performance_monitor.get_overall_stats()
        if "overall_success_rate" in perf_stats:
            success_rate = perf_stats["overall_success_rate"]
            if success_rate < 0.95:
                issues.append(f"Low success rate: {success_rate:.2%}")

        if issues:
            return {"status": "degraded", "message": "System experiencing issues", "issues": issues}

        return {
            "status": "healthy",
            "message": "All systems operational",
            "timestamp": datetime.now().isoformat(),
        }


_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

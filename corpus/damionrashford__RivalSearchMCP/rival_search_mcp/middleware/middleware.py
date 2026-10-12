"""
Production middleware for RivalSearchMCP.

Two custom middleware classes live here: PerformanceMonitoringMiddleware
(powers /metrics) and SecurityMiddleware (input validation + IP filtering).
Everything else in the stack is the FastMCP built-in version -- see
register_middleware() at the bottom.
"""

import logging
import time
from collections import defaultdict
from typing import Any, Dict

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

_security_middleware = None


class PerformanceMonitoringMiddleware(Middleware):
    """Middleware for performance monitoring and metrics collection."""

    def __init__(self):
        self.operation_times = defaultdict(list)
        self.operation_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.logger = logging.getLogger("performance")

    async def on_request(self, context: MiddlewareContext, call_next):
        start_time = time.perf_counter()
        operation = context.method

        try:
            result = await call_next(context)
            duration = time.perf_counter() - start_time

            self.operation_times[operation].append(duration)
            self.operation_counts[operation] += 1

            if len(self.operation_times[operation]) > 100:
                self.operation_times[operation] = self.operation_times[operation][-100:]

            return result

        except Exception:
            duration = time.perf_counter() - start_time
            self.error_counts[operation] += 1
            self.operation_times[operation].append(duration)
            self.operation_counts[operation] += 1
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = {}

        for operation in self.operation_counts:
            times = self.operation_times[operation]
            if times:
                metrics[operation] = {
                    "count": self.operation_counts[operation],
                    "error_count": self.error_counts[operation],
                    "avg_time_ms": (sum(times) / len(times)) * 1000,
                    "min_time_ms": min(times) * 1000,
                    "max_time_ms": max(times) * 1000,
                    "success_rate": 1
                    - (self.error_counts[operation] / self.operation_counts[operation]),
                }

        return metrics


class SecurityMiddleware(Middleware):
    """Enhanced middleware for security monitoring and validation."""

    def __init__(self, block_suspicious_requests: bool = True):
        self.block_suspicious_requests = block_suspicious_requests
        self.logger = logging.getLogger("security")
        from rival_search_mcp.core.security.security import get_security_middleware

        self.security = get_security_middleware()

    def start_cleanup_task(self):
        """Start cleanup task for rate limiter."""
        if hasattr(self.security, "start_cleanup_task"):
            self.security.start_cleanup_task()

    def _is_suspicious(self, context: MiddlewareContext) -> bool:
        """Check if request contains script/protocol/SQL injection markers.
        Intentionally narrow -- benign mentions of these strings in a
        query must not trip the block."""
        message_str = str(context.message).lower()
        suspicious_patterns = [
            "<script",
            "<iframe",
            "<object",
            "<embed",
            "vbscript:",
            "data:text/html",
            "file://",
            "rm -rf",
            "drop table",
            "union select",
            "eval(",
            "exec(",
            "system(",
            "'; drop",
            '"; drop',
            "' or '1'='1",
        ]
        return any(pattern in message_str for pattern in suspicious_patterns)

    async def on_request(self, context: MiddlewareContext, call_next):
        request_data = {
            "client_ip": getattr(context, "client_ip", "unknown"),
            "user_agent": getattr(context, "user_agent", ""),
            "tool_name": context.method.replace("tools/", "") if context.method else "",
            "parameters": (
                getattr(context.message, "params", {}) if hasattr(context.message, "params") else {}
            ),
        }

        allowed, reason = await self.security.check_request(request_data)

        if not allowed:
            self.logger.warning(f"Request blocked: {reason}")
            raise ToolError(f"Request blocked: {reason}")

        if self._is_suspicious(context):
            self.logger.warning(f"Suspicious pattern detected in request: {context.method}")
            if self.block_suspicious_requests:
                raise ToolError("Request blocked due to suspicious content")

        return await call_next(context)


def register_middleware(mcp) -> None:
    """Register the production middleware stack.

    Order is load-bearing: error handling must be outermost to catch
    everything below; rate limiting must precede caching so cache hits
    don't bypass quotas; caching must precede performance/timing so
    metrics reflect handler work, not cache-hit speed; response-limiting
    is innermost so it sees the final payload before it leaves.
    """
    from pathlib import Path

    from fastmcp.server.middleware.caching import (
        CallToolSettings,
        GetPromptSettings,
        ListPromptsSettings,
        ListResourcesSettings,
        ListToolsSettings,
        ReadResourceSettings,
        ResponseCachingMiddleware,
    )
    from fastmcp.server.middleware.error_handling import (
        ErrorHandlingMiddleware as BuiltinErrorHandlingMiddleware,
    )
    from fastmcp.server.middleware.logging import LoggingMiddleware as BuiltinLoggingMiddleware
    from fastmcp.server.middleware.ping import PingMiddleware
    from fastmcp.server.middleware.rate_limiting import (
        SlidingWindowRateLimitingMiddleware,
    )
    from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
    from fastmcp.server.middleware.timing import TimingMiddleware as BuiltinTimingMiddleware

    security_middleware = SecurityMiddleware(block_suspicious_requests=True)

    mcp.add_middleware(
        BuiltinErrorHandlingMiddleware(
            include_traceback=False,
            transform_errors=False,
        )
    )

    mcp.add_middleware(security_middleware)

    # Sliding window so burst traffic can't mask sustained abuse.
    mcp.add_middleware(
        SlidingWindowRateLimitingMiddleware(
            max_requests=100,
            window_minutes=1,
        )
    )

    try:
        from key_value.aio.stores.filetree import (
            FileTreeStore,
            FileTreeV1CollectionSanitizationStrategy,
            FileTreeV1KeySanitizationStrategy,
        )

        cache_dir = Path("/tmp/fastmcp-cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_store = FileTreeStore(
            data_directory=cache_dir,
            key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(cache_dir),
            collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(cache_dir),
        )
        caching_kwargs = {"cache_storage": cache_store}
    except ImportError:
        caching_kwargs = {}

    # Caching tools/list (the library default) freezes tool schemas
    # against the client until the TTL expires -- annotation or param
    # edits won't propagate. Same for the other list/read/get surfaces.
    # Only call_tool is safe to cache, and only for the two URL-
    # fetching tools whose output is a near-pure function of the URL;
    # caching search-family tools serves stale results and masks
    # transient source flakes (a 0-result Reddit response stays for 5m).
    _disabled = {"enabled": False}
    mcp.add_middleware(
        ResponseCachingMiddleware(
            list_tools_settings=ListToolsSettings(**_disabled),
            list_resources_settings=ListResourcesSettings(**_disabled),
            list_prompts_settings=ListPromptsSettings(**_disabled),
            read_resource_settings=ReadResourceSettings(**_disabled),
            get_prompt_settings=GetPromptSettings(**_disabled),
            call_tool_settings=CallToolSettings(
                ttl=300,
                included_tools=["content_operations", "document_analysis"],
            ),
            **caching_kwargs,
        )
    )

    mcp.add_middleware(PerformanceMonitoringMiddleware())
    mcp.add_middleware(BuiltinTimingMiddleware())
    mcp.add_middleware(
        BuiltinLoggingMiddleware(
            include_payloads=True,
            max_payload_length=500,
        )
    )

    mcp.add_middleware(
        ResponseLimitingMiddleware(
            max_size=1_000_000,
            tools=["content_operations", "map_website", "document_analysis"],
        )
    )

    mcp.add_middleware(PingMiddleware(interval_ms=30_000))

    global _security_middleware
    _security_middleware = security_middleware

    logging.getLogger("middleware").info(
        "Middleware stack registered: error, security, rate-limit, cache, "
        "perf, timing, logging, response-limit, ping"
    )


def start_background_tasks():
    """Start background tasks that require an event loop."""
    global _security_middleware
    if _security_middleware:
        try:
            # Only start if there's a running event loop
            import asyncio

            if asyncio.get_running_loop():
                _security_middleware.start_cleanup_task()
                logging.getLogger("middleware").info("Security middleware background tasks started")
            else:
                logging.getLogger("middleware").info(
                    "No running event loop, background tasks will start on first request"
                )
        except RuntimeError:
            logging.getLogger("middleware").info(
                "No running event loop, background tasks will start on first request"
            )

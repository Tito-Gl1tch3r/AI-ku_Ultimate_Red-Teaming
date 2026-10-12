"""Base ToolExecutor class that all tool wrappers inherit from."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

from tengu.executor.process import run_command
from tengu.executor.registry import resolve_tool_path
from tengu.security.allowlist import make_allowlist_from_config
from tengu.security.audit import get_audit_logger
from tengu.security.rate_limiter import rate_limited

logger = structlog.get_logger(__name__)


class ToolExecutor(ABC):
    """Abstract base class for all external tool wrappers.

    Provides:
    - Target validation via allowlist
    - Rate limiting
    - Audit logging
    - Standardized async execution via asyncio.create_subprocess_exec
    """

    #: Override in subclasses to set the tool name used in rate limiting + audit
    tool_name: str = "unknown"

    #: Default execution timeout in seconds
    default_timeout: int = 600

    def __init__(self) -> None:
        self._allowlist = make_allowlist_from_config()
        self._audit = get_audit_logger()

    def _validate_target(self, target: str) -> None:
        """Validate target against the allowlist. Raises TargetNotAllowedError if blocked."""
        self._allowlist.check(target)

    async def _run(
        self,
        args: list[str],
        target: str,
        params: dict[str, Any],
        timeout: int | None = None,
        env: dict[str, str] | None = None,
    ) -> tuple[str, str, int]:
        """Execute the tool with rate limiting and audit logging."""
        effective_timeout = timeout or self.default_timeout

        async with rate_limited(self.tool_name):
            await self._audit.log_tool_call(
                tool=self.tool_name,
                target=target,
                params=params,
                result="started",
            )

            try:
                stdout, stderr, returncode = await run_command(
                    args,
                    timeout=effective_timeout,
                    env=env,
                )
                await self._audit.log_tool_call(
                    tool=self.tool_name,
                    target=target,
                    params=params,
                    result="completed",
                )
                return stdout, stderr, returncode

            except Exception as exc:
                await self._audit.log_tool_call(
                    tool=self.tool_name,
                    target=target,
                    params=params,
                    result="failed",
                    error=str(exc),
                )
                raise

    def _resolve_path(self, configured_path: str = "") -> str:
        """Resolve the tool executable path."""
        return resolve_tool_path(self.tool_name, configured_path)

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool. Must be implemented by each subclass."""
        ...

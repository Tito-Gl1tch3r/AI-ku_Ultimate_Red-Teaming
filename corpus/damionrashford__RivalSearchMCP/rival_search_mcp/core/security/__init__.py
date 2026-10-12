"""
Security module interface.
Provides simplified access to security functionality.
"""

from .security import get_security_middleware


class SecurityManager:
    """Simplified security manager interface."""

    def __init__(self):
        self._middleware = get_security_middleware()

    async def validate_request(self, request_data):
        """Validate an incoming request."""
        return await self._middleware.check_request(request_data)

    async def get_stats(self):
        """Get security statistics."""
        return await self._middleware.get_security_stats()

    def block_ip(self, ip_address: str):
        """Block an IP address."""
        import asyncio

        return asyncio.create_task(self._middleware.block_ip(ip_address))

    def unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        import asyncio

        return asyncio.create_task(self._middleware.unblock_ip(ip_address))

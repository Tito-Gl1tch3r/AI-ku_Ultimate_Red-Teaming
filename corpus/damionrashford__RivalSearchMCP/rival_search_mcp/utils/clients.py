"""
HTTP client management utilities for RivalSearchMCP.
Handles HTTP client session management with connection pooling.
"""

from typing import Optional

import httpx

from .agents import get_random_user_agent

# Use certifi for SSL verification (fixes macOS Python cert issues)
try:
    import certifi

    SSL_VERIFY = certifi.where()
except ImportError:
    SSL_VERIFY = True

# Global connection pool
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create a reusable HTTP client with connection pooling."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            verify=SSL_VERIFY,
            headers={"User-Agent": get_random_user_agent()},
        )
    return _http_client


async def close_http_clients():
    """Close all HTTP clients and free resources."""
    global _http_client

    if _http_client:
        await _http_client.aclose()
        _http_client = None

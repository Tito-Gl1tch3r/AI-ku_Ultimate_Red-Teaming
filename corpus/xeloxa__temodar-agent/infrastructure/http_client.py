"""
HTTP Client Infrastructure
"""

from __future__ import annotations

import threading
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import MAX_POOL_SIZE

DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_BACKOFF_FACTOR = 0.5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)

_session_lock = threading.Lock()
_session: Optional[requests.Session] = None
_configured_pool_size = 0


def _build_retry_strategy() -> Retry:
    """Create a conservative retry strategy for transient HTTP failures."""
    return Retry(
        total=DEFAULT_RETRY_ATTEMPTS,
        connect=DEFAULT_RETRY_ATTEMPTS,
        read=DEFAULT_RETRY_ATTEMPTS,
        status=DEFAULT_RETRY_ATTEMPTS,
        backoff_factor=DEFAULT_BACKOFF_FACTOR,
        status_forcelist=RETRYABLE_STATUS_CODES,
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        raise_on_status=False,
    )


def _build_adapter(pool_size: int) -> HTTPAdapter:
    """Create a pooled HTTP adapter with bounded concurrency."""
    return HTTPAdapter(
        pool_connections=pool_size,
        pool_maxsize=pool_size,
        max_retries=_build_retry_strategy(),
    )


def _configure_session(session: requests.Session, pool_size: int) -> None:
    """Apply pooled adapters to both HTTP and HTTPS transports."""
    adapter = _build_adapter(pool_size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)


def get_session(pool_size: int = MAX_POOL_SIZE) -> requests.Session:
    """Get or create the shared requests session with bounded pooling.

    If a later caller requests a larger pool size, the shared session is upgraded
    to that size up to the configured security ceiling.
    """
    global _session, _configured_pool_size

    safe_pool_size = min(max(pool_size, 1), MAX_POOL_SIZE)
    with _session_lock:
        if _session is None:
            _session = requests.Session()
            _configure_session(_session, safe_pool_size)
            _configured_pool_size = safe_pool_size
            return _session

        if safe_pool_size > _configured_pool_size:
            _configure_session(_session, safe_pool_size)
            _configured_pool_size = safe_pool_size

        return _session

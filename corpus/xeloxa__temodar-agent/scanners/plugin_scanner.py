"""
Temodar Agent Plugin Scanner

Plugin fetching and analysis from WordPress.org API.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, Optional

import requests

from analyzers.risk_labeler import apply_relative_risk_labels
from analyzers.vps_scorer import calculate_vps_score
from config import (
    FEATURE_KEYWORDS,
    RISKY_TAGS,
    SECURITY_KEYWORDS,
    USER_FACING_TAGS,
)
from infrastructure.http_client import get_session
from logger import setup_logger
from models import PluginResult, ScanConfig
from utils.date_utils import calculate_days_ago

logger = setup_logger(__name__)

WORDPRESS_PLUGIN_API_URL = "https://api.wordpress.org/plugins/info/1.2/"
WORDPRESS_PLUGIN_PAGE_SIZE = 100
DEFAULT_FETCH_RETRIES = 3
FETCH_TIMEOUT_SECONDS = 30
RATE_LIMIT_BACKOFF_SECONDS = 5
NETWORK_RETRY_DELAY_SECONDS = 2
AGGRESSIVE_SCAN_THREADS = 50
DEFAULT_SCAN_THREADS = 5
TRUSTED_AUTHOR_KEYWORDS = ("automattic", "wordpress.org")


def analyze_changelog(sections: Dict[str, str]) -> tuple[list[str], list[str]]:
    """Analyze changelog text for security and feature keywords."""
    changelog = str(sections.get("changelog", "") or "").lower()
    if not changelog:
        return [], []

    recent_log = changelog[:2000]
    found_security = [keyword for keyword in SECURITY_KEYWORDS if keyword in recent_log]
    found_features = [keyword for keyword in FEATURE_KEYWORDS if keyword in recent_log]
    return found_security, found_features


def _plugin_query_params(page: int, browse_type: str) -> Dict[str, Any]:
    """Build the WordPress.org plugin query payload."""
    return {
        "action": "query_plugins",
        "request[browse]": browse_type,
        "request[page]": page,
        "request[per_page]": WORDPRESS_PLUGIN_PAGE_SIZE,
        "request[fields][active_installs]": True,
        "request[fields][short_description]": True,
        "request[fields][last_updated]": True,
        "request[fields][download_link]": True,
        "request[fields][ratings]": True,
        "request[fields][num_ratings]": True,
        "request[fields][support_threads]": True,
        "request[fields][support_threads_resolved]": True,
        "request[fields][tested]": True,
        "request[fields][author]": True,
        "request[fields][version]": True,
        "request[fields][tags]": True,
        "request[fields][sections]": True,
        "request[fields][donate_link]": True,
    }


def _handle_rate_limit(attempt: int) -> None:
    """Pause after WordPress API rate limiting."""
    wait_time = RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1)
    logger.error("Rate limited, waiting %ss...", wait_time)
    time.sleep(wait_time)


def _handle_network_retry(error: Exception) -> None:
    """Pause after transient network failures."""
    logger.error("Network error (%s), retrying...", error)
    time.sleep(NETWORK_RETRY_DELAY_SECONDS)


def fetch_plugins(
    page: int,
    browse_type: str,
    max_retries: int = DEFAULT_FETCH_RETRIES,
) -> list[Dict[str, Any]]:
    """Fetch plugins from WP API with retry logic."""
    session = get_session()
    params = _plugin_query_params(page, browse_type)

    for attempt in range(max_retries):
        try:
            response = session.get(
                WORDPRESS_PLUGIN_API_URL,
                params=params,
                timeout=FETCH_TIMEOUT_SECONDS,
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            _handle_network_retry(exc)
            continue
        except Exception as exc:
            logger.error("Unexpected API Error: %s", exc)
            break

        if response.status_code == 200:
            data = response.json()
            return data.get("plugins", []) if data else []

        if response.status_code == 429:
            _handle_rate_limit(attempt)
            continue

        logger.warning(
            "Plugin API request returned non-success status",
            extra={"status_code": response.status_code, "page": page, "browse_type": browse_type},
        )
        break

    return []


def _matches_any_tag(
    candidates: set[str],
    plugin_tags: list[str],
    name: str,
    description: str,
) -> list[str]:
    """Find matching tags across plugin tags, name, and description."""
    return [
        tag for tag in candidates if tag in plugin_tags or tag in name or tag in description
    ]


def _resolve_user_facing(
    config: ScanConfig,
    plugin_tags: list[str],
    name: str,
    description: str,
) -> tuple[bool, bool]:
    """Resolve user-facing filter pass state and final flag."""
    user_facing_match = _matches_any_tag(USER_FACING_TAGS, plugin_tags, name, description)
    if config.user_facing and not user_facing_match:
        return False, False
    return True, bool(user_facing_match)


def _support_resolution_rate(plugin: Dict[str, Any]) -> int:
    """Compute support thread resolution rate percent."""
    total_support = int(plugin.get("support_threads", 0) or 0)
    resolved_support = int(plugin.get("support_threads_resolved", 0) or 0)
    if total_support <= 0:
        return 0
    return int((resolved_support / total_support) * 100)


def _is_trusted_author(author_raw: str) -> bool:
    """Determine whether the plugin author matches trusted publishers."""
    author_lower = author_raw.lower()
    return any(keyword in author_lower for keyword in TRUSTED_AUTHOR_KEYWORDS)


def _build_plugin_result(
    *,
    plugin: Dict[str, Any],
    slug: str,
    installs: int,
    days_ago: int,
    tested_ver: str,
    matched_tags: list[str],
    sec_flags: list[str],
    feat_flags: list[str],
    vps_score: int,
    is_user_facing: bool,
    is_trusted: bool,
) -> PluginResult:
    """Build the normalized PluginResult DTO."""
    return PluginResult(
        name=plugin.get("name", "Unknown"),
        slug=slug,
        version=plugin.get("version", "?"),
        score=vps_score,
        installations=installs,
        days_since_update=days_ago,
        tested_wp_version=tested_ver,
        author_trusted=is_trusted,
        is_risky_category=bool(matched_tags),
        is_user_facing=is_user_facing,
        is_theme=False,
        risk_tags=matched_tags,
        security_flags=sec_flags,
        feature_flags=feat_flags,
        download_link=plugin.get("download_link", ""),
        wp_org_link=f"https://wordpress.org/plugins/{slug}/",
        cve_search_link=f"https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword={slug}",
        wpscan_link=f"https://wpscan.com/plugin/{slug}",
        trac_link=f"https://plugins.trac.wordpress.org/log/{slug}/",
    )


class PluginScanner:
    """High-level plugin scanner with configurable callbacks."""

    def __init__(
        self,
        config: ScanConfig,
        on_result: Optional[Callable[[PluginResult], None]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        self.config = config
        self.on_result = on_result
        self.on_progress = on_progress
        self.results: list[PluginResult] = []
        self.found_count = 0
        self.stop_event = threading.Event()
        self._results_lock = threading.Lock()

    def stop(self) -> None:
        """Stop the scan."""
        self.stop_event.set()

    def _limit_reached(self) -> bool:
        with self._results_lock:
            return self.config.limit > 0 and self.found_count >= self.config.limit

    def _should_stop(self) -> bool:
        return self.stop_event.is_set() or self._limit_reached()

    def _store_result(self, result: PluginResult) -> bool:
        with self._results_lock:
            if self.config.limit > 0 and self.found_count >= self.config.limit:
                return False
            self.found_count += 1
            self.results.append(result)
            return True

    def _passes_install_filters(self, installs: int) -> bool:
        """Check install-count filters."""
        if installs < self.config.min_installs:
            return False
        if self.config.max_installs > 0 and installs > self.config.max_installs:
            return False
        return True

    def _passes_update_age_filters(self, days_ago: int) -> bool:
        """Check update-age and abandoned filters."""
        if self.config.min_days > 0 and days_ago < self.config.min_days:
            return False
        if self.config.max_days > 0 and days_ago > self.config.max_days:
            return False
        if self.config.abandoned and days_ago < 730:
            return False
        return True

    def process_plugin(self, plugin: Dict[str, Any]) -> Optional[PluginResult]:
        """Process a single plugin and return a PluginResult if it passes filters."""
        installs = int(plugin.get("active_installs", 0) or 0)
        if not self._passes_install_filters(installs):
            return None

        days_ago = calculate_days_ago(plugin.get("last_updated"))
        if not self._passes_update_age_filters(days_ago):
            return None

        plugin_tags = list((plugin.get("tags") or {}).keys())
        name = str(plugin.get("name", "") or "").lower()
        description = str(plugin.get("short_description", "") or "").lower()
        matched_tags = _matches_any_tag(RISKY_TAGS, plugin_tags, name, description)
        if self.config.smart and not matched_tags:
            return None

        user_facing_passed, is_user_facing = _resolve_user_facing(
            self.config,
            plugin_tags,
            name,
            description,
        )
        if not user_facing_passed:
            return None

        sec_flags, feat_flags = analyze_changelog(plugin.get("sections", {}))
        tested_ver = str(plugin.get("tested", "?") or "?")
        slug = str(plugin.get("slug", "") or "")
        author_raw = str(plugin.get("author", "Unknown") or "Unknown")
        vps_score = calculate_vps_score(
            plugin,
            days_ago,
            matched_tags,
            _support_resolution_rate(plugin),
            tested_ver,
            sec_flags,
            None,
        )

        return _build_plugin_result(
            plugin=plugin,
            slug=slug,
            installs=installs,
            days_ago=days_ago,
            tested_ver=tested_ver,
            matched_tags=matched_tags,
            sec_flags=sec_flags,
            feat_flags=feat_flags,
            vps_score=vps_score,
            is_user_facing=is_user_facing,
            is_trusted=_is_trusted_author(author_raw),
        )

    def scan_page(self, page: int) -> list[PluginResult]:
        """Scan a single page of plugins."""
        if self._should_stop():
            return []

        plugins = fetch_plugins(page, self.config.sort)
        page_results: list[PluginResult] = []
        for plugin in plugins:
            if self._should_stop():
                break

            result = self.process_plugin(plugin)
            if result is None:
                continue
            if not self._store_result(result):
                break

            page_results.append(result)
            if self.on_result:
                self.on_result(result)
        return page_results

    def _notify_progress(self, current: int, total: int) -> None:
        if self.on_progress:
            self.on_progress(current, total)

    def _scan_sequentially(self, pages_to_scan: list[int]) -> list[PluginResult]:
        """Run pages sequentially when a hard result limit is enforced."""
        total_pages = len(pages_to_scan)
        for index, page in enumerate(pages_to_scan, start=1):
            if self._should_stop():
                break
            self.scan_page(page)
            self._notify_progress(index, total_pages)
        return self.results

    def _drain_future_results(
        self,
        futures: Dict[Future[list[PluginResult]], int],
        total_pages: int,
        executor: ThreadPoolExecutor,
    ) -> list[PluginResult]:
        """Collect concurrent page scan results and emit progress updates."""
        for index, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()
            except Exception as exc:
                failed_page = futures[future]
                logger.error("Page scan failed for page %s: %s", failed_page, exc)

            self._notify_progress(index, total_pages)
            if self.stop_event.is_set():
                executor.shutdown(wait=False, cancel_futures=True)
                break
        return self.results

    def _scan_concurrently(
        self,
        pages_to_scan: list[int],
        max_threads: int,
    ) -> list[PluginResult]:
        """Run page scans concurrently for unrestricted scans."""
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {
                executor.submit(self.scan_page, page): page for page in pages_to_scan
            }
            return self._drain_future_results(futures, len(pages_to_scan), executor)

    def scan(self) -> list[PluginResult]:
        """Run the full scan based on configuration."""
        pages_to_scan = list(range(1, self.config.pages + 1))
        max_threads = (
            AGGRESSIVE_SCAN_THREADS if self.config.aggressive else DEFAULT_SCAN_THREADS
        )
        if self.config.aggressive:
            logger.info("Using aggressive scan mode", extra={"max_threads": max_threads})

        results = (
            self._scan_sequentially(pages_to_scan)
            if self.config.limit > 0
            else self._scan_concurrently(pages_to_scan, max_threads)
        )
        self._apply_relative_risk_labels()
        return results

    def _apply_relative_risk_labels(self) -> None:
        """Apply relative risk labels on top of absolute critical rules."""
        apply_relative_risk_labels(
            self.results,
            get_score=lambda item: item.score,
            set_label=lambda item, label: setattr(item, "relative_risk", label),
        )

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import BackgroundTasks, HTTPException

from analyzers.risk_labeler import apply_relative_risk_labels
from database.repository import ScanRepository
from models import PluginResult, ScanConfig, ScanStatus
from scanners.plugin_scanner import PluginScanner
from scanners.theme_scanner import ThemeScanner
from server.websockets import manager

active_scans: Dict[int, Any] = {}
HIGH_RISK_LABELS = {"HIGH", "CRITICAL"}


def request_scanner_stop(scanner: Any) -> None:
    """Stop a scanner instance if it supports cooperative cancellation."""
    stop = getattr(scanner, "stop", None)
    if callable(stop):
        stop()


def apply_relative_risk_labels_to_dict_results(results: List[Dict[str, Any]]) -> None:
    """Apply percentile-based relative risk labels to API result dictionaries."""
    apply_relative_risk_labels(
        results,
        get_score=lambda item: int(item.get("score", 0) or 0),
        set_label=lambda item, label: item.__setitem__("relative_risk", label),
    )


def build_scan_config(scan_request) -> ScanConfig:
    """Normalize incoming scan request values into repository scan config."""
    sort = scan_request.sort
    pages = scan_request.pages

    if scan_request.abandoned and sort == "updated":
        sort = "popular"
    if scan_request.abandoned and pages == 5:
        pages = 100

    return ScanConfig(
        pages=pages,
        limit=scan_request.limit,
        min_installs=scan_request.min_installs,
        max_installs=scan_request.max_installs,
        sort=sort,
        smart=scan_request.smart,
        abandoned=scan_request.abandoned,
        user_facing=scan_request.user_facing,
        themes=scan_request.themes,
        min_days=scan_request.min_days,
        max_days=scan_request.max_days,
        aggressive=scan_request.aggressive,
    )


def _build_theme_plugin_result(result: Dict[str, Any]) -> PluginResult:
    """Convert a theme scanner payload into PluginResult storage format."""
    return PluginResult(
        slug=result.get("slug", ""),
        name=result.get("name", "Unknown"),
        version=result.get("version", "?"),
        score=result.get("risk_score", 0),
        relative_risk=result.get("risk_level", ""),
        installations=result.get("downloads", 0),
        days_since_update=result.get("days_since_update", 0),
        is_theme=True,
        wp_org_link=result.get("wp_org_link", ""),
        trac_link=result.get("trac_link", ""),
        wpscan_link=result.get("wpscan_link", ""),
        cve_search_link=result.get("cve_search_link", ""),
        download_link=result.get("download_link", ""),
    )


async def _send_session_event(session_id: int, payload: Dict[str, Any]) -> None:
    """Send a websocket event to scan listeners."""
    await manager.send_to_session(session_id, payload)


def _send_session_event_threadsafe(
    loop: asyncio.AbstractEventLoop,
    session_id: int,
    payload: Dict[str, Any],
) -> None:
    """Schedule websocket event delivery from a worker thread."""
    asyncio.run_coroutine_threadsafe(_send_session_event(session_id, payload), loop)


def _scan_was_cancelled(session_id: int, repo: ScanRepository) -> bool:
    """Check whether a scan has already been marked cancelled."""
    session_state = repo.get_session(session_id)
    return bool(
        session_state and session_state.get("status") == ScanStatus.CANCELLED.value
    )


async def _handle_scan_cancellation(
    *,
    session_id: int,
    repo: ScanRepository,
    found_count: int,
    high_risk_count: int,
) -> bool:
    """Persist and emit cancellation state if scan was cancelled."""
    if not _scan_was_cancelled(session_id, repo):
        return False

    repo.update_session_status(
        session_id,
        ScanStatus.CANCELLED,
        total_found=found_count,
        high_risk_count=high_risk_count,
    )
    await _send_session_event(
        session_id,
        {
            "type": "cancelled",
            "session_id": session_id,
            "total_found": found_count,
            "high_risk_count": high_risk_count,
        },
    )
    return True


async def _deduplicate_completed_scan(
    *,
    session_id: int,
    repo: ScanRepository,
    config: ScanConfig,
) -> bool:
    """Merge duplicate completed scans that match previous results/config."""
    prev_session_id = repo.get_latest_session_by_config(config.to_dict(), session_id)
    if not prev_session_id:
        return False

    current_slugs = set(repo.get_result_slugs(session_id))
    prev_slugs = set(repo.get_result_slugs(prev_session_id))
    if current_slugs != prev_slugs:
        return False

    repo.delete_session(session_id)
    repo.mark_session_merged(prev_session_id)
    await _send_session_event(
        session_id,
        {
            "type": "deduplicated",
            "original_session_id": prev_session_id,
            "message": "Results identical to previous scan. Merged.",
        },
    )
    return True


def _save_plugin_result_and_emit(
    *,
    loop: asyncio.AbstractEventLoop,
    session_id: int,
    repo: ScanRepository,
    result: PluginResult,
    found_count: int,
) -> None:
    """Persist a plugin result and notify listeners."""
    repo.save_result(session_id, result)
    _send_session_event_threadsafe(
        loop,
        session_id,
        {
            "type": "result",
            "data": result.to_dict(),
            "found_count": found_count,
        },
    )


def _emit_progress(
    *,
    loop: asyncio.AbstractEventLoop,
    session_id: int,
    current: int,
    total: int,
) -> None:
    """Emit scan progress updates."""
    _send_session_event_threadsafe(
        loop,
        session_id,
        {
            "type": "progress",
            "current": current,
            "total": total,
            "percent": int((current / total) * 100),
        },
    )


def _count_high_risk_plugin_results(results: List[PluginResult]) -> int:
    """Count high-risk plugin results after relative labeling."""
    return sum(
        1
        for result in results
        if getattr(result, "relative_risk", "") in HIGH_RISK_LABELS
    )


async def _run_theme_scan(
    *,
    session_id: int,
    config: ScanConfig,
    repo: ScanRepository,
) -> tuple[int, int]:
    """Run theme scanning mode and persist streaming results."""
    found_count = 0
    high_risk_count = 0
    loop = asyncio.get_running_loop()

    def sync_on_theme_result(result: Dict[str, Any]) -> None:
        nonlocal found_count, high_risk_count
        found_count += 1
        if result.get("risk_level") == "HIGH":
            high_risk_count += 1

        plugin_result = _build_theme_plugin_result(result)
        _save_plugin_result_and_emit(
            loop=loop,
            session_id=session_id,
            repo=repo,
            result=plugin_result,
            found_count=found_count,
        )

    scanner = ThemeScanner(
        pages=config.pages,
        limit=config.limit,
        sort=config.sort,
        on_result=sync_on_theme_result,
    )
    active_scans[session_id] = scanner
    await loop.run_in_executor(None, scanner.scan)
    return found_count, high_risk_count


async def _run_plugin_scan(
    *,
    session_id: int,
    config: ScanConfig,
    repo: ScanRepository,
) -> tuple[int, int]:
    """Run plugin scanning mode and persist streaming results."""
    found_count = 0
    loop = asyncio.get_running_loop()
    scanner = PluginScanner(config)
    active_scans[session_id] = scanner

    def sync_on_result(result: PluginResult) -> None:
        nonlocal found_count
        found_count += 1
        _save_plugin_result_and_emit(
            loop=loop,
            session_id=session_id,
            repo=repo,
            result=result,
            found_count=found_count,
        )

    def sync_on_progress(current: int, total: int) -> None:
        _emit_progress(
            loop=loop,
            session_id=session_id,
            current=current,
            total=total,
        )

    scanner.on_result = sync_on_result
    scanner.on_progress = sync_on_progress
    await loop.run_in_executor(None, scanner.scan)
    return found_count, _count_high_risk_plugin_results(scanner.results)


async def _run_scan_mode(
    *,
    session_id: int,
    config: ScanConfig,
    repo: ScanRepository,
) -> tuple[int, int]:
    """Dispatch the configured scan mode."""
    if config.themes:
        return await _run_theme_scan(session_id=session_id, config=config, repo=repo)
    return await _run_plugin_scan(session_id=session_id, config=config, repo=repo)


async def _finalize_scan_completion(
    *,
    session_id: int,
    config: ScanConfig,
    repo: ScanRepository,
    found_count: int,
    high_risk_count: int,
) -> bool:
    """Persist completion state, handling cancellation/dedup pathways."""
    if await _handle_scan_cancellation(
        session_id=session_id,
        repo=repo,
        found_count=found_count,
        high_risk_count=high_risk_count,
    ):
        return False

    repo.update_session_status(
        session_id,
        ScanStatus.COMPLETED,
        total_found=found_count,
        high_risk_count=high_risk_count,
    )

    if await _deduplicate_completed_scan(
        session_id=session_id,
        repo=repo,
        config=config,
    ):
        return False

    await _send_session_event(
        session_id,
        {
            "type": "complete",
            "session_id": session_id,
            "total_found": found_count,
            "high_risk_count": high_risk_count,
        },
    )
    return True


async def run_scan_task(session_id: int, config: ScanConfig, repo: ScanRepository) -> None:
    """Background task to run a scan (plugin or theme)."""
    try:
        repo.update_session_status(session_id, ScanStatus.RUNNING)
        await _send_session_event(session_id, {"type": "start", "session_id": session_id})

        found_count, high_risk_count = await _run_scan_mode(
            session_id=session_id,
            config=config,
            repo=repo,
        )

        await _finalize_scan_completion(
            session_id=session_id,
            config=config,
            repo=repo,
            found_count=found_count,
            high_risk_count=high_risk_count,
        )
    except Exception as exc:
        repo.update_session_status(session_id, ScanStatus.FAILED, error_message=str(exc))
        await _send_session_event(session_id, {"type": "error", "message": str(exc)})
    finally:
        active_scans.pop(session_id, None)


def list_scan_sessions(*, repo: ScanRepository, limit: int) -> Dict[str, Any]:
    """Return scan session list payload."""
    return {"sessions": repo.get_all_sessions(limit)}


def create_scan_session(
    *,
    repo: ScanRepository,
    scan_request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """Create a session and enqueue the background scan task."""
    config = build_scan_config(scan_request)
    session_id = repo.create_session(config)
    background_tasks.add_task(run_scan_task, session_id, config, repo)
    return {
        "session_id": session_id,
        "status": "started",
        "websocket_url": f"/ws/scans/{session_id}",
    }


def get_scan_session(*, repo: ScanRepository, session_id: int) -> Dict[str, Any]:
    """Return one scan session or raise 404."""
    session = repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return session


def get_scan_session_results(
    *,
    repo: ScanRepository,
    session_id: int,
    sort_by: str,
    sort_order: str,
    limit: int,
) -> Dict[str, Any]:
    """Return scan session results plus Semgrep state."""
    get_scan_session(repo=repo, session_id=session_id)
    results = repo.get_session_results(session_id, sort_by, sort_order, limit)
    apply_relative_risk_labels_to_dict_results(results)

    slugs = [result["slug"] for result in results]
    semgrep_statuses = repo.get_semgrep_statuses_for_slugs(slugs)
    for result in results:
        result["semgrep"] = semgrep_statuses.get(result["slug"])

    return {"session_id": session_id, "total": len(results), "results": results}


def delete_scan_session(*, repo: ScanRepository, session_id: int) -> Dict[str, Any]:
    """Delete a scan session and stop active scanner if needed."""
    scanner = active_scans.pop(session_id, None)
    if scanner is not None:
        request_scanner_stop(scanner)

    success = repo.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Scan session not found")
    return {"status": "deleted"}

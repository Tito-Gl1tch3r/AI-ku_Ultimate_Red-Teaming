"""
Semgrep Router
"""

from fastapi import APIRouter, BackgroundTasks, Request

from database.repository import ScanRepository
from server.limiter import limiter
from server.routers.semgrep_helpers import build_semgrep_rules_response
from server.routers.semgrep_service import (
    add_custom_rule,
    add_ruleset,
    delete_custom_rule,
    delete_ruleset,
    get_bulk_semgrep_scan_stats,
    get_latest_semgrep_scan,
    start_bulk_semgrep_scan,
    start_semgrep_scan_for_plugin,
    stop_bulk_semgrep_scan,
    toggle_all_custom_rules,
    toggle_custom_rule,
    toggle_ruleset,
)
from server.schemas import (
    DownloadRequest,
    SemgrepBulkToggleRequest,
    SemgrepRuleRequest,
    SemgrepRulesetRequest,
)

router = APIRouter(prefix="/api/semgrep", tags=["semgrep"])
repo = ScanRepository()


@router.post("/scan")
@limiter.limit("5000/minute")
async def start_semgrep_scan(
    request: Request, scan_request: DownloadRequest, background_tasks: BackgroundTasks
):
    """Start a Semgrep scan for a specific plugin."""
    return start_semgrep_scan_for_plugin(
        repo=repo,
        scan_request=scan_request,
        background_tasks=background_tasks,
    )


@router.get("/scan/{slug}")
async def get_semgrep_scan(slug: str):
    """Get the latest Semgrep scan for a plugin."""
    return get_latest_semgrep_scan(repo=repo, slug=slug)


@router.get("/rules")
async def get_semgrep_rules():
    """Get Semgrep configuration (rulesets and custom rules)."""
    return build_semgrep_rules_response()


@router.post("/rules")
async def create_semgrep_rule(rule: SemgrepRuleRequest):
    """Add a custom Semgrep rule."""
    return add_custom_rule(rule)


@router.delete("/rules/{rule_id}")
async def remove_semgrep_rule(rule_id: str):
    """Delete a custom Semgrep rule."""
    return delete_custom_rule(rule_id)


@router.post("/rules/{rule_id}/toggle")
async def toggle_semgrep_rule(rule_id: str):
    """Enable or disable a custom Semgrep rule."""
    return toggle_custom_rule(rule_id)


@router.post("/rules/actions/toggle-all")
async def toggle_all_semgrep_rules(toggle_request: SemgrepBulkToggleRequest):
    return toggle_all_custom_rules(enabled=toggle_request.enabled)


@router.post("/rulesets")
async def create_ruleset(ruleset_request: SemgrepRulesetRequest):
    """Add a Semgrep ruleset (e.g., p/cwe-top-25) and enable it."""
    return add_ruleset(ruleset_request.ruleset)


@router.post("/rulesets/{ruleset_id:path}/toggle")
async def toggle_semgrep_ruleset(ruleset_id: str):
    """Enable or disable a Semgrep ruleset."""
    return toggle_ruleset(ruleset_id)


@router.delete("/rulesets/{ruleset_id:path}")
async def remove_ruleset(ruleset_id: str):
    """Delete a user-added Semgrep ruleset."""
    return delete_ruleset(ruleset_id)


@router.post("/bulk/{session_id}")
async def run_bulk_semgrep(session_id: int, background_tasks: BackgroundTasks):
    """Start or resume a bulk Semgrep scan for all plugins in a session."""
    return start_bulk_semgrep_scan(
        repo=repo,
        session_id=session_id,
        background_tasks=background_tasks,
    )


@router.post("/bulk/{session_id}/stop")
async def stop_bulk_semgrep(session_id: int):
    """Stop a running bulk Semgrep scan."""
    return stop_bulk_semgrep_scan(session_id)


@router.get("/bulk/{session_id}/stats")
async def get_bulk_semgrep_stats(session_id: int):
    """Get aggregated stats for a bulk scan."""
    return get_bulk_semgrep_scan_stats(repo=repo, session_id=session_id)

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import BackgroundTasks, HTTPException

from server.routers.semgrep_helpers import (
    CORE_RULESET_CONFIGS,
    CORE_RULESET_KEYS,
    CUSTOM_RULES_PATH,
    SEMGREP_REGISTRY_RULESETS,
    _canonicalize_ruleset_value,
    _validate_rule_id_or_raise,
    _validate_semgrep_rules_config,
    _validate_slug_or_raise,
    get_disabled_config,
    load_custom_rules_document,
    save_custom_rules_document,
    save_disabled_config,
    validate_ruleset_or_raise,
)
from server.routers.semgrep_tasks import (
    active_bulk_scans,
    run_bulk_semgrep_task,
    run_plugin_semgrep_scan,
)

SEMGREP_BULK_RESULT_LIMIT = 9999


def require_valid_slug(slug: str) -> str:
    """Validate plugin slug and map failures to HTTP 400."""
    try:
        return _validate_slug_or_raise(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid slug format") from exc


def require_valid_rule_id(rule_id: str) -> str:
    """Validate custom rule id and map failures to HTTP 400."""
    try:
        return _validate_rule_id_or_raise(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid rule ID format") from exc


def require_valid_ruleset(ruleset: str) -> str:
    """Validate ruleset identifier and map failures to HTTP 400."""
    try:
        return validate_ruleset_or_raise(ruleset)
    except ValueError as exc:
        detail = (
            "Ruleset cannot be empty"
            if not str(ruleset or "").strip()
            else str(exc)
        )
        raise HTTPException(status_code=400, detail=detail) from exc


def _resolve_single_scan_version(*, repo, slug: str) -> str:
    """Resolve the best available version for a single-plugin Semgrep scan."""
    try:
        resolved = repo.get_catalog_latest_version(slug, is_theme=False)
    except Exception:
        resolved = None
    return str(resolved or "latest")



def start_semgrep_scan_for_plugin(*, repo, scan_request, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Create a Semgrep scan record and enqueue the background task."""
    safe_slug = require_valid_slug(scan_request.slug)
    resolved_version = _resolve_single_scan_version(repo=repo, slug=safe_slug)
    scan_id = repo.create_semgrep_scan(safe_slug, version=resolved_version)
    background_tasks.add_task(
        run_plugin_semgrep_scan,
        scan_id,
        safe_slug,
        str(scan_request.download_url),
        repo,
    )
    return {"success": True, "scan_id": scan_id, "status": "pending"}


def get_latest_semgrep_scan(*, repo, slug: str) -> Dict[str, Any]:
    """Return the latest Semgrep scan payload for a plugin."""
    safe_slug = require_valid_slug(slug)
    scan = repo.get_semgrep_scan(safe_slug)
    return scan or {"status": "none"}


def add_custom_rule(rule) -> Dict[str, Any]:
    """Persist a validated custom Semgrep rule."""
    rule_id = require_valid_rule_id(rule.id)
    existing_rules = load_custom_rules_document()
    for existing in existing_rules.get("rules", []):
        if existing.get("id") == rule_id:
            raise HTTPException(
                status_code=400,
                detail=f"Rule with ID '{rule_id}' already exists",
            )

    new_rule = {
        "id": rule_id,
        "pattern": rule.pattern,
        "message": rule.message,
        "languages": rule.languages,
        "severity": rule.severity,
    }
    existing_rules.setdefault("rules", []).append(new_rule)

    validation_error = _validate_semgrep_rules_config(existing_rules)
    if validation_error:
        raise HTTPException(
            status_code=400,
            detail=(
                "Rule validation failed. Please check your Semgrep pattern syntax. "
                f"Details: {validation_error}"
            ),
        )

    try:
        save_custom_rules_document(existing_rules)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save rule: {exc}",
        ) from exc
    return {"success": True, "rule_id": rule_id}


def delete_custom_rule(rule_id: str) -> Dict[str, Any]:
    """Delete an existing custom Semgrep rule."""
    rule_id = require_valid_rule_id(rule_id)
    if not CUSTOM_RULES_PATH.exists():
        raise HTTPException(status_code=404, detail="No custom rules file found")

    try:
        rules_data = load_custom_rules_document()
        original_count = len(rules_data.get("rules", []))
        rules_data["rules"] = [
            rule for rule in rules_data.get("rules", []) if rule.get("id") != rule_id
        ]
        if len(rules_data["rules"]) == original_count:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
        save_custom_rules_document(rules_data)
        return {"success": True, "deleted": rule_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete rule: {exc}",
        ) from exc


def toggle_custom_rule(rule_id: str) -> Dict[str, Any]:
    """Toggle a custom rule enabled state."""
    rule_id = require_valid_rule_id(rule_id)
    config = get_disabled_config()
    if rule_id in config["rules"]:
        config["rules"].remove(rule_id)
        save_disabled_config(config)
        return {"success": True, "rule_id": rule_id, "enabled": True}

    config["rules"].append(rule_id)
    save_disabled_config(config)
    return {"success": True, "rule_id": rule_id, "enabled": False}


def toggle_all_custom_rules(*, enabled: bool) -> Dict[str, Any]:
    """Bulk toggle all custom rule states."""
    rules_data = load_custom_rules_document()
    custom_rule_ids: List[str] = []
    for rule in rules_data.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_id = rule.get("id")
        if not isinstance(rule_id, str):
            continue
        try:
            custom_rule_ids.append(_validate_rule_id_or_raise(rule_id))
        except ValueError:
            continue

    if not custom_rule_ids:
        return {"success": True, "enabled": enabled, "changed": 0, "total": 0}

    config = get_disabled_config()
    disabled_rules = set(config.get("rules", []))
    changed = 0

    if enabled:
        for rule_id in custom_rule_ids:
            if rule_id in disabled_rules:
                disabled_rules.remove(rule_id)
                changed += 1
    else:
        for rule_id in custom_rule_ids:
            if rule_id not in disabled_rules:
                disabled_rules.add(rule_id)
                changed += 1

    config["rules"] = sorted(disabled_rules)
    save_disabled_config(config)
    return {
        "success": True,
        "enabled": enabled,
        "changed": changed,
        "total": len(custom_rule_ids),
    }


def add_ruleset(ruleset: str) -> Dict[str, Any]:
    """Add and enable a Semgrep ruleset."""
    ruleset_id = require_valid_ruleset(ruleset)
    config = get_disabled_config()
    if (
        ruleset_id not in config["extra_rulesets"]
        and ruleset_id not in SEMGREP_REGISTRY_RULESETS
    ):
        config["extra_rulesets"].append(ruleset_id)

    if ruleset_id in config["rulesets"]:
        config["rulesets"].remove(ruleset_id)

    save_disabled_config(config)
    return {"success": True, "ruleset_id": ruleset_id, "enabled": True}


def toggle_ruleset(ruleset_id: str) -> Dict[str, Any]:
    """Toggle a ruleset enabled state."""
    ruleset_id = require_valid_ruleset(ruleset_id)
    config = get_disabled_config()
    available_rulesets = set(CORE_RULESET_KEYS) | set(config.get("extra_rulesets", []))
    if ruleset_id not in available_rulesets:
        raise HTTPException(status_code=404, detail=f"Ruleset '{ruleset_id}' not found")

    if ruleset_id in config["rulesets"]:
        config["rulesets"].remove(ruleset_id)
        save_disabled_config(config)
        return {"success": True, "ruleset_id": ruleset_id, "enabled": True}

    config["rulesets"].append(ruleset_id)
    save_disabled_config(config)
    return {"success": True, "ruleset_id": ruleset_id, "enabled": False}


def delete_ruleset(ruleset_id: str) -> Dict[str, Any]:
    """Delete a user-added Semgrep ruleset."""
    ruleset_id = require_valid_ruleset(ruleset_id)
    canonical = _canonicalize_ruleset_value(ruleset_id)
    if canonical in CORE_RULESET_KEYS or canonical in CORE_RULESET_CONFIGS:
        raise HTTPException(status_code=400, detail="Built-in rulesets cannot be deleted")

    config = get_disabled_config()
    extras = config.get("extra_rulesets", [])
    if ruleset_id not in extras:
        raise HTTPException(status_code=404, detail=f"Ruleset '{ruleset_id}' not found")

    config["extra_rulesets"] = [item for item in extras if item != ruleset_id]
    config["rulesets"] = [item for item in config.get("rulesets", []) if item != ruleset_id]
    save_disabled_config(config)
    return {"success": True, "deleted": ruleset_id}


def start_bulk_semgrep_scan(*, repo, session_id: int, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Start or resume a bulk Semgrep scan for all plugins in a session."""
    if session_id in active_bulk_scans:
        raise HTTPException(status_code=400, detail="Bulk scan already running for this session")

    results = repo.get_session_results(session_id, limit=SEMGREP_BULK_RESULT_LIMIT)
    if not results:
        raise HTTPException(status_code=404, detail="No plugins found in this session")

    stop_event = asyncio.Event()
    active_bulk_scans[session_id] = stop_event
    background_tasks.add_task(run_bulk_semgrep_task, session_id, results, repo, stop_event)
    return {"success": True, "count": len(results), "status": "started"}


def stop_bulk_semgrep_scan(session_id: int) -> Dict[str, Any]:
    """Signal a running bulk Semgrep scan to stop."""
    if session_id not in active_bulk_scans:
        raise HTTPException(status_code=404, detail="No active bulk scan found for this session")

    active_bulk_scans[session_id].set()
    return {"success": True, "status": "stopping"}


def get_bulk_semgrep_scan_stats(*, repo, session_id: int) -> Dict[str, Any]:
    """Return aggregated Semgrep stats for a scan session."""
    results = repo.get_session_results(session_id, limit=SEMGREP_BULK_RESULT_LIMIT)
    slugs = [result["slug"] for result in results]
    stats = repo.get_semgrep_stats_for_slugs(slugs)

    total_plugins = len(slugs)
    scanned_count = int(stats.get("scanned_count", 0) or 0)
    progress = int((scanned_count / total_plugins) * 100) if total_plugins > 0 else 0

    return {
        "session_id": session_id,
        "total_plugins": total_plugins,
        "scanned_count": scanned_count,
        "progress": progress,
        "total_findings": stats.get("total_findings", 0),
        "breakdown": stats.get("breakdown", {}),
        "running_count": stats.get("running_count", 0),
        "pending_count": stats.get("pending_count", 0),
        "failed_count": stats.get("failed_count", 0),
        "completed_count": stats.get("completed_count", 0),
        "is_running": session_id in active_bulk_scans,
    }

from __future__ import annotations

import json
from typing import Any, cast

from playwright.async_api import BrowserContext

SESSION_STORAGE_KEY = "session_storage"
StorageState = dict[str, Any]
SessionStorageEntry = dict[str, Any]
SessionStorageEntries = list[SessionStorageEntry]


def split_storage_state(
    bundle: StorageState | None,
) -> tuple[StorageState | None, SessionStorageEntries]:
    if not bundle:
        return None, []
    sessions = cast(SessionStorageEntries, bundle.get(SESSION_STORAGE_KEY) or [])

    if SESSION_STORAGE_KEY in bundle:
        storage = {k: v for k, v in bundle.items() if k != SESSION_STORAGE_KEY}
    else:
        storage = dict(bundle)

    if not storage:
        storage = None
    return storage, list(sessions)


async def dump_session_storage(context: BrowserContext) -> SessionStorageEntries:
    by_origin: dict[str, dict[str, str]] = {}
    for page in context.pages:
        try:
            origin = await page.evaluate("() => window.location.origin")
        except Exception:
            continue

        if not origin or origin == "null":
            continue

        try:
            items = await page.evaluate(
                "() => Object.fromEntries(Object.entries(sessionStorage))",
            )
        except Exception:
            continue
        if not items:
            continue

        merged = by_origin.setdefault(origin, {})
        for k, v in items.items():
            merged[str(k)] = str(v)
    return [{"origin": origin, "items": items} for origin, items in by_origin.items()]


def build_session_storage_init_script(sessions: SessionStorageEntries) -> str:
    by_origin: dict[str, dict[str, str]] = {}
    for entry in sessions or ():
        if not isinstance(entry, dict):
            continue
        origin = entry.get("origin")
        if not origin or not isinstance(origin, str):
            continue
        items = entry.get("items")
        mapping: dict[str, str] = {}

        if isinstance(items, dict):
            mapping = {str(k): str(v) for k, v in items.items()}
        elif isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                value = item.get("value")
                if name is None or value is None:
                    continue
                mapping[str(name)] = str(value)
        if mapping:
            by_origin.setdefault(origin, {}).update(mapping)

    if not by_origin:
        return ""

    payload = json.dumps(by_origin, ensure_ascii=False)
    return (
        "(function(){"
        f"var data={payload};"
        "var here=window.location.origin;"
        "if(!Object.prototype.hasOwnProperty.call(data,here))return;"
        "var entries=data[here];"
        "for(var k in entries){"
        "if(!Object.prototype.hasOwnProperty.call(entries,k))continue;"
        "try{sessionStorage.setItem(k,entries[k]);}catch(_){}}"
        "})();"
    )


async def apply_auth_bundle_to_context(
    context: BrowserContext,
    bundle: StorageState | None,
) -> None:
    if not bundle:
        return

    _, sessions = split_storage_state(bundle)
    if not sessions:
        return

    script = build_session_storage_init_script(sessions)
    if not script:
        return

    await context.add_init_script(script)


async def export_auth_bundle(context: BrowserContext) -> StorageState:
    storage = await context.storage_state()
    bundle: dict[str, Any] = dict(storage)

    sessions = await dump_session_storage(context)
    if sessions:
        bundle[SESSION_STORAGE_KEY] = sessions
    return bundle

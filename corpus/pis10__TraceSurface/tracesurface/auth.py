from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from tracesurface.collection.runtime.auth import export_auth_bundle
from tracesurface.config import DEFAULT_SETTINGS


def format_age(seconds: float) -> str:
    seconds_i = max(0, int(seconds))

    if seconds_i < 60:
        return f"{seconds_i} 秒前"
    if seconds_i < 3600:
        return f"{seconds_i // 60} 分钟前"
    if seconds_i < 86400:
        return f"{seconds_i // 3600} 小时前"
    return f"{seconds_i // 86400} 天前"


def load_auth_state(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


async def save_login_state(
    *,
    url: str | None,
    output_path: Path,
    notice,
    warn,
) -> None:
    from tracesurface.collection.runtime.browser_context import launch_browser

    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, headless=False)
        try:
            context = await browser.new_context(
                user_agent=DEFAULT_SETTINGS.browser.user_agent,
                ignore_https_errors=DEFAULT_SETTINGS.browser.ignore_https_errors,
            )
            page = await context.new_page()

            if url:
                try:
                    await page.goto(url)
                except Exception as exc:
                    warn(exc)

            notice()
            await asyncio.to_thread(input)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            bundle = await export_auth_bundle(context)
            with output_path.open("w", encoding="utf-8") as file:
                json.dump(bundle, file, ensure_ascii=False, indent=2)
        finally:
            await browser.close()


def auth_state_age(path: Path) -> str:
    return format_age(time.time() - path.stat().st_mtime)

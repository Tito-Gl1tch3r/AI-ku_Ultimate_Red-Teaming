from __future__ import annotations
from typing import Any
from datetime import datetime, date, timezone
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import StrictUndefined
from zoneinfo import ZoneInfo

class LockedDownEnv(SandboxedEnvironment):
    def is_safe_callable(self, obj: Any) -> bool:
        return False

def _datefmt(value: Any, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day).strftime(fmt)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).strftime(fmt)
        except Exception:
            return value
    return str(value)

def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
    return datetime.fromtimestamp(0, tz=timezone.utc)

def _tz(value: Any, tz_name: str = "UTC") -> datetime:
    dt = _to_datetime(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc) # assume UTC
    if ZoneInfo is None:
        return dt
    try:
        return dt.astimezone(ZoneInfo(tz_name))
    except Exception:
        return dt


def _build_env(*, autoescape: bool) -> LockedDownEnv:
    # Block all function calls
    env = LockedDownEnv(autoescape=autoescape, undefined=StrictUndefined)

    # No globals
    env.globals.clear()

    allowed_filters = {
        "upper",
        "lower",
        "replace",
        "default",
        "escape",
        "length",
        "trim",
        "title",
        "urlencode",
    }
    env.filters = {k: v for k, v in env.filters.items() if k in allowed_filters}

    # Add date formatter
    env.filters["datefmt"] = _datefmt
    env.filters["tz"] = _tz

    return env

env_html = _build_env(autoescape=True)
env_text = _build_env(autoescape=False)
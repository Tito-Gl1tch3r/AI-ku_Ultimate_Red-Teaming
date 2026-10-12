from __future__ import annotations

from urllib.parse import urljoin, urlparse

AppConfig = dict[str, object]


def classify_app_entries(
    apps: list[AppConfig],
    target_url: str,
) -> tuple[set[str], set[str], set[str]]:
    js_urls: set[str] = set()
    activation_prefixes: set[str] = set()
    html_entry_urls: set[str] = set()

    parsed_target = urlparse(target_url)
    base_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

    def _to_absolute(u: str) -> str:
        if u.startswith("//"):
            return parsed_target.scheme + ":" + u
        if u.startswith("http://") or u.startswith("https://"):
            return u

        if u.startswith("/"):
            return base_origin + u

        return urljoin(target_url, u)

    for app in apps:
        entry = app.get("entry")
        active_rule = app.get("activeRule")

        if isinstance(entry, dict):
            scripts = entry.get("scripts")
            if isinstance(scripts, list):
                for s in scripts:
                    if not (isinstance(s, str) and s):
                        continue
                    abs_url = _to_absolute(s).split("?")[0]
                    if abs_url.endswith(".js"):
                        js_urls.add(abs_url)

        elif isinstance(entry, str) and entry:
            abs_url = _to_absolute(entry).split("?")[0]
            if abs_url.endswith(".js"):
                js_urls.add(abs_url)
            else:
                html_entry_urls.add(abs_url)
                p = urlparse(abs_url)
                if p.path:
                    activation_prefixes.add(p.path.rstrip("/") or "/")

        if isinstance(active_rule, str) and active_rule:
            prefix = active_rule if active_rule.startswith("/") else "/" + active_rule
            activation_prefixes.add(prefix)
        elif isinstance(active_rule, list):
            for r in active_rule:
                if isinstance(r, str) and r:
                    prefix = r if r.startswith("/") else "/" + r
                    activation_prefixes.add(prefix)

    return js_urls, activation_prefixes, html_entry_urls

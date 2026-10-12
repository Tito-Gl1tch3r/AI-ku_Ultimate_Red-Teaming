from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, urlsplit, urlunparse

from tracesurface.models import RouteFact, SourceRef


def clean_url(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query="", fragment=""))


@dataclass(frozen=True, slots=True)
class JSFact:
    url: str
    source: str
    evidence_url: str = ""


@dataclass(frozen=True, slots=True)
class HTMLFact:
    url: str
    ref: SourceRef
    source: str


_NON_PAGE_EXTENSIONS = {
    ".7z",
    ".avi",
    ".css",
    ".csv",
    ".doc",
    ".docx",
    ".eot",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".map",
    ".mjs",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".rar",
    ".svg",
    ".ttf",
    ".webp",
    ".woff",
    ".woff2",
    ".xls",
    ".xlsx",
    ".zip",
}
_RESOURCE_SEGMENTS = {
    "assets",
    "css",
    "font",
    "fonts",
    "img",
    "image",
    "images",
    "js",
    "static",
    "template",
    "templates",
}


def _normalize_route_path(path: str) -> str:
    path = path.strip()

    if not path.startswith("/"):
        path = "/" + path

    while "//" in path:
        path = path.replace("//", "/")

    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def _is_page_route_path(path: str) -> bool:
    route_path = urlsplit(path).path

    suffix = Path(route_path.lower()).suffix
    if suffix in _NON_PAGE_EXTENSIONS:
        return False

    segments = {seg.lower() for seg in route_path.split("/") if seg}
    return not bool(segments & _RESOURCE_SEGMENTS)


@dataclass(slots=True)
class FactStore:
    js_facts: dict[str, JSFact] = field(default_factory=dict)
    html_facts: dict[str, HTMLFact] = field(default_factory=dict)
    route_facts: dict[str, RouteFact] = field(default_factory=dict)
    mfe_entry_urls: set[str] = field(default_factory=set)
    fetched_mfe_entries: set[str] = field(default_factory=set)
    processed_js_sources: set[str] = field(default_factory=set)
    processed_html_sources: set[str] = field(default_factory=set)
    js_sources: dict[str, SourceRef] = field(default_factory=dict)

    def add_js(self, url: str, *, source: str, evidence_url: str = "") -> bool:
        if not url:
            return False

        clean = clean_url(url)
        if not clean or clean in self.js_facts:
            return False
        self.js_facts[clean] = JSFact(clean, source=source, evidence_url=evidence_url)
        return True

    def add_js_source(self, url: str, ref: SourceRef) -> bool:
        self.js_sources[url] = ref

        return self.add_js(url, source="downloaded")

    def add_html(self, url: str, ref: SourceRef, *, source: str) -> bool:
        if not url or not ref:
            return False

        clean = clean_url(url)
        if not clean or clean in self.html_facts:
            return False
        self.html_facts[clean] = HTMLFact(clean, ref=ref, source=source)
        return True

    def add_route(
        self,
        path: str | RouteFact,
        *,
        source: str = "",
        evidence_url: str = "",
    ) -> bool:
        fact = (
            path
            if isinstance(path, RouteFact)
            else RouteFact(
                path=_normalize_route_path(path),
                source=source,
                evidence_url=evidence_url,
            )
        )

        if not fact.path or not _is_page_route_path(fact.path):
            return False

        if fact.path in self.route_facts:
            return False
        self.route_facts[fact.path] = fact
        return True

    def add_mfe_entry(self, url: str) -> bool:
        clean = clean_url(url)
        if not clean or clean in self.mfe_entry_urls:
            return False
        self.mfe_entry_urls.add(clean)
        return True

    def fingerprint(self) -> tuple[int, int, int, int, int]:
        return (
            len(self.js_facts),
            len(self.html_facts),
            len(self.route_facts),
            len(self.mfe_entry_urls),
            len(self.fetched_mfe_entries),
        )

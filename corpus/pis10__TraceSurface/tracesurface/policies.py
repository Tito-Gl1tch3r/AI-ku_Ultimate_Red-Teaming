from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

SAFE_METHODS = frozenset({"GET", "POST", "UNKNOWN"})
BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


@dataclass(frozen=True, slots=True)
class ReplaySafetyPolicy:
    allow_destructive: bool = False

    def can_send(self, method: str) -> bool:
        method = (method or "UNKNOWN").upper()

        return self.allow_destructive or method in SAFE_METHODS


DEFAULT_RESPONSE_BODY_CAPTURE_LIMIT = 1024 * 1024

BINARY_CONTENT_TYPE_PREFIXES = (
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/x-gzip",
    "image/",
    "audio/",
    "video/",
    "font/",
)


@dataclass(frozen=True, slots=True)
class ResponseCapturePolicy:
    body_capture_limit: int = DEFAULT_RESPONSE_BODY_CAPTURE_LIMIT

    def is_text_mime(self, mime: str) -> bool:
        mime = (mime or "").lower()

        return (
            mime.startswith("text/")
            or "json" in mime
            or "xml" in mime
            or "x-www-form-urlencoded" in mime
            or "javascript" in mime
        )

    def normalize_content_type(self, content_type: str) -> str:
        ct = (content_type or "").lower().split(";", 1)[0].strip()

        if not ct:
            return "text"

        if any(ct.startswith(prefix) for prefix in BINARY_CONTENT_TYPE_PREFIXES):
            return "bin"

        if "json" in ct:
            return "json"
        if "html" in ct:
            return "html"
        if "xml" in ct:
            return "xml"
        return "text"


DEFAULT_STATIC_RESOURCE_EXTS = frozenset(
    {
        ".js",
        ".css",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".map",
        ".mp3",
        ".mp4",
        ".pdf",
        ".zip",
        ".gz",
    }
)


@dataclass(frozen=True, slots=True)
class StaticResourcePolicy:
    extensions: frozenset[str] = DEFAULT_STATIC_RESOURCE_EXTS

    def is_static_resource_path(self, path: str) -> bool:
        filename = (path or "").rsplit("/", 1)[-1]
        ext = PurePosixPath(filename).suffix.lower() if "." in filename else ""
        return ext in self.extensions

    def is_static_resource_url(self, url: str) -> bool:
        return self.is_static_resource_path(urlparse(url).path)


MULTI_LABEL_SUFFIXES = (
    "com.cn",
    "net.cn",
    "org.cn",
    "gov.cn",
    "edu.cn",
    "com.hk",
    "com.tw",
    "com.sg",
    "co.jp",
    "co.uk",
    "co.kr",
)

DEFAULT_THIRD_PARTY_DOMAINS = (
    "baidu.com",
    "google-analytics.com",
    "googletagmanager.com",
    "umeng.com",
    "cnzz.com",
    "51.la",
    "sensorsdata.cn",
    "pv.sohu.com",
    "mmstat.com",
    "miaozhen.com",
    "googlesyndication.com",
    "doubleclick.net",
    "sentry.io",
    "fundebug.com",
    "frontjs.com",
    "meiqia.com",
    "crisp.chat",
    "intercom.io",
    "sobot.com",
    "clink.cn",
    "bcebos.com",
    "aliyuncs.com",
    "myqcloud.com",
    "bootcdn.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "jsdelivr.net",
    "alicdn.com",
    "youtube.com",
    "youtu.be",
    "apple.com",
    "tiny.cloud",
    "amap.com",
    "map.qq.com",
    "hotjar.com",
    "clarity.ms",
    "facebook.net",
    "recaptcha.net",
    "gstatic.com",
)


def root_domain(host: str | None) -> str:
    host = (host or "").lower().strip(".")
    if not host:
        return ""
    parts = host.split(".")

    if len(parts) <= 2:
        return host
    tail2 = ".".join(parts[-2:])

    if tail2 in MULTI_LABEL_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return tail2


def same_site(host: str, target_host: str) -> bool:
    if not host or not target_host:
        return False
    return root_domain(host) == root_domain(target_host)


@dataclass(frozen=True, slots=True)
class TargetContext:
    requested_url: str
    effective_url: str | None = None

    @property
    def policy_url(self) -> str:
        return self.effective_url or self.requested_url


@dataclass(frozen=True, slots=True)
class ThirdPartyPolicy:
    domains: tuple[str, ...] = DEFAULT_THIRD_PARTY_DOMAINS

    def is_third_party(
        self,
        url: str,
        target: TargetContext | str | None = None,
    ) -> bool:
        host = (urlparse(url).hostname or "").strip(".")

        if not host:
            return False

        target_url = (
            target.policy_url if isinstance(target, TargetContext) else (target or "")
        )

        if target_url:
            target_host = urlparse(target_url).hostname or ""
            if same_site(host, target_host):
                return False

        return any(host == d or host.endswith("." + d) for d in self.domains)

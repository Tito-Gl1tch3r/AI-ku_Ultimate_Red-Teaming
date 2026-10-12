import asyncio
from typing import List, Tuple

import pytest

from bladerecon.modules.subdomains import _extract_hosts
from bladerecon.modules import subdomains
from bladerecon.modules.utils import deduplicate_subdomains


def test_subdomain_deduplication_normalizes_hosts() -> None:
    values = ["API.EXAMPLE.COM.", "api.example.com", "*.wild.example.com", "bad/path"]

    assert deduplicate_subdomains(values) == ["api.example.com"]


def test_extract_hosts_from_html_and_csv_sources() -> None:
    text = "1.1.1.1,api.example.com <td>admin.example.com</td> evil-example.com"

    assert _extract_hosts(text, "example.com") == ["api.example.com", "admin.example.com"]


def test_wordlist_expansion_resolves_missing_hosts_with_source_tag(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_detect(domain: str, timeout: float = 3.0, retries: int = 1) -> List[Tuple[str, ...]]:
        return []

    async def fake_fingerprint(host: str, timeout: float = 3.0, retries: int = 1) -> Tuple[str, ...]:
        return ("ip:192.0.2.10",) if host in {"dev.example.com", "api.example.com"} else ()

    monkeypatch.setattr(subdomains, "_detect_wildcard_dns", fake_detect)
    monkeypatch.setattr(subdomains, "_resolve_fingerprint", fake_fingerprint)

    rows, wildcard_detected, filtered, _ = asyncio.run(
        subdomains._dns_wordlist_expand(
            "example.com",
            ["api", "dev", "dev", "missing"],
            ["api.example.com"],
            concurrency=2,
            timeout=1,
            retries=0,
        )
    )

    assert rows == [{"subdomain": "dev.example.com", "source": "wordlist"}]
    assert wildcard_detected is False
    assert filtered == 0


def test_wordlist_expansion_filters_wildcard_fingerprints(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_detect(domain: str, timeout: float = 3.0, retries: int = 1) -> List[Tuple[str, ...]]:
        return [("ip:192.0.2.123",)]

    async def fake_fingerprint(host: str, timeout: float = 3.0, retries: int = 1) -> Tuple[str, ...]:
        if host == "api.example.com":
            return ("ip:198.51.100.20",)
        return ("ip:192.0.2.123",)

    monkeypatch.setattr(subdomains, "_detect_wildcard_dns", fake_detect)
    monkeypatch.setattr(subdomains, "_resolve_fingerprint", fake_fingerprint)

    rows, wildcard_detected, filtered, fingerprints = asyncio.run(
        subdomains._dns_wordlist_expand(
            "example.com",
            ["api", "grafana", "admin"],
            [],
            concurrency=2,
            timeout=1,
            retries=0,
        )
    )

    assert rows == [{"subdomain": "api.example.com", "source": "wordlist"}]
    assert wildcard_detected is True
    assert filtered == 2
    assert fingerprints == ["192.0.2.123"]

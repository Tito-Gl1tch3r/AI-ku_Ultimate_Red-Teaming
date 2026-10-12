from __future__ import annotations

from typing import Any

from ai_recon.collectors.shodan import ShodanCollector
from ai_recon.models import EvidenceMode, EvidenceStatus, Target


def test_collect_returns_unavailable_when_api_key_is_missing() -> None:
    collector = ShodanCollector(api_key=None)

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.source == "shodan"
    assert evidence.target == "example.com"
    assert evidence.mode is EvidenceMode.LIVE
    assert evidence.status is EvidenceStatus.UNAVAILABLE
    assert evidence.observations == {}
    assert evidence.error == "AI_RECON_SHODAN_API_KEY is not configured."


def test_collect_returns_normalized_live_evidence() -> None:
    def search(identifier: str) -> dict[str, Any]:
        assert identifier == "example.com"

        return {
            "matches": [
                {
                    "port": 443,
                    "hostnames": [
                        "www.example.com",
                        "example.com",
                    ],
                    "org": "Example ISP",
                    "location": {
                        "country_code": "NG",
                    },
                    "vulns": {
                        "CVE-2024-0001": {},
                        "CVE-2023-0002": {},
                    },
                    "data": "Example service banner",
                },
                {
                    "port": 80,
                    "hostnames": [
                        "api.example.com",
                    ],
                    "org": "Another ISP",
                    "location": {
                        "country_code": "US",
                    },
                    "vulns": {
                        "CVE-2024-0001": {},
                    },
                    "data": "Another service banner",
                },
            ]
        }

    collector = ShodanCollector(
        api_key=None,
        search=search,
    )

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.source == "shodan"
    assert evidence.target == "example.com"
    assert evidence.mode is EvidenceMode.LIVE
    assert evidence.status is EvidenceStatus.SUCCESS

    assert evidence.observations["ports"] == [80, 443]

    assert evidence.observations["hostnames"] == [
        "api.example.com",
        "example.com",
        "www.example.com",
    ]

    assert evidence.observations["org"] == "Example ISP"
    assert evidence.observations["country"] == "NG"

    assert evidence.observations["vulnerabilities"] == [
        "CVE-2023-0002",
        "CVE-2024-0001",
    ]

    assert evidence.observations["data"] == [
        {
            "banner": "Example service banner",
        },
        {
            "banner": "Another service banner",
        },
    ]


def test_collect_returns_error_evidence_when_search_fails() -> None:
    def failing_search(_: str) -> dict[str, Any]:
        raise RuntimeError("Shodan service unavailable")

    collector = ShodanCollector(
        api_key="test-key",
        search=failing_search,
    )

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.source == "shodan"
    assert evidence.status is EvidenceStatus.ERROR
    assert evidence.observations == {}
    assert evidence.error == "Shodan service unavailable"


def test_collect_ignores_invalid_matches() -> None:
    def search(_: str) -> dict[str, Any]:
        return {
            "matches": [
                "invalid",
                123,
                None,
                {
                    "port": 443,
                    "hostnames": "not-a-list",
                    "org": "Example ISP",
                    "location": "not-a-dict",
                    "vulns": [],
                    "data": "",
                },
            ]
        }

    collector = ShodanCollector(
        api_key=None,
        search=search,
    )

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.status is EvidenceStatus.SUCCESS
    assert evidence.observations["ports"] == [443]
    assert evidence.observations["hostnames"] == ["example.com"]
    assert evidence.observations["org"] == "Example ISP"
    assert evidence.observations["country"] is None
    assert evidence.observations["vulnerabilities"] == []
    assert evidence.observations["data"] == []

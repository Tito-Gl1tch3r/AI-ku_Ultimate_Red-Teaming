from __future__ import annotations

from ai_recon.analyzers import WhoisAnalyzer
from ai_recon.models import (
    Evidence,
    EvidenceMode,
    EvidenceStatus,
    Severity,
)


def test_analyze_returns_single_provider_dns_finding() -> None:
    evidence = Evidence(
        source="whois",
        target="example.com",
        observations={
            "name_servers": [
                "ns1.example.com",
                "ns2.example.com",
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = WhoisAnalyzer().analyze(evidence)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.id == "WHOIS_SINGLE_PROVIDER_DNS"
    assert finding.severity is Severity.LOW


def test_analyze_returns_no_findings_for_other_source() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "name_servers": [
                "ns1.example.com",
                "ns2.example.com",
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = WhoisAnalyzer().analyze(evidence)

    assert findings == []


def test_analyze_returns_no_findings_for_insufficient_name_servers() -> None:
    evidence = Evidence(
        source="whois",
        target="example.com",
        observations={
            "name_servers": [
                "ns1.example.com",
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = WhoisAnalyzer().analyze(evidence)

    assert findings == []

from __future__ import annotations

from ai_recon.analyzers import ShodanAnalyzer
from ai_recon.models import (
    Evidence,
    EvidenceMode,
    EvidenceStatus,
    Severity,
)


def test_analyze_returns_remote_access_finding() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "ports": [80, 443, 3389],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.id == "SHODAN_EXPOSED_REMOTE_ACCESS"
    assert finding.severity is Severity.HIGH
    assert finding.evidence_references == ["3389"]


def test_analyze_returns_known_vulnerability_finding() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "vulnerabilities": [
                "CVE-2024-0001",
                "CVE-2024-0002",
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.id == "SHODAN_KNOWN_VULNERABILITIES"
    assert finding.severity is Severity.HIGH
    assert finding.evidence_references == [
        "CVE-2024-0001",
        "CVE-2024-0002",
    ]


def test_analyze_returns_many_ports_finding() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "ports": [21, 25, 53, 80, 443, 8080],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.id == "SHODAN_MANY_OPEN_PORTS"
    assert finding.severity is Severity.MEDIUM


def test_analyze_returns_legacy_banner_finding() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "data": [
                {
                    "banner": ("HTTP/1.1 200 OK\nServer: Apache/2.2.34"),
                },
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.id == "SHODAN_LEGACY_SERVICE_BANNER"
    assert finding.severity is Severity.MEDIUM


def test_analyze_returns_no_findings_for_other_source() -> None:
    evidence = Evidence(
        source="whois",
        target="example.com",
        observations={
            "ports": [3389],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    assert findings == []


def test_analyze_can_return_multiple_findings() -> None:
    evidence = Evidence(
        source="shodan",
        target="example.com",
        observations={
            "ports": [21, 22, 23, 80, 443, 3389, 8080],
            "vulnerabilities": [
                "CVE-2024-0001",
            ],
            "data": [
                {
                    "banner": "Server: Apache/2.2.34",
                },
            ],
        },
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
    )

    findings = ShodanAnalyzer().analyze(evidence)

    finding_ids = {finding.id for finding in findings}

    assert finding_ids == {
        "SHODAN_EXPOSED_REMOTE_ACCESS",
        "SHODAN_MANY_OPEN_PORTS",
        "SHODAN_KNOWN_VULNERABILITIES",
        "SHODAN_LEGACY_SERVICE_BANNER",
    }

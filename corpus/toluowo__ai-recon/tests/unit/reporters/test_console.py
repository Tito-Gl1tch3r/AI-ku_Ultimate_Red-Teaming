from __future__ import annotations

from datetime import datetime, timezone

from ai_recon.models import (
    Assessment,
    Confidence,
    Evidence,
    EvidenceMode,
    EvidenceStatus,
    Finding,
    Severity,
    Target,
)
from ai_recon.reporters import ConsoleReporter


def make_assessment() -> Assessment:
    return Assessment(
        target=Target(identifier="example.com"),
        created_at=datetime(
            2026,
            9,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_render_includes_assessment_header() -> None:
    assessment = make_assessment()

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "AI-RECON SECURITY ASSESSMENT" in result
    assert "Target: example.com" in result
    assert "Type: domain" in result


def test_render_includes_empty_messages() -> None:
    assessment = make_assessment()

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "No evidence collected." in result

    assert "No security findings identified." in result


def test_render_includes_evidence() -> None:
    assessment = make_assessment()

    assessment.add_evidence(
        Evidence(
            source="whois",
            target="example.com",
            observations={},
            mode=EvidenceMode.LIVE,
        )
    )

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "[SUCCESS] WHOIS (live)" in result


def test_render_includes_evidence_error() -> None:
    assessment = make_assessment()

    assessment.add_evidence(
        Evidence(
            source="shodan",
            target="example.com",
            observations={},
            mode=EvidenceMode.LIVE,
            status=EvidenceStatus.ERROR,
            error="Request failed.",
        )
    )

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "[ERROR] SHODAN (live)" in result
    assert "Error: Request failed." in result


def test_render_orders_findings_by_severity() -> None:
    assessment = make_assessment()

    assessment.add_finding(
        Finding(
            id="LOW-001",
            title="Low finding",
            severity=Severity.LOW,
            confidence=Confidence.HIGH,
            description="Low severity finding.",
            source="test",
        )
    )

    assessment.add_finding(
        Finding(
            id="CRITICAL-001",
            title="Critical finding",
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            description="Critical severity finding.",
            source="test",
        )
    )

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    critical_position = result.index("[CRITICAL] CRITICAL-001")

    low_position = result.index("[LOW] LOW-001")

    assert critical_position < low_position


def test_render_includes_finding_details() -> None:
    assessment = make_assessment()

    assessment.add_finding(
        Finding(
            id="TEST-001",
            title="Test finding",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            description="A test security finding.",
            source="shodan",
            evidence_references=[
                "port:3389",
            ],
            remediation="Restrict external access.",
        )
    )

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "[HIGH] TEST-001" in result
    assert "Test finding" in result
    assert "Source: shodan" in result
    assert "Confidence: HIGH" in result
    assert "A test security finding." in result
    assert "Evidence References:" in result
    assert "- port:3389" in result
    assert "Remediation:" in result
    assert "Restrict external access." in result


def test_render_includes_analysis() -> None:
    assessment = make_assessment()

    assessment.analysis = "External exposure requires further review."

    reporter = ConsoleReporter()

    result = reporter.render(assessment)

    assert "ANALYSIS" in result

    assert "External exposure requires further review." in result

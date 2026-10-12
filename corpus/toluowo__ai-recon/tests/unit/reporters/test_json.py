from __future__ import annotations

import json
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
from ai_recon.reporters import JsonReporter


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


def test_render_returns_valid_json() -> None:
    assessment = make_assessment()

    reporter = JsonReporter()

    result = reporter.render(assessment)

    payload = json.loads(result)

    assert payload["target"]["identifier"] == "example.com"
    assert payload["target"]["type"] == "domain"


def test_render_includes_evidence() -> None:
    assessment = make_assessment()

    assessment.add_evidence(
        Evidence(
            source="whois",
            target="example.com",
            observations={
                "registrar": "Example Registrar",
            },
            mode=EvidenceMode.LIVE,
            status=EvidenceStatus.SUCCESS,
            collected_at=datetime(
                2026,
                9,
                1,
                12,
                5,
                tzinfo=timezone.utc,
            ),
        )
    )

    reporter = JsonReporter()

    payload = json.loads(reporter.render(assessment))

    assert len(payload["evidence"]) == 1

    evidence = payload["evidence"][0]

    assert evidence["source"] == "whois"
    assert evidence["status"] == "success"
    assert evidence["mode"] == "live"


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
            id="HIGH-001",
            title="High finding",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            description="High severity finding.",
            source="test",
        )
    )

    reporter = JsonReporter()

    payload = json.loads(reporter.render(assessment))

    assert [finding["id"] for finding in payload["findings"]] == [
        "HIGH-001",
        "LOW-001",
    ]


def test_render_includes_collection_errors() -> None:
    assessment = make_assessment()

    assessment.add_evidence(
        Evidence(
            source="shodan",
            target="example.com",
            observations={},
            mode=EvidenceMode.LIVE,
            status=EvidenceStatus.ERROR,
            error="API request failed.",
        )
    )

    reporter = JsonReporter()

    payload = json.loads(reporter.render(assessment))

    assert payload["has_collection_errors"] is True

    assert payload["evidence"][0]["error"] == ("API request failed.")


def test_render_includes_analysis() -> None:
    assessment = make_assessment()

    assessment.analysis = "The target has externally exposed services."

    reporter = JsonReporter()

    payload = json.loads(reporter.render(assessment))

    assert payload["analysis"] == ("The target has externally exposed services.")

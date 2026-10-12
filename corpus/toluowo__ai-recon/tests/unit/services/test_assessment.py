from __future__ import annotations

from ai_recon.analyzers import EvidenceAnalyzer
from ai_recon.collectors import EvidenceCollector
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
from ai_recon.services.assessment import AssessmentService


def make_finding(identifier: str = "TEST-001") -> Finding:
    return Finding(
        id=identifier,
        title="Test finding",
        severity=Severity.LOW,
        confidence=Confidence.HIGH,
        description="A finding created for testing.",
        source="test",
    )


class FakeCollector(EvidenceCollector):
    """Test collector that records the targets it receives."""

    source = "fake"

    def __init__(
        self,
        source: str,
        status: EvidenceStatus = EvidenceStatus.SUCCESS,
    ) -> None:
        self.source = source
        self.status = status
        self.received_targets: list[Target] = []

    def collect(self, target: Target) -> Evidence:
        self.received_targets.append(target)

        return Evidence(
            source=self.source,
            target=target.identifier,
            observations={
                "collector": self.source,
            },
            mode=EvidenceMode.LIVE,
            status=self.status,
            error=("Collection failed." if self.status == EvidenceStatus.ERROR else None),
        )


class FakeAnalyzer(EvidenceAnalyzer):
    source = "whois"

    def __init__(
        self,
        findings: list[Finding],
    ) -> None:
        self.findings = findings
        self.calls: list[Evidence] = []

    def analyze(
        self,
        evidence: Evidence,
    ) -> list[Finding]:
        self.calls.append(evidence)
        return self.findings


class NonMatchingAnalyzer(EvidenceAnalyzer):
    source = "shodan"

    def __init__(self) -> None:
        self.calls: list[Evidence] = []

    def analyze(
        self,
        evidence: Evidence,
    ) -> list[Finding]:
        self.calls.append(evidence)
        return []


def make_whois_evidence() -> Evidence:
    return Evidence(
        source="whois",
        target="example.com",
        mode=EvidenceMode.LIVE,
        status=EvidenceStatus.SUCCESS,
        observations={
            "domain_name": [
                "example.com",
            ],
        },
    )


def test_create_assessment_returns_assessment_for_target() -> None:
    target = Target(identifier="example.com")

    service = AssessmentService()

    assessment = service.create_assessment(target)

    assert isinstance(assessment, Assessment)
    assert assessment.target == target
    assert assessment.evidence == []
    assert assessment.findings == []


def test_collect_evidence_executes_all_collectors() -> None:
    target = Target(identifier="example.com")

    whois_collector = FakeCollector("whois")
    shodan_collector = FakeCollector("shodan")

    service = AssessmentService(
        collectors=[
            whois_collector,
            shodan_collector,
        ]
    )

    assessment = service.create_assessment(target)

    result = service.collect_evidence(assessment)

    assert result is assessment

    assert whois_collector.received_targets == [target]
    assert shodan_collector.received_targets == [target]

    assert len(assessment.evidence) == 2

    assert assessment.evidence[0].source == "whois"
    assert assessment.evidence[1].source == "shodan"


def test_collect_evidence_allows_empty_collector_configuration() -> None:
    target = Target(identifier="example.com")

    service = AssessmentService()

    assessment = service.create_assessment(target)

    result = service.collect_evidence(assessment)

    assert result is assessment
    assert assessment.evidence == []


def test_collect_evidence_preserves_error_evidence() -> None:
    target = Target(identifier="example.com")

    failing_collector = FakeCollector(
        "failing",
        status=EvidenceStatus.ERROR,
    )

    service = AssessmentService(
        collectors=[
            failing_collector,
        ]
    )

    assessment = service.create_assessment(target)

    service.collect_evidence(assessment)

    assert len(assessment.evidence) == 1

    evidence = assessment.evidence[0]

    assert evidence.status is EvidenceStatus.ERROR
    assert evidence.error == "Collection failed."
    assert assessment.has_collection_errors


def test_analyze_evidence_executes_matching_analyzer() -> None:
    finding = make_finding()

    analyzer = FakeAnalyzer([finding])

    service = AssessmentService(
        analyzers=[
            analyzer,
        ]
    )

    assessment = Assessment(
        target=Target(identifier="example.com"),
        evidence=[
            make_whois_evidence(),
        ],
    )

    result = service.analyze_evidence(assessment)

    assert result is assessment

    assert analyzer.calls == [
        assessment.evidence[0],
    ]

    assert assessment.findings == [
        finding,
    ]


def test_analyze_evidence_ignores_non_matching_analyzer() -> None:
    analyzer = NonMatchingAnalyzer()

    service = AssessmentService(
        analyzers=[
            analyzer,
        ]
    )

    assessment = Assessment(
        target=Target(identifier="example.com"),
        evidence=[
            make_whois_evidence(),
        ],
    )

    result = service.analyze_evidence(assessment)

    assert result is assessment
    assert analyzer.calls == []
    assert assessment.findings == []


def test_analyze_evidence_adds_all_findings() -> None:
    first_finding = make_finding("TEST-001")

    second_finding = make_finding("TEST-002")

    analyzer = FakeAnalyzer(
        [
            first_finding,
            second_finding,
        ]
    )

    service = AssessmentService(
        analyzers=[
            analyzer,
        ]
    )

    assessment = Assessment(
        target=Target(identifier="example.com"),
        evidence=[
            make_whois_evidence(),
        ],
    )

    service.analyze_evidence(assessment)

    assert assessment.findings == [
        first_finding,
        second_finding,
    ]


def test_analyze_evidence_allows_empty_analyzer_configuration() -> None:
    service = AssessmentService()

    assessment = Assessment(
        target=Target(identifier="example.com"),
        evidence=[
            make_whois_evidence(),
        ],
    )

    result = service.analyze_evidence(assessment)

    assert result is assessment
    assert assessment.findings == []


def test_run_executes_collection_and_analysis_workflow() -> None:
    finding = make_finding()

    collector = FakeCollector("whois")

    analyzer = FakeAnalyzer([finding])

    service = AssessmentService(
        collectors=[
            collector,
        ],
        analyzers=[
            analyzer,
        ],
    )

    target = Target(identifier="example.com")

    assessment = service.run(target)

    assert assessment.target == target

    assert len(assessment.evidence) == 1

    assert assessment.evidence[0].source == "whois"

    assert analyzer.calls == [
        assessment.evidence[0],
    ]

    assert assessment.findings == [
        finding,
    ]

from __future__ import annotations

from collections.abc import Sequence

from ai_recon.analyzers import EvidenceAnalyzer
from ai_recon.collectors import EvidenceCollector
from ai_recon.models import Assessment, Target


class AssessmentService:
    """Coordinates an authorized reconnaissance assessment workflow."""

    def __init__(
        self,
        collectors: Sequence[EvidenceCollector] = (),
        analyzers: Sequence[EvidenceAnalyzer] = (),
    ) -> None:
        self._collectors = collectors
        self._analyzers = analyzers

    def create_assessment(self, target: Target) -> Assessment:
        """Create an assessment for a target."""

        return Assessment(target=target)

    def collect_evidence(
        self,
        assessment: Assessment,
    ) -> Assessment:
        """Collect evidence from all configured collectors."""

        for collector in self._collectors:
            evidence = collector.collect(assessment.target)
            assessment.add_evidence(evidence)

        return assessment

    def analyze_evidence(
        self,
        assessment: Assessment,
    ) -> Assessment:
        """Analyze collected evidence and add findings to the assessment."""

        for evidence in assessment.evidence:
            for analyzer in self._analyzers:
                if analyzer.source != evidence.source:
                    continue

                findings = analyzer.analyze(evidence)

                for finding in findings:
                    assessment.add_finding(finding)

        return assessment

    def run(
        self,
        target: Target,
    ) -> Assessment:
        """Run the complete collection and analysis workflow."""

        assessment = self.create_assessment(target)

        self.collect_evidence(assessment)
        self.analyze_evidence(assessment)

        return assessment

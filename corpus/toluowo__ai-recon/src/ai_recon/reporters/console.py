from __future__ import annotations

from ai_recon.models import Assessment, Finding, Severity

from .base import AssessmentReporter


class ConsoleReporter(AssessmentReporter):
    """Render assessments as human-readable console reports."""

    _SEVERITY_ORDER = {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
        Severity.INFO: 4,
    }

    def render(self, assessment: Assessment) -> str:
        """Render an assessment into a human-readable report."""

        lines: list[str] = []

        lines.extend(
            [
                "AI-RECON SECURITY ASSESSMENT",
                "=" * 27,
                "",
                f"Target: {assessment.target.identifier}",
                f"Type: {assessment.target.target_type.value}",
                f"Created: {assessment.created_at.isoformat()}",
                "",
            ]
        )

        lines.extend(
            [
                "EVIDENCE",
                "-" * 8,
            ]
        )

        if assessment.evidence:
            for evidence in assessment.evidence:
                lines.append(
                    f"[{evidence.status.value.upper()}] "
                    f"{evidence.source.upper()} "
                    f"({evidence.mode.value})"
                )

                if evidence.error:
                    lines.append(f"  Error: {evidence.error}")
        else:
            lines.append("No evidence collected.")

        lines.append("")

        lines.extend(
            [
                "FINDINGS",
                "-" * 8,
            ]
        )

        findings = self._sorted_findings(assessment.findings)

        if findings:
            for finding in findings:
                lines.extend(self._render_finding(finding))
        else:
            lines.append("No security findings identified.")

        if assessment.analysis:
            lines.extend(
                [
                    "",
                    "ANALYSIS",
                    "-" * 8,
                    assessment.analysis,
                ]
            )

        return "\n".join(lines)

    def _render_finding(
        self,
        finding: Finding,
    ) -> list[str]:
        """Render a single finding."""

        lines = [
            "",
            (f"[{finding.severity.value.upper()}] {finding.id}"),
            finding.title,
            f"Source: {finding.source}",
            f"Confidence: {finding.confidence.value.upper()}",
            "",
            finding.description,
        ]

        if finding.evidence_references:
            lines.extend(
                [
                    "",
                    "Evidence References:",
                ]
            )

            lines.extend(f"- {reference}" for reference in finding.evidence_references)

        if finding.remediation:
            lines.extend(
                [
                    "",
                    "Remediation:",
                    finding.remediation,
                ]
            )

        return lines

    def _sorted_findings(
        self,
        findings: list[Finding],
    ) -> list[Finding]:
        """Return findings ordered by severity and identifier."""

        return sorted(
            findings,
            key=lambda finding: (
                self._SEVERITY_ORDER[finding.severity],
                finding.id,
            ),
        )

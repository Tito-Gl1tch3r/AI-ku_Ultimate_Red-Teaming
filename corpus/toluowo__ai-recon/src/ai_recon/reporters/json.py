from __future__ import annotations

import json
from typing import Any

from ai_recon.models import Assessment

from .base import AssessmentReporter


class JsonReporter(AssessmentReporter):
    """Render assessments as deterministic JSON."""

    def render(self, assessment: Assessment) -> str:
        """Render an assessment into JSON."""

        payload = self.to_dict(assessment)

        return json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            default=str,
        )

    def to_dict(
        self,
        assessment: Assessment,
    ) -> dict[str, Any]:
        """Convert an assessment into a JSON-serializable dictionary."""

        return {
            "target": {
                "identifier": assessment.target.identifier,
                "type": assessment.target.target_type.value,
            },
            "created_at": assessment.created_at.isoformat(),
            "analysis": assessment.analysis,
            "has_collection_errors": assessment.has_collection_errors,
            "evidence": [
                {
                    "source": evidence.source,
                    "target": evidence.target,
                    "observations": evidence.observations,
                    "mode": evidence.mode.value,
                    "status": evidence.status.value,
                    "collected_at": evidence.collected_at.isoformat(),
                    "error": evidence.error,
                }
                for evidence in assessment.evidence
            ],
            "findings": [
                {
                    "id": finding.id,
                    "title": finding.title,
                    "severity": finding.severity.value,
                    "confidence": finding.confidence.value,
                    "description": finding.description,
                    "source": finding.source,
                    "evidence_references": finding.evidence_references,
                    "remediation": finding.remediation,
                }
                for finding in self._sorted_findings(assessment)
            ],
        }

    @staticmethod
    def _sorted_findings(assessment: Assessment) -> list[Any]:
        """Return findings ordered by severity and identifier."""

        severity_order = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }

        return sorted(
            assessment.findings,
            key=lambda finding: (
                severity_order[finding.severity.value],
                finding.id,
            ),
        )

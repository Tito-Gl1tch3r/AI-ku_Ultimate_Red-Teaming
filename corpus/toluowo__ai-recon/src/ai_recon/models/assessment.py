from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from .evidence import Evidence, EvidenceStatus
from .finding import Finding
from .target import Target


@dataclass(slots=True)
class Assessment:
    target: Target
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    analysis: str | None = None

    def add_evidence(self, item: Evidence) -> None:
        self.evidence.append(item)

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def has_collection_errors(self) -> bool:
        return any(item.status == EvidenceStatus.ERROR for item in self.evidence)

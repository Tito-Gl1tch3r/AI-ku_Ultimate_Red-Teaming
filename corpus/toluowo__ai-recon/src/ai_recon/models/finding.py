from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    title: str
    severity: Severity
    confidence: Confidence
    description: str
    source: str
    evidence_references: list[str] = field(default_factory=list)
    remediation: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Finding ID must not be empty.")

        if not self.title.strip():
            raise ValueError("Finding title must not be empty.")

        if not self.description.strip():
            raise ValueError("Finding description must not be empty.")

        if not self.source.strip():
            raise ValueError("Finding source must not be empty.")

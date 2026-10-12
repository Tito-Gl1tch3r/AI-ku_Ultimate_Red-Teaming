from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EvidenceMode(str, Enum):
    LIVE = "live"
    MOCK = "mock"
    CACHED = "cached"


class EvidenceStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    target: str
    observations: dict[str, Any]
    mode: EvidenceMode
    status: EvidenceStatus = EvidenceStatus.SUCCESS
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("Evidence source must not be empty.")

        if not self.target.strip():
            raise ValueError("Evidence target must not be empty.")

        if self.status == EvidenceStatus.ERROR and not self.error:
            raise ValueError("Error evidence must include an error description.")

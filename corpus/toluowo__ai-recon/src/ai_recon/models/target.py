from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TargetType(str, Enum):
    DOMAIN = "domain"
    HOSTNAME = "hostname"
    IP_ADDRESS = "ip_address"
    ORGANIZATION = "organization"


@dataclass(frozen=True, slots=True)
class Target:
    identifier: str
    target_type: TargetType = TargetType.DOMAIN
    scope: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        identifier = self.identifier.strip()

        if not identifier:
            raise ValueError("Target identifier must not be empty.")

        object.__setattr__(self, "identifier", identifier)

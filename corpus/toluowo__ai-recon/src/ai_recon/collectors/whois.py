from __future__ import annotations

from collections.abc import Callable
from typing import Any

import whois  # type: ignore[import-untyped]

from ai_recon.collectors.base import EvidenceCollector
from ai_recon.models import Evidence, EvidenceMode, EvidenceStatus, Target

WhoisLookup = Callable[[str], Any]


class WhoisCollector(EvidenceCollector):
    """Collect normalized WHOIS evidence for domain targets."""

    source = "whois"

    def __init__(
        self,
        lookup: WhoisLookup | None = None,
    ) -> None:
        self._lookup = lookup or whois.whois

    def collect(self, target: Target) -> Evidence:
        """Collect WHOIS evidence for the supplied target."""

        try:
            result = self._lookup(target.identifier)
        except Exception as exc:
            return Evidence(
                source=self.source,
                target=target.identifier,
                observations={},
                mode=EvidenceMode.LIVE,
                status=EvidenceStatus.ERROR,
                error=str(exc),
            )

        observations = {
            "domain_name": self._normalize(getattr(result, "domain_name", None))
            or target.identifier,
            "registrar": self._normalize(getattr(result, "registrar", None)),
            "creation_date": self._normalize(getattr(result, "creation_date", None)),
            "expiration_date": self._normalize(getattr(result, "expiration_date", None)),
            "name_servers": self._normalize_collection(getattr(result, "name_servers", None)),
            "emails": self._normalize(getattr(result, "emails", None)),
            "org": self._normalize(getattr(result, "org", None)),
            "country": self._normalize(getattr(result, "country", None)),
        }

        return Evidence(
            source=self.source,
            target=target.identifier,
            observations=observations,
            mode=EvidenceMode.LIVE,
        )

    @staticmethod
    def _normalize(value: Any) -> str | list[str] | None:
        """Normalize common python-whois values."""

        if value is None:
            return None

        if isinstance(value, (list, set, tuple)):
            return [str(item) for item in value]

        return str(value)

    @staticmethod
    def _normalize_collection(value: Any) -> list[str]:
        """Normalize a collection-like value into a deterministic string list."""

        if value is None:
            return []

        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]

        if isinstance(value, set):
            return sorted(str(item) for item in value)

        return [str(value)]

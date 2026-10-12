from __future__ import annotations

from ai_recon.analyzers.base import EvidenceAnalyzer
from ai_recon.models import Confidence, Evidence, Finding, Severity


class WhoisAnalyzer(EvidenceAnalyzer):
    """Analyze WHOIS evidence for configuration-related indicators."""

    source = "whois"

    def analyze(self, evidence: Evidence) -> list[Finding]:
        """Analyze WHOIS evidence and return findings."""

        if evidence.source != self.source:
            return []

        name_servers = self._as_string_list(evidence.observations.get("name_servers"))

        if not self._has_single_provider_dns(name_servers):
            return []

        return [
            Finding(
                id="WHOIS_SINGLE_PROVIDER_DNS",
                title="Potential single-provider DNS footprint",
                severity=Severity.LOW,
                confidence=Confidence.LOW,
                description=(
                    "The observed authoritative name servers appear "
                    "to belong to a single DNS provider. This may "
                    "reduce provider diversity, but it is not by "
                    "itself evidence of a security vulnerability."
                ),
                source=evidence.source,
                evidence_references=name_servers,
                remediation=(
                    "Review DNS resilience and determine whether the "
                    "current provider configuration meets availability "
                    "and resilience requirements."
                ),
            )
        ]

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        """Convert an observation value to a string list."""

        if not isinstance(value, list):
            return []

        return [item for item in value if isinstance(item, str)]

    @staticmethod
    def _has_single_provider_dns(
        name_servers: list[str],
    ) -> bool:
        """Determine whether DNS data suggests one provider."""

        if len(name_servers) < 2:
            return False

        providers = {
            ".".join(name_server.lower().split(".")[-2:])
            for name_server in name_servers
            if "." in name_server
        }

        return len(providers) == 1

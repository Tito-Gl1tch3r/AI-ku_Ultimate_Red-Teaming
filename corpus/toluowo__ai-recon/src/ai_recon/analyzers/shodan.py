from __future__ import annotations

from ai_recon.analyzers.base import EvidenceAnalyzer
from ai_recon.models import Confidence, Evidence, Finding, Severity


class ShodanAnalyzer(EvidenceAnalyzer):
    """Analyze Shodan evidence for externally observable security risks."""

    source = "shodan"

    REMOTE_ACCESS_PORTS = {
        22: "SSH",
        23: "Telnet",
        3389: "RDP",
        5900: "VNC",
    }

    LEGACY_BANNER_INDICATORS = (
        "apache/2.2",
        "openssl/1.0.",
        "php/5.",
        "microsoft-iis/6.0",
    )

    def analyze(self, evidence: Evidence) -> list[Finding]:
        """Analyze Shodan evidence and return findings."""

        if evidence.source != self.source:
            return []

        findings: list[Finding] = []

        observations = evidence.observations

        ports = self._as_int_list(observations.get("ports"))

        vulnerabilities = self._as_string_list(observations.get("vulnerabilities"))

        banners = self._as_banner_list(observations.get("data"))

        remote_access_ports = [port for port in ports if port in self.REMOTE_ACCESS_PORTS]

        if remote_access_ports:
            findings.append(
                Finding(
                    id="SHODAN_EXPOSED_REMOTE_ACCESS",
                    title="Externally exposed remote access service",
                    severity=Severity.HIGH,
                    confidence=Confidence.HIGH,
                    description=(
                        "One or more remote access services are "
                        "externally observable through internet-facing "
                        "ports."
                    ),
                    source=evidence.source,
                    evidence_references=[str(port) for port in remote_access_ports],
                    remediation=(
                        "Verify that remote access services are "
                        "intentionally internet-facing. Restrict access "
                        "with network controls, strong authentication, "
                        "and secure remote access gateways where "
                        "appropriate."
                    ),
                )
            )

        if len(ports) > 5:
            findings.append(
                Finding(
                    id="SHODAN_MANY_OPEN_PORTS",
                    title="Large external service exposure",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    description=(
                        "Multiple externally observable services were "
                        "identified. A larger exposed service footprint "
                        "can increase attack surface."
                    ),
                    source=evidence.source,
                    evidence_references=[str(port) for port in ports],
                    remediation=(
                        "Review exposed services and close or restrict "
                        "ports that are not required for the intended "
                        "business function."
                    ),
                )
            )

        if vulnerabilities:
            findings.append(
                Finding(
                    id="SHODAN_KNOWN_VULNERABILITIES",
                    title="Potential known vulnerabilities in exposed services",
                    severity=Severity.HIGH,
                    confidence=Confidence.MEDIUM,
                    description=(
                        "Shodan returned vulnerability identifiers "
                        "associated with one or more externally "
                        "observable services. Vulnerability applicability "
                        "should be validated before treating these as "
                        "confirmed exploitable issues."
                    ),
                    source=evidence.source,
                    evidence_references=vulnerabilities,
                    remediation=(
                        "Validate the affected software and versions, "
                        "then patch, upgrade, mitigate, or remove "
                        "affected services as appropriate."
                    ),
                )
            )

        legacy_banners = self._find_legacy_banners(banners)

        if legacy_banners:
            findings.append(
                Finding(
                    id="SHODAN_LEGACY_SERVICE_BANNER",
                    title="Potentially outdated service software observed",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    description=(
                        "Service banners contain indicators associated "
                        "with older software versions. Banner information "
                        "should be validated because service "
                        "identification can be incomplete or misleading."
                    ),
                    source=evidence.source,
                    evidence_references=legacy_banners,
                    remediation=(
                        "Validate the actual deployed software versions "
                        "and upgrade unsupported or vulnerable "
                        "components."
                    ),
                )
            )

        return findings

    @staticmethod
    def _as_int_list(value: object) -> list[int]:
        """Convert an observation value to an integer list."""

        if not isinstance(value, list):
            return []

        return [item for item in value if isinstance(item, int)]

    @staticmethod
    def _as_string_list(value: object) -> list[str]:
        """Convert an observation value to a string list."""

        if not isinstance(value, list):
            return []

        return [item for item in value if isinstance(item, str)]

    @staticmethod
    def _as_banner_list(value: object) -> list[str]:
        """Extract banner strings from normalized Shodan data."""

        if not isinstance(value, list):
            return []

        banners: list[str] = []

        for item in value:
            if not isinstance(item, dict):
                continue

            banner = item.get("banner")

            if isinstance(banner, str):
                banners.append(banner)

        return banners

    def _find_legacy_banners(
        self,
        banners: list[str],
    ) -> list[str]:
        """Return banners containing legacy software indicators."""

        matches: list[str] = []

        for banner in banners:
            normalized = banner.lower()

            if any(indicator in normalized for indicator in self.LEGACY_BANNER_INDICATORS):
                matches.append(banner)

        return matches

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import shodan  # type: ignore[import-untyped]

from ai_recon.collectors.base import EvidenceCollector
from ai_recon.models import Evidence, EvidenceMode, EvidenceStatus, Target

ShodanSearch = Callable[[str], dict[str, Any]]


class ShodanCollector(EvidenceCollector):
    """Collect normalized Shodan evidence for authorized targets."""

    source = "shodan"

    def __init__(
        self,
        api_key: str | None,
        search: ShodanSearch | None = None,
    ) -> None:
        self._api_key = api_key
        self._search = search

    def collect(self, target: Target) -> Evidence:
        """Collect Shodan evidence for the supplied target."""

        if not self._api_key and self._search is None:
            return Evidence(
                source=self.source,
                target=target.identifier,
                observations={},
                mode=EvidenceMode.LIVE,
                status=EvidenceStatus.UNAVAILABLE,
                error="AI_RECON_SHODAN_API_KEY is not configured.",
            )

        try:
            results = self._execute_search(target.identifier)
        except Exception as exc:
            return Evidence(
                source=self.source,
                target=target.identifier,
                observations={},
                mode=EvidenceMode.LIVE,
                status=EvidenceStatus.ERROR,
                error=str(exc),
            )

        observations = self._normalize_results(
            target.identifier,
            results,
        )

        return Evidence(
            source=self.source,
            target=target.identifier,
            observations=observations,
            mode=EvidenceMode.LIVE,
        )

    def _execute_search(
        self,
        identifier: str,
    ) -> dict[str, Any]:
        """Execute a Shodan hostname search."""

        if self._search is not None:
            return self._search(identifier)

        if self._api_key is None:
            raise RuntimeError("AI_RECON_SHODAN_API_KEY is not configured.")

        api = shodan.Shodan(self._api_key)

        return cast(
            dict[str, Any],
            api.search(
                f"hostname:{identifier}",
                limit=100,
            ),
        )

    @staticmethod
    def _normalize_results(
        identifier: str,
        results: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalize Shodan search results into evidence observations."""

        ports: set[int] = set()
        vulnerabilities: set[str] = set()
        hostnames: set[str] = set()
        banners: list[dict[str, str]] = []

        organization: str | None = None
        country: str | None = None

        matches = results.get("matches", [])

        for match in matches:
            if not isinstance(match, dict):
                continue

            port = match.get("port")

            if isinstance(port, int):
                ports.add(port)

            match_hostnames = match.get("hostnames")

            if isinstance(match_hostnames, list):
                hostnames.update(str(hostname) for hostname in match_hostnames)

            match_org = match.get("org")

            if organization is None and isinstance(match_org, str):
                organization = match_org

            location = match.get("location")

            if isinstance(location, dict):
                country_code = location.get("country_code")

                if country is None and isinstance(country_code, str):
                    country = country_code

            vulnerabilities_data = match.get("vulns", {})

            if isinstance(vulnerabilities_data, dict):
                vulnerabilities.update(str(vulnerability) for vulnerability in vulnerabilities_data)

            banner = match.get("data")

            if isinstance(banner, str) and banner:
                banners.append(
                    {
                        "banner": banner[:500],
                    }
                )

        return {
            "hostnames": sorted(hostnames) or [identifier],
            "ports": sorted(ports),
            "org": organization,
            "country": country,
            "vulnerabilities": sorted(vulnerabilities),
            "data": banners,
        }

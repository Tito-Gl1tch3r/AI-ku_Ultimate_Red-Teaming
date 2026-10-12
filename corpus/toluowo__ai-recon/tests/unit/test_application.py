from __future__ import annotations

from ai_recon.analyzers import ShodanAnalyzer, WhoisAnalyzer
from ai_recon.application import create_assessment_service
from ai_recon.collectors import ShodanCollector, WhoisCollector


def test_create_assessment_service_configures_collectors() -> None:
    service = create_assessment_service(
        shodan_api_key="test-api-key",
    )

    assert len(service._collectors) == 2

    assert isinstance(
        service._collectors[0],
        WhoisCollector,
    )

    assert isinstance(
        service._collectors[1],
        ShodanCollector,
    )


def test_create_assessment_service_configures_analyzers() -> None:
    service = create_assessment_service(
        shodan_api_key="test-api-key",
    )

    assert len(service._analyzers) == 2

    assert isinstance(
        service._analyzers[0],
        WhoisAnalyzer,
    )

    assert isinstance(
        service._analyzers[1],
        ShodanAnalyzer,
    )


def test_create_assessment_service_allows_missing_shodan_api_key() -> None:
    service = create_assessment_service()

    shodan_collector = service._collectors[1]

    assert isinstance(
        shodan_collector,
        ShodanCollector,
    )

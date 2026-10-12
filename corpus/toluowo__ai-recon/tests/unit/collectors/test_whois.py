from __future__ import annotations

from ai_recon.collectors.whois import WhoisCollector
from ai_recon.models import EvidenceMode, EvidenceStatus, Target


class FakeWhoisResult:
    domain_name = ["example.com"]
    registrar = "Example Registrar"
    creation_date = "2020-01-01"
    expiration_date = "2030-01-01"
    name_servers = {
        "ns2.example.com",
        "ns1.example.com",
    }
    emails = ["admin@example.com"]
    org = "Example Organization"
    country = "NG"


def test_collect_returns_normalized_live_evidence() -> None:
    def lookup(identifier: str) -> FakeWhoisResult:
        assert identifier == "example.com"
        return FakeWhoisResult()

    collector = WhoisCollector(lookup=lookup)
    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.source == "whois"
    assert evidence.target == "example.com"
    assert evidence.mode is EvidenceMode.LIVE
    assert evidence.status is EvidenceStatus.SUCCESS

    assert evidence.observations["domain_name"] == ["example.com"]
    assert evidence.observations["registrar"] == "Example Registrar"
    assert evidence.observations["name_servers"] == [
        "ns1.example.com",
        "ns2.example.com",
    ]
    assert evidence.observations["country"] == "NG"


def test_collect_uses_target_when_domain_name_is_missing() -> None:
    class Result:
        domain_name = None
        registrar = None
        creation_date = None
        expiration_date = None
        name_servers = None
        emails = None
        org = None
        country = None

    collector = WhoisCollector(lookup=lambda _: Result())

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.status is EvidenceStatus.SUCCESS
    assert evidence.observations["domain_name"] == "example.com"
    assert evidence.observations["name_servers"] == []


def test_collect_returns_error_evidence_when_lookup_fails() -> None:
    def failing_lookup(_: str) -> object:
        raise RuntimeError("WHOIS service unavailable")

    collector = WhoisCollector(lookup=failing_lookup)

    evidence = collector.collect(Target(identifier="example.com"))

    assert evidence.source == "whois"
    assert evidence.status is EvidenceStatus.ERROR
    assert evidence.observations == {}
    assert evidence.error == "WHOIS service unavailable"

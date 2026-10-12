from __future__ import annotations

import argparse

import pytest

from ai_recon.cli import (
    build_parser,
    create_reporter,
    resolve_shodan_api_key,
)
from ai_recon.reporters.console import ConsoleReporter
from ai_recon.reporters.json import JsonReporter


def test_build_parser_returns_argument_parser() -> None:
    parser = build_parser()

    assert isinstance(parser, argparse.ArgumentParser)


def test_build_parser_requires_target() -> None:
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--authorized",
            ]
        )


def test_build_parser_accepts_authorized_target() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--target",
            "example.com",
            "--authorized",
        ]
    )

    assert args.target == "example.com"
    assert args.authorized is True
    assert args.format == "console"


def test_build_parser_accepts_json_format() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--target",
            "example.com",
            "--authorized",
            "--format",
            "json",
        ]
    )

    assert args.target == "example.com"
    assert args.authorized is True
    assert args.format == "json"


def test_create_reporter_returns_console_reporter() -> None:
    reporter = create_reporter("console")

    assert isinstance(reporter, ConsoleReporter)


def test_create_reporter_returns_json_reporter() -> None:
    reporter = create_reporter("json")

    assert isinstance(reporter, JsonReporter)


def test_resolve_shodan_api_key_prefers_cli_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AI_RECON_SHODAN_API_KEY",
        "environment-key",
    )

    api_key = resolve_shodan_api_key(
        "cli-key",
    )

    assert api_key == "cli-key"


def test_resolve_shodan_api_key_uses_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AI_RECON_SHODAN_API_KEY",
        "environment-key",
    )

    api_key = resolve_shodan_api_key(None)

    assert api_key == "environment-key"


def test_resolve_shodan_api_key_returns_none_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        "AI_RECON_SHODAN_API_KEY",
        raising=False,
    )

    api_key = resolve_shodan_api_key(None)

    assert api_key is None

import pytest

from ai_recon.models import Target, TargetType


def test_target_defaults_to_domain() -> None:
    target = Target(identifier="example.com")

    assert target.identifier == "example.com"
    assert target.target_type is TargetType.DOMAIN


def test_target_strips_identifier() -> None:
    target = Target(identifier="  example.com  ")

    assert target.identifier == "example.com"


def test_target_rejects_empty_identifier() -> None:
    with pytest.raises(ValueError):
        Target(identifier="   ")

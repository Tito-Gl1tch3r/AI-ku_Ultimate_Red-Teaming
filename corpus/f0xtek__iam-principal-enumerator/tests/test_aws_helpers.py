import pytest
from unittest.mock import Mock
from iam_principal_enumerator.aws.helpers import generate_test_arns, valid_principal
from mypy_boto3_iam import IAMClient


def test_generate_test_arns():
    account_id = "123456789012"
    principals = ["principal1", "principal2"]
    expected_arns = [
        "arn:aws:iam::123456789012:role/principal1",
        "arn:aws:iam::123456789012:role/principal2",
        "arn:aws:iam::123456789012:user/principal1",
        "arn:aws:iam::123456789012:user/principal2",
    ]
    assert generate_test_arns(account_id, principals) == expected_arns


def test_principal_valid():
    client = Mock(spec=IAMClient)
    role_name = "test-role"
    arn = "arn:aws:iam::123456789012:role/test-role"

    # Mock the is_valid_principal function to return True
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "iam_principal_enumerator.aws.helpers.is_valid_principal",
            lambda c, r, a: True,
        )
        assert valid_principal(client, role_name, arn) == arn


def test_principal_invalid():
    client = Mock(spec=IAMClient)
    role_name = "test-role"
    arn = "arn:aws:iam::123456789012:role/test-role"

    # Mock the is_valid_principal function to return False
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "iam_principal_enumerator.aws.helpers.is_valid_principal",
            lambda c, r, a: False,
        )
        assert valid_principal(client, role_name, arn) is None

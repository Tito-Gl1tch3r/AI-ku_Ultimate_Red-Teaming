import pytest
from unittest.mock import Mock, patch
from iam_principal_enumerator.main import parse_args, search_valid_principals
from mypy_boto3_iam import IAMClient


def test_parse_args():
    test_args = ["123456789012", "-r", "TestRole", "-w", "test_wordlist.txt"]
    with patch("sys.argv", ["main.py"] + test_args):
        args = parse_args()
        assert args.account_id == 123456789012
        assert args.enum_role_name == "TestRole"
        assert args.wordlist == "test_wordlist.txt"


def test_search_valid_principals():
    client = Mock(spec=IAMClient)
    target_account_id = "123456789012"
    principal_list = ["principal-valid", "principal-invalid"]
    role_name = "test-role"

    # Mock the valid_principal function to return the ARN if valid
    with patch(
        "iam_principal_enumerator.aws.helpers.valid_principal",
        side_effect=lambda c, r, a: a if a.endswith("-valid") else None,
    ):
        with patch(
            "iam_principal_enumerator.aws.helpers.generate_test_arns",
            return_value=[
                "arn:aws:iam::123456789012:role/principal-valid",
                "arn:aws:iam::123456789012:role/principal-invalid",
            ],
        ):
            with patch(
                "concurrent.futures.ThreadPoolExecutor.__enter__",
                return_value=Mock(
                    map=Mock(
                        return_value=["arn:aws:iam::123456789012:role/principal-valid"]
                    )
                ),
            ):
                valid_principals = search_valid_principals(
                    client, target_account_id, principal_list, role_name
                )
                assert valid_principals == [
                    "arn:aws:iam::123456789012:role/principal-valid"
                ]

import json

import pytest

from iam_principal_enumerator.aws.iam import (
    is_valid_arn,
    build_arn,
    create_role_trust_policy,
)


def test_is_valid_arn():
    valid_arns = [
        "arn:aws:iam::123456789012:root",
        "arn:aws:iam::123456789012:user/test-user",
        "arn:aws-us-gov:iam::123456789012:root",
        "arn:aws-cn:iam::123456789012:user/test-user",
    ]
    invalid_arns = [
        "arn:aws:iam::123456789012",
        "arn:aws:iam::12345678901:user/test-user",
        "arn:aws:iam::123456789012:user/test_user_with_invalid_characters!",
        "arn:aws:iam::123456789012:group/test-group",
    ]
    for arn in valid_arns:
        assert is_valid_arn(arn) is True
    for arn in invalid_arns:
        assert is_valid_arn(arn) is False


def test_build_arn():
    account_id = "123456789012"
    principal = "root"
    expected_arn = "arn:aws:iam::123456789012:root"
    assert build_arn(account_id, principal) == expected_arn

    principal = "user/test-user"
    expected_arn = "arn:aws:iam::123456789012:user/test-user"
    assert build_arn(account_id, principal) == expected_arn


def test_create_role_trust_policy():
    principal_arn = "arn:aws:iam::123456789012:root"
    expected_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"AWS": principal_arn},
            }
        ],
    }
    assert create_role_trust_policy(principal_arn) == json.dumps(expected_policy)

"""
Helper functions for generating ARNs and validating IAM principals.

This module provides functions to validate AWS account IDs, generate ARNs for IAM roles and users
based on principal names and to validate these ARNs using the AWS IAM client.
"""

import re
import sys
from typing import List, Optional

from loguru import logger
from mypy_boto3_iam import IAMClient

from .iam import is_valid_principal

logger.remove()
logger.add(sys.stderr, level="INFO")


def generate_test_arns(account_id: str, principals: List[str]) -> List[str]:
    """
    Generate ARNs for roles and users based on the principal names.

    :param account_id: AWS account ID
    :param principals: List of principal names
    :return: List of generated ARNs
    """
    arn_prefix = f"arn:aws:iam::{account_id}"
    return [f"{arn_prefix}:role/{principal}" for principal in principals] + [
        f"{arn_prefix}:user/{principal}" for principal in principals
    ]


def valid_principal(client: IAMClient, role_name: str, arn: str) -> Optional[str]:
    """
    Test a single ARN for validity.

    :param client: Boto3 IAM client
    :param role_name: Name of the IAM role to test
    :param arn: ARN to test
    :return: The ARN if valid, None otherwise
    """
    logger.debug(f"Testing ARN: {arn}")
    return arn if is_valid_principal(client, role_name, arn) else None


def is_valid_aws_account_id(account_id: str) -> bool:
    """
    Validate that the AWS account ID is a 12-digit number.

    :param account_id: AWS account ID to validate
    :return: True if valid, False otherwise
    """
    return re.fullmatch(r"\d{12}", str(account_id)) is not None

"""
IAM utility functions.

This module provides utility functions for working with AWS IAM, including
validating ARNs, building ARNs, and creating IAM roles
and trust policies.
"""

import json
import re
import sys

from loguru import logger

from mypy_boto3_iam import IAMClient

logger.remove()
logger.add(sys.stderr, level="INFO")


def is_valid_arn(arn: str) -> bool:
    """
    Validate the AWS ARN.

    :param arn: AWS ARN to validate
    :return: True if valid, False otherwise
    """
    return (
        re.fullmatch(
            r"^(?:\d{12}|(arn:(aws|aws-us-gov|aws-cn):iam::\d{12}(:(root|user\/[0-9A-Za-z\+\.@_,-]{1,64}))))$",
            arn,
        )
        is not None
    )


def build_arn(account_id: str, principal: str) -> str:
    """
    Build an AWS ARN.

    :param account_id: AWS account ID
    :param principal: Principal (e.g., root, user)
    :return: Constructed ARN string
    """
    return f"arn:aws:iam::{account_id}:{principal}"


def create_role_trust_policy(principal_arn: str) -> str:
    """
    Create a trust policy for an IAM role.

    :param principal_arn: ARN of the principal
    :return: Trust policy as a JSON string
    """
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Principal": {"AWS": principal_arn},
            }
        ],
    }
    return json.dumps(trust_policy)


def create_iam_role(client: IAMClient, role_name: str, trust_policy: str) -> str:
    """
    Create an IAM role with a trust policy for the current AWS account.

    :param role_name: Name of the IAM role to create
    :return: None
    """
    try:
        resp = client.create_role(
            RoleName=role_name, AssumeRolePolicyDocument=trust_policy
        )
        arn = resp["Role"]["Arn"]
        logger.info(f"IAM role created: {arn}")
        return arn
    except client.exceptions.EntityAlreadyExistsException:
        logger.error(f"IAM role {role_name} already exists.")
        return ""
    except client.exceptions.MalformedPolicyDocumentException as e:
        logger.error(f"Malformed policy document for role {role_name}: {e}")
        raise


def delete_iam_role(client: IAMClient, role_name: str) -> None:
    """
    Delete the specified IAM role.

    :param client: Boto3 IAM client
    :param role_name: Name of the IAM role to delete
    :return: None
    """
    try:
        client.delete_role(RoleName=role_name)
        logger.info(f"IAM role {role_name} deleted")
    except client.exceptions.NoSuchEntityException:
        logger.error(f"Role {role_name} does not exist.")


def is_valid_principal(client: IAMClient, role_name: str, principal_arn: str) -> bool:
    """
    Test if the given ARN is a valid principal for assuming the role.

    :param client: Boto3 IAM client
    :param role_name: Name of the IAM role to test
    :param principal_arn: ARN of the principal to test
    :return: True if the principal can assume the role, False otherwise
    """
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "sts:AssumeRole",
                "Principal": {"AWS": principal_arn},
            }
        ],
    }
    try:
        client.update_assume_role_policy(
            RoleName=role_name, PolicyDocument=json.dumps(policy_doc)
        )
        return True
    except client.exceptions.MalformedPolicyDocumentException:
        return False
    except client.exceptions.ClientError as e:
        logger.error(f"Error while testing principal {principal_arn}: {e}")
        return False

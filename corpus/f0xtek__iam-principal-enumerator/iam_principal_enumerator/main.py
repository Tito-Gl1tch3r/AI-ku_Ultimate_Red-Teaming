"""
Main module for enumerating valid IAM principals in an AWS account.

This module provides the main functionality for enumerating valid IAM principals
in a specified AWS account. It includes functions for parsing command-line arguments,
validating inputs, creating and deleting IAM roles, and testing principal ARNs.
"""

from argparse import ArgumentParser, Namespace
from pathlib import Path
import concurrent.futures
import sys

from loguru import logger
import boto3
from mypy_boto3_iam import IAMClient

from iam_principal_enumerator.aws.iam import (
    build_arn,
    create_iam_role,
    create_role_trust_policy,
    delete_iam_role,
    is_valid_arn,
)
from iam_principal_enumerator.aws.sts import get_current_account_id
from iam_principal_enumerator.aws.helpers import (
    is_valid_aws_account_id,
    generate_test_arns,
    valid_principal,
)
from iam_principal_enumerator.util import (
    generate_random_string,
    is_valid_file,
    read_lines_from_file,
    print_results,
)

logger.remove()
logger.add(sys.stderr, level="INFO")


def parse_args() -> Namespace:
    """
    Parse command-line arguments.

    :return: Parsed arguments
    """
    parser = ArgumentParser(
        description="Enumerate valid IAM principals in an AWS account."
    )
    parser.add_argument("account_id", type=int, help="The target AWS account ID")
    parser.add_argument(
        "-r",
        "--enum-role-name",
        type=str,
        default="IAMEnum",
        help="The name of the IAM role used for enumeration. "
        "The role name will be suffixed with an 8-character random string.",
    )
    parser.add_argument(
        "-w",
        "--wordlist",
        type=str,
        default="./principal_names.txt",
        help="Path to a wordlist to use when enumerating IAM principal names.",
    )
    return parser.parse_args()


def search_valid_principals(
    client: IAMClient, target_account_id: str, principal_list: list[str], role_name: str
) -> list[str]:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return list(
            filter(
                None,
                executor.map(
                    lambda arn: valid_principal(
                        client=client, role_name=role_name, arn=arn
                    ),
                    generate_test_arns(target_account_id, principal_list),
                ),
            )
        )


def main() -> None:
    """
    Main function to enumerate valid IAM principals in an AWS account.

    - Parses arguments
    - Validates inputs
    - Creates an IAM role
    - Tests principal ARNs
    - Deletes the IAM role
    """
    logger.info("IAM Principal Enumerator")
    args = parse_args()

    iam_client = boto3.client("iam")
    sts_client = boto3.client("sts")

    target_account_id = args.account_id
    my_account_id = get_current_account_id(client=sts_client)

    if not is_valid_aws_account_id(account_id=my_account_id):
        print(f"Invalid source account ID: {my_account_id}")
        sys.exit(1)

    my_account_principal_arn = build_arn(account_id=my_account_id, principal="root")

    if not is_valid_arn(arn=my_account_principal_arn):
        print(f"Invalid arn: {my_account_principal_arn}")
        sys.exit(1)

    initial_trust_policy = create_role_trust_policy(
        principal_arn=my_account_principal_arn
    )
    role_name = f"{args.enum_role_name}-{generate_random_string()}"

    try:
        create_iam_role(
            client=iam_client, role_name=role_name, trust_policy=initial_trust_policy
        )
    except Exception as e:
        logger.error(f"Error creating IAM role: {e}")
        sys.exit(1)

    wordlist_file = Path(args.wordlist)
    if not is_valid_file(wordlist_file):
        logger.error(f"Invalid wordlist file: {wordlist_file}")
        sys.exit(1)

    principal_list = list(read_lines_from_file(wordlist_file))

    logger.info("Searching for valid IAM principals...")
    valid_principals = search_valid_principals(
        iam_client, target_account_id, principal_list, role_name
    )

    logger.info(f"Deleting IAM role: {role_name}")
    try:
        delete_iam_role(client=iam_client, role_name=role_name)
    except Exception as e:
        logger.error(f"Error deleting IAM role: {e}")

    print_results(valid_principals)


if __name__ == "__main__":
    main()

"""
Helper functions for various utility operations.

This module provides utility functions for generating random strings,
validating file existence, and reading lines from a file.
"""

import random
import string
from pathlib import Path
from typing import Any, Generator, List


def generate_random_string(length=8):
    """
    Generate a random string of the specified length.

    :param length: Length of the random string (default is 8)
    :return: A random alphanumeric string
    """
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def is_valid_file(filename: Path):
    """
    Check if the given file exists.

    :param filename: Path to the file
    :return: True if file exists, False otherwise
    """
    return filename.is_file()


def read_lines_from_file(filename: Path) -> Generator[str, Any, None]:
    """
    Read lines from a file.

    :param filename: Path to the file
    :yield: Lines from the file, stripped of whitespace
    """
    with open(filename, "r") as f:
        for line in f:
            yield line.strip()


def print_results(valid_principals: List[str]) -> None:
    """
    Print the results of valid principals.

    :param valid_principals: List of valid principal ARNs
    :return: None
    """
    print("\n" + "*" * 40)
    print(f"Found {len(valid_principals)} valid principals:")
    print("*" * 40 + "\n")
    print("\n".join(valid_principals))
    print()

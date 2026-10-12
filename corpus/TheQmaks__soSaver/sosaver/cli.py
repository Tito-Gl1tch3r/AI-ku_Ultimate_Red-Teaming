"""Module for handling the command-line interface."""

import argparse
from argparse import Namespace

import sosaver
from sosaver.utils.logging import logger


class CommandLineInterface:
    """Class for handling the command-line interface."""

    def __init__(self):
        """Initialize the CommandLineInterface."""
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """
        Create the argument parser.

        Returns:
            The configured argument parser
        """
        parser = argparse.ArgumentParser(
            prog="sosaver",
            description="soSaver - a utility for dumping .so files from Android applications using Frida",
            epilog="Usage example: sosaver com.example.app --output myapp_libs"
        )

        parser.add_argument(
            "target",
            help="Process/package name or PID of the target application"
        )

        parser.add_argument(
            "-o", "--output",
            dest="output_folder",
            default="dumped_so",
            help="Directory for saving dumped libraries (default: dumped_so)"
        )

        parser.add_argument(
            "-d", "--debug",
            action="store_true",
            help="Enable debug mode (more detailed logging)"
        )

        parser.add_argument(
            "-v", "--version",
            action="version",
            version=f"soSaver {sosaver.__version__}",
            help="Show program version and exit"
        )

        return parser

    def parse_arguments(self) -> Namespace:
        """
        Parse command line arguments.

        Returns:
            Parsed arguments

        Raises:
            SystemExit: If arguments are invalid or --help is used
        """
        args = self.parser.parse_args()

        # If target can be converted to a number, consider it a PID
        try:
            args.target = int(args.target)
            logger.debug(f"Received PID: {args.target}")
        except ValueError:
            logger.debug(f"Received process/package name: {args.target}")

        return args

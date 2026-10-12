#!/usr/bin/env python3
"""Entry point for running the package as a module: python -m sosaver."""

from sosaver import __version__
from sosaver.cli import CommandLineInterface
from sosaver.dumper.module_dumper import ModuleDumper
from sosaver.utils.logging import LogLevel, logger


def main():
    """Main function of the project."""
    # Get command line parameters
    cli = CommandLineInterface()
    args = cli.parse_arguments()

    # Configure logging if debug mode is enabled
    if args.debug:
        logger.set_level(LogLevel.DEBUG)
        logger.info("Debug mode enabled")

    logger.info(f"Starting soSaver v{__version__}")
    logger.info(f"Target process: {args.target}")
    logger.info(f"Output directory: {args.output_folder}")

    # Create and run the module dumper
    dumper = ModuleDumper(
        target=args.target,
        output_folder=args.output_folder
    )

    try:
        dumper.run()
    except KeyboardInterrupt:
        logger.info("Interrupt signal received. Terminating...")
    finally:
        # Show statistics upon completion
        summary = dumper.get_summary()
        logger.info("Statistics:")
        logger.info(f"  Modules dumped: {summary['dumped_modules_count']}")
        logger.info(f"  Files saved: {summary['files_count']}")
        logger.info(f"  Total size: {summary['total_size_mb']} MB")


if __name__ == "__main__":
    main()

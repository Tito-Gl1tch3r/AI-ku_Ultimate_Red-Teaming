import argparse
import os

from ai_recon.application import create_assessment_service
from ai_recon.models import Target, TargetType
from ai_recon.reporters import AssessmentReporter, ConsoleReporter, JsonReporter


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="ai-recon",
        description=(
            "Modular reconnaissance and exposure analysis for authorized security assessments."
        ),
    )

    parser.add_argument(
        "--target",
        required=True,
        help="Target identifier to assess.",
    )

    parser.add_argument(
        "--authorized",
        action="store_true",
        help=("Acknowledge that you are authorized to assess the specified target."),
    )

    parser.add_argument(
        "--format",
        choices=("console", "json"),
        default="console",
        help="Output format. Defaults to console.",
    )

    parser.add_argument(
        "--shodan-api-key",
        help=("Shodan API key. If omitted, AI_RECON_SHODAN_API_KEY is used when available."),
    )

    return parser


def create_reporter(output_format: str) -> AssessmentReporter:
    """Create the reporter for the requested output format."""

    reporters: dict[str, AssessmentReporter] = {
        "console": ConsoleReporter(),
        "json": JsonReporter(),
    }

    return reporters[output_format]


def resolve_shodan_api_key(
    cli_api_key: str | None,
) -> str | None:
    """Resolve the Shodan API key from CLI input or environment."""

    if cli_api_key:
        return cli_api_key

    return os.getenv("AI_RECON_SHODAN_API_KEY")


def main() -> int:
    """Run the AI Recon command-line application."""

    parser = build_parser()
    args = parser.parse_args()

    if not args.authorized:
        parser.error("You must provide --authorized to acknowledge authorization for the target.")

    target = Target(
        identifier=args.target,
        target_type=TargetType.DOMAIN,
    )

    shodan_api_key = resolve_shodan_api_key(
        args.shodan_api_key,
    )

    service = create_assessment_service(
        shodan_api_key=shodan_api_key,
    )

    assessment = service.run(target)

    reporter = create_reporter(args.format)

    print(reporter.render(assessment))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

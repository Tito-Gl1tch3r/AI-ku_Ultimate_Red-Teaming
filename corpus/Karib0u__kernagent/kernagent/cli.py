"""kernagent command-line interface."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path, PureWindowsPath

from .agent import ReverseEngineeringAgent
from .config import load_settings
from .llm_client import LLMClient
from .log import get_logger, setup_logging
from .oneshot import OneshotPruningError, build_oneshot_summary
from .prompts import AUTO_SUMMARY_ONESHOT_SYSTEM_PROMPT, ONESHOT_SYSTEM_PROMPT, TOOLS
from .snapshot import SnapshotError, SnapshotTools, build_snapshot, build_tool_map

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kernagent", description="Static snapshot assistant.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging.")
    parser.add_argument("--model", type=str, help="Override the LLM model to use.")
    parser.add_argument("--base-url", type=str, help="Override the OpenAI-compatible API base URL.")
    parser.add_argument("--api-key", type=str, help="Override the API key for the LLM provider.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_binary_argument(sub):
        sub.add_argument("binary", type=Path, help="Path to the binary to analyze.")

    summary = subparsers.add_parser("summary", help="Generate executive summary.")
    add_binary_argument(summary)
    summary.add_argument("--json", action="store_true", help="Output raw JSON instead of LLM analysis.")

    ask = subparsers.add_parser("ask", help="Ask a custom question about the binary.")
    add_binary_argument(ask)
    ask.add_argument("question", help="Question to run through the agent.")

    oneshot = subparsers.add_parser("oneshot", help="Generate deterministic pruned summary.")
    add_binary_argument(oneshot)
    oneshot.add_argument("--json", action="store_true", help="Output raw JSON instead of LLM analysis.")

    return parser


def _archive_dir_for(binary_path: Path) -> Path:
    return binary_path.parent / f"{binary_path.stem}_archive"


def _safe_extract_zip(zip_path: Path, destination: Path) -> None:
    """
    Extract zip_path into destination while preventing path traversal.

    Raises:
        SnapshotError: if a member attempts to escape destination.
    """

    destination.mkdir(parents=True, exist_ok=True)
    dest_root = destination.resolve()

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            member_name = member.filename
            if not member_name:
                continue

            member_path = Path(member_name)
            if member_path.is_absolute() or member_path.drive:
                raise SnapshotError(f"Unsafe absolute path in archive entry: {member_name}")

            if PureWindowsPath(member_name).drive:
                raise SnapshotError(f"Unsafe absolute path in archive entry: {member_name}")

            if any(part == ".." for part in member_path.parts):
                raise SnapshotError(f"Unsafe relative path in archive entry: {member_name}")

            target_path = (dest_root / member_path).resolve(strict=False)
            if not str(target_path).startswith(str(dest_root)):
                raise SnapshotError(f"Archive entry escapes destination: {member_name}")

        zf.extractall(dest_root)


def _maybe_unpack_zip(zip_path: Path) -> Path | None:
    if not zip_path.exists():
        return None
    archive_dir = zip_path.parent / zip_path.stem
    logger.info("Extracting snapshot zip %s", zip_path)
    try:
        _safe_extract_zip(zip_path, zip_path.parent)
    except SnapshotError as exc:
        logger.error("Failed to extract snapshot zip %s: %s", zip_path, exc)
        raise
    return archive_dir if archive_dir.exists() else None


def ensure_snapshot(binary_path: Path, verbose: bool = False) -> Path:
    archive_dir = _archive_dir_for(binary_path)
    if archive_dir.exists():
        return archive_dir

    zip_candidate = archive_dir.with_suffix(".zip")
    unpacked = _maybe_unpack_zip(zip_candidate)
    if unpacked:
        return unpacked

    logger.info("Snapshot not found; building via Ghidra/PyGhidra")
    return build_snapshot(binary_path, None, verbose=verbose)


def run_agent_and_print(archive_dir: Path, question: str, settings, verbose: bool) -> None:
    snapshot = SnapshotTools(archive_dir)
    tool_map = build_tool_map(snapshot)
    llm = LLMClient(settings)
    agent = ReverseEngineeringAgent(llm, TOOLS, tool_map)
    answer = agent.run(question, verbose=verbose)
    print(answer)


def run_oneshot_and_print(archive_dir: Path, settings, verbose: bool, json_output: bool = False) -> None:
    summary = build_oneshot_summary(archive_dir, verbose=verbose)

    if json_output:
        print(json.dumps(summary, indent=2))
        return

    llm = LLMClient(settings)
    payload = json.dumps(summary, indent=2)
    try:
        response = llm.chat(
            verbose=verbose,
            messages=[
                {"role": "system", "content": ONESHOT_SYSTEM_PROMPT},
                {"role": "user", "content": payload},
            ],
            temperature=0,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        logger.error("Oneshot LLM call failed: %s", exc)
        raise
    print(response.choices[0].message.content or "")


def run_summary_and_print(archive_dir: Path, settings, verbose: bool, json_output: bool = False) -> None:
    """
    Lightweight summary path intended to work well on smaller LLMs.

    Flow:
    - Build deterministic pruned snapshot via build_oneshot_summary()
    - Single chat completion with AUTO_SUMMARY_ONESHOT_SYSTEM_PROMPT
    - No tools/function-calling at inference time
    """
    summary = build_oneshot_summary(archive_dir, verbose=verbose)

    if json_output:
        print(json.dumps(summary, indent=2))
        return

    payload = json.dumps(summary, indent=2)

    llm = LLMClient(settings)
    try:
        response = llm.chat(
            verbose=verbose,
            messages=[
                {"role": "system", "content": AUTO_SUMMARY_ONESHOT_SYSTEM_PROMPT},
                {"role": "user", "content": payload},
            ],
            temperature=0,
        )
    except Exception as exc:  # pragma: no cover - network dependent
        logger.error("Summary LLM call failed: %s", exc)
        raise

    print(response.choices[0].message.content or "")


def main() -> None:
    settings = load_settings()

    parser = build_parser()
    args = parser.parse_args()

    # Configure logging - only debug mode shows httpx logs
    setup_logging(settings.debug)

    # Apply CLI overrides to settings
    if args.model:
        settings.model = args.model
    if args.base_url:
        settings.base_url = args.base_url
    if args.api_key:
        settings.api_key = args.api_key

    binary_path = Path(args.binary).expanduser().resolve()
    if not binary_path.exists():
        raise FileNotFoundError(binary_path)

    try:
        archive_dir = ensure_snapshot(binary_path, verbose=args.verbose)
    except SnapshotError as exc:
        logger.error("Snapshot build failed: %s", exc)
        raise SystemExit(str(exc)) from exc

    if args.command == "summary":
        try:
            json_output = getattr(args, "json", False)
            run_summary_and_print(archive_dir, settings, args.verbose, json_output)
        except OneshotPruningError as exc:
            logger.error("Summary build failed: %s", exc)
            raise SystemExit(str(exc)) from exc
    elif args.command == "ask":
        run_agent_and_print(archive_dir, args.question, settings, args.verbose)
    elif args.command == "oneshot":
        try:
            json_output = getattr(args, "json", False)
            run_oneshot_and_print(archive_dir, settings, args.verbose, json_output)
        except OneshotPruningError as exc:
            raise SystemExit(str(exc)) from exc
    else:  # pragma: no cover
        parser.error("Unknown command")


if __name__ == "__main__":  # pragma: no cover
    main()

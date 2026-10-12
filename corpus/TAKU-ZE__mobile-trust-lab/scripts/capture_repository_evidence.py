from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "evidence" / "repository-verification.json"
HASHED_FILES = (
    "README.md",
    "CITATION.cff",
    "docs/cvp-defensive-use-case.md",
    "docs/researcher-verification.md",
    "docs/validation-status.md",
    "sample-reports/vulnerable.json",
    "sample-reports/hardened.json",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_verification_output(output: str) -> dict[str, str]:
    summary: dict[str, str] = {}
    for line in output.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        summary[key] = value
    return summary


def current_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def working_tree_changes() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def collect_hashes() -> dict[str, str]:
    return {name: sha256_file(ROOT / name) for name in HASHED_FILES}


def capture_record() -> tuple[dict, int]:
    command = [sys.executable, str(ROOT / "scripts" / "verify.py")]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    summary = parse_verification_output(result.stdout)
    passed = result.returncode == 0 and summary.get("Result") == "PASS"
    record = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_commit": current_git_commit(),
        "repository": "https://github.com/TAKU-ZE/mobile-trust-lab",
        "command": "python scripts/verify.py",
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "verification": {
            "status": "PASS" if passed else "FAIL",
            "exit_code": result.returncode,
            "summary": summary,
            "stdout": result.stdout.splitlines(),
            "stderr": result.stderr.splitlines(),
        },
        "file_sha256": collect_hashes(),
        "scope_note": (
            "This record verifies repository tests, deterministic reports, and documentation links. "
            "It is not a substitute for owned-device runtime evidence."
        ),
    }
    return record, 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture machine-readable repository verification evidence.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    changes = working_tree_changes()
    if changes:
        print("Refusing to capture evidence from a dirty working tree.", file=sys.stderr)
        for change in changes:
            print(f"  {change}", file=sys.stderr)
        return 2

    record, exit_code = capture_record()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Evidence record: {output.relative_to(ROOT).as_posix()}")
    print(f"Source commit: {record['source_commit']}")
    print(f"Verification: {record['verification']['status']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

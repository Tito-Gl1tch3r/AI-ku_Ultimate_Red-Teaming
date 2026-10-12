from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

SCHEMA = "mobile-trust-build/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_artifacts(input_directory: Path, output_directory: Path) -> dict[str, object]:
    input_directory = input_directory.resolve()
    output_directory = output_directory.resolve()
    apks = sorted(input_directory.glob("*.apk"), key=lambda path: path.name)
    if not apks:
        raise FileNotFoundError(f"no APK files found in {input_directory}")

    output_directory.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, str | int]] = []
    checksum_lines: list[str] = []
    for source in apks:
        destination = output_directory / source.name
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
        checksum = sha256_file(destination)
        size = destination.stat().st_size
        files.append({"name": destination.name, "sha256": checksum, "size_bytes": size})
        checksum_lines.append(f"{checksum}  {destination.name}")

    manifest: dict[str, object] = {"schema": SCHEMA, "files": files}
    (output_directory / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    (output_directory / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy APKs and create deterministic checksum manifests"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("lab-app/build/outputs"),
        help="directory containing APK files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist"),
        help="directory for APKs and generated manifests",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = package_artifacts(args.input, args.output)
    for artifact in manifest["files"]:
        print(f"{artifact['sha256']}  {artifact['name']} ({artifact['size_bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

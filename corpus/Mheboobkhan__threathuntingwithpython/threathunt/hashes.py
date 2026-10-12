"""Pull MD5/SHA1/SHA256 tokens out of arbitrary text (logs, IOC lists, pastes).

Rewrite of the original hash-extractor.py: that version treated *any*
whitespace-delimited token of length 32/40/64 as a hash, so plain words or
GUID fragments were silently misclassified. This version requires the token
to actually be hex.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_HEX = re.compile(r"^[0-9a-fA-F]+$")
_LENGTHS = {32: "md5", 40: "sha1", 64: "sha256"}


def extract(text: str) -> dict[str, list[str]]:
    """Return {"md5": [...], "sha1": [...], "sha256": [...]} found in text.

    Order is preserved and duplicates are removed within each bucket.
    """
    found: dict[str, list[str]] = {name: [] for name in _LENGTHS.values()}
    seen: dict[str, set[str]] = {name: set() for name in _LENGTHS.values()}
    for token in re.findall(r"[0-9a-fA-F]{32,64}", text):
        kind = _LENGTHS.get(len(token))
        if kind is None or not _HEX.match(token):
            continue
        if token not in seen[kind]:
            seen[kind].add(token)
            found[kind].append(token)
    return found


def extract_from_file(path: str | Path) -> dict[str, list[str]]:
    return extract(Path(path).read_text(errors="replace"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to the text/log file to scan")
    parser.add_argument(
        "--out-dir", default=".", help="directory to write md5.txt/sha1.txt/sha256.txt into"
    )
    args = parser.parse_args()

    found = extract_from_file(args.file)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, tokens in found.items():
        out_path = out_dir / f"{kind}.txt"
        out_path.write_text("\n".join(tokens) + ("\n" if tokens else ""))
        print(f"{kind}: {len(tokens)} unique hash(es) -> {out_path}")


if __name__ == "__main__":
    main()

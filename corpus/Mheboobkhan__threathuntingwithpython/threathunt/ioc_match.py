"""Scan any log/text file for known-bad IPs, domains, or hashes.

Deliberately format-agnostic: rather than parsing each log type's schema,
this does a case-insensitive substring scan of the raw file content against
a small watchlist. That means it works unmodified against every sample
format in this repo (Zeek conn/dns JSON, Sysmon CSV, Suricata JSON, a plain
hash dump) - the same "grep for something I already know is bad" task a
hunter runs constantly, without writing a new parser for it every time.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from threathunt.io_utils import read_csv


def load_watchlist(path: str | Path) -> pd.DataFrame:
    """Load a CSV with ioc_type, value, description columns."""
    return read_csv(path)


def scan_text(text: str, watchlist: pd.DataFrame) -> pd.DataFrame:
    """Return one row per watchlist entry that appears in text, with a hit count."""
    haystack = text.lower()
    rows = []
    for _, ioc in watchlist.iterrows():
        needle = str(ioc["value"]).strip().lower()
        hit_count = haystack.count(needle) if needle else 0
        if hit_count > 0:
            rows.append({
                "ioc_type": ioc["ioc_type"],
                "value": ioc["value"],
                "description": ioc.get("description", ""),
                "hit_count": hit_count,
            })
    result = pd.DataFrame(rows, columns=["ioc_type", "value", "description", "hit_count"])
    if result.empty:
        return result
    return result.sort_values("hit_count", ascending=False).reset_index(drop=True)


def scan_file(path: str | Path, watchlist: pd.DataFrame) -> pd.DataFrame:
    text = Path(path).read_text(errors="replace")
    return scan_text(text, watchlist)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("watchlist", help="CSV with ioc_type,value,description columns")
    parser.add_argument("files", nargs="+", help="one or more log/text files to scan")
    args = parser.parse_args()

    watchlist = load_watchlist(args.watchlist)
    any_hits = False
    for path in args.files:
        hits = scan_file(path, watchlist)
        if hits.empty:
            continue
        any_hits = True
        print(f"\n{path}:")
        print(hits.to_string(index=False))
    if not any_hits:
        print("no watchlist matches in any of the given files")


if __name__ == "__main__":
    main()

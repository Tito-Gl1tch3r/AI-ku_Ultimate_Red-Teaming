"""Stack-count parent -> child process pairs to surface rare ones.

"Least frequency analysis" (stacking) is one of the oldest tricks in
threat hunting: attackers' process launches are rare by nature (a given
LOLBAS abuse pattern happens far less often than svchost.exe spawning its
usual children), so sorting by count ascending puts them near the top with
almost no modeling required. This also flags known living-off-the-land
binaries by name so a rare *and* LOLBAS pair stands out doubly.
"""
from __future__ import annotations

import argparse
from pathlib import PureWindowsPath

import pandas as pd

from threathunt.io_utils import read_csv

KNOWN_LOLBAS = {
    "rundll32.exe", "regsvr32.exe", "mshta.exe", "certutil.exe", "wmic.exe",
    "cscript.exe", "wscript.exe", "msiexec.exe", "installutil.exe",
    "regasm.exe", "regsvcs.exe", "bitsadmin.exe", "msbuild.exe",
}


def _basename(path: str) -> str:
    return PureWindowsPath(str(path)).name.lower()


def stack_count(df: pd.DataFrame, parent_col: str = "parent_image", child_col: str = "image") -> pd.DataFrame:
    """Count every (parent, child) pair, rarest first, with a LOLBAS flag."""
    for col in (parent_col, child_col):
        if col not in df.columns:
            raise KeyError(f"expected column {col!r}")
    counts = (
        df.groupby([parent_col, child_col])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=True)
        .reset_index(drop=True)
    )
    counts["is_lolbas"] = counts[child_col].apply(lambda p: _basename(p) in KNOWN_LOLBAS)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lineage_csv", help="CSV with parent_image/image columns")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--lolbas-only", action="store_true", help="only show known LOLBAS children")
    args = parser.parse_args()

    df = read_csv(args.lineage_csv)
    counts = stack_count(df)
    if args.lolbas_only:
        counts = counts[counts["is_lolbas"]]
    print(counts.head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()

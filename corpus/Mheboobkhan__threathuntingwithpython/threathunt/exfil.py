"""Flag anomalously large data transfers in a Zeek conn.log-style flow log.

A companion to beaconing.py: beaconing catches *regular, low-volume*
check-ins, this catches the opposite pattern of a real exfil/data-movement
event - one (src, dst, port) pair moving far more data than its peers.
Uses a robust (median/MAD-based) modified z-score rather than mean/stdev so
that a handful of huge transfers don't blow out the baseline they're
supposed to stand out from.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from threathunt.beaconing import GROUP_COLS
from threathunt.io_utils import read_zeek_json


def _modified_z_scores(values: pd.Series) -> np.ndarray:
    """Iglewicz & Hoaglin's modified z-score: 0.6745 * (x - median) / MAD.

    Falls back to the mean absolute deviation (their paper's own suggestion)
    when MAD is 0 - which happens whenever a majority of pairs move an
    identical, or near-identical, amount of data. That's the common case in
    a real conn log (most connections to the same service move similar
    byte counts), and without the fallback a real outlier sitting among a
    block of ties would get silently zeroed out along with everything else.
    """
    values = values.to_numpy(dtype=float)
    median = np.median(values)
    abs_deviation = np.abs(values - median)
    mad = np.median(abs_deviation)
    if mad != 0:
        return 0.6745 * (values - median) / mad
    mean_abs_deviation = np.mean(abs_deviation)
    if mean_abs_deviation == 0:
        return np.zeros(len(values))
    return (values - median) / (1.253314 * mean_abs_deviation)


def aggregate_transfers(df: pd.DataFrame) -> pd.DataFrame:
    """Total bytes moved per (orig_h, resp_h, resp_p) pair."""
    for col in GROUP_COLS:
        if col not in df.columns:
            raise KeyError(f"expected column {col!r} in a Zeek conn DataFrame")
    working = df.copy()
    working["orig_bytes"] = pd.to_numeric(working.get("orig_bytes"), errors="coerce").fillna(0)
    working["resp_bytes"] = pd.to_numeric(working.get("resp_bytes"), errors="coerce").fillna(0)
    return (
        working.groupby(GROUP_COLS)
        .agg(
            connection_count=("orig_bytes", "size"),
            total_orig_bytes=("orig_bytes", "sum"),
            total_resp_bytes=("resp_bytes", "sum"),
        )
        .reset_index()
    )


def score_transfers(df: pd.DataFrame, threshold: float = 3.5) -> pd.DataFrame:
    """Score every (orig_h, resp_h, resp_p) pair by outbound/inbound transfer outlier-ness.

    Adds orig_z/resp_z (modified z-scores) and is_outlier (either direction
    beyond `threshold`, the standard Iglewicz & Hoaglin cutoff), sorted by
    the larger of the two z-scores.
    """
    agg = aggregate_transfers(df)
    if agg.empty:
        return agg
    agg["orig_z"] = _modified_z_scores(agg["total_orig_bytes"]).round(2)
    agg["resp_z"] = _modified_z_scores(agg["total_resp_bytes"]).round(2)
    agg["is_outlier"] = (agg["orig_z"].abs() > threshold) | (agg["resp_z"].abs() > threshold)
    agg["max_abs_z"] = agg[["orig_z", "resp_z"]].abs().max(axis=1)
    return agg.sort_values("max_abs_z", ascending=False).drop(columns="max_abs_z").reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conn_log", help="path to a Zeek conn.log JSONL file")
    parser.add_argument("--threshold", type=float, default=3.5)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    df = read_zeek_json(args.conn_log)
    scored = score_transfers(df, threshold=args.threshold)
    if scored.empty:
        print("no conn records to score")
        return

    outliers = scored[scored["is_outlier"]]
    print(f"{len(scored)} pairs scored, {len(outliers)} outlier transfer(s) at |z| > {args.threshold}\n")
    print(scored.head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()

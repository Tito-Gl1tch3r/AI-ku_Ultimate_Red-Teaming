"""C2 beacon detection over Zeek conn.log-style flow records.

Rewrite of the original Beaconing_analysis.py, which just scatter-plotted
``frame.time_delta_displayed`` vs ``ip.len`` for a single hardcoded DNS CSV
and left the actual "is this a beacon" judgment entirely to the analyst's
eyeball. This module does the part a human is bad at: scoring every
(src, dst, port) pair in a flow log by how *regular* its connection interval
is, since a real C2 beacon calls home on a near-fixed timer with only small
jitter, while normal human/application traffic is bursty and irregular.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from threathunt.io_utils import read_zeek_json

GROUP_COLS = ["id.orig_h", "id.resp_h", "id.resp_p"]


def _mad(values: np.ndarray) -> float:
    """Median absolute deviation - robust to the occasional missed check-in."""
    median = np.median(values)
    return float(np.median(np.abs(values - median)))


def score_beacons(df: pd.DataFrame, min_observations: int = 4) -> pd.DataFrame:
    """Score every (orig_h, resp_h, resp_p) pair in a Zeek conn DataFrame.

    Returns one row per pair with connection_count, median_interval_s,
    jitter_pct (lower = more regular = more beacon-like) and a beacon_score
    that rewards both regularity and repetition, sorted highest-first.
    """
    working = df.copy()
    working["ts"] = pd.to_datetime(working["ts"])
    for col in GROUP_COLS:
        if col not in working.columns:
            raise KeyError(f"expected column {col!r} in a Zeek conn DataFrame")

    rows = []
    for key, group in working.groupby(GROUP_COLS):
        if len(group) < min_observations:
            continue
        times = group["ts"].sort_values().to_numpy()
        intervals = np.diff(times).astype("timedelta64[ms]").astype(float) / 1000.0
        if len(intervals) == 0 or np.median(intervals) == 0:
            continue
        median_interval = float(np.median(intervals))
        jitter_pct = min(_mad(intervals) / median_interval * 100.0, 100.0)
        beacon_score = len(group) * (1 - jitter_pct / 100.0)
        total_bytes = int(
            group.get("orig_bytes", pd.Series(dtype=float)).fillna(0).sum()
            + group.get("resp_bytes", pd.Series(dtype=float)).fillna(0).sum()
        )
        rows.append({
            "id.orig_h": key[0],
            "id.resp_h": key[1],
            "id.resp_p": key[2],
            "connection_count": len(group),
            "median_interval_s": round(median_interval, 3),
            "jitter_pct": round(jitter_pct, 1),
            "total_bytes": total_bytes,
            "beacon_score": round(beacon_score, 2),
        })
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("beacon_score", ascending=False).reset_index(drop=True)


def candidate_beacons(scored: pd.DataFrame, jitter_threshold_pct: float = 30.0) -> pd.DataFrame:
    """Filter score_beacons() output down to pairs regular enough to flag."""
    if scored.empty:
        return scored
    return scored[scored["jitter_pct"] <= jitter_threshold_pct].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("conn_log", help="path to a Zeek conn.log JSONL file")
    parser.add_argument("--min-observations", type=int, default=4)
    parser.add_argument("--jitter-threshold", type=float, default=30.0,
                         help="max jitter %% to flag a pair as a candidate beacon")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    df = read_zeek_json(args.conn_log)
    scored = score_beacons(df, min_observations=args.min_observations)
    if scored.empty:
        print("no (src, dst, port) pair had enough connections to score")
        return

    candidates = candidate_beacons(scored, args.jitter_threshold)
    print(f"{len(scored)} pairs scored, {len(candidates)} under {args.jitter_threshold}% jitter\n")
    print(scored.head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()

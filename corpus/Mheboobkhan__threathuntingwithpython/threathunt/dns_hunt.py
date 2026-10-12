"""Heuristic hunting over DNS query logs: tunneling, exfil, and blocklisted categories.

Rewrite of the original DNS analysis idea (a hardcoded dns.csv scatter plot
of ip.len vs. frame.time_delta_displayed, with no actual scoring). This
module works off whatever query-name column a real DNS log gives it -
Sysmon EventID 22 XML, a Zeek dns.log, or a proxy/DNS-security vendor CSV -
and ranks queries by how much they look like DNS tunneling / C2 (long,
high-entropy, deeply-labeled, or explicitly categorized as an anonymizer).
"""
from __future__ import annotations

import argparse
import math
from collections import Counter

import pandas as pd

from threathunt.io_utils import read_csv, read_jsonl

_QUERY_COLUMN_CANDIDATES = ["query_name", "query", "domain", "QueryName", "qname"]
_CATEGORY_COLUMN_CANDIDATES = ["categories", "category", "blocked_categories"]
_SUSPICIOUS_CATEGORIES = ["anonymizer", "proxy", "filter avoidance", "dynamic dns"]


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    length = len(s)
    return -sum((n / length) * math.log2(n / length) for n in counts.values())


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


def hunt(df: pd.DataFrame, query_col: str | None = None) -> pd.DataFrame:
    """Score every row of a DNS query log by tunneling/exfil suspicion.

    Returns the input DataFrame with query_length, label_count, entropy,
    digit_ratio, suspicious_category, and suspicion_score columns added,
    sorted highest-suspicion first.
    """
    query_col = query_col or _find_column(df, _QUERY_COLUMN_CANDIDATES)
    if query_col is None:
        raise KeyError(
            f"no query-name column found; looked for {_QUERY_COLUMN_CANDIDATES}"
        )
    category_col = _find_column(df, _CATEGORY_COLUMN_CANDIDATES)

    working = df.copy()
    queries = working[query_col].fillna("").astype(str).str.rstrip(".")

    working["query_length"] = queries.str.len()
    working["label_count"] = queries.apply(lambda q: q.count(".") + 1 if q else 0)
    leftmost_label = queries.apply(lambda q: q.split(".")[0] if q else "")
    working["entropy"] = leftmost_label.apply(shannon_entropy)
    working["digit_ratio"] = queries.apply(
        lambda q: sum(c.isdigit() for c in q) / len(q) if q else 0.0
    )

    if category_col is not None:
        cats = working[category_col].fillna("").astype(str).str.lower()
        working["suspicious_category"] = cats.apply(
            lambda c: any(term in c for term in _SUSPICIOUS_CATEGORIES)
        )
    else:
        working["suspicious_category"] = False

    length_score = (working["query_length"] / 60.0).clip(upper=1.0)
    entropy_score = (working["entropy"] / 4.0).clip(upper=1.0)
    label_score = (working["label_count"] / 6.0).clip(upper=1.0)
    category_score = working["suspicious_category"].astype(float)

    working["suspicion_score"] = (
        0.35 * length_score
        + 0.35 * entropy_score
        + 0.10 * label_score
        + 0.20 * category_score
    ).round(3)

    return working.sort_values("suspicion_score", ascending=False).reset_index(drop=True)


def _load(path: str) -> pd.DataFrame:
    if path.endswith(".jsonl") or path.endswith(".json"):
        return read_jsonl(path)
    return read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dns_log", help="CSV or JSONL DNS query log")
    parser.add_argument("--query-col", default=None)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    df = _load(args.dns_log)
    ranked = hunt(df, query_col=args.query_col)
    query_col = args.query_col or _find_column(df, _QUERY_COLUMN_CANDIDATES)
    cols = [query_col, "query_length", "entropy", "label_count", "suspicious_category", "suspicion_score"]
    print(ranked[cols].head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()

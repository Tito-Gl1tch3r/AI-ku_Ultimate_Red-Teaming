"""Flag anomalous TLS certificates: self-signed, blank subject/issuer, unusual validity.

A classic C2-over-HTTPS signal that's independent of both connection timing
(beaconing.py) and volume (exfil.py): a lot of C2 frameworks - Cobalt
Strike's default SSL profile among them - serve a certificate with no real
issuer/subject fields and an oddly long validity window, because nobody
bothered (or needed) to make it look like a real CA-issued cert.
"""
from __future__ import annotations

import argparse
from datetime import datetime

import pandas as pd

from threathunt.io_utils import read_jsonl

_BLANK_DN = "C = , ST = , L = , O = , OU = , CN = "
_CERT_TIME_FORMAT = "%b %d %H:%M:%S %Y %Z"


def _validity_days(start: str, end: str) -> float:
    try:
        start_dt = datetime.strptime(start.strip(), _CERT_TIME_FORMAT)
        end_dt = datetime.strptime(end.strip(), _CERT_TIME_FORMAT)
        return (end_dt - start_dt).days
    except (ValueError, AttributeError):
        return float("nan")


def _column_or_default(df: pd.DataFrame, name: str, default):
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def hunt_certificates(df: pd.DataFrame, long_validity_days: int = 3650) -> pd.DataFrame:
    """Score every certificate row by self-signed/blank-DN/unusual-validity suspicion."""
    working = df.copy()
    working["is_self_signed"] = _column_or_default(working, "ssl_cert_self_signed", 0).fillna(0).astype(int) == 1
    working["is_blank_subject"] = _column_or_default(working, "ssl_subject", "").fillna("").eq(_BLANK_DN)
    starts = _column_or_default(working, "ssl_validity_start", "")
    ends = _column_or_default(working, "ssl_validity_end", "")
    working["validity_days"] = [
        _validity_days(start, end) for start, end in zip(starts, ends)
    ]
    working["is_long_validity"] = working["validity_days"] >= long_validity_days

    working["suspicion_score"] = (
        0.6 * working["is_self_signed"].astype(float)
        + 0.3 * working["is_blank_subject"].astype(float)
        + 0.1 * working["is_long_validity"].fillna(False).astype(float)
    ).round(3)

    return working.sort_values("suspicion_score", ascending=False).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tls_log", help="JSONL file of TLS certificate records")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    df = read_jsonl(args.tls_log)
    ranked = hunt_certificates(df)
    cols = ["src_ip", "ssl_issuer", "ssl_cert_sha1", "is_self_signed", "validity_days", "suspicion_score"]
    cols = [c for c in cols if c in ranked.columns]
    print(ranked[cols].head(args.top).to_string(index=False))


if __name__ == "__main__":
    main()

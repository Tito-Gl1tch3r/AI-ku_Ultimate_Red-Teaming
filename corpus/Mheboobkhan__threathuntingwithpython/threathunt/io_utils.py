"""Shared loaders for the log/flow formats the rest of threathunt works with."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def read_jsonl(path: str | Path) -> pd.DataFrame:
    """Load a newline-delimited JSON file into a flat DataFrame.

    Handles Zeek-style dotted keys (``id.orig_h``) by normalizing nested
    dicts, so callers don't have to special-case flow records vs. plain JSON.
    """
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    if not records:
        return pd.DataFrame()
    return pd.json_normalize(records)


def read_zeek_json(path: str | Path) -> pd.DataFrame:
    """Alias for read_jsonl kept for readability at call sites that load Zeek logs."""
    return read_jsonl(path)


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(path, **kwargs)

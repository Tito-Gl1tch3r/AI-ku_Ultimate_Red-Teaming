"""Classify HTTP requests into a threat category (c2 / malware / pua / rmm).

Rewrite of C2_detection_using_random_forest/C2_prediction.py, which trained
a RandomForestClassifier against a hardcoded /home/wh/... http.csv of
unknown, undocumented provenance with an unexplained "Satus" label column.
This version builds real, labeled features from Suricata HTTP telemetry
(threathunt/../data/samples/suricata_http_useragents.jsonl, sourced from
real C2/malware/PUA/RMM traffic captures) and trains a multi-class
classifier over those categories.

Caveat, stated up front rather than hidden: the bundled sample has ~50 rows
across four *malicious* categories and no clean benign baseline, so this is
a small illustrative model, not a production detector. Point it at a larger
labeled dataset (same feature extractor, any source) for real use.
"""
from __future__ import annotations

import argparse

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from threathunt.dns_hunt import shannon_entropy
from threathunt.io_utils import read_jsonl

FEATURE_COLUMNS = [
    "ua_length", "ua_entropy", "url_length", "url_entropy",
    "has_query_string", "is_post", "status",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw Suricata HTTP rows into a numeric feature table."""
    ua = df["http_user_agent"].fillna("")
    url = df["url"].fillna("")
    features = pd.DataFrame({
        "ua_length": ua.str.len(),
        "ua_entropy": ua.apply(shannon_entropy),
        "url_length": url.str.len(),
        "url_entropy": url.apply(shannon_entropy),
        "has_query_string": url.str.contains(r"\?", regex=True).astype(int),
        "is_post": df["http_method"].fillna("").str.upper().eq("POST").astype(int),
        "status": pd.to_numeric(df.get("status"), errors="coerce").fillna(0),
    })
    return features


def train(df: pd.DataFrame, test_size: float = 0.3, random_state: int = 0):
    """Train a RandomForest over build_features(df) vs. the 'label' column.

    Returns (model, X_test, y_test, report_str). Falls back to an
    unstratified split when a class is too small to stratify on.
    """
    X = build_features(df)
    y = df["label"]

    class_counts = y.value_counts()
    stratify = y if class_counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    model = RandomForestClassifier(n_estimators=200, random_state=random_state)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    report = classification_report(y_test, y_pred, zero_division=0)
    return model, X_test, y_test, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", help="labeled Suricata HTTP JSONL file")
    parser.add_argument("--test-size", type=float, default=0.3)
    args = parser.parse_args()

    df = read_jsonl(args.data)
    model, X_test, y_test, report = train(df, test_size=args.test_size)

    print(f"trained on {len(df)} rows, classes: {dict(df['label'].value_counts())}\n")
    print(report)
    print("confusion matrix (rows=true, cols=predicted):")
    labels = sorted(df["label"].unique())
    y_pred = model.predict(X_test)
    print(pd.DataFrame(confusion_matrix(y_test, y_pred, labels=labels), index=labels, columns=labels))


if __name__ == "__main__":
    main()

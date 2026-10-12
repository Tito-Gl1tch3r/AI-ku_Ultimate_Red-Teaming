import pandas as pd

from threathunt.exfil import aggregate_transfers, score_transfers


def _conn_rows(orig_h, resp_h, resp_p, orig_bytes_list):
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    return [
        {
            "ts": base + pd.Timedelta(seconds=i),
            "id.orig_h": orig_h,
            "id.resp_h": resp_h,
            "id.resp_p": resp_p,
            "orig_bytes": b,
            "resp_bytes": 10,
        }
        for i, b in enumerate(orig_bytes_list)
    ]


def _typical_and_outlier_dataset():
    rows = []
    # ten "normal" pairs moving a few KB each
    for i in range(10):
        rows += _conn_rows("10.0.0.5", f"203.0.113.{i}", 443, [2000, 2100, 1900])
    # one pair moving orders of magnitude more data
    rows += _conn_rows("10.0.0.5", "203.0.113.99", 443, [50_000_000])
    return pd.DataFrame(rows)


def test_aggregate_transfers_sums_bytes_per_pair():
    df = pd.DataFrame(_conn_rows("10.0.0.5", "203.0.113.9", 443, [100, 200, 300]))
    agg = aggregate_transfers(df)
    assert len(agg) == 1
    assert agg.iloc[0]["total_orig_bytes"] == 600
    assert agg.iloc[0]["connection_count"] == 3


def test_large_outbound_transfer_is_flagged_as_an_outlier():
    df = _typical_and_outlier_dataset()
    scored = score_transfers(df, threshold=3.5)

    top = scored.iloc[0]
    assert top["id.resp_h"] == "203.0.113.99"
    assert top["is_outlier"]

    outliers = scored[scored["is_outlier"]]
    assert len(outliers) == 1


def test_uniform_traffic_has_no_outliers():
    rows = []
    for i in range(10):
        rows += _conn_rows("10.0.0.5", f"203.0.113.{i}", 443, [2000, 2100, 1900])
    df = pd.DataFrame(rows)
    scored = score_transfers(df, threshold=3.5)
    assert not scored["is_outlier"].any()

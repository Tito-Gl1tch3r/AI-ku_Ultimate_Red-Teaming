import pandas as pd

from threathunt.beaconing import candidate_beacons, score_beacons


def _conn_rows(orig_h, resp_h, resp_p, timestamps):
    return [
        {
            "ts": ts,
            "id.orig_h": orig_h,
            "id.resp_h": resp_h,
            "id.resp_p": resp_p,
            "orig_bytes": 100,
            "resp_bytes": 50,
        }
        for ts in timestamps
    ]


def test_regular_interval_traffic_scores_as_a_beacon():
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    timestamps = [base + pd.Timedelta(seconds=60 * i) for i in range(10)]
    df = pd.DataFrame(_conn_rows("10.0.0.5", "203.0.113.9", 443, timestamps))

    scored = score_beacons(df, min_observations=4)
    assert len(scored) == 1
    row = scored.iloc[0]
    assert row["jitter_pct"] < 5
    assert row["connection_count"] == 10

    candidates = candidate_beacons(scored, jitter_threshold_pct=30.0)
    assert len(candidates) == 1


def test_irregular_traffic_is_not_flagged_as_a_beacon():
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    offsets = [0, 3, 47, 51, 240, 241, 900, 1500, 1501, 1502]
    timestamps = [base + pd.Timedelta(seconds=s) for s in offsets]
    df = pd.DataFrame(_conn_rows("10.0.0.5", "203.0.113.9", 443, timestamps))

    scored = score_beacons(df, min_observations=4)
    assert len(scored) == 1
    assert scored.iloc[0]["jitter_pct"] > 30

    candidates = candidate_beacons(scored, jitter_threshold_pct=30.0)
    assert len(candidates) == 0


def test_pairs_below_min_observations_are_dropped():
    base = pd.Timestamp("2024-01-01T00:00:00Z")
    timestamps = [base, base + pd.Timedelta(seconds=60)]
    df = pd.DataFrame(_conn_rows("10.0.0.5", "203.0.113.9", 443, timestamps))

    scored = score_beacons(df, min_observations=4)
    assert scored.empty

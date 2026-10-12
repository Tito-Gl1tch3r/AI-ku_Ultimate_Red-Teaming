import pandas as pd

from threathunt.dns_hunt import hunt, shannon_entropy


def test_shannon_entropy_is_zero_for_a_single_repeated_character():
    assert shannon_entropy("aaaaaaaa") == 0.0


def test_shannon_entropy_is_higher_for_random_looking_text():
    assert shannon_entropy("DC011UWhRCAAAAAAAAAAAAAAAAAAAAAAAAAAAAwbEAYBAAAA") > shannon_entropy("google")


def test_long_high_entropy_query_outranks_a_benign_lookup():
    df = pd.DataFrame({
        "query_name": [
            "google.com",
            "DC011UWhRCAAAAAAAAAAAAAAAAAAAAAAAAAAAAwbEAYBAAAA.attackrange.local",
        ],
    })
    ranked = hunt(df)
    assert ranked.iloc[0]["query_name"].startswith("DC011UWhRC")
    assert ranked.iloc[0]["suspicion_score"] > ranked.iloc[1]["suspicion_score"]


def test_suspicious_category_flag_is_detected():
    df = pd.DataFrame({
        "domain": ["www.proxysite.com.", "www.example.com."],
        "categories": ["Proxy/Anonymizer,Application,Filter Avoidance", "Business"],
    })
    ranked = hunt(df)
    assert ranked.iloc[0]["domain"] == "www.proxysite.com."
    assert bool(ranked.iloc[0]["suspicious_category"]) is True


def test_raises_when_no_query_column_is_found():
    df = pd.DataFrame({"unrelated": [1, 2, 3]})
    try:
        hunt(df)
        assert False, "expected KeyError"
    except KeyError:
        pass

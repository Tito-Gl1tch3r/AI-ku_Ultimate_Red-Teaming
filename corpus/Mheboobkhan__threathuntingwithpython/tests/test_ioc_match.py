import pandas as pd

from threathunt.ioc_match import scan_text


def _watchlist():
    return pd.DataFrame([
        {"ioc_type": "ip", "value": "34.218.235.219", "description": "C2 beacon"},
        {"ioc_type": "domain", "value": "footprintdns.com", "description": "DNS tunneling"},
        {"ioc_type": "md5", "value": "8E024A4C90F17F1AEDC7FC53D5CA23C6", "description": "nxc.exe"},
    ])


def test_finds_a_matching_ip_in_raw_text():
    text = 'conn from 10.0.1.14 to 34.218.235.219 port 443'
    hits = scan_text(text, _watchlist())
    assert len(hits) == 1
    assert hits.iloc[0]["ioc_type"] == "ip"


def test_domain_match_is_case_insensitive():
    text = "query for abc.AZR.FootprintDNS.com seen"
    hits = scan_text(text, _watchlist())
    assert len(hits) == 1
    assert hits.iloc[0]["ioc_type"] == "domain"


def test_hash_match_is_case_insensitive():
    text = "MD5=8e024a4c90f17f1aedc7fc53d5ca23c6 seen in process log"
    hits = scan_text(text, _watchlist())
    assert len(hits) == 1
    assert hits.iloc[0]["ioc_type"] == "md5"


def test_counts_multiple_occurrences():
    text = "34.218.235.219 34.218.235.219 34.218.235.219"
    hits = scan_text(text, _watchlist())
    assert hits.iloc[0]["hit_count"] == 3


def test_no_matches_returns_empty_dataframe():
    hits = scan_text("nothing interesting here", _watchlist())
    assert hits.empty

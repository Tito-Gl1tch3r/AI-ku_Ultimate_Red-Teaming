import pandas as pd

from threathunt.tls_hunt import hunt_certificates


def _dataset():
    return pd.DataFrame([
        {
            "src_ip": "10.0.1.14",
            "ssl_issuer": "C = , ST = , L = , O = , OU = , CN = ",
            "ssl_subject": "C = , ST = , L = , O = , OU = , CN = ",
            "ssl_cert_sha1": "6ECE5ECE4192683D2D84E25B0BA7E04F9CB7EB7C",
            "ssl_cert_self_signed": 1,
            "ssl_validity_start": "May 20 18:26:24 2015 GMT",
            "ssl_validity_end": "May 17 18:26:24 2025 GMT",
        },
        {
            "src_ip": "10.0.1.18",
            "ssl_issuer": "C = US, O = DigiCert Inc, CN = DigiCert SHA2 Secure Server CA",
            "ssl_subject": "CN = www.example.com",
            "ssl_cert_sha1": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
            "ssl_cert_self_signed": 0,
            "ssl_validity_start": "Jan  1 00:00:00 2024 GMT",
            "ssl_validity_end": "Jan  1 00:00:00 2025 GMT",
        },
    ])


def test_self_signed_blank_cert_outranks_a_ca_issued_cert():
    ranked = hunt_certificates(_dataset())
    assert ranked.iloc[0]["src_ip"] == "10.0.1.14"
    assert ranked.iloc[0]["suspicion_score"] > ranked.iloc[1]["suspicion_score"]


def test_validity_days_is_computed_correctly():
    ranked = hunt_certificates(_dataset())
    ca_row = ranked[ranked["src_ip"] == "10.0.1.18"].iloc[0]
    assert ca_row["validity_days"] == 366  # 2024 is a leap year


def test_long_validity_flag_set_for_the_ten_year_cert():
    ranked = hunt_certificates(_dataset())
    self_signed_row = ranked[ranked["src_ip"] == "10.0.1.14"].iloc[0]
    assert self_signed_row["is_long_validity"]


def test_missing_optional_columns_do_not_raise():
    df = pd.DataFrame({"src_ip": ["10.0.0.1"]})
    ranked = hunt_certificates(df)
    assert len(ranked) == 1
    assert ranked.iloc[0]["suspicion_score"] == 0

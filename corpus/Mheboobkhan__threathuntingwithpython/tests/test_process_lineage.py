import pandas as pd

from threathunt.process_lineage import stack_count


def _dataset():
    common = [
        {"parent_image": r"C:\Windows\System32\services.exe", "image": r"C:\Windows\System32\svchost.exe"}
        for _ in range(20)
    ]
    rare = [{
        "parent_image": r"C:\Windows\System32\winword.exe",
        "image": r"C:\Windows\System32\rundll32.exe",
    }]
    return pd.DataFrame(common + rare)


def test_rare_pair_is_ranked_first():
    counts = stack_count(_dataset())
    top = counts.iloc[0]
    assert top["image"].lower().endswith("rundll32.exe")
    assert top["count"] == 1


def test_common_pair_has_a_higher_count():
    counts = stack_count(_dataset())
    common_row = counts[counts["image"].str.lower().str.endswith("svchost.exe")].iloc[0]
    assert common_row["count"] == 20


def test_lolbas_flag_is_set_for_known_binaries():
    counts = stack_count(_dataset())
    rundll32_row = counts[counts["image"].str.lower().str.endswith("rundll32.exe")].iloc[0]
    svchost_row = counts[counts["image"].str.lower().str.endswith("svchost.exe")].iloc[0]
    assert rundll32_row["is_lolbas"]
    assert not svchost_row["is_lolbas"]


def test_raises_on_missing_columns():
    df = pd.DataFrame({"unrelated": [1, 2]})
    try:
        stack_count(df)
        assert False, "expected KeyError"
    except KeyError:
        pass

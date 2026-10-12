from threathunt.hashes import extract


def test_extracts_valid_hex_hashes_by_length():
    text = (
        "md5=8E024A4C90F17F1AEDC7FC53D5CA23C6 "
        "sha1=B35EAC197F2556DB1F4DFB6FDE59EC107BD57A00 "
        "sha256=8C378F6200EEC750ED66BDE1E54C29B7BD172E503A5874CA2EEAD4705DD7B515"
    )
    found = extract(text)
    assert found["md5"] == ["8E024A4C90F17F1AEDC7FC53D5CA23C6"]
    assert found["sha1"] == ["B35EAC197F2556DB1F4DFB6FDE59EC107BD57A00"]
    assert found["sha256"] == ["8C378F6200EEC750ED66BDE1E54C29B7BD172E503A5874CA2EEAD4705DD7B515"]


def test_ignores_non_hex_tokens_of_matching_length():
    # 32 alphabetic characters, but not hex -> the old length-only check
    # would have misclassified this as an MD5.
    text = "ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ this-is-just-a-guid-like-word"
    found = extract(text)
    assert found["md5"] == []


def test_deduplicates_within_a_bucket():
    text = "8E024A4C90F17F1AEDC7FC53D5CA23C6 8E024A4C90F17F1AEDC7FC53D5CA23C6"
    found = extract(text)
    assert found["md5"] == ["8E024A4C90F17F1AEDC7FC53D5CA23C6"]


def test_longest_hex_run_is_not_double_counted_as_a_shorter_hash():
    sha256 = "8C378F6200EEC750ED66BDE1E54C29B7BD172E503A5874CA2EEAD4705DD7B515"
    found = extract(sha256)
    assert found["sha256"] == [sha256]
    assert found["md5"] == []

import numpy as np

from threathunt.text_similarity import cluster, similarity_matrix


TEXTS = [
    "powershell -EncodedCommand JgBjAGgAYwBwAC4AYwBvAG0AIAA2ADUAMAAwADEA",
    "powershell -EncodedCommand JgBjAGgAYwBwAC4AYwBvAG0AIAA2ADUAMAAwADIA",
    "cmd.exe /C whoami /all",
]


def test_similarity_matrix_is_symmetric():
    sim = similarity_matrix(TEXTS)
    assert np.allclose(sim, sim.T)


def test_self_similarity_is_approximately_one():
    sim = similarity_matrix(TEXTS)
    assert np.allclose(np.diag(sim), 1.0, atol=1e-6)


def test_near_identical_lines_are_more_similar_than_unrelated_ones():
    sim = similarity_matrix(TEXTS)
    # the two near-identical encoded PowerShell commands (differ by one
    # trailing token) must score higher than either does against the
    # unrelated cmd.exe line - this is exactly the comparison the original
    # PowerShell script's l1/l2 norm bug got backwards.
    assert sim[0, 1] > sim[0, 2]
    assert sim[0, 1] > sim[1, 2]


def test_cluster_groups_near_duplicates_together():
    groups = cluster(TEXTS, threshold=0.8)
    biggest = max(groups, key=len)
    assert set(biggest) == {0, 1}


def test_similarity_matrix_handles_a_single_text():
    sim = similarity_matrix(["only one line"])
    assert sim.shape == (1, 1)
    assert sim[0, 0] == 1.0

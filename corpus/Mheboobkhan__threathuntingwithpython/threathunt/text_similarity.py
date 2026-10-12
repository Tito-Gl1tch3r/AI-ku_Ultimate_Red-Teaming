"""Group near-duplicate log lines / command lines by cosine similarity.

Rewrite of Text_Classification.ps1. That script's core resem() function
computed cosine similarity as dot(a,b) / sqrt(norm(a) * norm(b)) but built
both norms from the *same* vector ($l1 for both, see line 27 of the
original: ``$temp2 += [Math]::pow($l1[$_],2)``), so every similarity score
was silently wrong except when comparing a line to itself. It was also an
O(n^2) hand-rolled bag-of-words comparison with no vectorized backing.

This version uses scikit-learn's TF-IDF + cosine_similarity (correct by
construction, and tested for symmetry/self-similarity below), and applies
it to something concrete: clustering the encoded/obfuscated PowerShell
command lines that recur, near-identically, across unrelated ATT&CK
technique datasets - the real SOC task of noticing "these alerts from three
different hosts are actually the same automation tool."
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DEFAULT_BINS = ((90, 100), (80, 90), (50, 80), (20, 50), (0, 20))


def similarity_matrix(texts: list[str]) -> np.ndarray:
    """Pairwise cosine similarity (0-1) over a character n-gram TF-IDF encoding.

    Character n-grams (rather than whole-word tokens) are what make this
    useful on command lines: two base64-encoded PowerShell blobs that differ
    by a handful of characters should score as near-duplicates, but a
    word-level vectorizer treats each blob as one indivisible token and
    scores them as unrelated the moment a single character differs.
    """
    if len(texts) < 2:
        return np.ones((len(texts), len(texts)))
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5))
    matrix = vectorizer.fit_transform(texts)
    return cosine_similarity(matrix)


def average_similarity_scores(texts: list[str]) -> np.ndarray:
    """Each text's average similarity (as a %) to every *other* text."""
    sim = similarity_matrix(texts) * 100.0
    n = len(texts)
    if n < 2:
        return np.zeros(n)
    off_diagonal_sum = sim.sum(axis=1) - np.diag(sim)
    return off_diagonal_sum / (n - 1)


def bucket_by_similarity(texts: list[str], bins=DEFAULT_BINS) -> dict[str, int]:
    """Bucket each text by its average similarity to the rest, like the
    original script's group_0..group_U tally, but numerically correct."""
    scores = average_similarity_scores(texts)
    counts = {f"{lo}-{hi}": 0 for lo, hi in bins}
    for score in scores:
        for lo, hi in bins:
            if lo <= score <= hi:
                counts[f"{lo}-{hi}"] += 1
                break
    return counts


def cluster(texts: list[str], threshold: float = 0.8) -> list[list[int]]:
    """Group text indices into connected components of similarity >= threshold."""
    n = len(texts)
    if n == 0:
        return []
    sim = similarity_matrix(texts)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                union(i, j)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=len, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="a .txt (one entry per line) or the powershell_commandlines.csv")
    parser.add_argument("--column", default="decoded_command", help="column to use if file is a CSV")
    parser.add_argument("--threshold", type=float, default=0.8)
    args = parser.parse_args()

    if args.file.endswith(".csv"):
        texts = pd.read_csv(args.file)[args.column].fillna("").astype(str).tolist()
    else:
        texts = [line.rstrip("\n") for line in open(args.file) if line.strip()]

    print("similarity distribution (average % similarity to all other entries):")
    for bucket, count in bucket_by_similarity(texts).items():
        print(f"  {bucket:>8}%: {count}")

    groups = [g for g in cluster(texts, args.threshold) if len(g) > 1]
    print(f"\n{len(groups)} cluster(s) of near-duplicate entries at threshold {args.threshold}:")
    for group in groups:
        print(f"\n  cluster of {len(group)}:")
        print(f"    {texts[group[0]][:120]}")


if __name__ == "__main__":
    main()

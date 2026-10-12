"""Grep for a pattern while keeping the N lines of context that preceded it.

Direct port of pattern_over_history.py (the logic was already correct) with
an argparse CLI and a test added.
"""
from __future__ import annotations

import argparse
from collections import deque
from typing import Iterable, Iterator


def search(lines: Iterable[str], pattern: str, history: int = 5) -> Iterator[tuple[str, tuple]]:
    """Yield (matching_line, preceding_lines) for every line containing pattern.

    preceding_lines is a snapshot tuple, not the live deque - yielding the
    deque itself would let later appends silently mutate a result a caller
    is still holding onto (e.g. after ``list(search(...))``).
    """
    previous_lines: deque = deque(maxlen=history)
    for line in lines:
        if pattern in line:
            yield line, tuple(previous_lines)
        previous_lines.append(line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file")
    parser.add_argument("pattern")
    parser.add_argument("--history", type=int, default=5)
    args = parser.parse_args()

    with open(args.file) as f:
        for line, prevlines in search(f, args.pattern, args.history):
            for pline in prevlines:
                print(pline, end="")
            print(line, end="")
            print("-" * 20)


if __name__ == "__main__":
    main()

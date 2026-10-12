"""
Rule-based conflict detection across research sources.

The three kinds of disagreement worth surfacing deterministically:

1. Numeric   — two sources quote different numbers for the same
               referent (price, headcount, year, percentage, version).
               "OpenAI raised $10B" vs "OpenAI raised $6.6B" is the
               canonical case.

2. Date      — two sources disagree on when something happened.
               "Founded in 2015" vs "Founded in 2016".

3. Polarity  — two sources take opposing stances toward the same
               claim ("X is safe" vs "X is unsafe", "Y supports Z" vs
               "Y does not support Z").

All three are extracted with regex + a small set of hand-tuned
heuristics; they're deliberately boring and auditable. Optional
semantic-conflict detection via the client's LLM (`ctx.sample()`) is
a separate concern wired at the tool layer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ConflictType(str, Enum):
    NUMERIC = "numeric"
    DATE = "date"
    POLARITY = "polarity"


@dataclass
class Conflict:
    """One detected disagreement between two sources."""

    type: ConflictType
    topic: str
    source_a_index: int
    source_b_index: int
    value_a: str
    value_b: str
    context_a: str
    context_b: str
    # 0..1 confidence that this is a real conflict (not false positive)
    confidence: float = 0.5

    def as_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "topic": self.topic,
            "source_a_index": self.source_a_index,
            "source_b_index": self.source_b_index,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "context_a": self.context_a,
            "context_b": self.context_b,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class ConflictReport:
    """Aggregate report across all pairs of sources."""

    claim: Optional[str]
    source_count: int
    conflicts: List[Conflict] = field(default_factory=list)
    agreements: List[Dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "claim": self.claim,
            "source_count": self.source_count,
            "conflict_count": len(self.conflicts),
            "conflicts": [c.as_dict() for c in self.conflicts],
            "agreements": self.agreements,
        }


# ---------------------------------------------------------------------------
# Text preprocessing
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Collapse whitespace and strip."""
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def _context_around(text: str, start: int, end: int, radius: int = 60) -> str:
    """Extract a window of `radius` chars on either side of a span."""
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    snippet = text[lo:hi]
    if lo > 0:
        snippet = "…" + snippet
    if hi < len(text):
        snippet = snippet + "…"
    return _normalize(snippet)


# ---------------------------------------------------------------------------
# Numeric extraction
# ---------------------------------------------------------------------------

# Matches things like: $1.2B, 1,200, 45%, 3.14, 2 million, 5.5 kg, 100MB.
# We capture: (value, unit_or_scale)
_NUMBER_RE = re.compile(
    r"""
    (?P<prefix>\$|€|£|¥)?             # optional currency prefix
    (?P<value>\d{1,3}(?:,\d{3})+       # 1,234 style
              |\d+(?:\.\d+)?           # 3.14 / 42
    )
    \s?
    (?P<unit>
        %|percent|pc                  # percent
       |[KkMmBbTt](?![a-zA-Z])        # scale letter not followed by another letter (filter 'Kernel')
       |thousand|million|billion|trillion
       |[gG][bB]|[mM][bB]|[kK][bB]    # storage
       |[gG][hH][zZ]|[mM][hH][zZ]
       |kg|g\b|lb|lbs|oz
       |mph|kph|m/s
       |years?|yrs?|months?|days?|hours?|hrs?
       |people|users|employees|customers
    )?
    """,
    re.VERBOSE,
)


_SCALE_MULTIPLIERS = {
    "k": 1_000,
    "thousand": 1_000,
    "m": 1_000_000,
    "million": 1_000_000,
    "b": 1_000_000_000,
    "billion": 1_000_000_000,
    "t": 1_000_000_000_000,
    "trillion": 1_000_000_000_000,
}


def _parse_number(raw: str, unit: str) -> Optional[float]:
    try:
        v = float(raw.replace(",", ""))
    except ValueError:
        return None
    m = _SCALE_MULTIPLIERS.get((unit or "").lower())
    if m:
        v *= m
    return v


def _unit_class(unit: str) -> str:
    """Coarse unit category so we only compare numbers in the same family."""
    u = (unit or "").lower()
    if u in {"%", "percent", "pc"}:
        return "percent"
    if u in {"k", "m", "b", "t", "thousand", "million", "billion", "trillion"}:
        return "count"
    if u in {"kg", "g", "lb", "lbs", "oz"}:
        return "mass"
    if u in {"gb", "mb", "kb"}:
        return "storage"
    if u in {"ghz", "mhz"}:
        return "frequency"
    if u in {
        "years",
        "year",
        "yrs",
        "yr",
        "months",
        "month",
        "days",
        "day",
        "hours",
        "hour",
        "hrs",
        "hr",
    }:
        return "duration"
    if u in {"people", "users", "employees", "customers"}:
        return "headcount"
    return "bare"


def _extract_numbers(text: str) -> List[Tuple[float, str, str, int, int]]:
    """Return list of (value, unit_class, raw_text, start, end)."""
    out: List[Tuple[float, str, str, int, int]] = []
    for m in _NUMBER_RE.finditer(text):
        raw_val = m.group("value")
        unit = m.group("unit") or ""
        val = _parse_number(raw_val, unit)
        if val is None:
            continue
        out.append((val, _unit_class(unit), m.group(0), m.start(), m.end()))
    return out


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

_MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
_DATE_PATTERNS = [
    (re.compile(rf"({_MONTH})\s+(\d{{1,2}}),?\s+(\d{{4}})", re.IGNORECASE), "MDY"),
    (re.compile(rf"(\d{{1,2}})\s+({_MONTH}),?\s+(\d{{4}})", re.IGNORECASE), "DMY"),
    (re.compile(r"(\d{4})-(\d{2})-(\d{2})"), "ISO"),
    (re.compile(r"\b(19|20)\d{2}\b"), "YEAR"),
]
_MONTH_IDX = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _extract_dates(text: str) -> List[Tuple[date, str, int, int, str]]:
    """Return list of (date, raw_text, start, end, precision).

    precision is one of: "full" (year+month+day), "year" (year only).
    """
    found: List[Tuple[date, str, int, int, str]] = []
    for pattern, kind in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            try:
                if kind == "MDY":
                    mo = _MONTH_IDX.get(m.group(1).lower())
                    day = int(m.group(2))
                    yr = int(m.group(3))
                    if not mo:
                        continue
                    d = date(yr, mo, day)
                    found.append((d, m.group(0), m.start(), m.end(), "full"))
                elif kind == "DMY":
                    day = int(m.group(1))
                    mo = _MONTH_IDX.get(m.group(2).lower())
                    yr = int(m.group(3))
                    if not mo:
                        continue
                    d = date(yr, mo, day)
                    found.append((d, m.group(0), m.start(), m.end(), "full"))
                elif kind == "ISO":
                    d = date.fromisoformat(m.group(0))
                    found.append((d, m.group(0), m.start(), m.end(), "full"))
                elif kind == "YEAR":
                    yr = int(m.group(0))
                    if 1900 <= yr <= 2100:
                        d = date(yr, 1, 1)
                        found.append((d, m.group(0), m.start(), m.end(), "year"))
            except (ValueError, AttributeError):
                continue
    return found


# ---------------------------------------------------------------------------
# Polarity detection
# ---------------------------------------------------------------------------

_NEGATION_TOKENS = {
    "not",
    "no",
    "never",
    "nothing",
    "neither",
    "nor",
    "none",
    "cannot",
    "can't",
    "won't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "doesn't",
    "don't",
    "didn't",
    "hasn't",
    "haven't",
    "hadn't",
    "shouldn't",
    "wouldn't",
}


def _has_negation_near(text: str, center_start: int, center_end: int, radius: int = 30) -> bool:
    lo = max(0, center_start - radius)
    hi = min(len(text), center_end + radius)
    window = text[lo:hi].lower()
    tokens = re.findall(r"\b[a-z']+\b", window)
    return any(t in _NEGATION_TOKENS for t in tokens)


def _claim_polarity(text: str, claim: str) -> Optional[bool]:
    """Return True if `claim` is supported, False if negated, None if absent.

    Strategy:
      1. Exact-substring match of the full claim -> supported unless a
         negation token sits within 30 chars on either side.
      2. Otherwise, split the claim into subject + tail on the first
         content word past "is/are/was/were/has/have". If the subject
         phrase appears followed by a tail word within ~40 chars AND a
         negation token sits between them, treat that as an opposing
         stance ("the vaccine is not safe" opposes "the vaccine is safe").
    """
    if not claim:
        return None
    text_lc = text.lower()
    claim_lc = claim.lower().strip()

    # Strategy 1: direct substring
    idx = text_lc.find(claim_lc)
    if idx != -1:
        return not _has_negation_near(text_lc, idx, idx + len(claim_lc))

    # Strategy 2: subject + predicate-tail, allowing inserted negation
    parts = re.split(r"\b(is|are|was|were|has|have|do|does|did)\b", claim_lc, maxsplit=1)
    if len(parts) < 3:
        return None
    subject = parts[0].strip()
    copula = parts[1]
    tail = parts[2].strip()
    # Find the subject in the source
    sub_idx = text_lc.find(subject)
    if sub_idx == -1:
        return None
    # Look for the first occurrence of the tail within ~60 chars after the copula
    window_start = sub_idx + len(subject)
    window = text_lc[window_start : window_start + 150]
    if copula not in window:
        return None
    copula_idx = window.find(copula) + window_start
    tail_in_window = text_lc[copula_idx : copula_idx + 100]
    tail_first_word = (tail.split() or [""])[0]
    if not tail_first_word or tail_first_word not in tail_in_window:
        return None
    tail_idx = tail_in_window.find(tail_first_word) + copula_idx
    # Negation between copula and tail => opposing stance.
    between = text_lc[copula_idx:tail_idx]
    if any(tok in between for tok in _NEGATION_TOKENS):
        return False
    return True


# ---------------------------------------------------------------------------
# Numeric conflict detection across sources
# ---------------------------------------------------------------------------

# Words that are almost always topical anchors when they appear near a number.
_TOPIC_WORDS_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")
_STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "about",
    "which",
    "than",
    "over",
    "under",
    "between",
    "been",
    "have",
    "their",
    "there",
    "these",
    "those",
    "each",
    "some",
    "more",
    "most",
    "least",
}


def _topic_signature(text: str, start: int, end: int, radius: int = 50) -> set:
    """Tokens near a number that act as a fuzzy 'topic' key."""
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    window = text[lo:hi]
    tokens = _TOPIC_WORDS_RE.findall(window.lower())
    return {t for t in tokens if len(t) > 3 and t not in _STOP}


def _relative_diff(a: float, b: float) -> float:
    """0 when equal, 1 when completely different."""
    if a == 0 and b == 0:
        return 0.0
    return abs(a - b) / max(abs(a), abs(b), 1e-9)


def _find_numeric_conflicts(sources: List[str]) -> List[Conflict]:
    extracted = [_extract_numbers(s) for s in sources]
    conflicts: List[Conflict] = []

    for i, nums_i in enumerate(extracted):
        for j in range(i + 1, len(sources)):
            nums_j = extracted[j]
            for val_i, cls_i, raw_i, s_i, e_i in nums_i:
                sig_i = _topic_signature(sources[i], s_i, e_i)
                if not sig_i:
                    continue
                for val_j, cls_j, raw_j, s_j, e_j in nums_j:
                    if cls_i != cls_j:
                        continue
                    if _relative_diff(val_i, val_j) < 0.05:
                        continue  # essentially agrees
                    sig_j = _topic_signature(sources[j], s_j, e_j)
                    if not sig_j:
                        continue
                    overlap = sig_i & sig_j
                    if len(overlap) < 2:
                        continue  # not actually about the same thing
                    # Confidence scales with signature overlap + unit match.
                    conf = min(1.0, 0.5 + 0.1 * len(overlap))
                    conflicts.append(
                        Conflict(
                            type=ConflictType.NUMERIC,
                            topic=" ".join(sorted(overlap)[:5]),
                            source_a_index=i,
                            source_b_index=j,
                            value_a=raw_i,
                            value_b=raw_j,
                            context_a=_context_around(sources[i], s_i, e_i),
                            context_b=_context_around(sources[j], s_j, e_j),
                            confidence=conf,
                        )
                    )
    return conflicts


# ---------------------------------------------------------------------------
# Date conflict detection
# ---------------------------------------------------------------------------


def _find_date_conflicts(sources: List[str]) -> List[Conflict]:
    extracted = [_extract_dates(s) for s in sources]
    conflicts: List[Conflict] = []

    for i, dates_i in enumerate(extracted):
        for j in range(i + 1, len(sources)):
            dates_j = extracted[j]
            for d_i, raw_i, s_i, e_i, prec_i in dates_i:
                sig_i = _topic_signature(sources[i], s_i, e_i)
                if not sig_i:
                    continue
                for d_j, raw_j, s_j, e_j, prec_j in dates_j:
                    # Only compare at the shared precision.
                    if prec_i == "year" or prec_j == "year":
                        if d_i.year == d_j.year:
                            continue
                    else:
                        if d_i == d_j:
                            continue
                    sig_j = _topic_signature(sources[j], s_j, e_j)
                    if not sig_j:
                        continue
                    overlap = sig_i & sig_j
                    if len(overlap) < 2:
                        continue
                    conflicts.append(
                        Conflict(
                            type=ConflictType.DATE,
                            topic=" ".join(sorted(overlap)[:5]),
                            source_a_index=i,
                            source_b_index=j,
                            value_a=raw_i,
                            value_b=raw_j,
                            context_a=_context_around(sources[i], s_i, e_i),
                            context_b=_context_around(sources[j], s_j, e_j),
                            confidence=min(1.0, 0.5 + 0.1 * len(overlap)),
                        )
                    )
    return conflicts


# ---------------------------------------------------------------------------
# Polarity conflict detection (requires a specific claim)
# ---------------------------------------------------------------------------


def _find_polarity_conflicts(sources: List[str], claim: str) -> List[Conflict]:
    polarities: List[Tuple[int, bool]] = []
    for i, src in enumerate(sources):
        p = _claim_polarity(src, claim)
        if p is not None:
            polarities.append((i, p))

    conflicts: List[Conflict] = []
    for a, (i, pi) in enumerate(polarities):
        for j, pj in polarities[a + 1 :]:
            if pi != pj:
                conflicts.append(
                    Conflict(
                        type=ConflictType.POLARITY,
                        topic=claim,
                        source_a_index=i,
                        source_b_index=j,
                        value_a="supports" if pi else "contradicts",
                        value_b="supports" if pj else "contradicts",
                        context_a=_snippet_around_claim(sources[i], claim),
                        context_b=_snippet_around_claim(sources[j], claim),
                        confidence=0.7,
                    )
                )
    return conflicts


def _snippet_around_claim(text: str, claim: str) -> str:
    idx = text.lower().find(claim.lower())
    if idx == -1:
        return ""
    return _context_around(text, idx, idx + len(claim))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def find_conflicts(
    sources: List[str],
    claim: Optional[str] = None,
) -> ConflictReport:
    """Run every rule-based detector across a list of source snippets."""
    sources = [_normalize(s) for s in sources]
    conflicts: List[Conflict] = []
    conflicts.extend(_find_numeric_conflicts(sources))
    conflicts.extend(_find_date_conflicts(sources))
    if claim:
        conflicts.extend(_find_polarity_conflicts(sources, claim))

    # Surface pairwise agreements when a claim was given -- useful signal
    # that sources concur rather than just that they don't disagree.
    agreements: List[Dict[str, Any]] = []
    if claim:
        support_positions = [(i, _claim_polarity(s, claim)) for i, s in enumerate(sources)]
        supporters = [i for i, p in support_positions if p is True]
        opponents = [i for i, p in support_positions if p is False]
        if len(supporters) >= 2:
            agreements.append({"type": "supports_claim", "sources": supporters, "claim": claim})
        if len(opponents) >= 2:
            agreements.append({"type": "opposes_claim", "sources": opponents, "claim": claim})

    return ConflictReport(
        claim=claim,
        source_count=len(sources),
        conflicts=conflicts,
        agreements=agreements,
    )

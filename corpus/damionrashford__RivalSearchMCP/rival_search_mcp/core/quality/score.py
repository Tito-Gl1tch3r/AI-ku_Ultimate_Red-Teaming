"""
Per-URL source-quality scoring.

Four composable signals, combined into a single 0-100 score plus a
coarse tier label that's easy for downstream agents/humans to act on:

  domain_tier   "primary" (gov, edu, standards bodies), "reference"
                (Wikipedia, MDN, RFCs, OA preprint servers), "news"
                (established outlets), "community" (SO, HN, Reddit,
                Lobste.rs), "vendor" (company blogs), "aggregator"
                (listicles, SEO farms), "unknown"

  freshness     How recent the page is, from any of: provided
                `published` / `last_modified` field, ISO-date in the
                result metadata, or None.

  corroboration How many *other independent domains* in the same
                result set point to the same fact (based on
                title/url overlap and shared DOIs).

  citations     Normalized citation count for academic sources,
                social score (HN points, Reddit upvotes) for
                community sources.

Each signal contributes to the final score with weights tuned for
research workflows (primary > corroborated > fresh > cited). The
tier is the single most useful one-line summary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set
from urllib.parse import urlparse


class DomainTier(str, Enum):
    """Coarse trust tier. Ordered roughly by default weight."""

    PRIMARY = "primary"
    REFERENCE = "reference"
    ACADEMIC = "academic"
    NEWS = "news"
    COMMUNITY = "community"
    VENDOR = "vendor"
    AGGREGATOR = "aggregator"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Domain classification
# ---------------------------------------------------------------------------

# Suffix match on the registered domain (not the FQDN). Kept small and hand-
# curated -- sprawling allowlists go stale fast.
_PRIMARY_SUFFIXES = (
    ".gov",
    ".gov.uk",
    ".europa.eu",
    ".who.int",
    ".un.org",
    ".nist.gov",
    ".nih.gov",
    ".cdc.gov",
    ".ec.europa.eu",
    ".bls.gov",
    ".fda.gov",
    ".sec.gov",
    ".nasa.gov",
)
_ACADEMIC_SUFFIXES = (".edu", ".ac.uk", ".ac.jp", ".edu.au")

_REFERENCE_DOMAINS: Set[str] = {
    "wikipedia.org",
    "developer.mozilla.org",
    "docs.python.org",
    "rfc-editor.org",
    "w3.org",
    "ietf.org",
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "openalex.org",
    "doi.org",
    "europepmc.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "crossref.org",
    "semanticscholar.org",
    "zenodo.org",
    "dataverse.harvard.edu",
}
_NEWS_DOMAINS: Set[str] = {
    "nytimes.com",
    "washingtonpost.com",
    "theguardian.com",
    "bbc.com",
    "bbc.co.uk",
    "reuters.com",
    "apnews.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "economist.com",
    "nature.com",
    "science.org",
    "sciencemag.org",
    "arstechnica.com",
    "wired.com",
    "theverge.com",
    "techcrunch.com",
    "forbes.com",
    "cnbc.com",
    "npr.org",
    "propublica.org",
}
_COMMUNITY_DOMAINS: Set[str] = {
    "stackoverflow.com",
    "serverfault.com",
    "superuser.com",
    "askubuntu.com",
    "news.ycombinator.com",
    "reddit.com",
    "old.reddit.com",
    "lobste.rs",
    "dev.to",
    "medium.com",
    "bsky.app",
    "lemmy.world",
    "lemmy.ml",
    "stackexchange.com",
    "hackaday.com",
}

# Classic content-farm / SEO-only domains we down-weight. Only obvious
# cases -- being in this list costs points, so we keep it conservative.
_AGGREGATOR_DOMAINS: Set[str] = {
    "pinterest.com",
    "quora.com",
    "buzzfeed.com",
    "dailymail.co.uk",
    "tomsguide.com",
    "makeuseof.com",
    "howtogeek.com",
    "lifewire.com",
    "yourstory.com",
    "medium.freecodecamp.org",
}


def _registered_domain(host: str) -> str:
    """Best-effort 'eTLD+1' without dragging in `tldextract`.

    Handles the common cases we care about: two-label ccTLDs (.co.uk,
    .com.au, .ac.uk) and generic TLDs. Falls back to last two labels.
    """
    host = (host or "").lower().strip()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Known three-label ccTLD patterns
    if parts[-2] in {"co", "ac", "com", "org", "gov", "net", "edu"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def classify_domain(url: str) -> DomainTier:
    """Return the tier for the registered domain of `url`."""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return DomainTier.UNKNOWN
    if not host:
        return DomainTier.UNKNOWN

    host = host.lower()
    reg = _registered_domain(host)

    # Suffix checks (government / academic)
    for suf in _PRIMARY_SUFFIXES:
        if host.endswith(suf):
            return DomainTier.PRIMARY
    for suf in _ACADEMIC_SUFFIXES:
        if host.endswith(suf):
            return DomainTier.ACADEMIC

    # Exact / registered-domain membership
    if reg in _REFERENCE_DOMAINS or host in _REFERENCE_DOMAINS:
        return DomainTier.REFERENCE
    if reg in _NEWS_DOMAINS or host in _NEWS_DOMAINS:
        return DomainTier.NEWS
    if reg in _COMMUNITY_DOMAINS or host in _COMMUNITY_DOMAINS:
        return DomainTier.COMMUNITY
    if reg in _AGGREGATOR_DOMAINS or host in _AGGREGATOR_DOMAINS:
        return DomainTier.AGGREGATOR

    # Vendor heuristic: subdomain contains "blog" or "docs", or domain
    # is a .com whose host starts with something product-like. Left as
    # UNKNOWN for now to avoid false positives.
    return DomainTier.UNKNOWN


# ---------------------------------------------------------------------------
# Freshness
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_YEAR_RE = re.compile(r"(19|20)\d{2}")


def _parse_date(value: Any) -> Optional[datetime]:
    """Best-effort: ISO string -> datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        # epoch seconds or years
        try:
            if value > 1e9:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            if 1900 < value < 2200:
                return datetime(int(value), 1, 1, tzinfo=timezone.utc)
        except (ValueError, OSError):
            return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    m = _ISO_RE.search(s)
    if m:
        try:
            return datetime.fromisoformat(m.group(0) + "T00:00:00+00:00")
        except ValueError:
            pass
    y = _YEAR_RE.search(s)
    if y:
        try:
            return datetime(int(y.group(0)), 1, 1, tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def _freshness_score(published: Optional[datetime]) -> Optional[float]:
    """Return 0..1, or None if we can't tell. Linear decay over ~2 years."""
    if published is None:
        return None
    now = datetime.now(tz=timezone.utc)
    days = max(0, (now - published).days)
    # Full credit for <90 days, decays linearly to 0 over 2 years.
    if days <= 90:
        return 1.0
    if days >= 730:
        return 0.1
    return max(0.1, 1.0 - (days - 90) / (730 - 90))


# ---------------------------------------------------------------------------
# Citation / popularity normalization
# ---------------------------------------------------------------------------


def _citation_score(result: Dict[str, Any]) -> Optional[float]:
    """Normalize citation/score signals to 0..1, or None."""
    # Academic
    for k in ("citationCount", "citation_count", "cited_by_count", "is-referenced-by-count"):
        v = result.get(k)
        if isinstance(v, (int, float)) and v >= 0:
            # log-scaled: 0 -> 0, 10 -> 0.3, 100 -> 0.5, 1000 -> 0.7, 10000 -> 0.9
            import math

            return min(0.95, math.log10(max(1.0, float(v))) / 4.4)
    # Social
    for k in ("score", "points", "upvotes", "public_reactions_count", "like_count"):
        v = result.get(k)
        if isinstance(v, (int, float)) and v >= 0:
            import math

            return min(0.8, math.log10(max(1.0, float(v))) / 3.5)
    return None


# ---------------------------------------------------------------------------
# Corroboration across a result set
# ---------------------------------------------------------------------------

_TITLE_STOP = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "is", "are"}


def _title_tokens(title: str) -> Set[str]:
    toks = re.findall(r"[a-z0-9]{4,}", (title or "").lower())
    return {t for t in toks if t not in _TITLE_STOP}


def _corroboration_map(results: List[Dict[str, Any]]) -> Dict[int, int]:
    """For each result index, count *independent other domains* that
    overlap ≥50% on title tokens or share a DOI. Returns a dict of
    index -> unique-corroborating-domain-count."""
    tokens = [_title_tokens(r.get("title", "")) for r in results]
    domains = [_registered_domain((urlparse(r.get("url", "")).hostname or "")) for r in results]
    dois = [(r.get("doi") or "").lower().strip() for r in results]

    out: Dict[int, int] = {}
    for i, tok_i in enumerate(tokens):
        supporting: Set[str] = set()
        for j, tok_j in enumerate(tokens):
            if i == j:
                continue
            if domains[i] and domains[j] == domains[i]:
                continue  # same domain doesn't count as independent
            if dois[i] and dois[i] == dois[j]:
                supporting.add(domains[j])
                continue
            if tok_i and tok_j:
                overlap = len(tok_i & tok_j) / max(1, min(len(tok_i), len(tok_j)))
                if overlap >= 0.5:
                    supporting.add(domains[j])
        out[i] = len(supporting)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class QualityScore:
    """A transparent 0-100 score with the four contributing signals."""

    score: int
    tier: DomainTier
    signals: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "tier": self.tier.value,
            "signals": self.signals,
        }


_TIER_BASE = {
    DomainTier.PRIMARY: 80,
    DomainTier.REFERENCE: 75,
    DomainTier.ACADEMIC: 75,
    DomainTier.NEWS: 60,
    DomainTier.COMMUNITY: 50,
    DomainTier.VENDOR: 45,
    DomainTier.UNKNOWN: 40,
    DomainTier.AGGREGATOR: 25,
}


def score_url(
    url: str,
    result: Optional[Dict[str, Any]] = None,
    *,
    corroboration: int = 0,
) -> QualityScore:
    """Score a single URL with optional metadata and corroboration count."""
    result = result or {}
    tier = classify_domain(url)
    base = _TIER_BASE.get(tier, 40)

    published = _parse_date(
        result.get("published")
        or result.get("published_at")
        or result.get("publication_date")
        or result.get("date")
        or result.get("year")
    )
    fresh = _freshness_score(published)
    cites = _citation_score(result)

    # Composite: tier base (0-80), freshness (+/-10), citations (+/-8),
    # corroboration (+/-12). Clamped to [0, 100].
    score = float(base)
    if fresh is not None:
        score += (fresh - 0.5) * 20  # fresh=1.0 -> +10, fresh=0.0 -> -10
    if cites is not None:
        score += cites * 16 - 4  # cites=0 -> -4, cites=0.5 -> +4, cites=1 -> +12
    score += min(corroboration, 4) * 3  # cap at +12 for 4+ corroborating domains

    score = int(max(0, min(100, round(score))))

    return QualityScore(
        score=score,
        tier=tier,
        signals={
            "freshness": round(fresh, 2) if fresh is not None else None,
            "citations": round(cites, 2) if cites is not None else None,
            "corroboration": corroboration,
            "published": published.isoformat() if published else None,
        },
    )


def assess_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach a `quality` block to each result, computed with cross-result
    corroboration. Returns a **new** list; the originals are not mutated.
    """
    if not results:
        return results
    corr = _corroboration_map(results)
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(results):
        url = r.get("url", "")
        q = score_url(url, r, corroboration=corr.get(i, 0))
        new = dict(r)
        new["quality"] = q.as_dict()
        out.append(new)
    return out


def summarize_quality(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Roll up a result set into an aggregate confidence summary."""
    results = list(results)
    if not results:
        return {
            "result_count": 0,
            "mean_score": 0,
            "independent_domains": 0,
            "tier_distribution": {},
            "confidence": "none",
        }

    scores = []
    tiers: Dict[str, int] = {}
    domains: Set[str] = set()
    for r in results:
        q = (r.get("quality") or {}) if isinstance(r, dict) else {}
        if "score" in q:
            scores.append(q["score"])
            tiers[q["tier"]] = tiers.get(q["tier"], 0) + 1
        host = urlparse(r.get("url", "")).hostname or ""
        domains.add(_registered_domain(host))

    mean = int(sum(scores) / len(scores)) if scores else 0
    n_domains = len([d for d in domains if d])
    confidence = (
        "high"
        if mean >= 65 and n_domains >= 3
        else "medium" if mean >= 50 and n_domains >= 2 else "low"
    )
    return {
        "result_count": len(results),
        "mean_score": mean,
        "independent_domains": n_domains,
        "tier_distribution": tiers,
        "confidence": confidence,
    }

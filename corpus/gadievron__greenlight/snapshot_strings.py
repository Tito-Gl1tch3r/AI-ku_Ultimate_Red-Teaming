"""
Snapshot-pinned substrings observed in Anthropic error texts.

These are the discriminating markers the classifier matches against. Pin
them — if Anthropic rewords the refusal or rate-limit text, the snapshot
eval tests fail loudly, rather than the harness silently regressing to
treating every refused session as a transport flake.

These exact substrings are stable across Opus-4.7 on shellshock-like and
format-string-like across 27 refused sessions and multiple rate-limit
events.

The priority order declared below (rate-limit > refusal > transport)
is not decorative — it is load-bearing for the classifier. See
`classifier.py::classify()` for why.
"""
from __future__ import annotations

from typing import Final


# Anthropic usage-policy refusal markers. All four have co-occurred in
# every refused session on the reference corpus; the classifier matches
# on any one. POLICY_REFUSAL_MARKERS is the union of HARD and SOFT below
# (kept as a single tuple for backward-compatible callers that don't need
# the distinction).
HARD_REFUSAL_MARKERS: Final[tuple[str, ...]] = (
    # The "hard" markers — terminal refusal text that the SDK emits as a
    # final assistant message before the session is killed.
    "Claude Code is unable to respond to this request",
    "violate our Usage Policy",
    "violative cyber content",
    "anthropic.com/legal/aup",
)

SOFT_REFUSAL_MARKERS: Final[tuple[str, ...]] = (
    # "Soft" markers — mid-stream events suggesting a different approach.
    # On the post-pin corpus, soft markers co-occur with hard 29% of the
    # time and appear without hard 71% of the time (F6.1). Distinct from
    # hard for any harness that wants asymmetric retry policy per F1.3 (M11).
    "Try rephrasing",
    "attempting a different approach",
    "try running /model claude-sonnet",
)

# Backward-compatible union — preserved so existing callers continue to
# work without changes. New callers preferring the distinction should
# import HARD_REFUSAL_MARKERS / SOFT_REFUSAL_MARKERS directly.
POLICY_REFUSAL_MARKERS: Final[tuple[str, ...]] = HARD_REFUSAL_MARKERS + SOFT_REFUSAL_MARKERS

# Workspace rate-limit markers. These appear either in the exception text
# (when the SDK surfaces the rate-limit directly) or as a text event in
# the stream ("You've hit your limit · resets <time>") before the CLI
# exits non-zero. The classifier checks both surfaces.
RATE_LIMIT_MARKERS: Final[tuple[str, ...]] = (
    "hit your limit",
    "rate_limit",
    "rate limit",
    "429",
)

# SDK transport faults — these are GENUINE flakes, retryable. Kept
# separate so the classifier can distinguish "retry" from "do not retry."
SDK_TRANSPORT_MARKERS: Final[tuple[str, ...]] = (
    "Command failed with exit code",
    "Fatal error in message reader",
)

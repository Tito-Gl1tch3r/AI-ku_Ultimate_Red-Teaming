"""
Error classifier for defensive-security evals research benches using
claude-agent-sdk.

Distills the three-root-causes-one-exception problem into a single function:

    classify(exception, trajectory_path) -> Classification

The kinds are deliberately small. Add a new one only when you have observed
the failure mode and the retry/cleanup policy for it differs from UNKNOWN.

Priority order inside classify() is load-bearing:

    1. Rate-limit (check exception message, then trajectory text).
       The workspace quota needs to clear before anything else happens;
       retrying would race the orchestrator's quota-window handler.

    2. Policy refusal (trajectory text only — exception is indistinguishable
       from a transport flake). Refusal means the prompt itself won't succeed
       on identical re-submission, so retry-at-the-run-layer is wrong; this
       is signal for the skill/proposer layer.

    3. SDK transport. The last branch — covers real CLI crashes, now that
       the other two root causes are peeled off first.

If you forget the priority, rate-limits get classified as transport and
quietly retried (wasting quota), and refusals get classified as transport
and retried (wasting money on identical refusals).

Stdlib only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .snapshot_strings import (
    HARD_REFUSAL_MARKERS,
    POLICY_REFUSAL_MARKERS,
    RATE_LIMIT_MARKERS,
    SDK_TRANSPORT_MARKERS,
    SOFT_REFUSAL_MARKERS,
)


RATE_LIMIT: Final = "RATE_LIMIT"
# F1.3 (M11a): SOFT_REFUSAL and HARD_REFUSAL distinguish the two refusal
# texts the filter emits. POLICY_REFUSAL is preserved as a backward-compat
# alias so existing callers that don't care about the distinction still work.
# Per F6.1 on our corpus: hard implies soft (100%), soft alone is 71%, both
# is 29%. Harness authors wanting asymmetric retry policy (e.g. cap=2 on
# soft, cap=1 on hard) should branch on the new kinds; default callers
# treat both as POLICY_REFUSAL.
POLICY_REFUSAL: Final = "POLICY_REFUSAL"
HARD_REFUSAL: Final = "HARD_REFUSAL"
SOFT_REFUSAL: Final = "SOFT_REFUSAL"
SDK_TRANSPORT: Final = "SDK_TRANSPORT"
UNKNOWN: Final = "UNKNOWN"


@dataclass(frozen=True)
class Classification:
    kind: str
    retryable: bool
    message: str


def _scan_trajectory_text(trajectory_path: Path, needles: tuple[str, ...]) -> bool:
    """Return True if any text event in the trajectory contains any needle."""
    try:
        with trajectory_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                text = event.get("text", "")
                if isinstance(text, str) and any(s in text for s in needles):
                    return True
    except (FileNotFoundError, OSError):
        return False
    return False


def _has_exhausted_api_retry(trajectory_path: Path) -> bool:
    """Detect SDK-level API retry exhaustion — symptom of workspace overload
    or silent rate-limit when the explicit rate-limit text isn't emitted.

    The SDK writes a `{"kind": "system", "subtype": "api_retry",
    "attempt": N, "max_retries": N, "error": "unknown"}` event when it gives
    up after its retry budget. Observed 2026-04-24 during a workspace overload
    window — four consecutive seeds failed with only this marker, no 429 text.

    Treated as RATE_LIMIT: same handling (non-retryable at run layer; caller
    backs off at orchestrator/driver level).
    """
    try:
        with trajectory_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("kind") != "system" or event.get("subtype") != "api_retry":
                    continue
                # SDK nests the payload under `data` in real trajectories; earlier
                # schema had attempt/max_retries at the top level. Check both.
                src = event.get("data") if isinstance(event.get("data"), dict) else event
                attempt = src.get("attempt")
                max_retries = src.get("max_retries")
                if (
                    isinstance(attempt, int) and isinstance(max_retries, int)
                    and max_retries >= 5 and attempt >= max_retries
                ):
                    return True
    except (FileNotFoundError, OSError):
        return False
    return False


def classify(
    exc: BaseException, trajectory_path: Path | None = None
) -> Classification:
    """Classify an SDK exception. See module docstring for priority order.

    Pass `trajectory_path` whenever you have one. Rate-limit and policy-refusal
    detection both require scanning trajectory text; without it, they fall
    through to SDK_TRANSPORT and are silently retried.
    """
    msg = str(exc)
    lowered = msg.lower()

    # 1a. Rate-limit directly in the exception text.
    if any(needle in lowered for needle in RATE_LIMIT_MARKERS):
        return Classification(kind=RATE_LIMIT, retryable=False, message=msg)

    # 1b. Rate-limit in trajectory text (CLI exited after a quota-exhausted
    # stream event). Same non-retryable policy.
    if trajectory_path is not None and _scan_trajectory_text(
        trajectory_path, RATE_LIMIT_MARKERS
    ):
        return Classification(kind=RATE_LIMIT, retryable=False, message=msg)

    # 1c. SDK retry-exhaustion — workspace overload symptom without explicit
    # rate-limit text. Treated as RATE_LIMIT (see `_has_exhausted_api_retry`).
    if trajectory_path is not None and _has_exhausted_api_retry(trajectory_path):
        return Classification(kind=RATE_LIMIT, retryable=False, message=msg)

    # 2. Policy refusal — only detectable via trajectory text. Marked
    # retryable=True so the harness can attempt one re-roll (max_consecutive_
    # refusals=1 — see INTEGRATION.md §Retry policy for the bimodal-distribution
    # reasoning that justifies this specific cap).
    #
    # F1.3 (M11a): now distinguishes HARD_REFUSAL vs SOFT_REFUSAL. Hard implies
    # soft (per F6.1); soft alone fires often (71% of refusals on our corpus).
    # Callers that only care about "is this a refusal" should test
    # `kind in (POLICY_REFUSAL, HARD_REFUSAL, SOFT_REFUSAL)` or use the
    # `is_policy_refusal()` helper below.
    if trajectory_path is not None:
        has_hard = _scan_trajectory_text(trajectory_path, HARD_REFUSAL_MARKERS)
        has_soft = _scan_trajectory_text(trajectory_path, SOFT_REFUSAL_MARKERS)
        if has_hard:
            # If both present, return HARD (the more discriminating signal).
            # Hard refusals always have a soft co-marker on our corpus, so
            # this is the typical "both" case as well.
            return Classification(kind=HARD_REFUSAL, retryable=True, message=msg)
        if has_soft:
            return Classification(kind=SOFT_REFUSAL, retryable=True, message=msg)

    # 3. SDK transport — genuine flake, retry with a fresh subprocess.
    if any(needle in msg for needle in SDK_TRANSPORT_MARKERS):
        return Classification(kind=SDK_TRANSPORT, retryable=True, message=msg)

    return Classification(kind=UNKNOWN, retryable=False, message=msg)


def is_policy_refusal(kind: str) -> bool:
    """Backward-compat helper for callers that don't need the soft/hard split.

    Returns True for POLICY_REFUSAL, HARD_REFUSAL, or SOFT_REFUSAL.
    """
    return kind in (POLICY_REFUSAL, HARD_REFUSAL, SOFT_REFUSAL)

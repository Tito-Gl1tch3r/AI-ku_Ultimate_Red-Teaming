"""
Snapshot tests for the refusal-handling classifier.

These tests pin the exact substrings the classifier matches against. If
Anthropic rewords its refusal or rate-limit text, these eval tests fail here —
loudly, in CI — instead of the classifier silently regressing in production.

Do not relax the assertions to "handle variation." The point is to notice
variation the moment it happens.

Reference corpus: 27 refused sessions observed 2026-04-22 through 2026-04-24
against Opus-4.7. Every one matched all four POLICY_REFUSAL_MARKERS. See
`../FINDINGS.md` §F1.5.
"""
from __future__ import annotations

import json

from .classifier import (
    HARD_REFUSAL,
    POLICY_REFUSAL,
    RATE_LIMIT,
    SDK_TRANSPORT,
    SOFT_REFUSAL,
    UNKNOWN,
    classify,
    is_policy_refusal,
)


# ---- Policy-refusal detection via trajectory ---------------------------------


def _write_trajectory(tmp_path, events):
    traj = tmp_path / "trajectory.jsonl"
    traj.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return traj


def test_policy_refusal_via_trajectory_text(tmp_path):
    """Exact wire format observed 2026-04-23 on refused Opus sessions."""
    traj = _write_trajectory(
        tmp_path,
        [
            {
                "kind": "text",
                "role": "assistant",
                "turn": 44,
                "text": (
                    "API Error: Claude Code is unable to respond to this "
                    "request, which appears to violate our Usage Policy "
                    "(https://www.anthropic.com/legal/aup). Try rephrasing "
                    "the request or attempting a different approach."
                ),
            }
        ],
    )
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=traj)
    # F1.3 (M11a): hard markers present → returns HARD_REFUSAL.
    # is_policy_refusal() returns True for HARD/SOFT/POLICY_REFUSAL alike,
    # the right helper for "is this any kind of refusal?".
    assert c.kind == HARD_REFUSAL
    assert is_policy_refusal(c.kind)
    assert c.retryable is True


def test_policy_refusal_recognized_by_any_single_marker(tmp_path):
    """A trajectory containing only one of the four hard markers must still classify."""
    for marker in (
        "Claude Code is unable to respond to this request",
        "violate our Usage Policy",
        "violative cyber content",
        "anthropic.com/legal/aup",
    ):
        traj = _write_trajectory(
            tmp_path, [{"kind": "text", "text": f"some preamble {marker} trailing"}]
        )
        c = classify(Exception("Command failed with exit code 1"), trajectory_path=traj)
        assert c.kind == HARD_REFUSAL, f"missed marker: {marker}"
        assert is_policy_refusal(c.kind)


# ---- Rate-limit detection ----------------------------------------------------


def test_rate_limit_in_exception_message():
    exc = Exception("anthropic rate_limit error: retry after 60s")
    c = classify(exc)
    assert c.kind == RATE_LIMIT
    assert c.retryable is False


def test_rate_limit_in_trajectory_stream(tmp_path):
    """Observed 2026-04-23 when the workspace quota exhausted mid-stream."""
    traj = _write_trajectory(
        tmp_path,
        [
            {
                "kind": "text",
                "role": "assistant",
                "text": "You've hit your limit · resets 3:00 PM",
            }
        ],
    )
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=traj)
    assert c.kind == RATE_LIMIT


def test_api_retry_exhaustion_classified_as_rate_limit(tmp_path):
    """Observed 2026-04-24 during a workspace-overload window —
    SDK emits api_retry at max_retries without explicit rate-limit text.
    Should classify as RATE_LIMIT, not SDK_TRANSPORT."""
    traj = _write_trajectory(
        tmp_path,
        [
            {
                "kind": "system",
                "subtype": "api_retry",
                "attempt": 10,
                "max_retries": 10,
                "retry_delay_ms": 36318,
                "error": "unknown",
            }
        ],
    )
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=traj)
    assert c.kind == RATE_LIMIT
    assert c.retryable is False


def test_single_api_retry_does_not_false_match(tmp_path):
    """A normal single retry (attempt=1, max=10) is transient and should NOT
    be classified as rate-limit. Only exhaustion (attempt==max_retries) triggers."""
    traj = _write_trajectory(
        tmp_path,
        [
            {"kind": "system", "subtype": "api_retry",
             "attempt": 1, "max_retries": 10, "error": "unknown"}
        ],
    )
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=traj)
    assert c.kind == SDK_TRANSPORT  # falls through to transport classification


def test_rate_limit_beats_policy_refusal(tmp_path):
    """If both markers appear (stale refusal text + real rate-limit), the
    rate-limit must win — rate-limit policy is workspace-level and must
    take precedence over a cached refusal text in an old trajectory."""
    traj = _write_trajectory(
        tmp_path,
        [
            {"kind": "text", "text": "violative cyber content"},
            {"kind": "text", "text": "You've hit your limit · resets now"},
        ],
    )
    exc = Exception("anthropic rate_limit error")
    c = classify(exc, trajectory_path=traj)
    assert c.kind == RATE_LIMIT


# ---- SDK transport falls through -------------------------------------------


def test_sdk_transport_exact_observed_string():
    """Exact wire format observed 2026-04-23 on transport flakes."""
    exc = Exception(
        "Command failed with exit code 1 (exit code: 1)\n"
        "Error output: Check stderr output for details"
    )
    c = classify(exc)
    assert c.kind == SDK_TRANSPORT
    assert c.retryable is True


def test_sdk_transport_fatal_reader():
    exc = Exception("Fatal error in message reader")
    c = classify(exc)
    assert c.kind == SDK_TRANSPORT


# ---- Unknown fallback --------------------------------------------------------


def test_unknown_exception_does_not_falsely_match():
    exc = ValueError("something broke in user code")
    c = classify(exc)
    assert c.kind == UNKNOWN
    assert c.retryable is False


# ---- Priority-order regressions --------------------------------------------


def test_policy_refusal_beats_sdk_transport(tmp_path):
    """If the exception looks like a transport flake but the trajectory shows
    a refusal, refusal wins. Without this, refusals get silently retried."""
    traj = _write_trajectory(
        tmp_path,
        [{"kind": "text", "text": "violate our Usage Policy"}],
    )
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=traj)
    # F1.3 (M11a): hard marker present → returns HARD_REFUSAL.
    assert c.kind == HARD_REFUSAL
    assert is_policy_refusal(c.kind)


def test_trajectory_path_none_does_not_crash():
    """Callers that forget to pass trajectory_path must still get a sane answer
    (SDK_TRANSPORT is the right fallback for a bare exit-code-1 exception)."""
    exc = Exception("Command failed with exit code 1")
    c = classify(exc, trajectory_path=None)
    assert c.kind == SDK_TRANSPORT


# ---- F1.3 (M11a) — SOFT vs HARD refusal split ---------------------------------


def test_soft_refusal_returned_when_only_soft_markers_present(tmp_path):
    """Soft-only refusal (e.g. mid-stream 'try rephrasing' without the hard
    terminal text) should classify as SOFT_REFUSAL, not POLICY_REFUSAL.
    Per F6.1, soft-only is 71% of all refusals on the post-pin corpus."""
    traj = _write_trajectory(
        tmp_path,
        [{"kind": "text", "text": "Try rephrasing the request or doing something else."}],
    )
    c = classify(Exception("Command failed with exit code 1"), trajectory_path=traj)
    assert c.kind == SOFT_REFUSAL
    assert is_policy_refusal(c.kind)
    assert c.retryable is True


def test_hard_refusal_returned_when_both_markers_present(tmp_path):
    """When both hard and soft markers are present (the 'both' bucket per F6.1,
    29% of refusals), HARD_REFUSAL wins as the more discriminating signal."""
    traj = _write_trajectory(
        tmp_path,
        [
            {"kind": "text", "text": "API Error: violate our Usage Policy. Try rephrasing."}
        ],
    )
    c = classify(Exception("Command failed with exit code 1"), trajectory_path=traj)
    assert c.kind == HARD_REFUSAL
    assert is_policy_refusal(c.kind)


def test_is_policy_refusal_helper_covers_all_three_kinds():
    """Backward-compat helper covers the union — important for callers that
    don't want to enumerate kinds themselves."""
    assert is_policy_refusal(POLICY_REFUSAL)
    assert is_policy_refusal(HARD_REFUSAL)
    assert is_policy_refusal(SOFT_REFUSAL)
    assert not is_policy_refusal(SDK_TRANSPORT)
    assert not is_policy_refusal(RATE_LIMIT)
    assert not is_policy_refusal(UNKNOWN)

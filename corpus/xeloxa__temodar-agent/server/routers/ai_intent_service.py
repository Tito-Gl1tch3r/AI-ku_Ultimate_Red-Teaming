from typing import Any, Dict, List


SECURITY_MARKERS = {
    "security", "vulnerability", "nonce", "csrf", "xss", "sqli", "ssrf", "rce", "lfi", "auth",
    "authorization", "permission", "capability", "exploit", "güvenlik", "guvenlik", "açık", "acik",
}
STRUCTURED_MARKERS = {
    "json", "structured output", "schema", "fields", "extract as json",
}


def _contains_any(text: str, phrases: set[str]) -> bool:
    lowered = text.casefold()
    return any(str(phrase).casefold() in lowered for phrase in phrases if str(phrase).strip())


def summarize_recent_thread_context(repo, thread_id: int, limit: int = 6) -> str:
    messages = repo.list_messages(thread_id)
    if not messages:
        return ""

    lines: List[str] = []
    for message in messages[-limit:]:
        role = str(message.get("role") or "unknown")
        content = str(message.get("content") or "").strip()
        if not content:
            continue
        compact = " ".join(content.split())
        if len(compact) > 300:
            compact = f"{compact[:297]}..."
        lines.append(f"- {role}: {compact}")
    return "\n".join(lines)


def _build_workspace_intent(*, reason: str, content: str) -> Dict[str, Any]:
    lowered = str(content or "").casefold()
    return {
        "intent": "workspace_chat",
        "needs_tools": True,
        "needs_workspace_access": True,
        "requires_workspace_access": True,
        "scope": "workspace",
        "confidence": 0.99,
        "reason": reason,
        "execution_mode": "raw_open_multi_agent",
        "team_mode": "single_agent",
        "strategy": "agent",
        "security_focus": _contains_any(lowered, SECURITY_MARKERS),
        "structured_output_requested": _contains_any(lowered, STRUCTURED_MARKERS),
        "should_ask_clarification": False,
        "composition_source": "raw_open_multi_agent",
    }


def classify_message_intent(*, content: str, repo, thread_id: int) -> Dict[str, Any]:
    del repo, thread_id
    # Intent heuristics intentionally disabled:
    # every message runs in workspace mode with tools enabled.
    return _build_workspace_intent(
        reason="workspace_default",
        content=content,
    )


def summarize_intent_decision(intent_info: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "intent": str(intent_info.get("intent") or ""),
        "needs_tools": bool(intent_info.get("needs_tools")),
        "needs_workspace_access": bool(intent_info.get("needs_workspace_access")),
        "reason": str(intent_info.get("reason") or ""),
        "execution_mode": str(intent_info.get("execution_mode") or "raw_open_multi_agent"),
        "team_mode": str(intent_info.get("team_mode") or "single_agent"),
        "strategy": str(intent_info.get("strategy") or "agent"),
        "composition_source": "raw_open_multi_agent",
    }


def resolve_message_intent(
    *,
    content: str,
    repo,
    thread_id: int,
    thread: Dict[str, Any] | None = None,
    context_summary: str = "",
    active_provider: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    del thread, context_summary, active_provider
    resolved = classify_message_intent(content=content, repo=repo, thread_id=thread_id)
    resolved["normalized_decision"] = summarize_intent_decision(resolved)
    return resolved

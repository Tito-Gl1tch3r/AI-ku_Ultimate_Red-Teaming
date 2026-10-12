from pathlib import Path
from typing import Any, Dict, List


def summarize_thread_memory(repo, thread_id: int) -> str:
    memory = repo.get_thread_memory(thread_id)
    sections: List[str] = []
    if memory.get("conversation_summary"):
        sections.append(f"Conversation memory: {memory['conversation_summary']}")
    if memory.get("analysis_summary"):
        sections.append(f"Analysis memory: {memory['analysis_summary']}")
    important_files = list(memory.get("important_files") or [])
    if important_files:
        sections.append(f"Important files: {', '.join(important_files[:12])}")
    if memory.get("findings_summary"):
        sections.append(f"Findings memory: {memory['findings_summary']}")
    if memory.get("architecture_notes"):
        sections.append(f"Architecture memory: {memory['architecture_notes']}")
    if memory.get("last_source_path"):
        sections.append(f"Previous source path: {memory['last_source_path']}")
    return "\n".join(section for section in sections if section)


def _truncate_memory_text(value: str, limit: int = 500) -> str:
    compact = " ".join(str(value or "").split()).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


def _extract_memory_file_candidates(event: Dict[str, Any]) -> List[str]:
    payload = event.get("data") if isinstance(event.get("data"), dict) else {}
    candidates: List[str] = []

    def add_candidate(value: Any) -> None:
        candidate = str(value or "").strip()
        if not candidate:
            return
        if candidate.startswith("/"):
            return
        if "\n" in candidate:
            return
        if candidate not in candidates:
            candidates.append(candidate)

    for key in ("path", "file_path"):
        add_candidate(payload.get(key))

    nested_input = payload.get("input")
    if isinstance(nested_input, dict):
        for key in ("path", "file_path"):
            add_candidate(nested_input.get(key))

    nested_result = payload.get("result")
    if isinstance(nested_result, dict):
        for key in ("path", "file_path"):
            add_candidate(nested_result.get(key))

    return candidates


def build_updated_thread_memory(
    *,
    repo,
    thread_id: int,
    user_content: str,
    assistant_output: str,
    source_dir: Path | None,
    run_events: List[Dict[str, Any]],
    run_tasks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    existing = repo.get_thread_memory(thread_id)
    prior_files = list(existing.get("important_files") or [])
    discovered_files: List[str] = []
    for event in run_events:
        for candidate in _extract_memory_file_candidates(event):
            if candidate not in discovered_files:
                discovered_files.append(candidate)

    merged_files: List[str] = []
    for item in [*prior_files, *discovered_files]:
        normalized = str(item or "").strip()
        if normalized and normalized not in merged_files:
            merged_files.append(normalized)
    merged_files = merged_files[:20]

    task_summaries = []
    for task in run_tasks[:8]:
        title = str(task.get("title") or "").strip()
        result = str(task.get("result") or "").strip()
        if title and result:
            task_summaries.append(f"{title}: {result}")
        elif title:
            task_summaries.append(title)

    conversation_memory = _truncate_memory_text(
        " | ".join(
            part
            for part in [
                str(existing.get("conversation_summary") or "").strip(),
                f"User: {user_content}",
                f"Assistant: {assistant_output}",
            ]
            if part
        ),
        700,
    )
    analysis_memory = _truncate_memory_text(
        " | ".join(
            part
            for part in [
                str(existing.get("analysis_summary") or "").strip(),
                assistant_output,
                " ; ".join(task_summaries),
            ]
            if part
        ),
        900,
    )
    findings_memory = _truncate_memory_text(
        str(existing.get("findings_summary") or "")
        + (" | " if existing.get("findings_summary") and assistant_output else "")
        + assistant_output,
        700,
    )
    architecture_notes = _truncate_memory_text(
        " | ".join(
            part
            for part in [
                str(existing.get("architecture_notes") or "").strip(),
                "Files seen: " + ", ".join(merged_files[:8]) if merged_files else "",
            ]
            if part
        ),
        500,
    )
    return {
        "conversation_summary": conversation_memory,
        "analysis_summary": analysis_memory,
        "important_files": merged_files,
        "findings_summary": findings_memory,
        "architecture_notes": architecture_notes,
        "last_source_path": str(source_dir.resolve()) if source_dir is not None else str(existing.get("last_source_path") or ""),
    }

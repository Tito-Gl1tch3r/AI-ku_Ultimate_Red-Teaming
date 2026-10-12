from pathlib import Path
from typing import Any, Callable, Dict, List

from fastapi import HTTPException, status

from server.routers.ai_bridge_service import build_bridge_payload
from server.routers.ai_intent_service import (
    resolve_message_intent,
    summarize_intent_decision,
    summarize_recent_thread_context,
)
from server.routers.ai_memory_service import (
    build_updated_thread_memory,
    summarize_thread_memory,
)
from server.routers.ai_runtime_service import (
    arm_manual_run_approval_if_needed,
    auto_approve_pending_run_approval,
    cleanup_workspace,
    create_user_message_and_run,
    persist_completed_run,
    prepare_thread_for_message,
    prepare_thread_run_context,
    raise_mapped_ai_error,
)
from server.routers.ai_serialization import list_structured_thread_events, serialize_message, serialize_thread


def resolve_active_provider(*, repo, payload) -> Dict[str, Any]:
    requested_profile_key = str(getattr(payload, "profile_key", "") or "").strip()
    active_provider = (
        repo.get_provider_by_profile_key(requested_profile_key)
        if requested_profile_key
        else repo.get_active_provider()
    )
    if active_provider is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active AI provider configured.",
        )

    requested_model = str(getattr(payload, "model", "") or "").strip()
    if requested_model:
        active_provider = {**active_provider, "model": requested_model}
    return active_provider


def prepare_message_execution(*, repo, payload, active_provider: Dict[str, Any] | None = None) -> Dict[str, Any]:
    thread, effective_last_scan_session_id = prepare_thread_for_message(
        repo=repo,
        payload=payload,
    )
    recent_context_summary = summarize_recent_thread_context(repo, payload.thread_id)
    memory_summary = summarize_thread_memory(repo, payload.thread_id)
    context_summary = "\n".join(
        part for part in [memory_summary, recent_context_summary] if part
    )
    intent_info = resolve_message_intent(
        content=payload.content,
        repo=repo,
        thread_id=payload.thread_id,
        thread=thread,
        context_summary=context_summary,
        active_provider=active_provider,
    )
    requested_strategy = str(getattr(payload, "strategy", "auto") or "auto").strip().lower()
    if requested_strategy and requested_strategy != "auto":
        intent_info["strategy"] = requested_strategy
        intent_info["team_mode"] = "single_agent" if requested_strategy == "agent" else requested_strategy
    if getattr(payload, "output_schema", None):
        intent_info["structured_output_requested"] = True
    strategy = str(intent_info.get("strategy") or "agent")
    return {
        "thread": thread,
        "last_scan_session_id": effective_last_scan_session_id,
        "intent_info": intent_info,
        "execution_mode": "raw_open_multi_agent",
        "team_mode": "single_agent" if strategy == "agent" else strategy,
        "strategy": strategy,
        "context_summary": context_summary,
    }


def prepare_execution_workspace(
    *,
    repo,
    thread: Dict[str, Any],
    last_scan_session_id: int | None,
    path_cwd: Callable[[], Path],
    resolve_existing_thread_source_path,
    build_plugin_context_for_source,
    runtime_events: List[Dict[str, Any]],
    intent_info: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    source_dir, workspace_root, workspace_source_path = prepare_thread_run_context(
        repo=repo,
        thread=thread,
        last_scan_session_id=last_scan_session_id,
        path_cwd=path_cwd,
        resolve_existing_thread_source_path=resolve_existing_thread_source_path,
        runtime_events=runtime_events,
    )
    context = build_plugin_context_for_source(
        db_path=repo.db_path,
        plugin_slug=thread["plugin_slug"],
        is_theme=bool(thread.get("is_theme")),
        source_dir=source_dir,
        last_scan_session_id=last_scan_session_id,
    )

    context = {**context, "intent_info": dict(intent_info or {})}
    return {
        "source_dir": source_dir,
        "workspace_root": workspace_root,
        "workspace_source_path": workspace_source_path,
        "context": context,
    }


def build_effective_context_summary(*, intent_info: Dict[str, Any], context_summary: str) -> str:
    del intent_info
    return context_summary


def build_bridge_request(
    *,
    active_provider: Dict[str, Any],
    payload,
    context: Dict[str, Any],
    workspace_root: Path,
    source_dir: Path | None,
    execution_mode: str,
    team_mode: str,
    strategy: str,
    context_summary: str,
    approval_control_path: str | None = None,
) -> Dict[str, Any]:
    effective_provider = dict(active_provider)
    if getattr(payload, "output_schema", None):
        effective_provider["output_schema"] = payload.output_schema
    return build_bridge_payload(
        active_provider=effective_provider,
        prompt=payload.content,
        context=context,
        workspace_root=workspace_root,
        source_dir=source_dir,
        execution_mode=execution_mode,
        team_mode=team_mode,
        strategy=strategy,
        context_summary=context_summary,
        needs_tools=bool(context.get("intent_info", {}).get("needs_tools", True)),
        trace_enabled=bool(getattr(payload, "trace_enabled", True)),
        agents=getattr(payload, "agents", None) or None,
        tasks=getattr(payload, "tasks", None) or None,
        fanout=getattr(payload, "fanout", None) or None,
        loop_detection=getattr(payload, "loop_detection", None) or None,
        approval_mode=getattr(payload, "approval_mode", None) or None,
        approval_control_path=approval_control_path,
        before_run=getattr(payload, "before_run", None) or None,
        after_run=getattr(payload, "after_run", None) or None,
    )


def update_thread_memory_from_run(
    *,
    repo,
    payload,
    assistant_message: Dict[str, Any],
    source_dir: Path | None,
    runtime_events: List[Dict[str, Any]],
    run_events: List[Dict[str, Any]],
    run_tasks: List[Dict[str, Any]],
) -> None:
    repo.update_thread_memory(
        payload.thread_id,
        **build_updated_thread_memory(
            repo=repo,
            thread_id=payload.thread_id,
            user_content=payload.content,
            assistant_output=str(assistant_message.get("content") or ""),
            source_dir=source_dir,
            run_events=[*(runtime_events or []), *(run_events or [])],
            run_tasks=run_tasks,
        ),
    )


def build_final_response(
    *,
    repo,
    payload,
    user_message: Dict[str, Any] | None,
    assistant_message: Dict[str, Any] | None,
    run,
    team_events: List[Dict[str, Any]],
    persisted_tasks: List[Dict[str, Any]],
    bridge_result: Dict[str, Any],
) -> Dict[str, Any]:
    thread = repo.get_thread(payload.thread_id)
    result_payload = bridge_result.get("result", {}) if isinstance(bridge_result.get("result"), dict) else {}
    return {
        "user_message": serialize_message(user_message),
        "assistant_message": serialize_message(assistant_message),
        "events": list_structured_thread_events(repo, payload.thread_id),
        "run_id": int(run["id"]) if run is not None else None,
        "team_events": team_events,
        "tasks": persisted_tasks,
        "agents": result_payload.get("agents", []) if isinstance(result_payload, dict) else [],
        "structured": result_payload.get("structured") if isinstance(result_payload, dict) else None,
        "thread": serialize_thread(thread) if thread is not None else None,
    }


def execute_ai_message(
    *,
    repo,
    payload,
    path_cwd: Callable[[], Path],
    build_plugin_context_for_source,
    resolve_existing_thread_source_path,
    cleanup_run_workspace: Callable[[Path], None],
    run_agent_bridge,
) -> Dict[str, object]:
    active_provider = resolve_active_provider(repo=repo, payload=payload)
    execution = prepare_message_execution(repo=repo, payload=payload, active_provider=active_provider)
    thread = execution["thread"]

    workspace_root: Path | None = None
    source_dir: Path | None = None
    run = None
    user_message = None
    assistant_message = None
    bridge_result: Dict[str, object] = {"events": []}
    team_events: List[Dict[str, object]] = []
    persisted_tasks: List[Dict[str, object]] = []
    runtime_events: List[Dict[str, object]] = []

    try:
        workspace = prepare_execution_workspace(
            repo=repo,
            thread=thread,
            last_scan_session_id=execution["last_scan_session_id"],
            path_cwd=path_cwd,
            resolve_existing_thread_source_path=resolve_existing_thread_source_path,
            build_plugin_context_for_source=build_plugin_context_for_source,
            runtime_events=runtime_events,
            intent_info=execution["intent_info"],
        )
        source_dir = workspace["source_dir"]
        workspace_root = workspace["workspace_root"]
        runtime_events.append(
            {
                "type": "intent_resolved",
                "data": {
                    "decision_trace": summarize_intent_decision(execution["intent_info"]),
                },
            }
        )

        user_message, run = create_user_message_and_run(
            repo=repo,
            thread_id=payload.thread_id,
            content=payload.content,
            active_provider=active_provider,
            workspace_source_path=workspace["workspace_source_path"],
        )
        approval_control_path = arm_manual_run_approval_if_needed(
            repo=repo,
            payload=payload,
            run_id=run["id"],
            workspace_root=workspace_root,
        )
        bridge_payload = build_bridge_request(
            active_provider=active_provider,
            payload=payload,
            context=workspace["context"],
            workspace_root=workspace_root,
            source_dir=source_dir,
            execution_mode=execution["execution_mode"],
            team_mode=execution["team_mode"],
            strategy=execution["strategy"],
            context_summary=build_effective_context_summary(
                intent_info=execution["intent_info"],
                context_summary=execution["context_summary"],
            ),
            approval_control_path=approval_control_path,
        )
        bridge_result = run_agent_bridge(bridge_payload)
        assistant_message, team_events, persisted_tasks = persist_completed_run(
            repo=repo,
            thread_id=payload.thread_id,
            run_id=run["id"],
            bridge_result=bridge_result,
            source_dir=source_dir,
            runtime_events=runtime_events,
        )
        auto_approve_pending_run_approval(
            repo=repo,
            run_id=run["id"],
            thread_id=payload.thread_id,
        )
        update_thread_memory_from_run(
            repo=repo,
            payload=payload,
            assistant_message=assistant_message,
            source_dir=source_dir,
            runtime_events=runtime_events,
            run_events=bridge_result.get("events", []) or [],
            run_tasks=persisted_tasks,
        )
    except Exception as exc:
        raise_mapped_ai_error(
            repo=repo,
            exc=exc,
            run=run,
            thread_id=payload.thread_id,
        )
    finally:
        cleanup_workspace(
            source_dir=source_dir,
            workspace_root=workspace_root,
            cleanup_run_workspace=cleanup_run_workspace,
        )

    return build_final_response(
        repo=repo,
        payload=payload,
        user_message=user_message,
        assistant_message=assistant_message,
        run=run,
        team_events=team_events,
        persisted_tasks=persisted_tasks,
        bridge_result=bridge_result,
    )

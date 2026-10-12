import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterator

from fastapi import HTTPException

from server.routers.ai_runtime_service import (
    arm_manual_run_approval_if_needed,
    auto_approve_pending_run_approval,
    cleanup_workspace,
    create_user_message_and_run,
    persist_completed_run,
    raise_mapped_ai_error,
)
from server.routers.ai_serialization import serialize_message, serialize_run_approval
from server.routers.ai_service import (
    build_bridge_request,
    build_effective_context_summary,
    build_final_response,
    prepare_execution_workspace,
    prepare_message_execution,
    resolve_active_provider,
    update_thread_memory_from_run,
)
from server.routers.ai_intent_service import summarize_intent_decision


def stream_ai_message_events(
    *,
    repo,
    payload,
    path_cwd: Callable[[], Path],
    build_plugin_context_for_source: Callable[..., Dict[str, Any]],
    resolve_existing_thread_source_path: Callable[..., Path | None],
    cleanup_run_workspace: Callable[[Path], None],
    run_agent_bridge_stream: Callable[[Dict[str, Any]], Iterator[Dict[str, Any]]],
):
    try:
        active_provider = resolve_active_provider(repo=repo, payload=payload)
    except HTTPException as exc:
        yield json.dumps(
            {"type": "error", "data": {"detail": str(exc.detail)}},
            ensure_ascii=False,
        ) + "\n"
        return

    workspace_root = None
    source_dir = None
    run = None
    user_message = None
    runtime_events = []
    bridge_events = []
    bridge_result = {"events": [], "result": {}}

    try:
        execution = prepare_message_execution(repo=repo, payload=payload, active_provider=active_provider)
        workspace = prepare_execution_workspace(
            repo=repo,
            thread=execution["thread"],
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

        for event in runtime_events:
            yield json.dumps(
                {"type": "runtime_event", "data": event},
                ensure_ascii=False,
            ) + "\n"

        user_message, run = create_user_message_and_run(
            repo=repo,
            thread_id=payload.thread_id,
            content=payload.content,
            active_provider=active_provider,
            workspace_source_path=workspace["workspace_source_path"],
        )
        yield json.dumps(
            {"type": "user_message", "data": serialize_message(user_message)},
            ensure_ascii=False,
        ) + "\n"

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

        for event in run_agent_bridge_stream(bridge_payload):
            if event.get("type") == "approval_requested" and run is not None:
                event_data = event.get("data") or {}
                if isinstance(event_data, dict):
                    repo.upsert_run_approval(
                        run["id"],
                        payload.thread_id,
                        status="pending",
                        request_payload=event_data,
                    )
                    yield json.dumps(
                        {
                            "type": "pending_approval",
                            "data": serialize_run_approval(repo.get_run_approval(run["id"])),
                        },
                        ensure_ascii=False,
                    ) + "\n"
            if event.get("type") == "run_completed":
                event_data = event.get("data") or {}
                if isinstance(event_data, dict):
                    bridge_result = {
                        "output": str(
                            event_data.get("content") or event_data.get("output") or ""
                        ),
                        "events": bridge_events,
                        "result": event_data,
                    }
                else:
                    bridge_result = {
                        "output": str(event_data),
                        "events": bridge_events,
                        "result": {"content": str(event_data)},
                    }
                yield json.dumps(
                    {"type": "run_completed", "data": bridge_result["result"]},
                    ensure_ascii=False,
                ) + "\n"
                continue

            bridge_events.append(event)
            yield json.dumps(
                {"type": "bridge_event", "data": event},
                ensure_ascii=False,
            ) + "\n"

        assistant_message, team_events, persisted_tasks = persist_completed_run(
            repo=repo,
            thread_id=payload.thread_id,
            run_id=run["id"],
            bridge_result=bridge_result,
            source_dir=source_dir,
            runtime_events=runtime_events,
        )
        if run is not None:
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
            run_events=bridge_events,
            run_tasks=persisted_tasks,
        )
        final_payload = build_final_response(
            repo=repo,
            payload=payload,
            user_message=user_message,
            assistant_message=assistant_message,
            run=run,
            team_events=team_events,
            persisted_tasks=persisted_tasks,
            bridge_result=bridge_result,
        )
        final_payload["pending_approval"] = serialize_run_approval(repo.get_thread_pending_approval(payload.thread_id))
        yield json.dumps({"type": "final", "data": final_payload}, ensure_ascii=False) + "\n"
    except asyncio.CancelledError:
        if run is not None:
            try:
                repo.fail_run_with_assistant_message(
                    run_id=run["id"],
                    thread_id=payload.thread_id,
                    content="Yanıt akışı bağlantı kesildiği için yarıda kaldı. Mesajı tekrar gönderebilirsin.",
                    error_message="Run interrupted by client disconnect.",
                    tool_calls=[],
                    tool_results=[],
                )
            except Exception:
                try:
                    repo.finish_run(run["id"], "failed", "Run interrupted by client disconnect.")
                except Exception:
                    pass
        raise
    except Exception as exc:
        if run is not None:
            try:
                raise_mapped_ai_error(
                    repo=repo,
                    exc=exc,
                    run=run,
                    thread_id=payload.thread_id,
                )
            except HTTPException as mapped_exc:
                yield json.dumps(
                    {
                        "type": "error",
                        "data": {
                            "detail": str(mapped_exc.detail),
                            "status": mapped_exc.status_code,
                        },
                    },
                    ensure_ascii=False,
                ) + "\n"
                return
        else:
            yield json.dumps(
                {"type": "error", "data": {"detail": str(exc)}},
                ensure_ascii=False,
            ) + "\n"
            return
    finally:
        cleanup_workspace(
            source_dir=source_dir,
            workspace_root=workspace_root,
            cleanup_run_workspace=cleanup_run_workspace,
        )

import json
from typing import Any, Dict, List, Optional


PROVIDER_LABELS = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "copilot": "GitHub Copilot",
    "gemini": "Google Gemini",
    "grok": "xAI Grok",
}


def provider_label_for(provider: str) -> str:
    return PROVIDER_LABELS.get(provider, provider.title())


def json_or_none(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    return json.dumps(payload)


def decode_row(row) -> Dict[str, Any]:
    return dict(row) if row else {}


def decode_message_row(row) -> Dict[str, Any]:
    payload = decode_row(row)
    if not payload:
        return payload
    payload["tool_calls"] = json.loads(payload["tool_calls_json"]) if payload.get("tool_calls_json") else []
    payload["tool_results"] = json.loads(payload["tool_results_json"]) if payload.get("tool_results_json") else []
    return payload


def decode_run_event_row(row) -> Dict[str, Any]:
    payload = decode_row(row)
    if not payload:
        return payload
    payload["payload"] = json.loads(payload["payload_json"]) if payload.get("payload_json") else {}
    return payload


def decode_run_task_row(row) -> Dict[str, Any]:
    payload = decode_row(row)
    if not payload:
        return payload
    payload["depends_on"] = json.loads(payload["depends_on_json"]) if payload.get("depends_on_json") else []
    return payload


def decode_run_approval_row(row) -> Dict[str, Any]:
    payload = decode_row(row)
    if not payload:
        return payload
    payload["request_payload"] = json.loads(payload["request_payload_json"]) if payload.get("request_payload_json") else {}
    return payload


def maybe_preserve(existing: Dict[str, Any], new_value: Any, key: str) -> Any:
    return existing[key] if new_value is None else new_value


def normalize_thread_scope(is_theme: bool) -> int:
    return int(bool(is_theme))


def sanitize_thread_row(row) -> Dict[str, Any]:
    payload = decode_row(row)
    if payload:
        payload["is_theme"] = int(bool(payload.get("is_theme")))
        payload["important_files"] = json.loads(payload["important_files_json"]) if payload.get("important_files_json") else []
    return payload


def serialize_message_payload(
    thread_id: int,
    role: str,
    content: str,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    tool_results: Optional[List[Dict[str, Any]]] = None,
) -> tuple[Any, ...]:
    return (
        thread_id,
        role,
        content,
        json_or_none(tool_calls),
        json_or_none(tool_results),
    )


def insert_thread(
    cursor,
    plugin_slug: str,
    is_theme: bool,
    title: Optional[str],
    last_scan_session_id: Optional[int],
) -> int:
    cursor.execute(
        """
        INSERT INTO ai_threads (plugin_slug, is_theme, title, last_scan_session_id)
        VALUES (?, ?, ?, ?)
        """,
        (plugin_slug, normalize_thread_scope(is_theme), title, last_scan_session_id),
    )
    return cursor.lastrowid


def fetch_latest_thread(cursor, plugin_slug: str, is_theme: bool):
    cursor.execute(
        """
        SELECT * FROM ai_threads
        WHERE plugin_slug = ? AND is_theme = ?
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (plugin_slug, normalize_thread_scope(is_theme)),
    )
    return cursor.fetchone()


def fetch_threads_for_scope(cursor, plugin_slug: str, is_theme: bool):
    cursor.execute(
        """
        SELECT * FROM ai_threads
        WHERE plugin_slug = ? AND is_theme = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (plugin_slug, normalize_thread_scope(is_theme)),
    )
    return cursor.fetchall()


def fetch_thread_for_scope_by_id(cursor, thread_id: int, plugin_slug: str, is_theme: bool):
    cursor.execute(
        """
        SELECT * FROM ai_threads
        WHERE id = ? AND plugin_slug = ? AND is_theme = ?
        LIMIT 1
        """,
        (thread_id, plugin_slug, normalize_thread_scope(is_theme)),
    )
    return cursor.fetchone()


def count_thread_scope(cursor, plugin_slug: str, is_theme: bool) -> int:
    cursor.execute(
        "SELECT COUNT(*) AS count FROM ai_threads WHERE plugin_slug = ? AND is_theme = ?",
        (plugin_slug, normalize_thread_scope(is_theme)),
    )
    row = cursor.fetchone()
    return int(row["count"]) if row else 0


def build_thread_title(plugin_slug: str, title: Optional[str], sequence: int) -> str:
    explicit_title = str(title or "").strip()
    position = max(1, int(sequence or 1))
    if explicit_title:
        return explicit_title if position <= 1 else f"{explicit_title} Chat {position}"
    return f"Chat {position}"


def fetch_thread_by_id(cursor, thread_id: int):
    cursor.execute("SELECT * FROM ai_threads WHERE id = ?", (thread_id,))
    return cursor.fetchone()


def ensure_thread_for_scope(
    cursor,
    plugin_slug: str,
    is_theme: bool,
    title: Optional[str],
    last_scan_session_id: Optional[int],
):
    existing = fetch_latest_thread(cursor, plugin_slug, is_theme)
    if existing is not None:
        return existing
    sequence = count_thread_scope(cursor, plugin_slug, is_theme) + 1
    thread_id = insert_thread(
        cursor,
        plugin_slug,
        is_theme,
        build_thread_title(plugin_slug, title, sequence),
        last_scan_session_id,
    )
    return fetch_thread_by_id(cursor, thread_id)


def create_thread_record(
    cursor,
    plugin_slug: str,
    is_theme: bool,
    title: Optional[str],
    last_scan_session_id: Optional[int],
):
    sequence = count_thread_scope(cursor, plugin_slug, is_theme) + 1
    thread_id = insert_thread(
        cursor,
        plugin_slug,
        is_theme,
        build_thread_title(plugin_slug, title, sequence),
        last_scan_session_id,
    )
    return fetch_thread_by_id(cursor, thread_id)


def list_threads(cursor, plugin_slug: str, is_theme: bool):
    return fetch_threads_for_scope(cursor, plugin_slug, is_theme)


def fetch_thread_by_scope(cursor, plugin_slug: str, is_theme: bool):
    return fetch_latest_thread(cursor, plugin_slug, is_theme)


def fetch_thread_for_scope(cursor, thread_id: int, plugin_slug: str, is_theme: bool):
    return fetch_thread_for_scope_by_id(cursor, thread_id, plugin_slug, is_theme)


def finalize_run(cursor, run_id: int, status: str, error_message: Optional[str] = None) -> None:
    cursor.execute(
        """
        UPDATE ai_runs
        SET status = ?, error_message = ?, completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, error_message, run_id),
    )


def touch_thread_row(cursor, thread_id: int) -> None:
    cursor.execute(
        """
        UPDATE ai_threads
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (thread_id,),
    )


def fetch_message(cursor, message_id: int):
    cursor.execute("SELECT * FROM ai_messages WHERE id = ?", (message_id,))
    return cursor.fetchone()


def fetch_run(cursor, run_id: int):
    cursor.execute("SELECT * FROM ai_runs WHERE id = ?", (run_id,))
    return cursor.fetchone()


def fetch_run_events(cursor, run_id: int):
    cursor.execute(
        """
        SELECT * FROM ai_run_events
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        (run_id,),
    )
    return cursor.fetchall()


def fetch_run_tasks(cursor, run_id: int):
    cursor.execute(
        """
        SELECT * FROM ai_run_tasks
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        (run_id,),
    )
    return cursor.fetchall()


def insert_run_event(
    cursor,
    run_id: int,
    event_type: str,
    agent_name: Optional[str] = None,
    task_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO ai_run_events (run_id, event_type, agent_name, task_id, payload_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (run_id, event_type, agent_name, task_id, json_or_none(payload)),
    )
    return cursor.lastrowid


def upsert_run_task_row(
    cursor,
    run_id: int,
    task_id: str,
    title: str,
    status: str,
    assignee: Optional[str] = None,
    depends_on: Optional[List[str]] = None,
    result_text: Optional[str] = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO ai_run_tasks (
            run_id, task_id, title, status, assignee, depends_on_json, result_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id, task_id) DO UPDATE SET
            title = excluded.title,
            status = excluded.status,
            assignee = excluded.assignee,
            depends_on_json = excluded.depends_on_json,
            result_text = excluded.result_text,
            updated_at = CURRENT_TIMESTAMP
        """,
        (run_id, task_id, title, status, assignee, json_or_none(depends_on), result_text),
    )


def fetch_provider_by_profile_key(cursor, profile_key: str):
    cursor.execute(
        "SELECT * FROM ai_provider_settings WHERE profile_key = ? LIMIT 1",
        (profile_key,),
    )
    return cursor.fetchone()


def fetch_all_provider_profiles(cursor):
    cursor.execute(
        "SELECT * FROM ai_provider_settings ORDER BY is_active DESC, updated_at DESC, id DESC"
    )
    return cursor.fetchall()


def fetch_active_provider(cursor):
    cursor.execute(
        """
        SELECT * FROM ai_provider_settings
        WHERE is_active = 1
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """
    )
    return cursor.fetchone()


def fetch_thread_messages(cursor, thread_id: int):
    cursor.execute(
        """
        SELECT * FROM ai_messages
        WHERE thread_id = ?
        ORDER BY id ASC
        """,
        (thread_id,),
    )
    return cursor.fetchall()


def insert_message(
    cursor,
    thread_id: int,
    role: str,
    content: str,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    tool_results: Optional[List[Dict[str, Any]]] = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO ai_messages (thread_id, role, content, tool_calls_json, tool_results_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        serialize_message_payload(thread_id, role, content, tool_calls, tool_results),
    )
    return cursor.lastrowid


def fetch_run_approval(cursor, run_id: int):
    cursor.execute("SELECT * FROM ai_run_approvals WHERE run_id = ? LIMIT 1", (run_id,))
    return cursor.fetchone()


def fetch_thread_pending_approval(cursor, thread_id: int):
    cursor.execute(
        """
        SELECT a.*
        FROM ai_run_approvals a
        INNER JOIN ai_runs r ON r.id = a.run_id
        WHERE a.thread_id = ?
          AND a.status = 'pending'
          AND LOWER(COALESCE(r.status, '')) IN ('pending', 'running')
        ORDER BY a.id DESC
        LIMIT 1
        """,
        (thread_id,),
    )
    return cursor.fetchone()


def upsert_run_approval(
    cursor,
    run_id: int,
    thread_id: int,
    status: str,
    control_path: Optional[str] = None,
    mode: Optional[str] = None,
    request_payload: Optional[Dict[str, Any]] = None,
    decision: Optional[str] = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO ai_run_approvals (run_id, thread_id, status, control_path, mode, request_payload_json, decision, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END)
        ON CONFLICT(run_id) DO UPDATE SET
            status = excluded.status,
            control_path = COALESCE(excluded.control_path, ai_run_approvals.control_path),
            mode = COALESCE(excluded.mode, ai_run_approvals.mode),
            request_payload_json = COALESCE(excluded.request_payload_json, ai_run_approvals.request_payload_json),
            decision = COALESCE(excluded.decision, ai_run_approvals.decision),
            decided_at = CASE WHEN excluded.decision IS NOT NULL THEN CURRENT_TIMESTAMP ELSE ai_run_approvals.decided_at END,
            updated_at = CURRENT_TIMESTAMP
        """,
        (run_id, thread_id, status, control_path, mode, json_or_none(request_payload), decision, decision),
    )


def insert_run(
    cursor,
    thread_id: int,
    provider: str,
    provider_label: Optional[str],
    model: Optional[str],
    status: str,
    message_id: Optional[int],
    workspace_path: Optional[str],
) -> int:
    cursor.execute(
        """
        INSERT INTO ai_runs (
            thread_id, provider, provider_label, model, status, message_id, workspace_path
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            provider,
            provider_label or provider_label_for(provider),
            model,
            status,
            message_id,
            workspace_path,
        ),
    )
    return cursor.lastrowid

import json
from typing import Any, Dict, List, Optional

from ai.repository_utils import (
    create_thread_record,
    decode_message_row,
    fetch_message,
    fetch_thread_by_id,
    fetch_thread_by_scope,
    fetch_thread_for_scope,
    fetch_thread_messages,
    insert_message,
    json_or_none,
    list_threads,
    sanitize_thread_row,
    touch_thread_row,
)
from database.models import get_db


class ThreadRepositoryMixin:
    def get_or_create_thread(
        self,
        plugin_slug: str,
        is_theme: bool,
        title: Optional[str] = None,
        last_scan_session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        from ai.repository_utils import ensure_thread_for_scope

        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            thread = ensure_thread_for_scope(cursor, plugin_slug, is_theme, title, last_scan_session_id)
            conn.commit()
            return sanitize_thread_row(thread)

    def create_thread(
        self,
        plugin_slug: str,
        is_theme: bool,
        title: Optional[str] = None,
        last_scan_session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            thread = create_thread_record(cursor, plugin_slug, is_theme, title, last_scan_session_id)
            conn.commit()
            return sanitize_thread_row(thread)

    def list_threads_for_scope(self, plugin_slug: str, is_theme: bool) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            return [sanitize_thread_row(row) for row in list_threads(cursor, plugin_slug, is_theme)]

    def get_latest_thread_for_scope(self, plugin_slug: str, is_theme: bool) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_thread_by_scope(cursor, plugin_slug, is_theme)
            thread = sanitize_thread_row(row)
            return thread or None

    def get_thread_for_scope(self, thread_id: int, plugin_slug: str, is_theme: bool) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_thread_for_scope(cursor, thread_id, plugin_slug, is_theme)
            thread = sanitize_thread_row(row)
            return thread or None

    def get_thread(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_thread_by_id(cursor, thread_id)
            thread = sanitize_thread_row(row)
            return thread or None

    def create_message(
        self,
        thread_id: int,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            message_id = insert_message(cursor, thread_id, role, content, tool_calls, tool_results)
            touch_thread_row(cursor, thread_id)
            conn.commit()
            return decode_message_row(fetch_message(cursor, message_id))

    def list_messages(self, thread_id: int) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            return [decode_message_row(row) for row in fetch_thread_messages(cursor, thread_id)]

    def set_thread_title(self, thread_id: int, title: str) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ai_threads
                SET title = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, thread_id),
            )
            conn.commit()

    def update_thread_metadata(
        self,
        thread_id: int,
        title: Optional[str] = None,
        last_scan_session_id: Optional[int] = None,
    ) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ai_threads
                SET title = COALESCE(?, title),
                    last_scan_session_id = COALESCE(?, last_scan_session_id),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (title, last_scan_session_id, thread_id),
            )
            conn.commit()

    def get_thread_memory(self, thread_id: int) -> Dict[str, Any]:
        thread = self.get_thread(thread_id) or {}
        return {
            "conversation_summary": str(thread.get("conversation_summary") or ""),
            "analysis_summary": str(thread.get("analysis_summary") or ""),
            "important_files": list(thread.get("important_files") or []),
            "findings_summary": str(thread.get("findings_summary") or ""),
            "architecture_notes": str(thread.get("architecture_notes") or ""),
            "last_source_path": str(thread.get("last_source_path") or ""),
        }

    def update_thread_memory(
        self,
        thread_id: int,
        *,
        conversation_summary: Optional[str] = None,
        analysis_summary: Optional[str] = None,
        important_files: Optional[List[str]] = None,
        findings_summary: Optional[str] = None,
        architecture_notes: Optional[str] = None,
        last_source_path: Optional[str] = None,
    ) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ai_threads
                SET conversation_summary = COALESCE(?, conversation_summary),
                    analysis_summary = COALESCE(?, analysis_summary),
                    important_files_json = COALESCE(?, important_files_json),
                    findings_summary = COALESCE(?, findings_summary),
                    architecture_notes = COALESCE(?, architecture_notes),
                    last_source_path = COALESCE(?, last_source_path),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    conversation_summary,
                    analysis_summary,
                    json_or_none(important_files),
                    findings_summary,
                    architecture_notes,
                    last_source_path,
                    thread_id,
                ),
            )
            conn.commit()

    def delete_thread(self, thread_id: int) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_threads WHERE id = ?", (thread_id,))
            conn.commit()

    def list_thread_tool_audit(self, thread_id: int) -> List[Dict[str, Any]]:
        activity: List[Dict[str, Any]] = []
        for message in self.list_messages(thread_id):
            if message.get("tool_calls_json"):
                activity.extend(json.loads(message["tool_calls_json"]))
            if message.get("tool_results_json"):
                activity.extend(json.loads(message["tool_results_json"]))
        return activity

    def has_thread_scope(self, plugin_slug: str, is_theme: bool) -> bool:
        return self.get_latest_thread_for_scope(plugin_slug, is_theme) is not None


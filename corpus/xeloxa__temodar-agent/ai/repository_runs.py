from typing import Any, Dict, List, Optional

from ai.repository_utils import (
    decode_message_row,
    decode_row,
    decode_run_event_row,
    decode_run_task_row,
    fetch_message,
    fetch_run,
    fetch_run_events,
    fetch_run_tasks,
    finalize_run,
    insert_message,
    insert_run,
    insert_run_event,
    touch_thread_row,
    upsert_run_task_row,
)
from database.models import get_db


class RunRepositoryMixin:
    def create_run(
        self,
        thread_id: int,
        provider: str,
        provider_label: Optional[str] = None,
        model: Optional[str] = None,
        status: str = "pending",
        message_id: Optional[int] = None,
        workspace_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            run_id = insert_run(
                cursor,
                thread_id,
                provider,
                provider_label,
                model,
                status,
                message_id,
                workspace_path,
            )
            touch_thread_row(cursor, thread_id)
            conn.commit()
            return decode_row(fetch_run(cursor, run_id))

    def finish_run(self, run_id: int, status: str, error_message: Optional[str] = None) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            finalize_run(cursor, run_id, status, error_message)
            conn.commit()

    def fail_run_with_assistant_message(
        self,
        run_id: int,
        thread_id: int,
        content: str,
        error_message: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            message_id = insert_message(
                cursor,
                thread_id,
                "assistant",
                content,
                tool_calls,
                tool_results,
            )
            touch_thread_row(cursor, thread_id)
            finalize_run(cursor, run_id, "failed", error_message or content)
            conn.commit()
            return decode_message_row(fetch_message(cursor, message_id))

    def get_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_run(cursor, run_id)
            return decode_row(row) or None

    def create_run_event(
        self,
        run_id: int,
        event_type: str,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            event_id = insert_run_event(cursor, run_id, event_type, agent_name, task_id, payload)
            conn.commit()
            cursor.execute("SELECT * FROM ai_run_events WHERE id = ?", (event_id,))
            return decode_run_event_row(cursor.fetchone())

    def create_run_events(self, run_id: int, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            for event in events:
                insert_run_event(
                    cursor,
                    run_id,
                    event["event_type"],
                    event.get("agent_name"),
                    event.get("task_id"),
                    event.get("payload"),
                )
            conn.commit()

    def list_run_events(self, run_id: int) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            return [decode_run_event_row(row) for row in fetch_run_events(cursor, run_id)]

    def upsert_run_task(
        self,
        run_id: int,
        task_id: str,
        title: str,
        status: str,
        assignee: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        result_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            upsert_run_task_row(cursor, run_id, task_id, title, status, assignee, depends_on, result_text)
            conn.commit()
            cursor.execute(
                "SELECT * FROM ai_run_tasks WHERE run_id = ? AND task_id = ?",
                (run_id, task_id),
            )
            return decode_run_task_row(cursor.fetchone())

    def upsert_run_tasks(self, run_id: int, tasks: List[Dict[str, Any]]) -> None:
        if not tasks:
            return
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            for task in tasks:
                upsert_run_task_row(
                    cursor,
                    run_id,
                    task["task_id"],
                    task["title"],
                    task["status"],
                    task.get("assignee"),
                    task.get("depends_on"),
                    task.get("result_text"),
                )
            conn.commit()

    def list_run_tasks(self, run_id: int) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            return [decode_run_task_row(row) for row in fetch_run_tasks(cursor, run_id)]

    def list_thread_runs(self, thread_id: int) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM ai_runs WHERE thread_id = ? ORDER BY id ASC",
                (thread_id,),
            )
            return [decode_row(row) for row in cursor.fetchall()]

    def get_latest_run(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_runs WHERE thread_id = ? ORDER BY id DESC LIMIT 1", (thread_id,))
            row = cursor.fetchone()
            return decode_row(row) or None

    def fail_stale_thread_runs(self, thread_id: int, max_age_seconds: int = 30) -> int:
        threshold = max(5, int(max_age_seconds or 30))
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE ai_runs
                SET status = 'failed',
                    error_message = COALESCE(error_message, 'Run interrupted before completion.'),
                    completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP)
                WHERE thread_id = ?
                  AND status IN ('pending', 'running')
                  AND completed_at IS NULL
                  AND created_at <= datetime('now', ?)
                """,
                (thread_id, f"-{threshold} seconds"),
            )
            conn.commit()
            return int(cursor.rowcount or 0)

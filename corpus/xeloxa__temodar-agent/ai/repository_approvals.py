from typing import Any, Dict, Optional

from ai.repository_utils import decode_run_approval_row, fetch_run_approval, fetch_thread_pending_approval, upsert_run_approval
from database.models import get_db


class ApprovalRepositoryMixin:
    def upsert_run_approval(
        self,
        run_id: int,
        thread_id: int,
        status: str,
        control_path: Optional[str] = None,
        mode: Optional[str] = None,
        request_payload: Optional[Dict[str, Any]] = None,
        decision: Optional[str] = None,
    ) -> Dict[str, Any]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            upsert_run_approval(cursor, run_id, thread_id, status, control_path, mode, request_payload, decision)
            conn.commit()
            return decode_run_approval_row(fetch_run_approval(cursor, run_id))

    def get_run_approval(self, run_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_run_approval(cursor, run_id)
            return decode_run_approval_row(row) or None

    def get_thread_pending_approval(self, thread_id: int) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_thread_pending_approval(cursor, thread_id)
            return decode_run_approval_row(row) or None

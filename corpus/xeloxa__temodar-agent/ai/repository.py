from pathlib import Path
from typing import Optional

from ai.repository_approvals import ApprovalRepositoryMixin
from ai.repository_provider import ProviderRepositoryMixin
from ai.repository_runs import RunRepositoryMixin
from ai.repository_threads import ThreadRepositoryMixin
from database.models import get_db, init_db


class AIRepository(
    ProviderRepositoryMixin,
    ThreadRepositoryMixin,
    RunRepositoryMixin,
    ApprovalRepositoryMixin,
):
    """Repository for AI provider, thread, message, and run state."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        init_db(db_path)

    def clear_all_ai_state(self) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_runs")
            cursor.execute("DELETE FROM ai_messages")
            cursor.execute("DELETE FROM ai_threads")
            cursor.execute("DELETE FROM ai_provider_settings")
            conn.commit()

    def reset(self) -> None:
        self.clear_all_ai_state()

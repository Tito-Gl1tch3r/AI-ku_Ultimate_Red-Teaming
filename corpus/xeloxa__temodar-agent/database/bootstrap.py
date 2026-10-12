from pathlib import Path
from typing import Optional

from database.models import get_db, init_db


class DatabaseBootstrapper:
    """Initialize database schema and apply lightweight runtime migrations."""

    _catalog_backfill_attempted = False

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path

    def initialize(self) -> None:
        init_db(self.db_path)
        self._ensure_scan_results_columns()
        self._ensure_favorite_plugins_columns()
        self._ensure_ai_run_approvals_columns()

    def ensure_catalog_backfill(self, rebuild_catalog) -> None:
        if DatabaseBootstrapper._catalog_backfill_attempted:
            return

        DatabaseBootstrapper._catalog_backfill_attempted = True
        try:
            if not self._needs_catalog_backfill():
                return
            rebuild_catalog(reset=True)
        except Exception:
            pass

    def _needs_catalog_backfill(self) -> bool:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS c FROM plugin_catalog")
            catalog_count = int((cursor.fetchone() or {"c": 0})["c"])
            if catalog_count > 0:
                return False

            cursor.execute("SELECT COUNT(*) AS c FROM scan_results")
            results_count = int((cursor.fetchone() or {"c": 0})["c"])
            return results_count > 0

    def _ensure_scan_results_columns(self) -> None:
        self._ensure_columns(
            table_name="scan_results",
            columns={
                "is_duplicate": "INTEGER DEFAULT 0",
                "is_theme": "INTEGER DEFAULT 0",
                "wp_org_link": "TEXT",
                "cve_search_link": "TEXT",
                "wpscan_link": "TEXT",
                "trac_link": "TEXT",
            },
        )

    def _ensure_favorite_plugins_columns(self) -> None:
        self._ensure_columns(
            table_name="favorite_plugins",
            columns={
                "author_trusted": "INTEGER DEFAULT 0",
                "is_risky_category": "INTEGER DEFAULT 0",
                "is_user_facing": "INTEGER DEFAULT 0",
                "is_theme": "INTEGER DEFAULT 0",
                "wp_org_link": "TEXT",
                "risk_tags": "TEXT",
                "security_flags": "TEXT",
                "feature_flags": "TEXT",
                "code_analysis_json": "TEXT",
            },
        )

    def _ensure_ai_run_approvals_columns(self) -> None:
        self._ensure_columns(
            table_name="ai_run_approvals",
            columns={
                "control_path": "TEXT",
                "mode": "TEXT",
                "request_payload_json": "TEXT",
                "decision": "TEXT",
                "decided_at": "TIMESTAMP",
            },
        )

    def _ensure_columns(self, *, table_name: str, columns: dict[str, str]) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            for column_name, column_definition in columns.items():
                if self._column_exists(cursor, table_name, column_name):
                    continue
                try:
                    cursor.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                    )
                    conn.commit()
                except Exception:
                    pass

    @staticmethod
    def _column_exists(cursor, table_name: str, column_name: str) -> bool:
        try:
            cursor.execute(f"SELECT {column_name} FROM {table_name} LIMIT 1")
            return True
        except Exception:
            return False

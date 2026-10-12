"""
Temodar Agent Database Repository

CRUD operations for scan sessions and results.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from database.bootstrap import DatabaseBootstrapper
from database.models import get_db
from database.repository_catalog import CatalogRepositoryMixin
from database.repository_semgrep import SemgrepRepositoryMixin
from database.repository_sessions import SessionRepositoryMixin
from models import PluginResult


class ScanRepository(
    SessionRepositoryMixin,
    CatalogRepositoryMixin,
    SemgrepRepositoryMixin,
):
    """Repository for scan session and result operations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path
        self._session_created_at_cache: Dict[int, str] = {}
        self.bootstrapper = DatabaseBootstrapper(db_path)
        self.bootstrapper.initialize()
        self.bootstrapper.ensure_catalog_backfill(self.rebuild_plugin_catalog)

    def _get_session_created_at(self, cursor: Any, session_id: int) -> str:
        cached = self._session_created_at_cache.get(session_id)
        if cached:
            return cached

        cursor.execute(
            "SELECT created_at FROM scan_sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        created_at = row["created_at"] if row and row["created_at"] else ""
        self._session_created_at_cache[session_id] = created_at
        return created_at

    def _upsert_catalog_entry(
        self,
        cursor: Any,
        session_id: int,
        session_created_at: str,
        result: PluginResult,
    ) -> None:
        slug = result.slug
        is_theme = 1 if result.is_theme else 0

        cursor.execute(
            """
            SELECT id, seen_count, max_score_ever, first_seen_session_id, first_seen_at
            FROM plugin_catalog
            WHERE slug = ? AND is_theme = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (slug, is_theme),
        )
        existing = cursor.fetchone()

        if existing:
            catalog_id = existing["id"]
            previous_seen_count = int(existing["seen_count"] or 0)
            max_score_ever = max(
                int(existing["max_score_ever"] or 0), int(result.score or 0)
            )

            cursor.execute(
                """
                INSERT OR IGNORE INTO plugin_catalog_sessions (
                    catalog_id, session_id, seen_at, score_snapshot, version_snapshot,
                    installations_snapshot, days_since_update_snapshot, semgrep_findings_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    catalog_id,
                    session_id,
                    session_created_at,
                    int(result.score or 0),
                    result.version,
                    int(result.installations or 0),
                    int(result.days_since_update or 0),
                    None,
                ),
            )
            seen_increment = 1 if cursor.rowcount > 0 else 0

            cursor.execute(
                """
                UPDATE plugin_catalog
                SET last_seen_session_id = ?,
                    last_seen_at = ?,
                    seen_count = ?,
                    latest_version = ?,
                    latest_score = ?,
                    max_score_ever = ?,
                    latest_installations = ?,
                    latest_days_since_update = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    session_id,
                    session_created_at,
                    previous_seen_count + seen_increment,
                    result.version,
                    int(result.score or 0),
                    max_score_ever,
                    int(result.installations or 0),
                    int(result.days_since_update or 0),
                    catalog_id,
                ),
            )
            return

        cursor.execute(
            """
            INSERT INTO plugin_catalog (
                slug, is_theme,
                first_seen_session_id, last_seen_session_id,
                first_seen_at, last_seen_at,
                seen_count,
                latest_version, latest_score, max_score_ever,
                latest_installations, latest_days_since_update,
                latest_semgrep_findings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                slug,
                is_theme,
                session_id,
                session_id,
                session_created_at,
                session_created_at,
                1,
                result.version,
                int(result.score or 0),
                int(result.score or 0),
                int(result.installations or 0),
                int(result.days_since_update or 0),
                None,
            ),
        )
        catalog_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT OR IGNORE INTO plugin_catalog_sessions (
                catalog_id, session_id, seen_at, score_snapshot, version_snapshot,
                installations_snapshot, days_since_update_snapshot, semgrep_findings_snapshot
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                catalog_id,
                session_id,
                session_created_at,
                int(result.score or 0),
                result.version,
                int(result.installations or 0),
                int(result.days_since_update or 0),
                None,
            ),
        )

    def _refresh_catalog_entry(self, cursor: Any, catalog_id: int) -> None:
        cursor.execute(
            """
            SELECT COUNT(*) AS c, MIN(seen_at) AS first_seen, MAX(seen_at) AS last_seen
            FROM plugin_catalog_sessions
            WHERE catalog_id = ?
            """,
            (catalog_id,),
        )
        stats = cursor.fetchone()
        link_count = int((stats["c"] if stats else 0) or 0)

        if link_count <= 0:
            cursor.execute("DELETE FROM plugin_catalog WHERE id = ?", (catalog_id,))
            return

        cursor.execute(
            """
            SELECT session_id, score_snapshot, version_snapshot,
                   installations_snapshot, days_since_update_snapshot
            FROM plugin_catalog_sessions
            WHERE catalog_id = ?
            ORDER BY seen_at ASC, id ASC
            LIMIT 1
            """,
            (catalog_id,),
        )
        first_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT session_id, score_snapshot, version_snapshot,
                   installations_snapshot, days_since_update_snapshot
            FROM plugin_catalog_sessions
            WHERE catalog_id = ?
            ORDER BY seen_at DESC, id DESC
            LIMIT 1
            """,
            (catalog_id,),
        )
        last_row = cursor.fetchone()

        cursor.execute(
            """
            SELECT MAX(COALESCE(score_snapshot, 0)) AS max_score
            FROM plugin_catalog_sessions
            WHERE catalog_id = ?
            """,
            (catalog_id,),
        )
        max_row = cursor.fetchone()
        max_score = int((max_row["max_score"] if max_row else 0) or 0)

        cursor.execute(
            """
            UPDATE plugin_catalog
            SET first_seen_session_id = ?,
                last_seen_session_id = ?,
                first_seen_at = ?,
                last_seen_at = ?,
                seen_count = ?,
                latest_version = ?,
                latest_score = ?,
                max_score_ever = ?,
                latest_installations = ?,
                latest_days_since_update = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                first_row["session_id"] if first_row else None,
                last_row["session_id"] if last_row else None,
                stats["first_seen"],
                stats["last_seen"],
                link_count,
                last_row["version_snapshot"] if last_row else None,
                int((last_row["score_snapshot"] if last_row else 0) or 0),
                max_score,
                int((last_row["installations_snapshot"] if last_row else 0) or 0),
                int((last_row["days_since_update_snapshot"] if last_row else 0) or 0),
                catalog_id,
            ),
        )


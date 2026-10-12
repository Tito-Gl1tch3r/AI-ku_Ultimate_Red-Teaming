import json
from typing import Any, Dict, List, Optional, Set, Tuple

from config import DEFAULT_QUERY_LIMIT, MAX_QUERY_LIMIT
from database.models import get_db
from models import PluginResult, ScanConfig, ScanStatus

SESSION_OVERFETCH_MULTIPLIER = 4
SESSION_OVERFETCH_MINIMUM = 200
SESSION_RESULT_LIMIT = MAX_QUERY_LIMIT * 10 - 1


def _parse_json_value(raw: Any) -> Any:
    """Parse JSON database payloads safely."""
    return json.loads(raw) if raw else None


def _parse_csv_list(raw: Any) -> List[str]:
    """Convert persisted CSV-style text back to a list."""
    return str(raw).split(",") if raw else []


def _serialize_code_analysis(result: PluginResult) -> str | None:
    """Serialize code analysis payload for storage."""
    if not result.code_analysis:
        return None
    return json.dumps(
        {
            "dangerous_functions": result.code_analysis.dangerous_functions,
            "ajax_endpoints": result.code_analysis.ajax_endpoints,
            "file_operations": result.code_analysis.file_operations,
            "sql_queries": result.code_analysis.sql_queries,
            "nonce_usage": result.code_analysis.nonce_usage,
            "sanitization_issues": result.code_analysis.sanitization_issues,
        }
    )


def _serialize_session_row(row: Dict[str, Any], *, status_override: str | None = None, is_merged: bool = False) -> Dict[str, Any]:
    """Normalize a scan_sessions row for API consumers."""
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "status": status_override or row["status"],
        "is_merged": is_merged,
        "config": _parse_json_value(row.get("config_json")),
        "total_found": row["total_found"],
        "high_risk_count": row["high_risk_count"],
        "error_message": row["error_message"],
    }


def _serialize_result_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a scan_results row for API consumers."""
    result = {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "version": row["version"],
        "score": row["score"],
        "installations": row["installations"],
        "days_since_update": row["days_since_update"],
        "tested_wp_version": row["tested_wp_version"],
        "author_trusted": bool(row["author_trusted"]),
        "is_risky_category": bool(row["is_risky_category"]),
        "is_user_facing": bool(row["is_user_facing"]),
        "is_duplicate": bool(row["is_duplicate"]) if "is_duplicate" in row.keys() else False,
        "is_theme": bool(row["is_theme"]) if "is_theme" in row.keys() else False,
        "risk_tags": _parse_csv_list(row["risk_tags"]),
        "security_flags": _parse_csv_list(row["security_flags"]),
        "feature_flags": _parse_csv_list(row["feature_flags"]),
        "download_link": row["download_link"],
        "wp_org_link": row["wp_org_link"] if "wp_org_link" in row.keys() else None,
        "cve_search_link": row["cve_search_link"],
        "wpscan_link": row["wpscan_link"],
        "trac_link": row["trac_link"],
    }
    if row["code_analysis_json"]:
        result["code_analysis"] = json.loads(row["code_analysis_json"])
    return result


class SessionRepositoryMixin:
    """Session and scan result repository behavior."""

    _VALID_SORT_COLUMNS = {
        "score": "score",
        "installations": "installations",
        "days_since_update": "days_since_update",
        "name": "name",
        "slug": "slug",
    }
    _VALID_SORT_ORDERS = {"ASC", "DESC"}

    def create_session(self, config: ScanConfig) -> int:
        """Create a new scan session and return its ID."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scan_sessions (config_json, status)
                VALUES (?, ?)
            """,
                (json.dumps(config.to_dict()), ScanStatus.PENDING.value),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def update_session_status(
        self,
        session_id: int,
        status: ScanStatus,
        total_found: Optional[int] = None,
        high_risk_count: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update session status and statistics."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params: List[Any] = [status.value]

            if total_found is not None:
                updates.append("total_found = ?")
                params.append(total_found)
            if high_risk_count is not None:
                updates.append("high_risk_count = ?")
                params.append(high_risk_count)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            params.append(session_id)
            cursor.execute(
                f"""
                UPDATE scan_sessions
                SET {", ".join(updates)}
                WHERE id = ?
            """,
                params,
            )
            conn.commit()

    def _mark_result_duplicate_if_needed(self, cursor: Any, session_id: int, result: PluginResult) -> None:
        """Mark results duplicated when the same slug exists in another session."""
        cursor.execute(
            """
            SELECT 1 FROM scan_results
            WHERE slug = ? AND session_id != ?
            LIMIT 1
        """,
            (result.slug, session_id),
        )
        if cursor.fetchone():
            result.is_duplicate = True

    def save_result(self, session_id: int, result: PluginResult) -> int:
        """Save a scan result for a session."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            self._mark_result_duplicate_if_needed(cursor, session_id, result)
            code_analysis_json = _serialize_code_analysis(result)

            cursor.execute(
                """
                INSERT INTO scan_results (
                    session_id, slug, name, version, score, installations,
                    days_since_update, tested_wp_version, author_trusted,
                    is_risky_category, is_user_facing, is_duplicate, is_theme, risk_tags, security_flags,
                    feature_flags, download_link, wp_org_link, cve_search_link, wpscan_link, trac_link, code_analysis_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    result.slug,
                    result.name,
                    result.version,
                    result.score,
                    result.installations,
                    result.days_since_update,
                    result.tested_wp_version,
                    1 if result.author_trusted else 0,
                    1 if result.is_risky_category else 0,
                    1 if result.is_user_facing else 0,
                    1 if result.is_duplicate else 0,
                    1 if result.is_theme else 0,
                    ",".join(result.risk_tags),
                    ",".join(result.security_flags),
                    ",".join(result.feature_flags),
                    result.download_link,
                    result.wp_org_link,
                    result.cve_search_link,
                    result.wpscan_link,
                    result.trac_link,
                    code_analysis_json,
                ),
            )
            inserted_id = cursor.lastrowid or 0
            session_created_at = self._get_session_created_at(cursor, session_id)
            self._upsert_catalog_entry(cursor, session_id, session_created_at, result)
            conn.commit()
            return inserted_id

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get a scan session by ID."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scan_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return _serialize_session_row(dict(row)) if row else None

    def _fetch_recent_session_rows(self, cursor: Any, limit: int) -> List[Dict[str, Any]]:
        """Fetch recent session rows with overfetch for deduplication."""
        cursor.execute(
            """
            SELECT * FROM scan_sessions
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (max(limit * SESSION_OVERFETCH_MULTIPLIER, SESSION_OVERFETCH_MINIMUM),),
        )
        return [dict(row) for row in cursor.fetchall()]

    def _fetch_slugs_by_session(self, cursor: Any, session_ids: List[int]) -> Dict[int, Set[str]]:
        """Load all result slugs for a set of sessions in one query."""
        if not session_ids:
            return {}
        placeholders = ",".join(["?"] * len(session_ids))
        cursor.execute(
            f"""
            SELECT session_id, slug
            FROM scan_results
            WHERE session_id IN ({placeholders})
        """,
            session_ids,
        )
        slugs_by_session: Dict[int, Set[str]] = {}
        for row in cursor.fetchall():
            sid = int(row["session_id"])
            slugs_by_session.setdefault(sid, set()).add(str(row["slug"]))
        return slugs_by_session

    def _build_completed_signature_counts(
        self,
        rows: List[Dict[str, Any]],
        slugs_by_session: Dict[int, Set[str]],
    ) -> Dict[Tuple[bool, Tuple[str, ...]], int]:
        """Count duplicate completed-session signatures for merged presentation."""
        counts: Dict[Tuple[bool, Tuple[str, ...]], int] = {}
        for row in rows:
            sid = int(row["id"])
            slug_signature = tuple(sorted(slugs_by_session.get(sid, set())))
            has_results = bool(slug_signature)
            if row["status"] not in {ScanStatus.COMPLETED.value, ScanStatus.MERGED.value} or not has_results:
                continue
            signature = (has_results, slug_signature)
            counts[signature] = counts.get(signature, 0) + 1
        return counts

    def get_all_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scan sessions, deduplicated by identical result slug-set, most recent first."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            rows = self._fetch_recent_session_rows(cursor, limit)
            if not rows:
                return []

            slugs_by_session = self._fetch_slugs_by_session(
                cursor,
                [int(row["id"]) for row in rows],
            )
            signature_counts = self._build_completed_signature_counts(rows, slugs_by_session)

            sessions: List[Dict[str, Any]] = []
            seen_signatures: Set[Tuple[bool, Tuple[str, ...]]] = set()
            for row in rows:
                sid = int(row["id"])
                slug_signature = tuple(sorted(slugs_by_session.get(sid, set())))
                has_results = bool(slug_signature)
                signature = (has_results, slug_signature)
                is_completed_with_results = (
                    row["status"] in {ScanStatus.COMPLETED.value, ScanStatus.MERGED.value}
                    and has_results
                )
                if is_completed_with_results:
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)

                is_merged = row["status"] == ScanStatus.MERGED.value or (
                    is_completed_with_results and signature_counts.get(signature, 0) > 1
                )
                status_value = ScanStatus.MERGED.value if is_merged else row["status"]
                sessions.append(
                    _serialize_session_row(
                        row,
                        status_override=status_value,
                        is_merged=is_merged,
                    )
                )
                if len(sessions) >= limit:
                    break
            return sessions

    def get_session_results(
        self,
        session_id: int,
        sort_by: str = "score",
        sort_order: str = "desc",
        limit: int = DEFAULT_QUERY_LIMIT,
    ) -> List[Dict[str, Any]]:
        """Get results for a scan session."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            safe_sort_column = self._VALID_SORT_COLUMNS.get(sort_by, "score")
            requested_sort_order = str(sort_order or "").upper()
            safe_sort_order = (
                "DESC"
                if requested_sort_order in self._VALID_SORT_ORDERS and requested_sort_order == "DESC"
                else "ASC"
            )
            safe_limit = max(1, min(int(limit or DEFAULT_QUERY_LIMIT), SESSION_RESULT_LIMIT))
            cursor.execute(
                f"""
                SELECT * FROM scan_results
                WHERE session_id = ?
                ORDER BY {safe_sort_column} {safe_sort_order}
                LIMIT ?
            """,
                (session_id, safe_limit),
            )
            return [_serialize_result_row(dict(row)) for row in cursor.fetchall()]

    def delete_session(self, session_id: int) -> bool:
        """Delete a scan session and its results."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT catalog_id FROM plugin_catalog_sessions WHERE session_id = ?",
                (session_id,),
            )
            affected_catalog_ids = [int(row["catalog_id"]) for row in cursor.fetchall()]
            cursor.execute("DELETE FROM plugin_catalog_sessions WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM scan_results WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM scan_sessions WHERE id = ?", (session_id,))
            session_deleted = cursor.rowcount > 0
            for catalog_id in set(affected_catalog_ids):
                self._refresh_catalog_entry(cursor, catalog_id)
            conn.commit()
            return session_deleted

    def get_latest_session_by_config(
        self,
        config_dict: Dict[str, Any],
        exclude_id: int,
    ) -> Optional[int]:
        """Find the most recent completed session with identical configuration."""
        config_str = json.dumps(config_dict, sort_keys=True)
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, config_json FROM scan_sessions
                WHERE status IN ('completed', 'merged') AND id != ?
                ORDER BY id DESC LIMIT 20
            """,
                (exclude_id,),
            )
            for row in cursor.fetchall():
                try:
                    row_config = json.loads(row["config_json"])
                except Exception:
                    continue
                if json.dumps(row_config, sort_keys=True) == config_str:
                    return int(row["id"])
        return None

    def get_result_slugs(self, session_id: int) -> List[str]:
        """Get list of slugs for a session."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT slug FROM scan_results WHERE session_id = ?", (session_id,))
            return [str(row["slug"]) for row in cursor.fetchall()]

    def mark_session_merged(self, session_id: int) -> None:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE scan_sessions
                SET status = ?, created_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (ScanStatus.MERGED.value, session_id),
            )
            conn.commit()

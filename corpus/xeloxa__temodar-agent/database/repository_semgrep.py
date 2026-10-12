import json
from typing import Any, Dict, List, Optional

from database.models import get_db


class SemgrepRepositoryMixin:
    """Semgrep repository behavior."""

    def create_semgrep_scan(self, slug: str, version: Optional[str] = None) -> int:
        """Create a new Semgrep scan record."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO semgrep_scans (slug, version, status)
                VALUES (?, ?, 'pending')
            """,
                (slug, version),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def update_semgrep_scan(
        self,
        scan_id: int,
        status: str,
        summary: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Update Semgrep scan status and summary."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            updates = ["status = ?"]
            params: List[Any] = [status]

            if summary:
                updates.append("summary_json = ?")
                params.append(json.dumps(summary))

            if error:
                updates.append("error_message = ?")
                params.append(error)

            if status in ["completed", "failed"]:
                updates.append("completed_at = CURRENT_TIMESTAMP")

            params = params + [scan_id]

            cursor.execute(
                f"""
                UPDATE semgrep_scans
                SET {", ".join(updates)}
                WHERE id = ?
            """,
                params,
            )
            conn.commit()

    def save_semgrep_finding(self, scan_id: int, finding: Dict[str, Any]):
        """Save a single Semgrep finding."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO semgrep_findings (
                    scan_id, rule_id, message, severity, file_path,
                    line_number, code_snippet, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    scan_id,
                    finding.get("check_id"),
                    finding.get("extra", {}).get("message"),
                    finding.get("extra", {}).get("severity"),
                    finding.get("path"),
                    finding.get("start", {}).get("line"),
                    finding.get("extra", {}).get("lines"),
                    json.dumps(finding.get("extra", {}).get("metadata", {})),
                ),
            )
            conn.commit()

    def get_semgrep_scan(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get the latest Semgrep scan for a plugin."""
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*
                FROM semgrep_scans s
                INNER JOIN (
                    SELECT MAX(id) AS max_id
                    FROM semgrep_scans
                    WHERE slug = ?
                ) latest ON s.id = latest.max_id
            """,
                (slug,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            scan = dict(row)
            if scan["summary_json"]:
                scan["summary"] = json.loads(scan["summary_json"])

            # Get findings
            cursor.execute(
                """
                SELECT * FROM semgrep_findings WHERE scan_id = ?
            """,
                (scan["id"],),
            )

            scan["findings"] = [dict(r) for r in cursor.fetchall()]
            return scan

    def get_semgrep_stats_for_slugs(self, slugs: List[str]) -> Dict[str, Any]:
        """Aggregate Semgrep statistics for a list of plugin slugs using each slug's latest scan."""
        if not slugs:
            return {
                "total_findings": 0,
                "breakdown": {},
                "scanned_count": 0,
                "running_count": 0,
                "pending_count": 0,
                "failed_count": 0,
                "completed_count": 0,
            }

        placeholders = ",".join(["?"] * len(slugs))
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"""
                SELECT s.slug, s.status, s.summary_json
                FROM semgrep_scans s
                INNER JOIN (
                    SELECT slug, MAX(id) AS max_id
                    FROM semgrep_scans
                    WHERE slug IN ({placeholders})
                    GROUP BY slug
                ) latest ON s.id = latest.max_id
            """,
                slugs,
            )

            rows = cursor.fetchall()
            if not rows:
                return {
                    "total_findings": 0,
                    "breakdown": {},
                    "scanned_count": 0,
                    "running_count": 0,
                    "pending_count": 0,
                    "failed_count": 0,
                    "completed_count": 0,
                }

            breakdown: Dict[str, int] = {}
            completed_count = 0
            failed_count = 0
            pending_count = 0
            running_count = 0

            for row in rows:
                status = str(row["status"] or "").lower()
                if status == "completed":
                    completed_count += 1
                    summary = json.loads(row["summary_json"]) if row["summary_json"] else {}
                    row_breakdown = (
                        summary.get("breakdown", {}) if isinstance(summary, dict) else {}
                    )
                    for sev, count in (row_breakdown or {}).items():
                        breakdown[str(sev)] = int(breakdown.get(str(sev), 0)) + int(
                            count or 0
                        )
                elif status == "failed":
                    failed_count += 1
                elif status == "running":
                    running_count += 1
                else:
                    pending_count += 1

            total_findings = sum(int(v or 0) for v in breakdown.values())
            scanned_count = completed_count + failed_count

            return {
                "total_findings": total_findings,
                "breakdown": breakdown,
                "scanned_count": scanned_count,
                "running_count": running_count,
                "pending_count": pending_count,
                "failed_count": failed_count,
                "completed_count": completed_count,
            }

    def get_semgrep_statuses_for_slugs(
        self, slugs: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get the latest scan status and findings count for a list of slugs."""
        if not slugs:
            return {}

        placeholders = ",".join(["?"] * len(slugs))
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()

            # Get latest scan for each slug
            cursor.execute(
                f"""
                SELECT s.slug, s.status, s.summary_json
                FROM semgrep_scans s
                INNER JOIN (
                    SELECT slug, MAX(id) as max_id
                    FROM semgrep_scans
                    WHERE slug IN ({placeholders})
                    GROUP BY slug
                ) latest ON s.id = latest.max_id
            """,
                slugs,
            )

            results = {}
            for row in cursor.fetchall():
                slug = row["slug"]
                summary = json.loads(row["summary_json"]) if row["summary_json"] else {}
                results[slug] = {
                    "status": row["status"],
                    "findings_count": summary.get("total_findings", 0),
                    "breakdown": summary.get("breakdown", {}),
                }
            return results

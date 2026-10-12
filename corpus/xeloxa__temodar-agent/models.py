"""
Temodar Agent Data Models

All dataclasses and type definitions for the application.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ScanStatus(Enum):
    """Scan session status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    MERGED = "merged"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CodeAnalysisResult:
    """Code analysis result for plugins/themes."""

    dangerous_functions: List[str] = field(default_factory=list)
    ajax_endpoints: List[str] = field(default_factory=list)
    file_operations: List[str] = field(default_factory=list)
    sql_queries: List[str] = field(default_factory=list)
    nonce_usage: List[str] = field(default_factory=list)
    sanitization_issues: List[str] = field(default_factory=list)


@dataclass
class ScanConfig:
    """Scan configuration parameters."""

    # Basic scanning options
    pages: int = 5
    limit: int = 0
    min_installs: int = 1000
    max_installs: int = 0
    sort: str = "updated"  # new, updated, popular

    # Filter flags
    smart: bool = False
    abandoned: bool = False
    user_facing: bool = False
    themes: bool = False

    # Time filtering
    min_days: int = 0
    max_days: int = 0

    # Aggressive mode
    aggressive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "pages": self.pages,
            "limit": self.limit,
            "min_installs": self.min_installs,
            "max_installs": self.max_installs,
            "sort": self.sort,
            "smart": self.smart,
            "abandoned": self.abandoned,
            "user_facing": self.user_facing,
            "themes": self.themes,
            "min_days": self.min_days,
            "max_days": self.max_days,
            "aggressive": self.aggressive,
        }


@dataclass
class PluginResult:
    """Structured result for a scanned plugin."""

    # Basic info
    name: str
    slug: str
    version: str

    # Scores & metrics
    score: int = 0
    relative_risk: str = ""
    installations: int = 0
    days_since_update: int = 0
    tested_wp_version: str = "?"

    # Flags
    author_trusted: bool = False
    is_risky_category: bool = False
    is_user_facing: bool = False
    is_duplicate: bool = False
    is_theme: bool = False

    # Analysis data
    risk_tags: List[str] = field(default_factory=list)
    security_flags: List[str] = field(default_factory=list)
    feature_flags: List[str] = field(default_factory=list)
    code_analysis: Optional[CodeAnalysisResult] = None

    # Links
    download_link: str = ""
    wp_org_link: str = ""
    cve_search_link: str = ""
    wpscan_link: str = ""
    trac_link: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses and reports."""
        result = {
            "name": self.name,
            "slug": self.slug,
            "version": self.version,
            "score": self.score,
            "relative_risk": self.relative_risk,
            "installations": self.installations,
            "days_since_update": self.days_since_update,
            "tested_wp_version": self.tested_wp_version,
            "author_trusted": self.author_trusted,
            "is_risky_category": self.is_risky_category,
            "is_user_facing": self.is_user_facing,
            "is_duplicate": self.is_duplicate,
            "is_theme": self.is_theme,
            "risk_tags": self.risk_tags,
            "security_flags": self.security_flags,
            "feature_flags": self.feature_flags,
            "download_link": self.download_link,
            "wp_org_link": self.wp_org_link,
            "cve_search_link": self.cve_search_link,
            "wpscan_link": self.wpscan_link,
            "trac_link": self.trac_link,
        }

        if self.code_analysis:
            result["code_analysis"] = {
                "dangerous_functions": self.code_analysis.dangerous_functions,
                "ajax_endpoints": self.code_analysis.ajax_endpoints,
                "file_operations": self.code_analysis.file_operations,
                "sql_queries": self.code_analysis.sql_queries,
                "nonce_usage": self.code_analysis.nonce_usage,
                "sanitization_issues": self.code_analysis.sanitization_issues,
            }

        return result

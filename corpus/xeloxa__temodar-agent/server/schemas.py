"""
Pydantic Models for API
"""

from typing import Optional, List, Dict, Any
from typing_extensions import Literal
from pydantic import BaseModel, Field, HttpUrl


class ScanRequest(BaseModel):
    pages: int = 5
    limit: int = 0
    min_installs: int = 1000
    max_installs: int = 0
    sort: str = "updated"
    smart: bool = False
    abandoned: bool = False
    user_facing: bool = False
    themes: bool = False
    min_days: int = 0
    max_days: int = 0
    aggressive: bool = False


class DownloadRequest(BaseModel):
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    download_url: HttpUrl


class FavoritePluginRequest(BaseModel):
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    name: str = Field(..., min_length=1, max_length=300)
    version: Optional[str] = Field(default=None, max_length=100)
    score: int = 0
    installations: int = 0
    days_since_update: int = 0
    tested_wp_version: Optional[str] = Field(default=None, max_length=50)
    is_theme: bool = False
    download_link: Optional[str] = Field(default=None, max_length=2000)
    wp_org_link: Optional[str] = Field(default=None, max_length=2000)
    cve_search_link: Optional[str] = Field(default=None, max_length=2000)
    wpscan_link: Optional[str] = Field(default=None, max_length=2000)
    trac_link: Optional[str] = Field(default=None, max_length=2000)
    author_trusted: bool = False
    is_risky_category: bool = False
    is_user_facing: bool = False
    risk_tags: List[str] = Field(default_factory=list)
    security_flags: List[str] = Field(default_factory=list)
    feature_flags: List[str] = Field(default_factory=list)
    code_analysis: Optional[Dict[str, Any]] = None


class SemgrepRuleRequest(BaseModel):
    id: str = Field(
        ...,
        min_length=1,
        max_length=120,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    pattern: str = Field(..., min_length=1, max_length=10000)
    message: str = Field(..., min_length=1, max_length=500)
    severity: Literal["ERROR", "WARNING", "INFO"] = "WARNING"
    languages: List[str] = Field(default_factory=lambda: ["php"], min_length=1)


class SemgrepRulesetRequest(BaseModel):
    ruleset: str = Field(..., min_length=1, max_length=200)


class SemgrepBulkToggleRequest(BaseModel):
    enabled: bool


AIProviderLiteral = Literal["anthropic", "openai", "copilot", "gemini", "grok"]


class AISettingsRequest(BaseModel):
    provider: AIProviderLiteral
    profile_key: Optional[str] = Field(default=None, min_length=1, max_length=200)
    display_name: Optional[str] = Field(default=None, max_length=200)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    model: str = Field(..., min_length=1, max_length=200)
    models: List[str] = Field(default_factory=list)
    base_url: Optional[HttpUrl] = None
    is_active: bool = True


class AISettingsTestRequest(BaseModel):
    provider: AIProviderLiteral
    profile_key: Optional[str] = Field(default=None, min_length=1, max_length=200)
    display_name: Optional[str] = Field(default=None, max_length=200)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=1000)
    model: str = Field(..., min_length=1, max_length=200)
    models: List[str] = Field(default_factory=list)
    base_url: Optional[HttpUrl] = None


class AISettingsProfileResponse(BaseModel):
    id: int
    profile_key: str
    display_name: str
    provider: str
    provider_label: Optional[str] = None
    model: Optional[str] = None
    models: List[str] = Field(default_factory=list)
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    api_key_masked: Optional[str] = None
    has_api_key: bool = False
    is_active: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AISettingsStatsResponse(BaseModel):
    total_profiles: int = 0
    active_profiles: int = 0
    provider_count: int = 0
    configured_models: int = 0


class AISettingsDashboardResponse(BaseModel):
    active_profile: Optional[AISettingsProfileResponse] = None
    profiles: List[AISettingsProfileResponse] = Field(default_factory=list)
    stats: AISettingsStatsResponse = Field(default_factory=AISettingsStatsResponse)


class AISettingsTestResponse(BaseModel):
    ok: bool
    message: str
    provider: str
    model: str
    profile_key: Optional[str] = None


class AIPluginThreadRequest(BaseModel):
    plugin_slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    is_theme: bool = False
    title: Optional[str] = Field(default=None, max_length=300)
    last_scan_session_id: Optional[int] = Field(default=None, gt=0)


class AIThreadListResponse(BaseModel):
    threads: List["AIThreadResponse"] = Field(default_factory=list)


class AIMessageCreateRequest(BaseModel):
    thread_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1, max_length=20000)
    last_scan_session_id: Optional[int] = Field(default=None, gt=0)
    profile_key: Optional[str] = Field(default=None, min_length=1, max_length=200)
    model: Optional[str] = Field(default=None, min_length=1, max_length=200)
    strategy: Optional[Literal["auto", "agent", "team", "tasks", "fanout"]] = "auto"
    trace_enabled: Optional[bool] = True
    output_schema: Optional[Dict[str, Any]] = None
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    fanout: Optional[Dict[str, Any]] = None
    loop_detection: Optional[Dict[str, Any]] = None
    approval_mode: Optional[Literal["off", "auto_approve", "manual"]] = "off"
    before_run: Optional[Dict[str, Any]] = None
    after_run: Optional[Dict[str, Any]] = None


class AIMessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    tool_results: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: str


class AIThreadResponse(BaseModel):
    id: int
    plugin_slug: str
    is_theme: bool
    title: Optional[str] = None
    last_scan_session_id: Optional[int] = None
    created_at: str
    updated_at: str
    source_available: bool = False
    source_context_mode: str = "metadata_only"
    source_path: str = ""
    workspace_path: str = ""


class AISourcePrepareResponse(BaseModel):
    ok: bool
    thread: "AIThreadResponse"


class AIRunApprovalResponse(BaseModel):
    run_id: int
    thread_id: int
    status: str
    mode: Optional[str] = None
    decision: Optional[str] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AIRunApprovalDecisionRequest(BaseModel):
    plugin_slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    is_theme: bool = False
    decision: Literal["approved", "rejected"]


class AIThreadMessagesResponse(BaseModel):
    messages: List[AIMessageResponse]
    has_pending_run: bool = False
    team_events: List[Dict[str, Any]] = Field(default_factory=list)
    pending_approval: Optional[AIRunApprovalResponse] = None


class AIThreadUpdateRequest(BaseModel):
    plugin_slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    is_theme: bool = False
    title: str = Field(..., min_length=1, max_length=300)


class AIThreadDeleteRequest(BaseModel):
    plugin_slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="WordPress slug (letters, numbers, underscore, hyphen)",
    )
    is_theme: bool = False


class AIMessageExecutionResponse(BaseModel):
    user_message: AIMessageResponse
    assistant_message: AIMessageResponse
    events: List[Dict[str, Any]] = Field(default_factory=list)
    run_id: Optional[int] = None
    team_events: List[Dict[str, Any]] = Field(default_factory=list)
    tasks: List[Dict[str, Any]] = Field(default_factory=list)
    agents: List[Dict[str, Any]] = Field(default_factory=list)
    structured: Optional[Any] = None
    pending_approval: Optional[AIRunApprovalResponse] = None
    thread: Optional[AIThreadResponse] = None

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Literal
from zoneinfo import ZoneInfo
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
    new_password_confirm: str = Field(min_length=8)

class SessionOut(BaseModel):
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_seen: Optional[datetime] = None
    current: bool = False

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class UserOut(BaseModel):
    id: int
    email: EmailStr

class APIKeyCreate(BaseModel):
    name: str

class APIKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class APIKeyCreated(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str
    created_at: datetime

class UserCampaignRow(BaseModel):
    id: int
    name: str
    date: datetime

class ServerCreate(BaseModel):
    name: str
    host: str
    port: int
    use_tls: bool = True

    @validator('name')
    def _name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None

    @validator('name')
    def _name_not_blank(cls, v: Optional[str]):
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class ServerOut(ServerCreate):
    id: int

class ServerDuplicate(BaseModel):
    name: str

class ProfileCreate(BaseModel):
    profile_name: str
    display_name: str
    email: EmailStr
    password: str

    @validator('profile_name')
    def _profile_name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class ProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    @validator('profile_name')
    def _profile_name_not_blank(cls, v: Optional[str]):
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class ProfileOut(BaseModel):
    id: int
    profile_name: str
    display_name: str
    email: EmailStr

class ProfileDuplicate(BaseModel):
    profile_name: str

class TargetCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    extra_field: Optional[str] = None 
    extra: Optional[dict] = None

class TargetListCreate(BaseModel):
    name: str

    @validator('name')
    def _name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class TargetListUpdate(BaseModel):
    name: str

    @validator('name')
    def _name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

class TargetListOut(BaseModel):
    id: int
    name: str
    target_count: Optional[int] = None

class TargetListDuplicate(BaseModel):
    name: str

class CampaignCreate(BaseModel):
    name: str
    run_now: bool = False
    server_id: int
    profile_id: int
    template_id: int
    list_ids: List[int]
    use_batches: bool = False
    batch_size: Optional[int] = None
    batch_delay_seconds: Optional[int] = None
    custom_headers: Optional[Dict[str, str]] = None
    scheduled_start_at: Optional[str] = None
    remove_duplicate_targets: bool = False

    @validator('name')
    def _name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v

    @validator('list_ids')
    def _at_least_one_list(cls, v):
        if not v or len([x for x in v if x is not None]) == 0:
            raise ValueError("At least one target list must be selected")
        return v

class CampaignOut(BaseModel):
    id: int
    name: str
    status: str

class CampaignDetailOut(BaseModel):
    id: int
    name: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    scheduled_start_at: Optional[str]
    server: str
    profile: str
    profile_email: Optional[str]
    template: str
    lists: List[str]
    total: int
    sent: int
    failed: int
    pending: int
    custom_headers: Optional[Dict[str, str]] = None
    use_batches: bool = False
    batch_size: Optional[int] = None
    batch_delay_seconds: Optional[int] = None
    remove_duplicate_targets: bool = False
    last_error: Optional[str] = None
    last_error_trace: Optional[str] = None
    last_error_at: Optional[str] = None
    has_calendar_invite: bool = False
    has_calendar_reschedule: bool = False
    has_calendar_cancellation: bool = False
    calendar_uid: Optional[str] = None
    meeting_sequence: Optional[int] = None
    calendar_ics_prodid: Optional[str] = None
    meeting_summary: Optional[str] = None
    meeting_begin: Optional[str] = None
    meeting_end: Optional[str] = None
    meeting_tz: Optional[str] = None
    meeting_provider: Optional[Literal['none', 'teams', 'gmeet']] = None
    meeting_url: Optional[str] = None

class TargetStatus(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    status: str
    sent_at: Optional[str]
    error: Optional[str]
    opened: bool = False
    opened_at: Optional[str] = None

class CampaignVarRow(BaseModel):
    name: str
    email: EmailStr
    values: Dict[str, str]

class CampaignVariablesOut(BaseModel):
    static_vars: Dict[str, str]
    headers: List[str]
    rows: List[CampaignVarRow]


class StatsOut(BaseModel):
    total_campaigns: int
    active_campaigns: int
    paused_campaigns: int
    archived_campaigns: int
    scheduled_campaigns: int
    total_targets: int
    emails_sent_today: int

class MarkOpenedIn(BaseModel):
    email: Optional[EmailStr] = None
    var_name: Optional[str] = None
    var_value: Optional[str] = None
    opened: bool = True
    bulk: Optional[bool] = None

class MarkOpenedOut(BaseModel):
    updated: int

class GlobalVarIn(BaseModel):
    name: str
    kind: str
    value: Optional[str] = None
    pattern: Optional[str] = None
    tenant_guid: Optional[str] = None
    per_recipient: Optional[bool] = False

class GlobalVarOut(BaseModel):
    id: int
    name: str
    kind: str
    value: Optional[str] = None
    pattern: Optional[str] = None
    tenant_guid: Optional[str] = None
    per_recipient: bool = False

class SettingsIn(BaseModel):
    values: Dict[str, str]

class SettingsOut(BaseModel):
    values: Dict[str, str]

class AttachmentOut(BaseModel):
    id: int
    filename: str
    mime_type: str
    size: int

class CalendarAttendee(BaseModel):
    cn: str
    email: EmailStr

class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    calendar_enabled: bool = False
    meeting_summary: Optional[str] = None
    organizer_cn: Optional[str] = None
    organizer_email: Optional[EmailStr] = None
    attendees: Optional[List[CalendarAttendee]] = None
    disable_forwarding: bool = False
    calendar_priority: int = Field(default=2, ge=1, le=3)
    calendar_categories: Optional[List[str]] = None
    calendar_private: Optional[bool] = None
    meeting_begin: Optional[str] = None
    meeting_end: Optional[str] = None
    meeting_provider: Literal['none', 'teams', 'gmeet'] = 'none'
    meeting_url: Optional[str] = None
    meeting_tz: Optional[str] = None
    location: Optional[str] = None
    allow_responses: bool = False
    include_all_targets_as_attendees: Optional[bool] = False
    is_calendar_reschedule: bool = False
    is_calendar_cancellation: bool = False
    meeting_uid: Optional[str] = None
    meeting_sequence: Optional[int] = None

    @validator('name')
    def _name_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Name cannot be empty")
        return v
    
    @validator('subject')
    def _subject_not_blank(cls, v: str):
        if v is None or not v.strip():
            raise ValueError("Subject cannot be empty")
        return v
    
    @validator("meeting_tz")
    def _valid_tz(cls, v):
        if v is None or v.strip() == "":
            return None
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("meeting_tz must be a valid IANA timezone")
        return v

    @validator("calendar_categories", pre=True, always=True)
    def _sanitize_categories(cls, v):
        if v is None:
            return None
        if not isinstance(v, (list, tuple)):
            raise TypeError("calendar_categories must be a list of strings")
        out = []
        for item in v:
            if item is None:
                continue
            s = str(item).replace("\r", " ").replace("\n", " ").strip()
            if s:
                out.append(s)
        return out or None
    
    @validator('is_calendar_reschedule')
    def _reschedule_exclusive(cls, v, values):
        if v and values.get('calendar_enabled'):
            raise ValueError("A template cannot be both an invite and a reschedule")
        return v
    
    @validator('is_calendar_cancellation')
    def _exclusive_mode(cls, v, values):
        if v and values.get('calendar_enabled'):
            raise ValueError("A template cannot be both an invite and a cancellation")
        if v and values.get('is_calendar_reschedule'):
            raise ValueError("A template cannot be both a reschedule and a cancellation")
        return v

    @validator('meeting_sequence')
    def _seq_nonneg(cls, v, values):
        if values.get('is_calendar_cancellation') or values.get('is_calendar_reschedule'):
            if v is None:
                raise ValueError("meeting_sequence is required for cancellations and reschedules")
            if v < 0:
                raise ValueError("meeting_sequence must be >= 0")
        return v

    @validator('meeting_uid')
    def _uid_required_for_calendar(cls, v, values):
        if (values.get('is_calendar_cancellation') or values.get('is_calendar_reschedule')) and not (v and v.strip()):
            raise ValueError("meeting_uid is required for cancellations and reschedules")
        return v

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    attachments: Optional[List[Dict]] = None
    calendar_enabled: Optional[bool] = None
    meeting_summary: Optional[str] = None
    organizer_cn: Optional[str] = None
    organizer_email: Optional[EmailStr] = None
    attendees: Optional[List[CalendarAttendee]] = None
    disable_forwarding: Optional[bool] = None
    calendar_priority: Optional[int] = Field(default=None, ge=1, le=3)
    calendar_categories: Optional[List[str]] = None
    calendar_private: Optional[bool] = None
    meeting_begin: Optional[str] = None
    meeting_end: Optional[str] = None
    meeting_provider: Optional[Literal['none', 'teams', 'gmeet']] = None
    meeting_url: Optional[str] = None
    meeting_tz: Optional[str] = None
    location: Optional[str] = None
    allow_responses: Optional[bool] = None
    include_all_targets_as_attendees: Optional[bool] = False
    is_calendar_reschedule: bool = False
    is_calendar_cancellation: bool = False
    meeting_uid: Optional[str] = None
    meeting_sequence: Optional[int] = None

    @validator('name')
    def _name_not_blank(cls, v: Optional[str]):
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v

    @validator('subject')
    def _subject_not_blank(cls, v: Optional[str]):
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Subject cannot be empty")
        return v

    @validator("meeting_tz")
    def _valid_tz(cls, v):
        if v is None or v.strip() == "":
            return None
        try:
            ZoneInfo(v)
        except Exception:
            raise ValueError("meeting_tz must be a valid IANA timezone")
        return v

    @validator("calendar_categories", pre=True, always=True)
    def _sanitize_categories(cls, v):
        if v is None:
            return None
        if not isinstance(v, (list, tuple)):
            raise TypeError("calendar_categories must be a list of strings")
        out = []
        for item in v:
            if item is None:
                continue
            s = str(item).replace("\r", " ").replace("\n", " ").strip()
            if s:
                out.append(s)
        return out or None
    
    @validator('is_calendar_reschedule')
    def _reschedule_exclusive(cls, v, values):
        if v and values.get('calendar_enabled'):
            raise ValueError("A template cannot be both an invite and a reschedule")
        return v
    
    @validator('is_calendar_cancellation')
    def _exclusive_mode(cls, v, values):
        if v and values.get('calendar_enabled'):
            raise ValueError("A template cannot be both an invite and a cancellation")
        if v and values.get('is_calendar_reschedule'):
            raise ValueError("A template cannot be both a reschedule and a cancellation")
        return v

    @validator('meeting_sequence')
    def _seq_nonneg(cls, v, values):
        if values.get('is_calendar_cancellation') or values.get('is_calendar_reschedule'):
            if v is None:
                raise ValueError("meeting_sequence is required for cancellations and reschedules")
            if v < 0:
                raise ValueError("meeting_sequence must be >= 0")
        return v

    @validator('meeting_uid')
    def _uid_required_for_calendar(cls, v, values):
        if (values.get('is_calendar_cancellation') or values.get('is_calendar_reschedule')) and not (v and v.strip()):
            raise ValueError("meeting_uid is required for cancellations and reschedules")
        return v

class TemplateOut(BaseModel):
    id: int
    name: str
    subject: str
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    attachments: List[AttachmentOut] = []
    attachments_count: int = 0
    calendar_attachments_count: int = 0
    calendar_enabled: bool = False
    meeting_summary: Optional[str] = None
    organizer_cn: Optional[str] = None
    organizer_email: Optional[EmailStr] = None
    attendees: List[CalendarAttendee] = []
    disable_forwarding: bool = False
    calendar_priority: int = 2
    calendar_categories: Optional[List[str]] = None
    calendar_private: Optional[bool] = None
    meeting_begin: Optional[str] = None
    meeting_end: Optional[str] = None
    meeting_provider: Literal['none', 'teams', 'gmeet'] = 'none'
    meeting_url: Optional[str] = None
    meeting_tz: Optional[str] = None
    location: Optional[str] = None
    allow_responses: bool = False
    include_all_targets_as_attendees: Optional[bool] = False
    is_calendar_reschedule: bool = False
    is_calendar_cancellation: bool = False
    meeting_uid: Optional[str] = None
    meeting_sequence: Optional[int] = None

class TemplateDuplicate(BaseModel):
    name: str
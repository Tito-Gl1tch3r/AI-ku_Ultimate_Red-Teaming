from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey, Text, LargeBinary, DateTime, JSON, text
from datetime import datetime
from .database import Base
from sqlalchemy.dialects.postgresql import JSONB

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    api_keys = relationship("APIKey", back_populates="user")

class UserSession(Base):
    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)  # JWT ID
    user_agent: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))  # IPv4/IPv6
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

class SendingServer(Base):
    __tablename__ = "sending_servers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=587)
    use_tls: Mapped[bool] = mapped_column(Boolean, default=True)

class SenderProfile(Base):
    __tablename__ = "sender_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    profile_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    enc_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str | None] = mapped_column(Text)
    calendar_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting_summary: Mapped[str | None] = mapped_column(String(255))
    organizer_cn: Mapped[str | None] = mapped_column(String(255))
    organizer_email: Mapped[str | None] = mapped_column(String(255))
    attendees: Mapped[dict | None] = mapped_column(JSON)
    disable_forwarding: Mapped[bool] = mapped_column(Boolean, default=False)
    calendar_priority: Mapped[int | None] = mapped_column(Integer, default=2)
    calendar_categories: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    calendar_private: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    meeting_begin: Mapped[str | None] = mapped_column(String(15))
    meeting_end: Mapped[str | None] = mapped_column(String(15))
    meeting_provider: Mapped[str] = mapped_column(String(16), nullable=False, server_default="none")
    meeting_url: Mapped[str | None] = mapped_column(Text)
    meeting_tz: Mapped[str | None] = mapped_column(String(64))
    location: Mapped[str | None] = mapped_column(String(255))
    allow_responses: Mapped[bool] = mapped_column(Boolean, default=True)
    include_all_targets_as_attendees: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_calendar_reschedule: Mapped[bool] = mapped_column(Boolean, default=False)
    is_calendar_cancellation: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meeting_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

class TemplateCalendarAttachment(Base):
    __tablename__ = "template_calendar_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

class TemplateAttachment(Base):
    __tablename__ = "template_attachments"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

class TargetList(Base):
    __tablename__ = "target_lists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

class Target(Base):
    __tablename__ = "targets"
    id: Mapped[int] = mapped_column(primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("target_lists.id"), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    extra_field: Mapped[str | None] = mapped_column(String(255)) 
    extra: Mapped[dict | None] = mapped_column(JSON)

class CampaignTargetList(Base):
    __tablename__ = "campaign_target_lists"
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), primary_key=True)
    list_id: Mapped[int] = mapped_column(ForeignKey("target_lists.id"), primary_key=True)

class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("sending_servers.id", ondelete="SET NULL"),
        nullable=True
    )
    server_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("sender_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    profile_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    profile_email_snapshot: Mapped[str | None] = mapped_column(String(255))
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True
    )
    template_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    selected_list_names: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    used_var_names: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    use_batches: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_size: Mapped[int | None] = mapped_column(Integer)
    batch_delay_seconds: Mapped[int | None] = mapped_column(Integer)
    custom_headers: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="stopped")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    remove_duplicate_targets: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    last_error: Mapped[str | None] = mapped_column(Text)
    last_error_trace: Mapped[str | None] = mapped_column(Text)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime)
    calendar_uid: Mapped[str | None] = mapped_column(String(255))
    meeting_summary: Mapped[str | None] = mapped_column(String(255))
    meeting_begin: Mapped[str | None] = mapped_column(String(15))
    meeting_end: Mapped[str | None] = mapped_column(String(15))
    meeting_tz: Mapped[str | None] = mapped_column(String(64))
    meeting_provider: Mapped[str] = mapped_column(String(16), nullable=False, server_default="none")
    meeting_url: Mapped[str | None] = mapped_column(Text)
    include_all_targets_as_attendees = mapped_column(Boolean, nullable=True)
    is_calendar_reschedule: Mapped[bool] = mapped_column(Boolean, default=False)
    is_calendar_cancellation: Mapped[bool] = mapped_column(Boolean, default=False)
    meeting_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    target_id: Mapped[int | None] = mapped_column(
        ForeignKey("targets.id", ondelete="SET NULL"), index=True, nullable=True
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    gen_vars: Mapped[dict | None] = mapped_column(JSON)
    target_first_name: Mapped[str | None] = mapped_column(String(255))
    target_last_name:  Mapped[str | None] = mapped_column(String(255))
    target_extra_field: Mapped[str | None] = mapped_column(String(255))
    opened: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)

class GlobalVar(Base):
    __tablename__ = "global_vars"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True) 
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    value: Mapped[str | None] = mapped_column(Text)
    pattern: Mapped[str | None] = mapped_column(String(512))
    tenant_guid: Mapped[str | None] = mapped_column(String(64))
    per_recipient: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class GlobalSetting(Base):
    __tablename__ = "global_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    value: Mapped[str | None] = mapped_column(Text)
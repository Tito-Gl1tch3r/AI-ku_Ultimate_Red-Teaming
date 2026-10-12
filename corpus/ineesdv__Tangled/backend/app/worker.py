import traceback
from sqlalchemy.orm import Session
from time import sleep
from datetime import datetime
from .database import SessionLocal
from .models import Campaign, CampaignTargetList, EmailLog, SenderProfile, SendingServer, EmailTemplate, TemplateAttachment, Target, GlobalVar, GlobalSetting, TemplateCalendarAttachment
from .emailer import decrypt_password, render_body, compose_email, attach_files, send_smtp
from .config import settings
from .routers.core_routes import _snapshot_calendar_fields_if_empty, _track_used_vars_from_log, _cleanup_pending_emails, _campaign_used_vars, _snapshot_used_vars_if_empty
from .routers.config_routes import _gen_teams_meeting_url
import random, string
import rstr
import threading
import re
import base64
import uuid
import json
import urllib.parse
from .jinja_sandbox import env_text
from .emailer import _strip_html, build_calendar_ics  

DEFAULT_MAIL_DELAY = getattr(settings, 'default_mail_delay', 0.3)
MAX_CONCURRENT_CAMPAIGNS = getattr(settings, 'max_concurrent_campaigns', 10)
WORKER_POLL_INTERVAL = getattr(settings, 'worker_poll_interval', 2.5)

campaign_semaphore = threading.Semaphore(MAX_CONCURRENT_CAMPAIGNS)
active_campaign_threads = []
active_threads_lock = threading.Lock()

def _uid_hex(n=64):
    return "".join(random.choice("0123456789ABCDEF") for _ in range(n))

def _gen_calendar_uid_from_settings(db: Session) -> str:
    try:
        row = db.query(GlobalSetting).filter(GlobalSetting.key == "calendar_uid_pattern").first()
        pattern = (row.value or "").strip() if row else ""
        if pattern:
            try:
                uid = rstr.xeger(pattern)
                uid = re.sub(r'[\r\n]+', '', uid).strip()
                uid = uid.encode('ascii', 'ignore').decode('ascii')

                if not uid:
                    raise ValueError("empty")

                if len(uid) > 255:
                    raise ValueError("too long")
                
                return uid
            
            except Exception:
                pass
    except Exception:
        pass
    # Fallback
    return _uid_hex(64)

def _random_id(n=8):
    alphabet = string.ascii_letters
    return "".join(random.choice(alphabet) for _ in range(n))

def _merge_extra_attendees(base_extra: list[dict], bulk_all: list[dict], current_email: str) -> list[dict]:
    out: list[dict] = []

    # Explicit attendees
    for a in (base_extra or []):
        em = (a.get("email") or a.get("Email") or "").strip()

        if not em:
            continue

        cn = (a.get("cn") or a.get("CN") or "").strip()
        out.append({"cn": cn, "email": em})

    # All targets excluding current
    cur_lc = (current_email or "").strip().lower()
    for a in (bulk_all or []):
        em = (a.get("email") or "").strip()
        
        if not em:
            continue

        if em.lower() == cur_lc:
            continue
        
        cn = (a.get("cn") or "").strip()
        out.append({"cn": cn, "email": em})

    return out

def _escape_ics_text(text: str) -> str:
    if not text:
        return ""
    t = str(text)
    return t.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")

def build_context(db: Session, target: Target):
    context = {
        "firstName": target.first_name or "",
        "lastName": target.last_name or "",
        "email": target.email,
        "extraField": target.extra_field or "",
        "randomID": _random_id(8),
        **(target.extra or {})
    }

    # Global settings
    settings_map = {s.key: s.value for s in db.query(GlobalSetting).all()}
    context["cfg"] = settings_map

    # Regex variables
    regex_generated: dict[str, str] = {}

    for v in db.query(GlobalVar).all():
        if v.kind == "text":
            context[v.name] = v.value or ""
        elif v.kind == "regex":
            try:
                val = rstr.xeger(v.pattern or ".*")
            except Exception:
                val = ""
            context[v.name] = val
            regex_generated[v.name] = val
        elif v.kind == "teams":
            if getattr(v, "per_recipient", False):
                # per-recipient Teams meeting
                tg = (v.tenant_guid or "").strip()
                try:
                    url = _gen_teams_meeting_url(tg)
                except Exception:
                    url = ""
                context[v.name] = url
                regex_generated[v.name] = url
            else:
                # static Teams variable
                context[v.name] = v.value or ""

    return context, regex_generated

def _attempt_send_email(db: Session, log: EmailLog, c: Campaign, target: Target, profile: SenderProfile,
                        server: SendingServer, template: EmailTemplate, attachments: list, context: dict,
                        rendered: dict, calendar_ics: str, cal_method: str, target_cn: str, message_id_val: str) -> tuple[bool, str]:

    msg = compose_email(
        profile.display_name,
        profile.email,
        target.email,
        rendered["subject"],
        rendered["html"],
        rendered["text"],
        c.custom_headers or {},
        calendar_ics=calendar_ics,
        calendar_method=cal_method or None,
        to_display_name=target_cn,
        message_id=message_id_val
    )

    atts = [{"filename": a.filename, "mime_type": a.mime_type, "data": a.data} for a in attachments]
    attach_files(msg, atts)

    try:
        password = decrypt_password(profile.enc_password)
        ehlo = server.host if server else settings.smtp_default_ehlo
        send_smtp(server.host, server.port, server.use_tls, ehlo, profile.email, password, msg, profile.email, target.email, via_tcp_forwarder=True)
        return True, ""
    
    except Exception as e:
        return False, str(e)

def run_campaign_send(campaign_id: int):
    with campaign_semaphore:
        db: Session = SessionLocal()
        try:
            c = db.query(Campaign).get(campaign_id)
            if not c: 
                return

            # Make sure snapshots exist before sending
            template = db.query(EmailTemplate).get(c.template_id)
            _snapshot_calendar_fields_if_empty(db, c, template)
            _snapshot_used_vars_if_empty(db, c, template)
            db.commit()

            # Ensure a single UID per campaign for calendar invites
            if (template and template.calendar_enabled and not template.is_calendar_cancellation 
                and not template.is_calendar_reschedule and not getattr(c, "calendar_uid", None)):
                c.calendar_uid = _gen_calendar_uid_from_settings(db)
                _snapshot_calendar_fields_if_empty(db, c, template)
                db.commit()
            
            template = db.query(EmailTemplate).get(c.template_id)

            include_all = bool(getattr(c, "include_all_targets_as_attendees", False)) \
                        and (template and (template.calendar_enabled or template.is_calendar_reschedule)) \
                        and not (template and template.is_calendar_cancellation)

            _all_targets_attendees: list[dict] = []
            if include_all:
                rows = (
                    db.query(EmailLog.to_email, EmailLog.target_first_name, EmailLog.target_last_name)
                    .filter(EmailLog.campaign_id == c.id)
                    .order_by(EmailLog.id.asc())
                    .all()
                )

                # Keep order, no dedupe
                for em, fn, ln in rows:
                    if not em:
                        continue
                    cn = f"{(fn or '').strip()} {(ln or '').strip()}".strip()
                    _all_targets_attendees.append({"cn": cn, "email": em.strip()})

            # Retry configuration
            RETRY_DELAYS = [60, 300]
            MAX_RETRIES = len(RETRY_DELAYS)

            while True:
                db.refresh(c)
                if c.status != "running":
                    break
                
                # Get next pending email
                log = (
                    db.query(EmailLog)
                    .filter(EmailLog.campaign_id == c.id, EmailLog.status == "pending")
                    .order_by(EmailLog.id.asc())
                    .first()
                )
                
                if not log:
                    # Clean up pending/retrying emails before marking complete
                    _cleanup_pending_emails(db, c.id, "cancelled")
                    c.status = "completed"
                    c.completed_at = datetime.utcnow()
                    db.commit()
                    break

                # Load email data
                target = db.query(Target).get(log.target_id)
                profile = db.query(SenderProfile).get(c.profile_id)
                server = db.query(SendingServer).get(c.server_id)
                template = db.query(EmailTemplate).get(c.template_id)
                attachments = db.query(TemplateAttachment).filter(TemplateAttachment.template_id==template.id).all()
                context, regex_map = build_context(db, target)
                rendered = render_body(template.subject, template.body_html, template.body_text, context)
                
                # Persist the generated regex variables
                used_names = _campaign_used_vars(db, c, template)
                gen_vars = dict(regex_map or {})
                if "randomID" in context:
                    gen_vars["randomID"] = context["randomID"]
                log.gen_vars = gen_vars or None

                _track_used_vars_from_log(db, c, template, log.gen_vars)

                target_cn = " ".join([x for x in [(target.first_name or ""), (target.last_name or "")] if x]).strip() or target.email
                calendar_ics = None
                
                if template.is_calendar_cancellation:
                    tzid = (template.meeting_tz or settings.scheduler_timezone)

                    uid = c.calendar_uid or template.meeting_uid
                    if not uid:
                        log.status = "failed"
                        log.error = "Cancellation requires a meeting UID"
                        db.commit()

                        # Stop the campaign
                        c.status = "paused"
                        c.last_error = "Cancellation requires a meeting UID"
                        c.last_error_at = datetime.utcnow()
                        db.commit()
                        break

                    seq = c.meeting_sequence
                    if seq is None:
                        seq = template.meeting_sequence if (template.meeting_sequence is not None) else 1
                        c.meeting_sequence = seq

                    raw_desc = rendered["text"] or _strip_html(rendered["html"] or "")
                    description_plain = _escape_ics_text(raw_desc)

                    raw_location = template.location or ""
                    rendered_location = None
                    if raw_location:
                        try:
                            rendered_location = env_text.from_string(raw_location).render(**context)
                        except Exception:
                            rendered_location = raw_location
                    
                    calendar_ics = build_calendar_ics(
                        uid=uid,
                        tzid=tzid,
                        prodid=context["cfg"].get("ics_prodid") or "Microsoft Exchange Server 2019",
                        is_cancel=True,
                        organizer_cn=template.organizer_cn or (profile.display_name or ""),
                        organizer_email=template.organizer_email or profile.email,
                        target_cn=target_cn,
                        target_email=target.email,
                        meeting_summary=template.meeting_summary or rendered["subject"] or "",
                        description_plain=description_plain,
                        begin_local=template.meeting_begin or "",
                        end_local=template.meeting_end or "",
                        location=rendered_location,
                        priority=int(template.calendar_priority or 2),
                        disable_forwarding=bool(template.disable_forwarding),
                        extra_attendees=template.attendees or [],
                        allow_responses=bool(getattr(template, "allow_responses", True)),
                        calendar_categories=(template.calendar_categories or None),
                        calendar_private=getattr(template, "calendar_private", None),
                        sequence=int(seq),
                    )
                
                elif template.is_calendar_reschedule:
                    raw_desc = rendered["text"] or _strip_html(rendered["html"] or "")
                    description_plain = _escape_ics_text(raw_desc)

                    tzid = (template.meeting_tz or settings.scheduler_timezone)

                    cal_atts = (
                        db.query(TemplateCalendarAttachment)
                        .filter(TemplateCalendarAttachment.template_id == template.id)
                        .all()
                    )

                    attach_lines = []
                    for ca in cal_atts:
                        if not ca or not (ca.data or b""):
                            continue
                        b64 = base64.b64encode(ca.data or b"").decode("ascii")
                        attach_lines.append(
                            f"ATTACH;ENCODING=BASE64;VALUE=BINARY;FMTTYPE={ca.mime_type};X-FILENAME={ca.filename}:{b64}\r\n"
                        )

                    uid = c.calendar_uid or template.meeting_uid
                    if not uid:
                        log.status = "failed"
                        log.error = "Reschedule requires a meeting UID"
                        db.commit()
                        # Stop the campaign
                        c.status = "paused"
                        c.last_error = "Reschedule requires a meeting UID"
                        c.last_error_at = datetime.utcnow()
                        db.commit()
                        break
                    
                    seq = c.meeting_sequence
                    if seq is None:
                        seq = template.meeting_sequence if (template.meeting_sequence is not None) else 1
                        c.meeting_sequence = seq

                    prov = (getattr(template, "meeting_provider", None) or "none").lower()
                    meeting_url_rendered = None
                    if prov in ("teams", "gmeet"):
                        raw_url = template.meeting_url or ""
                        try:
                            meeting_url_rendered = env_text.from_string(raw_url).render(**context) if raw_url else None
                        except Exception:
                            meeting_url_rendered = raw_url or None
                    
                    raw_location = template.location or ""
                    rendered_location = None
                    if raw_location:
                        try:
                            rendered_location = env_text.from_string(raw_location).render(**context)
                        except Exception:
                            rendered_location = raw_location

                    # Attendees
                    base_extra = template.attendees or []
                    if include_all:
                        extra_attendees = _merge_extra_attendees(base_extra, _all_targets_attendees, target.email)
                    else:
                        extra_attendees = base_extra

                    calendar_ics = build_calendar_ics(
                        uid=uid,
                        tzid=tzid,
                        prodid=context["cfg"].get("ics_prodid") or "Microsoft Exchange Server 2019",
                        is_cancel=False,
                        organizer_cn=template.organizer_cn or (profile.display_name or ""),
                        organizer_email=template.organizer_email or profile.email,
                        target_cn=target_cn,
                        target_email=target.email,
                        meeting_summary=template.meeting_summary or rendered["subject"] or "",
                        description_plain=description_plain,
                        begin_local=template.meeting_begin or "",
                        end_local=template.meeting_end or "",
                        priority=int(template.calendar_priority or 2),
                        disable_forwarding=bool(template.disable_forwarding),
                        extra_attendees=extra_attendees,
                        meeting_provider=prov,
                        meeting_url=(meeting_url_rendered or None),
                        location=rendered_location,
                        allow_responses=bool(getattr(template, "allow_responses", True)),
                        attach_lines=attach_lines,
                        calendar_categories=(template.calendar_categories or None),
                        calendar_private=getattr(template, "calendar_private", None),
                        sequence=int(seq),
                    )
                
                elif template.calendar_enabled:
                    raw_desc = rendered["text"] or _strip_html(rendered["html"] or "")
                    description_plain = _escape_ics_text(raw_desc)

                    tzid = (template.meeting_tz or settings.scheduler_timezone)

                    cal_atts = (
                        db.query(TemplateCalendarAttachment)
                        .filter(TemplateCalendarAttachment.template_id == template.id)
                        .all()
                    )
                    attach_lines = []
                    for ca in cal_atts:
                        if not ca or not (ca.data or b""):
                            continue
                        b64 = base64.b64encode(ca.data or b"").decode("ascii")
                        attach_lines.append(
                            f"ATTACH;ENCODING=BASE64;VALUE=BINARY;FMTTYPE={ca.mime_type};X-FILENAME={ca.filename}:{b64}\r\n"
                        )
                    
                    prov = (getattr(template, "meeting_provider", None) or "none").lower()
                    meeting_url_rendered = None
                    if prov in ("teams", "gmeet"):
                        raw_url = template.meeting_url or ""
                        try:
                            meeting_url_rendered = env_text.from_string(raw_url).render(**context) if raw_url else None
                        except Exception:
                            meeting_url_rendered = raw_url or None
                    
                    raw_location = template.location or ""
                    rendered_location = None
                    if raw_location:
                        try:
                            rendered_location = env_text.from_string(raw_location).render(**context)
                        except Exception:
                            rendered_location = raw_location

                    # Attendees
                    base_extra = template.attendees or []
                    if include_all:
                        extra_attendees = _merge_extra_attendees(base_extra, _all_targets_attendees, target.email)
                    else:
                        extra_attendees = base_extra

                    calendar_ics = build_calendar_ics(
                        uid=c.calendar_uid,
                        tzid=tzid,
                        prodid=context["cfg"].get("ics_prodid") or "Microsoft Exchange Server 2019",
                        is_cancel=False,
                        organizer_cn=template.organizer_cn or (profile.display_name or ""),
                        organizer_email=template.organizer_email or profile.email,
                        target_cn=target_cn,
                        target_email=target.email,
                        meeting_summary=template.meeting_summary or rendered["subject"] or "",
                        description_plain=description_plain,
                        begin_local=template.meeting_begin or "",
                        end_local=template.meeting_end or "",
                        priority=int(template.calendar_priority or 2),
                        disable_forwarding=bool(template.disable_forwarding),
                        extra_attendees=extra_attendees,
                        meeting_provider=prov,
                        meeting_url=(meeting_url_rendered or None),
                        location=rendered_location,
                        allow_responses=bool(getattr(template, "allow_responses", True)),
                        attach_lines=attach_lines,
                        calendar_categories=(template.calendar_categories or None),
                        calendar_private=getattr(template, "calendar_private", None),
                        sequence=int(0),
                    )

                # Message-ID
                message_id_regex = (context["cfg"].get("message_id_pattern") or "").strip()
                message_id_val = None

                if message_id_regex:
                    try:
                        generated = rstr.xeger(message_id_regex)

                        # Normalize and validate
                        generated = re.sub(r'[\r\n]+', '', generated).strip()
                        generated = generated.encode('ascii', 'ignore').decode('ascii')

                        if re.fullmatch(r'[^<>@]+@[^<>@]+', generated):
                            candidate = f'<{generated}>'
                        else:
                            candidate = generated

                        if not re.fullmatch(r'<[^<>@]+@[^<>@]+>', candidate):
                            raise ValueError('Message-ID must look like <local@domain>.')
                        
                        message_id_val = candidate

                    except Exception:
                        # Fallback handled by compose_email
                        message_id_val = None
                
                cal_method = ""
                if template.is_calendar_cancellation:
                    cal_method = "CANCEL"
                elif template.is_calendar_reschedule:
                    cal_method = "REQUEST"
                elif template.calendar_enabled:
                    cal_method = "REQUEST"

                # Retry logic
                retry_attempt = 0
                final_success = False
                final_error = ""
                manual_pause = False
                
                while retry_attempt <= MAX_RETRIES:
                    # Check campaign status before each attempt
                    db.refresh(c)
                    if c.status != "running":
                        print(f"[campaign {c.id}] Campaign no longer running (status={c.status}), stopping retry loop", 
                              flush=True)
                        manual_pause = True
                        break
                    
                    if retry_attempt > 0:
                        # Wait before retry
                        delay = RETRY_DELAYS[retry_attempt - 1]
                        print(f"[campaign {c.id}] Waiting {delay}s before retry {retry_attempt}/{MAX_RETRIES} for {target.email}", 
                              flush=True)
                        
                        # Update log
                        log.status = "retrying"
                        log.error = f"Retry attempt {retry_attempt}/{MAX_RETRIES}. Previous error: {final_error[:200]}"
                        db.commit()
                        
                        # Sleep and check status
                        start_wait = datetime.utcnow()
                        while (datetime.utcnow() - start_wait).total_seconds() < delay:
                            db.refresh(c)
                            if c.status != "running":
                                print(f"[campaign {c.id}] Campaign paused/stopped during retry wait", flush=True)
                                manual_pause = True
                                break
                            sleep(1)
                        
                        db.refresh(c)
                        if c.status != "running":
                            manual_pause = True
                            break
                    
                    # Attempt to send
                    print(f"[campaign {c.id}] Attempt {retry_attempt + 1}/{MAX_RETRIES + 1} for {target.email}", flush=True)
                    
                    success, error = _attempt_send_email(
                        db, log, c, target, profile, server, template, 
                        attachments, context, rendered, calendar_ics, 
                        cal_method, target_cn, message_id_val
                    )
                    
                    if success:
                        log.status = "sent"
                        log.sent_at = datetime.utcnow()
                        log.error = None
                        final_success = True
                        db.commit()
                        
                        if retry_attempt > 0:
                            print(f"[campaign {c.id}] Successfully sent to {target.email} on attempt {retry_attempt + 1}", flush=True)
                        break
                    else:
                        # Failed
                        final_error = error
                        print(f"[campaign {c.id}] Attempt {retry_attempt + 1} failed for {target.email}: {error}", 
                              flush=True)
                        
                        if retry_attempt < MAX_RETRIES:
                            retry_attempt += 1
                        else:
                            # Max retries exhausted
                            print(f"[campaign {c.id}] All {MAX_RETRIES + 1} attempts failed for {target.email}", 
                                  flush=True)
                            break
                
                # Update log and campaign
                if manual_pause:
                    print(f"[campaign {c.id}] Manual pause detected after {retry_attempt} attempts", flush=True)
                    break
                
                if not final_success:
                    # All attempts failed
                    actual_attempts = retry_attempt + 1
                    log.status = "failed"
                    log.error = f"Failed after {actual_attempts} attempts. Last error: {final_error}"
                    db.commit()
                    
                    # Stop the campaign
                    print(f"[campaign {c.id}] Stopping campaign after {actual_attempts} failed attempts on {target.email}", flush=True)
                    c.status = "paused"
                    c.last_error = f"Auto-paused after {actual_attempts} failed delivery attempts to {target.email}. Error: {final_error[:200]}"
                    c.last_error_at = datetime.utcnow()
                    db.commit()
                    break

                # Batch delay
                if c.use_batches and c.batch_size and c.batch_delay_seconds:
                    sent_count = db.query(EmailLog).filter(
                        EmailLog.campaign_id==c.id, EmailLog.status=="sent").count()
                    if sent_count % c.batch_size == 0:
                        db.refresh(c)
                        if c.status != "running": 
                            break
                        sleep(max(0, c.batch_delay_seconds))
                else:
                    sleep(DEFAULT_MAIL_DELAY)
        
        except Exception as e:
            # Persist error message to UI
            tb = traceback.format_exc()
            c = db.query(Campaign).get(campaign_id)
            if c:
                c.status = "error"
                short = tb.strip().splitlines()[-1] if tb else "Unknown error"
                c.last_error = short[:1000]
                c.last_error_trace = tb[:1000000] or None
                c.last_error_at = datetime.utcnow()
                db.commit()
            print(tb, flush=True)
        finally:
            db.close()

def scheduled_watcher(stop_event: threading.Event):
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            updated = (
                db.query(Campaign)
                .filter(Campaign.status == "scheduled")
                .filter(Campaign.scheduled_start_at <= now)
                .update(
                    {"status": "starting", "started_at": now},
                    synchronize_session=False
                )
            )
            db.commit()
            
            if updated > 0:
                rows = (
                    db.query(Campaign)
                    .filter(Campaign.status == "starting")
                    .filter(Campaign.started_at == now)
                    .all()
                )
                
                for c in rows:
                    # Enqueue targets if not already present
                    existing = db.query(EmailLog).filter(EmailLog.campaign_id == c.id).count()
                    if existing == 0:
                        lids = [r.list_id for r in db.query(CampaignTargetList).filter(
                            CampaignTargetList.campaign_id == c.id).all()]
                        if lids:
                            targets = db.query(Target).filter(Target.list_id.in_(lids)).all()
                            for t in targets:
                                db.add(EmailLog(
                                    campaign_id=c.id,
                                    target_id=t.id,
                                    to_email=t.email,
                                    status="pending",
                                    target_first_name=t.first_name,
                                    target_last_name=t.last_name,
                                ))
                            db.commit()

                    template = db.query(EmailTemplate).get(c.template_id)
                    _snapshot_calendar_fields_if_empty(db, c, template)
                    _snapshot_used_vars_if_empty(db, c, template)

                    c.status = "running"
                    db.commit()
                    
                    t = threading.Thread(target=run_campaign_send, args=(c.id,), daemon=False)
                    
                    with active_threads_lock:
                        active_campaign_threads.append(t)
                    
                    t.start()
                    
        except Exception as e:
            print(f"[scheduled_watcher] Error: {e}", flush=True)
            traceback.print_exc()

        finally:
            db.close()
            # Clean up
            with active_threads_lock:
                active_campaign_threads[:] = [t for t in active_campaign_threads if t.is_alive()]

        stop_event.wait(WORKER_POLL_INTERVAL)

def shutdown_worker(stop_event: threading.Event, timeout: int = 30):
    print("[worker] SHUTDOWN INITIATED", flush=True)
    
    # Stop watcher from starting new campaigns
    stop_event.set()
    
    # Mark all running campaigns as paused
    db = SessionLocal()
    try:
        from .models import Campaign
        
        running_campaigns = db.query(Campaign).filter(Campaign.status == "running").all()
        
        if running_campaigns:
            print(f"[worker] Marking {len(running_campaigns)} running campaigns as paused...", flush=True)
            for c in running_campaigns:
                c.status = "paused"
                c.last_error = "Campaign paused due to system shutdown"
                c.last_error_at = datetime.utcnow()
            db.commit()
            print(f"[worker] Paused {len(running_campaigns)} campaigns", flush=True)
        else:
            print("[worker] No running campaigns to pause", flush=True)
            
    except Exception as e:
        print(f"[worker] Error pausing campaigns: {e}", flush=True)
    
    finally:
        db.close()
    
    # Give threads time to finish their current email
    with active_threads_lock:
        alive_count = len([t for t in active_campaign_threads if t.is_alive()])
    
    if alive_count > 0:
        print(f"[worker] Waiting {timeout}s for {alive_count} threads to finish current email...", flush=True)
        
        start_time = datetime.utcnow()
        while True:
            with active_threads_lock:
                alive = [t for t in active_campaign_threads if t.is_alive()]
            
            if not alive:
                print("[worker] All threads finished", flush=True)
                break
                
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout:
                print(f"[worker] Timeout reached. {len(alive)} threads still active (will be force-killed)", flush=True)
                break
            
            # Log every 5 seconds
            if int(elapsed) % 5 == 0:
                print(f"[worker] Still waiting... {len(alive)} threads active ({int(elapsed)}s elapsed)", flush=True)
            
            sleep(1)
    
    print("[worker] SHUTDOWN COMPLETE", flush=True)

def worker_health_check():
    with active_threads_lock:
        alive_count = len([t for t in active_campaign_threads if t.is_alive()])
    
    semaphore_available = campaign_semaphore._value
    actually_sending = min(alive_count, MAX_CONCURRENT_CAMPAIGNS)
    waiting = max(0, alive_count - MAX_CONCURRENT_CAMPAIGNS)
    
    return {
        "status": "healthy",
        "total_campaign_threads": alive_count,
        "actively_sending": actually_sending,
        "waiting_for_slot": waiting,
        "max_concurrent": MAX_CONCURRENT_CAMPAIGNS,
        "semaphore_available": semaphore_available,
    }
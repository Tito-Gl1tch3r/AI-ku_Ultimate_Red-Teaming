import smtplib, ssl
from email.utils import formatdate, make_msgid
from email.message import EmailMessage
from typing import Optional, Dict, List, Any
from .jinja_sandbox import env_html, env_text
from cryptography.fernet import Fernet, InvalidToken
from .config import settings
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import re
from email.headerregistry import Address
from email.policy import SMTP

def decrypt_password(enc: bytes) -> str:
    if not settings.fernet_key:
        raise RuntimeError("FERNET_KEY not set in environment")
    if not enc:
        raise ValueError("Password cannot be empty")
    try:
        f = Fernet(settings.fernet_key.encode() if isinstance(settings.fernet_key, str) else settings.fernet_key)
        return f.decrypt(enc).decode()
    except InvalidToken:
        raise RuntimeError("Invalid encryption key for SMTP password")
    except Exception:
        raise RuntimeError(f"Failed to decrypt password")

def _render_with(env, template_str: Optional[str], context: Dict[str, Any]) -> Optional[str]:
    if template_str is None:
        return None
    
    # Safe value to format via |datefmt
    safe_ctx = dict(context)
    safe_ctx.setdefault("_now", datetime.now(timezone.utc))
    return env.from_string(template_str).render(**safe_ctx)

def render_body(subject: str, body_html: Optional[str], body_text: Optional[str], context: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "subject": _render_with(env_text, subject, context),
        "html": _render_with(env_html, body_html, context),
        "text": _render_with(env_text, body_text, context),
    }

def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()

def _build_addr(email: str, display_name: str | None = None) -> Address:
    # Sanitize
    display = (display_name or "").strip()
    display = re.sub(r'[\r\n]+', ' ', display)
    display = re.sub(r'[\x00-\x1f\x7f]', '', display)

    if "@" not in email:
        raise ValueError(f"Invalid email address: {email}")
    local, domain = email.rsplit("@", 1)
    try:
        domain_ascii = domain.encode("idna").decode("ascii")
    except Exception:
        domain_ascii = domain # already ASCII

    return Address(
        display_name=(display or None),
        username=local,
        domain=domain_ascii
    )

def _make_vtimezone_block(tzid: str) -> tuple[str, str]:
    now = datetime.now(ZoneInfo(tzid))
    tz_label = now.tzname() or tzid
    offset = now.strftime("%z")
    off_h, off_m = offset[:3], offset[3:]

    block = (
        "BEGIN:VTIMEZONE\r\n"
        f"TZID:{tz_label}\r\n"
        "BEGIN:STANDARD\r\n"
        "DTSTART:16010101T020000\r\n"
        f"TZOFFSETFROM:{off_h}{off_m}\r\n"
        f"TZOFFSETTO:{off_h}{off_m}\r\n"
        "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\r\n"
        "END:STANDARD\r\n"
        "BEGIN:DAYLIGHT\r\n"
        "DTSTART:16010101T020000\r\n"
        f"TZOFFSETFROM:{off_h}{off_m}\r\n"
        f"TZOFFSETTO:{off_h}{off_m}\r\n"
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\r\n"
        "END:DAYLIGHT\r\n"
        "END:VTIMEZONE\r\n"
    )
    return tz_label, block

def build_calendar_ics(
    *,
    uid: str,
    tzid: str,
    prodid: str,
    is_cancel: bool,
    organizer_cn: str,
    organizer_email: str,
    target_cn: str,
    target_email: str,
    meeting_summary: str,
    description_plain: str,
    begin_local: str,
    end_local: str,
    priority: int,
    disable_forwarding: bool,
    extra_attendees: list[dict],
    meeting_provider: str | None = None,
    meeting_url: str | None = None,
    location: str | None = None,
    allow_responses: bool = True,
    attach_lines: list[str] | None = None,
    calendar_categories: list[str] | None = None,
    calendar_private: bool | None = None,
    sequence: bool = 0,
) -> str:
    
    def att_line_target(cn: str, mail: str) -> str:
        return f'ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE;CN="{cn}":mailto:{mail}\r\n'
    
    def att_line(cn: str, mail: str) -> str:
        return f'ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=ACCEPTED;RSVP=TRUE;CN="{cn}":mailto:{mail}\r\n'

    # Do we want to show that target user accepted the meeting? (applies only to Gmail)
    #attendees = att_line_target(target_cn, target_email)
    attendees = att_line(target_cn, target_email)
    for a in (extra_attendees or []):
        cn = (a.get("cn") or a.get("CN") or "").strip()
        em = (a.get("email") or a.get("Email") or "").strip()
        if em:
            attendees += att_line(cn, em)

    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    meeting_block = ""
    if not is_cancel and meeting_url:
        if meeting_provider == "teams":
            meeting_block = (
                'X-MICROSOFT-ONLINEMEETINGINFORMATION:{"OnlineMeetingChannelId":null,"OnlineMeetingProvider":3}\r\n'
                f"X-MICROSOFT-SKYPETEAMSMEETINGURL:{meeting_url}\r\n"
                f"X-MICROSOFT-LOCATIONDISPLAYNAME:Microsoft Teams Meeting\r\n"
                f"X-MICROSOFT-LOCATIONSOURCE:None\r\n"
                'X-MICROSOFT-LOCATIONS:[{"DisplayName":"Microsoft Teams Meeting"\,"LocationAnnotation":""\,"LocationUri":""\,"LocationStreet":""\,"LocationCity":""\,"LocationState":""\,"LocationCountry":""\,"LocationPostalCode":""\,"LocationFullAddress":""}]\r\n'
            )
        elif meeting_provider == "gmeet":
            meeting_block = (
               f"X-GOOGLE-CONFERENCE:{meeting_url}\r\n"
               f"CREATED:{now_utc}\r\n"
               f"LAST-MODIFIED:{now_utc}\r\n"
            )

    tz_label, vtz = _make_vtimezone_block(tzid)

    location_line = ""
    if (location or "").strip():
        location_line = f"LOCATION:{location}\r\n"

    allow_resp_line = "" if allow_responses else "X-MICROSOFT-ISRESPONSEREQUESTED:FALSE\r\n"
    
    attach_blob = ""
    if not is_cancel:
        attach_blob = "".join(attach_lines or [])

    if priority == 1:
        ics_priority = 1
        ms_importance = 2
    elif priority == 3:
        ics_priority = 6
        ms_importance = 0
    else:
        ics_priority = 5
        ms_importance = 1

    categories_line = ""
    if calendar_categories:
        # Sanitize
        cleaned = []
        for c in calendar_categories:
            s = (c or "").strip()
            s = re.sub(r"[\r\n\x00-\x1f\x7f]", "", s)
            if s:
                cleaned.append(s)
        if cleaned:
            categories_line = f"CATEGORIES:{','.join(cleaned)}\r\n"

    ical = (
        "BEGIN:VCALENDAR\r\n"
        f"METHOD:{'CANCEL' if is_cancel else 'REQUEST'}\r\n"
        f"PRODID:{prodid}\r\n"
        "VERSION:2.0\r\n"
        f"{vtz}"
        "BEGIN:VEVENT\r\n"
        f'ORGANIZER;CN="{organizer_cn}":mailto:{organizer_email}\r\n'
        f"{attendees}"
        f"DESCRIPTION:{description_plain}\r\n"
        f"UID:{uid}\r\n"
        f"SUMMARY:{meeting_summary}\r\n"
        f"{categories_line}"
        f"DTSTART;TZID={tz_label}:{begin_local}\r\n"
        f"DTEND;TZID={tz_label}:{end_local}\r\n"
        f"CLASS:{'PRIVATE' if calendar_private else 'PUBLIC'}\r\n"
        f"PRIORITY:{ics_priority}\r\n"
        f"DTSTAMP:{now_utc}\r\n"
        "TRANSP:OPAQUE\r\n"
        "STATUS:CONFIRMED\r\n"
        f"SEQUENCE:{sequence}\r\n"
        f"{location_line}"
        f"X-MICROSOFT-CDO-APPT-SEQUENCE:{sequence}\r\n"
        "X-MICROSOFT-CDO-BUSYSTATUS:TENTATIVE\r\n"
        "X-MICROSOFT-CDO-INTENDEDSTATUS:BUSY\r\n"
        "X-MICROSOFT-CDO-ALLDAYEVENT:FALSE\r\n"
        f"X-MICROSOFT-CDO-IMPORTANCE:{ms_importance}\r\n"
        "X-MICROSOFT-CDO-INSTTYPE:0\r\n"
        f"X-MICROSOFT-DONOTFORWARDMEETING:{'TRUE' if disable_forwarding else 'FALSE'}\r\n"
        f"{allow_resp_line}"
        f"{meeting_block}"
        f"{attach_blob}"
        "BEGIN:VALARM\r\n"
        "ACTION:DISPLAY\r\n"
        "DESCRIPTION:REMINDER\r\n"
        "TRIGGER;RELATED=START:-PT15M\r\n"
        "END:VALARM\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    return ical

def compose_email(display_name: str, from_email: str, to_email: str, subject: str, body_html: str | None, body_text: str | None, custom_headers: Optional[Dict[str,str]]=None, calendar_ics: str | None = None, to_display_name: str | None = None, message_id: Optional[str] = None, calendar_method: str | None = None) -> EmailMessage:
    msg = EmailMessage(policy=SMTP)
    msg["From"] = _build_addr(from_email, display_name)
    msg["To"] = _build_addr(to_email, to_display_name)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    
    from_domain = from_email.split("@", 1)[1]
    msg["Message-ID"] = (message_id or make_msgid(domain=from_domain))

    msg["MIME-Version"] = "1.0"
    if custom_headers:
        for k,v in custom_headers.items():
            if k.lower() in {"from","to","subject","date","mime-version","message-id"}:
                continue
            msg[k] = v
    if body_html and body_text:
        msg.set_content(body_text, charset="utf-8")
        msg.add_alternative(body_html, subtype="html", charset="utf-8", cte="base64")
    elif body_html:
        msg.add_alternative(body_html, subtype="html", charset="utf-8", cte="base64")
    elif body_text:
        msg.set_content(body_text, charset="utf-8")
    else:
        msg.set_content("", charset="utf-8")
    
    if calendar_ics and calendar_method:
        msg.add_alternative(
            calendar_ics,
            subtype="calendar",
            charset="utf-8",
            cte="base64",
        )

        cal_part = msg.get_payload()[-1]

        cal_part.replace_header(
            "Content-Type",
            f'text/calendar; method={calendar_method}; charset="utf-8"',
        )

    return msg

def attach_files(msg: EmailMessage, attachments: List[Dict] | None):
    if not attachments:
        return
    for a in attachments:
        filename = a["filename"]; mime = a.get("mime_type","application/octet-stream"); data = a["data"]
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(data, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

def send_smtp(host: str, port: int, use_tls: bool, ehlo_name: Optional[str], username: str, password: str, message: EmailMessage, from_addr: str, to_addr: str, via_tcp_forwarder: bool = True):
    helo = ehlo_name or host or settings.smtp_default_ehlo
    
    if port == 465 and use_tls:
        # Implicit TLS
        ctx = ssl.create_default_context()
        if via_tcp_forwarder:
            # Relax hostname verification
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        server = smtplib.SMTP_SSL(host=host, port=port, timeout=60, local_hostname=helo, context=ctx)
    else:
        # Plain TCP
        server = smtplib.SMTP(host=host, port=port, timeout=60, local_hostname=helo)
        server.ehlo()
        if use_tls:
            ctx = ssl.create_default_context()
            if via_tcp_forwarder:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            server.starttls(context=ctx)
            server.ehlo()

    if username and password:
        server.login(username, password)

    server.send_message(message, from_addr=from_addr, to_addrs=[to_addr])
    server.quit()

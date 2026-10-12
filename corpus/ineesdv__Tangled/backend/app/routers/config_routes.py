from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import re
from ..database import get_db
from ..models import GlobalVar, GlobalSetting
from ..schemas import GlobalVarIn, GlobalVarOut, SettingsIn, SettingsOut
from ..auth import get_current_user
import rstr
import uuid, base64, json, urllib.request, urllib.parse

router = APIRouter(prefix="/api/config", tags=["Config"])

def _gen_teams_meeting_url(tenant_guid: str) -> str:
    opaque = str(uuid.uuid4())
    organizer_guid = str(uuid.uuid4())
    opaque_b64 = base64.b64encode(opaque.encode("ascii")).decode("ascii")
    context_obj = {"Tid": tenant_guid, "Oid": organizer_guid}
    ctx_enc = urllib.parse.quote(json.dumps(context_obj), safe="")
    return f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_{opaque_b64}@thread.v2/0?context={ctx_enc}"

@router.get("/vars", response_model=List[GlobalVarOut])
def list_vars(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(GlobalVar).order_by(GlobalVar.name.asc()).all()
    return [
        GlobalVarOut(
            id=r.id, name=r.name, kind=r.kind, value=r.value, pattern=r.pattern,
            tenant_guid=r.tenant_guid, per_recipient=bool(getattr(r, "per_recipient", False))
        )
        for r in rows
    ]

@router.post("/vars", response_model=GlobalVarOut)
def create_var(payload: GlobalVarIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    name = payload.name.strip()

    if payload.kind == "teams":
        # Enforce TeamsMeeting_ prefix
        if not name.startswith("TeamsMeeting_"):
            raise HTTPException(status_code=400, detail="Teams variable names must start with 'TeamsMeeting_'")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise HTTPException(status_code=400, detail="Invalid variable name. Use letters, digits, underscore (cannot start with digit).")
    else:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise HTTPException(status_code=400, detail="Invalid variable name. Use letters, digits, underscore (cannot start with digit).")

    if db.query(GlobalVar).filter(GlobalVar.name == name).first():
        raise HTTPException(status_code=400, detail="Variable already exists")

    if payload.kind not in ("text","regex","teams"):
        raise HTTPException(status_code=400, detail="kind must be 'text', 'regex' or 'teams'")

    if payload.kind == "teams":
        tg = (payload.tenant_guid or "").strip()

        if not re.fullmatch(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", tg):
            raise HTTPException(status_code=400, detail="tenant_guid must be a GUID (8-4-4-4-12)")
        
        per_recipient = bool(payload.per_recipient)

        value = None
        if not per_recipient:
            # Pre-generate static teams meeting
            value = _gen_teams_meeting_url(tg)

        v = GlobalVar(
            name=name, kind="teams",
            tenant_guid=tg, per_recipient=per_recipient,
            value=value, pattern=None
        )

    else:
        v = GlobalVar(name=name, kind=payload.kind, value=payload.value, pattern=payload.pattern)

    db.add(v)
    db.commit()
    db.refresh(v)

    return GlobalVarOut(
        id=v.id, name=v.name, kind=v.kind, value=v.value, pattern=v.pattern,
        tenant_guid=v.tenant_guid, per_recipient=bool(getattr(v, "per_recipient", False))
    )

@router.put("/vars/{var_id}", response_model=GlobalVarOut)
def update_var(var_id: int, payload: GlobalVarIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    v = db.query(GlobalVar).get(var_id)
    if not v: raise HTTPException(status_code=404, detail="Not found")

    # Name changes
    if payload.name and payload.name != v.name:
        if v.kind == "teams":
            if not payload.name.startswith("TeamsMeeting_"):
                raise HTTPException(status_code=400, detail="Teams variable names must start with 'TeamsMeeting_'")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", payload.name):
            raise HTTPException(status_code=400, detail="Invalid variable name")
        if db.query(GlobalVar).filter(GlobalVar.name == payload.name).first():
            raise HTTPException(status_code=400, detail="Variable already exists")
        v.name = payload.name

    # Kind changes
    if payload.kind and payload.kind not in ("text","regex","teams"):
        raise HTTPException(status_code=400, detail="kind must be 'text', 'regex' or 'teams'")
    
    if payload.kind:
        v.kind = payload.kind

    if v.kind == "teams":
        if payload.tenant_guid is not None:
            tg = payload.tenant_guid.strip()
            if not re.fullmatch(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", tg):
                raise HTTPException(status_code=400, detail="tenant_guid must be a GUID (8-4-4-4-12)")
            v.tenant_guid = tg

        if payload.per_recipient is not None:
            v.per_recipient = bool(payload.per_recipient)

        # If now static generate velue
        if not v.per_recipient:
            v.value = _gen_teams_meeting_url(v.tenant_guid)
        # Remove stored value
        else:
            v.value = None

        v.pattern = None

    else:
        v.value = payload.value
        v.pattern = payload.pattern
        v.tenant_guid = None
        v.per_recipient = False

    db.commit()
    db.refresh(v)

    return GlobalVarOut(
        id=v.id, name=v.name, kind=v.kind, value=v.value, pattern=v.pattern,
        tenant_guid=v.tenant_guid, per_recipient=bool(getattr(v, "per_recipient", False))
    )

@router.delete("/vars/{var_id}")
def delete_var(var_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    v = db.query(GlobalVar).get(var_id)

    if not v:
        raise HTTPException(status_code=404, detail="Not found")
    
    db.delete(v)
    db.commit()
    return {"ok": True}

@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(GlobalSetting).all()
    data = {r.key: (r.value or "") for r in rows}
    return SettingsOut(values=data)

@router.put("/settings", response_model=SettingsOut)
def update_settings(payload: SettingsIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    for k, v in (payload.values or {}).items():
        if k == "message_id_pattern":
            val = (v or "").strip()
            if val:
                try:
                    sample = rstr.xeger(val)
                    sample = re.sub(r'[\r\n]+', '', sample).strip()
                    sample = sample.encode('ascii', 'ignore').decode('ascii')

                    # Validate and normalize
                    if re.fullmatch(r'[^<>@]+@[^<>@]+', sample):
                        sample = f'<{sample}>'
                    if not re.fullmatch(r'<[^<>@]+@[^<>@]+>', sample):
                        raise ValueError("pattern must generate <local@domain> (or local@domain).")
                    
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid message_id_pattern: {e}")

        if k == "calendar_uid_pattern":
            val = (v or "").strip()
            if val:
                try:
                    sample = rstr.xeger(val)
                    # Validate UID
                    sample = re.sub(r'[\r\n]+', '', sample).strip()
                    sample = sample.encode('ascii', 'ignore').decode('ascii')

                    if not sample:
                        raise ValueError("generated UID is empty after normalization")
                    
                    if len(sample) > 255:
                        raise ValueError("generated UID is too long (>255)")
                    
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"Invalid calendar_uid_pattern: {e}")
                
        row = db.query(GlobalSetting).filter(GlobalSetting.key == k).first()

        if row:
            row.value = v
        else:
            db.add(GlobalSetting(key=k, value=v))
    
    db.commit()

    rows = db.query(GlobalSetting).all()
    data = {r.key: (r.value or "") for r in rows}
    return SettingsOut(values=data)

@router.get("/tenant_guid")
def resolve_tenant_guid(domain: str, user=Depends(get_current_user)):
    if not domain or "." not in domain:
        raise HTTPException(status_code=400, detail="Invalid domain")

    url = f"https://login.microsoftonline.com/{domain}/v2.0/.well-known/openid-configuration"

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
        issuer = (data or {}).get("issuer") or ""
        m = re.search(r"login\.microsoftonline\.com/([0-9a-fA-F-]{36})/v2\.0", issuer)

        if not m:
            raise ValueError("Issuer does not contain a tenant GUID")
        
        return {"domain": domain, "tenant_guid": m.group(1)}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not resolve tenant GUID: {e}")

@router.get("/vars/preview")
def preview_var_list(db: Session = Depends(get_db), user=Depends(get_current_user)):
    vars = db.query(GlobalVar).all()
    results = {}
    
    # Default vars
    results.update({ # TODO: change values
        "firstName": "Ed",
        "lastName": "Smith", 
        "email": "ed.smith@example.com",
        "randomID": "AbCDefGh",
        "extraField": "Human Resources Manager",
    })
    
    # Custom vars
    for v in vars:
        example_val = ""

        if v.kind == "text":
            example_val = v.value or "StaticText"

        elif v.kind == "regex":
            try:
                example_val = rstr.xeger(v.pattern or ".*")
            except Exception:
                example_val = "RegexValue"

        elif v.kind == "teams":
            if getattr(v, "per_recipient", False):
                try:
                    _gen_teams_meeting_url(v.tenant_guid or "")
                except Exception:
                    example_val = "https://teams.microsoft.com/meeting"
            else:
                example_val = v.value or "https://teams.microsoft.com/static-meeting"
        
        if v.name:
            results[v.name] = example_val
    
    return results
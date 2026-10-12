from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db, Base, engine
from ..models import User, UserSession, APIKey
from ..auth import (
    hash_password, verify_password, create_access_token, 
    oauth2_scheme, get_current_user, generate_api_key
)
from ..schemas import (
    Token, UserCreate, UserOut, ChangePasswordIn, SessionOut,
    APIKeyCreate, APIKeyOut, APIKeyCreated
)
from uuid import uuid4
from jose import jwt
from ..config import settings
from typing import List

router = APIRouter(prefix="/auth", tags=["Auth"])
Base.metadata.create_all(bind=engine)

MAX_API_KEYS = getattr(settings, 'max_api_keys', 10)

# @router.post("/register", response_model=UserOut)
# def register(user: UserCreate, db: Session = Depends(get_db)):
#     if db.query(User).filter(User.email == user.email).first():
#         raise HTTPException(status_code=400, detail="User already exists")
#     u = User(email=user.email, password_hash=hash_password(user.password))
#     db.add(u)
#     db.commit()
#     db.refresh(u)
#     return UserOut(id=u.id, email=u.email)

@router.post("/token", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    xfwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    client_ip = xfwd or (request.client.host if request.client else None)
    ua = request.headers.get("user-agent")

    jti = str(uuid4())
    db.add(UserSession(user_id=user.id, jti=jti, user_agent=ua, ip_address=client_ip))
    db.commit()

    token = create_access_token({"sub": str(user.id), "jti": jti})
    return Token(access_token=token)

@router.post("/change-password")
def change_password(payload: ChangePasswordIn, token: str = Depends(oauth2_scheme), user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if payload.new_password != payload.new_password_confirm:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="New password must be different from current password")

    # Keep current session active
    try:
        payload_data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        current_jti = payload_data.get("jti")
    except Exception:
        current_jti = None

    # Revoke all sessions except the current one
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.jti != current_jti,
        UserSession.revoked == False
    ).update({"revoked": True})

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}

@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(token: str = Depends(oauth2_scheme), user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        current_jti = payload.get("jti")
    except Exception:
        current_jti = None

    rows = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.revoked == False)
        .order_by(UserSession.created_at.desc())
        .all()
    )

    return [
        SessionOut(
            id=r.id,
            ip_address=r.ip_address,
            user_agent=r.user_agent,
            created_at=r.created_at,
            last_seen=r.last_seen,
            current=(r.jti == current_jti),
        )
        for r in rows
    ]

@router.post("/sessions/{session_id}/revoke")
def revoke_session(session_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(UserSession).filter(UserSession.id == session_id, UserSession.user_id == user.id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    s.revoked = True
    db.commit()
    return {"ok": True}

@router.post("/sessions/revoke-all")
def revoke_all_sessions(token: str = Depends(oauth2_scheme), user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        current_jti = payload.get("jti")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Revoke all sessions except the current one
    revoked_count = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.revoked == False,
            UserSession.jti != current_jti
        )
        .update({"revoked": True}, synchronize_session=False)
    )
    db.commit()
    
    return {"ok": True, "revoked_count": revoked_count}

@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            jti = payload.get("jti")
            sub = payload.get("sub")
        except Exception:
            jti = None
            sub = None

        if jti:
            db.query(UserSession).filter(UserSession.jti == jti).update({"revoked": True})
            db.commit()

    return {"ok": True}

@router.post("/api-keys", response_model=APIKeyCreated)
def create_api_key(payload: APIKeyCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    existing_count = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.revoked == False
    ).count()
    
    if existing_count >= MAX_API_KEYS:
        raise HTTPException(
            status_code=400,
            detail="Maximum number of API keys reached"
        )
    
    full_key, key_prefix, key_hash = generate_api_key()
    
    api_key = APIKey(user_id=user.id, name=payload.name, key_prefix=key_prefix, key_hash=key_hash)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        key_prefix=key_prefix,
        created_at=api_key.created_at
    )

@router.get("/api-keys", response_model=List[APIKeyOut])
def list_api_keys(user=Depends(get_current_user), db: Session = Depends(get_db)):
    keys = (
        db.query(APIKey)
        .filter(APIKey.user_id == user.id, APIKey.revoked == False)
        .order_by(APIKey.created_at.desc())
        .all()
    )
    
    return [
        APIKeyOut(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            created_at=k.created_at,
            last_used_at=k.last_used_at
        )
        for k in keys
    ]

@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user.id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    key.revoked = True
    db.commit()
    
    return {"ok": True}
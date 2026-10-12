from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta
from typing import Optional
import secrets
from .database import get_db
from .models import User, APIKey
from .config import settings
from .models import UserSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def generate_api_key() -> tuple[str, str, str]:
    full_key = secrets.token_urlsafe(32)
    key_prefix = full_key[:8]
    key_hash = pwd_context.hash(full_key)
    return full_key, key_prefix, key_hash

def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    return pwd_context.verify(plain_key, hashed_key)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expires_delta = timedelta(seconds=settings.jwt_expiration_seconds)
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        user_id: int = int(payload.get("sub"))
        jti: str | None = payload.get("jti")
    except (JWTError, Exception):
        raise exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not jti:
        raise exc

    sess = (
        db.query(UserSession)
        .filter(UserSession.jti == jti, UserSession.user_id == user.id, UserSession.revoked == False)
        .first()
    )
    if not sess:
        raise exc

    sess.last_seen = datetime.utcnow()
    db.commit()

    return user

def get_user_from_api_key(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if not authorization.lower().startswith("apikey "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme. Expected: ApiKey <key>",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    api_key = authorization.split(" ", 1)[1].strip()
    
    # Find all non-revoked keys with this prefix
    key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
    api_keys = (
        db.query(APIKey)
        .filter(APIKey.key_prefix == key_prefix, APIKey.revoked == False)
        .all()
    )
    
    # Verify the full key
    for key_record in api_keys:
        if verify_api_key(api_key, key_record.key_hash):
            key_record.last_used_at = datetime.utcnow()
            db.commit()

            user = db.query(User).filter(User.id == key_record.user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            return user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )

def get_user_both_auths(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer, ApiKey"}
        )
    
    # Try bearer token
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            user_id: int = int(payload.get("sub"))
            jti: str | None = payload.get("jti")
            
            user = db.query(User).filter(User.id == user_id).first()
            if user and jti:
                sess = (
                    db.query(UserSession)
                    .filter(UserSession.jti == jti, UserSession.user_id == user.id, UserSession.revoked == False)
                    .first()
                )
                if sess:
                    sess.last_seen = datetime.utcnow()
                    db.commit()
                    return user
                
        except (JWTError, Exception):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    
    # Try API key
    elif authorization.lower().startswith("apikey "):
        api_key = authorization.split(" ", 1)[1].strip()
        key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
        
        api_keys = (
            db.query(APIKey)
            .filter(APIKey.key_prefix == key_prefix, APIKey.revoked == False)
            .all()
        )
        
        for key_record in api_keys:
            if verify_api_key(api_key, key_record.key_hash):
                key_record.last_used_at = datetime.utcnow()
                db.commit()
                
                user = db.query(User).filter(User.id == key_record.user_id).first()
                if user:
                    return user
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authorization scheme. Use 'Bearer <token>' or 'ApiKey <key>'",
        headers={"WWW-Authenticate": "Bearer, ApiKey"}
    )
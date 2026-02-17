import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from .config import JWT_SECRET
from .database import supabase

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, is_admin: bool = False, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "is_admin": is_admin,
        "token_version": token_version,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str, token_version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "token_version": token_version,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = get_user_by_id(user_id)
    if not user or not user.get("is_active", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or not found",
        )
    token_version = payload.get("token_version", 0)
    if token_version != user.get("token_version", 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )
    return {
        "id": user_id,
        "is_admin": user.get("is_admin", False),
    }


def get_current_admin(user: Dict = Depends(get_current_user)) -> Dict:
    if not user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def register_user(username: str, email: str, password: str) -> Dict:
    # Check if username already exists
    existing = supabase.table("app_users").select("id").eq("username", username).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    # Check if email already exists
    existing_email = supabase.table("app_users").select("id").eq("email", email).execute()
    if existing_email.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    password_hash = hash_password(password)
    result = supabase.table("app_users").insert({
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "is_active": True,
        "is_admin": False,
        "token_version": 0,
    }).execute()

    user = result.data[0]
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": user["is_admin"],
        "token_version": user.get("token_version", 0),
    }


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    result = supabase.table("app_users").select("*").eq("username", username).execute()
    if not result.data:
        return None

    user = result.data[0]
    if not user.get("is_active"):
        return None
    if not verify_password(password, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "is_admin": user.get("is_admin", False),
        "token_version": user.get("token_version", 0),
    }


def get_user_by_id(user_id: str) -> Optional[Dict]:
    result = supabase.table("app_users").select(
        "id,username,email,is_admin,is_active,token_version,created_at"
    ).eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0]


def bump_token_version(user_id: str) -> Optional[Dict]:
    """Increase token_version to invalidate all issued tokens for a user."""
    current = supabase.table("app_users").select("id,token_version").eq("id", user_id).execute()
    if not current.data:
        return None
    next_version = int(current.data[0].get("token_version", 0)) + 1
    result = supabase.table("app_users").update({"token_version": next_version}).eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0]

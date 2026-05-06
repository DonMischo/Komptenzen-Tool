# deps.py — FastAPI shared dependencies
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import db_schema

JWT_SECRET  = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALG     = "HS256"
JWT_EXPIRE  = int(os.environ.get("JWT_EXPIRE_HOURS", "8"))


# ---------------------------------------------------------------------------
# DB session: reads X-Active-DB header, switches ENGINE, yields session
# ---------------------------------------------------------------------------

def get_db(request: Request):
    active_db = request.headers.get("x-active-db")
    if active_db:
        db_schema.switch_engine(active_db)
    with Session(db_schema.ENGINE) as session:
        yield session


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE)
    return jwt.encode({"sub": username, "exp": expire}, JWT_SECRET, algorithm=JWT_ALG)


def _decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get("sub")
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Auth dependency — reads httpOnly cookie
# ---------------------------------------------------------------------------

def get_current_user(access_token: Optional[str] = Cookie(default=None)) -> str:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = _decode_token(access_token)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return username


def optional_user(access_token: Optional[str] = Cookie(default=None)) -> Optional[str]:
    if not access_token:
        return None
    return _decode_token(access_token)

# auth_pure.py
# Bcrypt authentication helpers — no streamlit dependency.
# Mirrors the logic in app/auth.py but usable from FastAPI.

from __future__ import annotations

import logging
import bcrypt
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session

from db_schema import _pg_base_url

logger = logging.getLogger(__name__)

_AUTH_URL = f"{_pg_base_url()}/postgres"
_auth_engine = create_engine(_AUTH_URL, echo=False, future=True)

AuthBase = declarative_base()


class AdminUser(AuthBase):
    __tablename__ = "admin_users"
    id            = Column(Integer, primary_key=True)
    username      = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


def _ensure_table() -> None:
    logger.debug("auth_pure: creating tables on %s", _auth_engine.url)
    AuthBase.metadata.create_all(_auth_engine)
    logger.debug("auth_pure: create_all completed")


def user_count() -> int:
    _ensure_table()
    with Session(_auth_engine) as ses:
        return ses.query(AdminUser).count()


def create_user(username: str, password: str) -> None:
    _ensure_table()
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with Session(_auth_engine) as ses:
        ses.add(AdminUser(username=username, password_hash=hashed))
        ses.commit()


def check_credentials(username: str, password: str) -> bool:
    _ensure_table()
    with Session(_auth_engine) as ses:
        user = ses.query(AdminUser).filter_by(username=username).first()
    if not user:
        return False
    return bcrypt.checkpw(password.encode(), user.password_hash.encode())

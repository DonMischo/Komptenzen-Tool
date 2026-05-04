# auth.py
# ------------------------------------------------------------------
# Admin authentication — stored in the postgres maintenance DB
# so credentials survive DB switches.
# ------------------------------------------------------------------
from __future__ import annotations

import bcrypt
import streamlit as st
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, Session

from db_schema import _pg_base_url

# Separate engine → always points at the maintenance DB
_AUTH_URL = f"{_pg_base_url()}/postgres"
_auth_engine = create_engine(_AUTH_URL, echo=False, future=True)

AuthBase = declarative_base()


class AdminUser(AuthBase):
    __tablename__ = "admin_users"
    id            = Column(Integer, primary_key=True)
    username      = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


def _ensure_table() -> None:
    AuthBase.metadata.create_all(_auth_engine)


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _user_count() -> int:
    _ensure_table()
    with Session(_auth_engine) as ses:
        return ses.query(AdminUser).count()


def _get_user(username: str) -> AdminUser | None:
    with Session(_auth_engine) as ses:
        return ses.query(AdminUser).filter_by(username=username).first()


def create_user(username: str, password: str) -> None:
    _ensure_table()
    with Session(_auth_engine) as ses:
        ses.add(AdminUser(username=username, password_hash=_hash(password)))
        ses.commit()


def check_credentials(username: str, password: str) -> bool:
    user = _get_user(username)
    if not user:
        return False
    return _verify(password, user.password_hash)


# ---------------------------------------------------------------------------
# Streamlit gate — call this at the top of any admin-only page.
# Returns True when the user is authenticated, False otherwise (page stops).
# ---------------------------------------------------------------------------

def require_admin_login() -> bool:
    """
    Show login or first-time setup form.
    Sets st.session_state['admin_authenticated'] = True on success.
    Returns True if already/newly authenticated.
    """
    if st.session_state.get("admin_authenticated"):
        return True

    st.title("Admin-Login")

    first_run = _user_count() == 0

    if first_run:
        st.info("Noch kein Admin-Konto vorhanden. Lege jetzt das erste Konto an.")
        with st.form("create_admin"):
            username = st.text_input("Benutzername")
            pw1      = st.text_input("Passwort",        type="password")
            pw2      = st.text_input("Passwort (wdh.)", type="password")
            submit   = st.form_submit_button("Konto anlegen")

        if submit:
            if not username or not pw1:
                st.error("Benutzername und Passwort dürfen nicht leer sein.")
            elif pw1 != pw2:
                st.error("Passwörter stimmen nicht überein.")
            elif len(pw1) < 8:
                st.error("Passwort muss mindestens 8 Zeichen lang sein.")
            else:
                create_user(username, pw1)
                st.session_state["admin_authenticated"] = True
                st.success("Konto angelegt. Willkommen!")
                st.rerun()
    else:
        with st.form("login_admin"):
            username = st.text_input("Benutzername")
            password = st.text_input("Passwort", type="password")
            submit   = st.form_submit_button("Anmelden")

        if submit:
            if check_credentials(username, password):
                st.session_state["admin_authenticated"] = True
                st.rerun()
            else:
                st.error("Ungültiger Benutzername oder Passwort.")

    st.stop()
    return False  # never reached

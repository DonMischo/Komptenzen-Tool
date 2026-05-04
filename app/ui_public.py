# ui_public.py
# ------------------------------------------------------------------
# Public-facing UI: Kompetenzen + Schülerdaten only.
# No setup, no admin, no DB switching.
# ------------------------------------------------------------------
import streamlit as st

from kompetenz_ui import run_competence_ui
from studenten_ui import run_student_ui

from db_schema import ENGINE
from sqlalchemy import inspect as sa_inspect


def _schema_ready() -> bool:
    try:
        return sa_inspect(ENGINE).has_table("subjects")
    except Exception:
        return False


def run_ui() -> None:
    if not _schema_ready():
        st.error("Keine Datenbank verbunden. Bitte den Administrator kontaktieren.")
        st.stop()

    pages = ["Kompetenzen", "Schülerdaten"]
    page = st.sidebar.selectbox("Ansicht", pages, key="_pub_page")

    if page == "Kompetenzen":
        run_competence_ui()
    elif page == "Schülerdaten":
        run_student_ui()

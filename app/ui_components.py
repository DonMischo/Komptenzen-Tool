# ------------------------------------------------------------------
# ui_components.py
# ------------------------------------------------------------------
import streamlit as st

from kompetenz_ui import run_competence_ui
from studenten_ui import run_student_ui
from admin_ui import run_admin_ui
from setup_ui import run_setup_ui
from auth import require_admin_login

from db_schema import ENGINE
from sqlalchemy import inspect as sa_inspect


def _schema_ready() -> bool:
    """Return True if the current DB has the expected tables."""
    try:
        return sa_inspect(ENGINE).has_table("subjects")
    except Exception:
        return False


def run_ui() -> None:
    schema_ok = _schema_ready()

    # If no schema is ready, always show setup (no sidebar nav yet)
    if not schema_ok:
        st.session_state.pop("setup_done", None)
        run_setup_ui()
        return

    # Sidebar navigation
    pages = ["⚙️ Setup", "Kompetenzen", "Schülerdaten", "Admin"]

    # Default to Setup if not yet confirmed done
    default_page = "Kompetenzen" if st.session_state.get("setup_done") else "⚙️ Setup"
    default_idx = pages.index(default_page)

    page = st.sidebar.selectbox("Modus wählen", pages, index=default_idx, key="_page_switch")

    if page == "⚙️ Setup":
        run_setup_ui()
    elif page == "Kompetenzen":
        st.session_state["setup_done"] = True
        run_competence_ui()
    elif page == "Schülerdaten":
        st.session_state["setup_done"] = True
        run_student_ui()
    elif page == "Admin":
        st.session_state["setup_done"] = True
        require_admin_login()
        if st.sidebar.button("🔓 Abmelden", key="_logout"):
            st.session_state.pop("admin_authenticated", None)
            st.rerun()
        run_admin_ui()

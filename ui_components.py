# ------------------------------------------------------------------
# ui_components.py
# ------------------------------------------------------------------
import streamlit as st
from typing import Dict
from kompetenz_ui import run_competence_ui 
from studenten_ui import run_student_ui
from admin_ui import run_admin_ui

# Import for fetching the current school year from the database
from db_schema import ENGINE, Session, SchoolYear
from time_functions import get_school_year


def run_ui() -> Dict:
    # ---------- Schuljahr-Anzeige in der Sidebar ----------------
    current_year = get_school_year()
    sy = None
    try:
        with Session(ENGINE) as ses:
            sy = ses.query(SchoolYear).filter_by(name=current_year).first()
    except Exception:
        pass

    if sy:
        label = "Endjahr" if sy.endjahr else "Halbjahr"
        st.sidebar.markdown(f"**Schuljahr:** {sy.name}  \n**{label}**")
    else:
        st.sidebar.markdown(f"**Schuljahr:** {current_year}")

    # ---------- Umschalter -------------------------------------
    page = st.sidebar.selectbox(
        "Modus wählen",
        ["Kompetenzen", "Schülerdaten", "Admin"],
        key="_page_switch",
    )

    if page == "Kompetenzen":
        return run_competence_ui()
    elif page == "Schülerdaten":
        return run_student_ui()
    elif page == "Admin":
        return run_admin_ui()

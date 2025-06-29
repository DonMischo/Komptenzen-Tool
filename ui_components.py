# ------------------------------------------------------------------
# ui_components.py
# ------------------------------------------------------------------
import streamlit as st
from typing import Dict
from kompetenz_ui import run_competence_ui 
from studenten_ui import run_student_ui

def run_ui() -> Dict:
    # ---------- Umschalter -------------------------------------
    page = st.sidebar.selectbox(
        "Modus wählen",
        ["Kompetenzen", "Schülerdaten"],
        key="_page_switch",
    )

    if page == "Kompetenzen":
        return run_competence_ui()     # ← exakt dein bisheriges run_ui
    elif page == "Schülerdaten":
        return run_student_ui()
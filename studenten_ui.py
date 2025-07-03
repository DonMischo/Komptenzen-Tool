# studenten_ui.py
# --------------------------------------------------------------------
"""
UI-Modul „Schülerdaten“.

• Sidebar:  Klasse & Fach wählen
• Hauptfenster: editierbare Tabelle
      Nachname | Vorname | Niveau | <alle Topics des Fachs>
  – Nachname/Vorname fix (read-only)
  – übrige Felder editierbar
• „Änderungen speichern“ schreibt zurück in die DB
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from db_schema   import ENGINE
from db_helpers  import (
    get_classes,                 # -> List[str]
    get_subjects,                # -> List[str]
    get_students_by_class,       # (klasse, ses) -> List[Student]
    get_topics_by_subject,       # (fach, ses)   -> List[str]
    fetch_grade_matrix,          # (students, topics, ses) -> pd.DataFrame
    persist_grade_matrix,        # (klasse, fach, df, ses) -> None
)
from helpers import unique_key as _unique_key
from helpers import safe_rerun
from competence_data  import SUBJECTS                     # Wunschreihenfolge
from student_base_data import run_base_data_editor # neu oben einfügen

# --------------------------------------------------------------------
def run_student_ui() -> None:
    """Haupt-Aufruf aus ui_components.run_ui()"""
    db_subjects = get_subjects()                          # aus DB
    ordered_subjects = [s for s in SUBJECTS if s in db_subjects] + [
        s for s in db_subjects if s not in SUBJECTS
    ]

    st.header("📋 Schüler-Notenmatrix")

    # ---------- Sidebar: Klasse & Fach --------------------------------
    classes  = get_classes()
    subjects = get_subjects()

    class_sel   = st.sidebar.selectbox("Klasse wählen",  classes,  key="stu_class")
    
    subject_sel = st.sidebar.selectbox(
        "Fach wählen", ordered_subjects, key=_unique_key("subject_select")
    )

    if not class_sel or not subject_sel:
        st.info("Bitte Klasse **und** Fach auswählen.")
        return

    # direkt nach der Klassenwahl
    if st.sidebar.button("⇨ Stammdaten bearbeiten", key="_btn_stammdaten"):
        st.session_state["mode"] = "stammdaten"

    if st.session_state.get("mode") == "stammdaten":
        run_base_data_editor(class_sel)      # classroom == ausgewählte Klasse
        if st.button("← Zurück", key="_back"):
            st.session_state.pop("mode")     # zurück zu den Kompetenzen
        st.stop()                            # Rest des Kompetenz-UIs überspringen


    # ---------- Daten laden -------------------------------------------
    with Session(ENGINE) as ses:
        students    = get_students_by_class(class_sel, ses)
        topics_raw  = get_topics_by_subject(subject_sel, ses, class_name=class_sel)

        # ------------------------------------------------------------------
        # Use *only* the primary-key as column id → no collisions possible
        # ------------------------------------------------------------------
        topic_ids = [str(t.id) for t in topics_raw]          # e.g. "12", "27", …

        if not students:
            st.warning(f"Keine Schüler für {class_sel} in der Datenbank.")
            return
        if not topics_raw:
            st.warning(f"Für {subject_sel} sind noch keine Topics erfasst.")
            return

        df = fetch_grade_matrix(students, topics_raw, subject_sel, ses)

        # ------------------------------------------------------------------
        # Re-order and rename columns: keep the first 3 unchanged, then ids
        # ------------------------------------------------------------------
        order       = ["Nachname", "Vorname", "Niveau", *topics_raw]
        df          = df.reindex(columns=order)
        df.columns  = df.columns[:3].tolist() + topic_ids

        # Nice labels for the Streamlit table header
        col_cfg = {
            str(t.id): st.column_config.Column(
                label=f"{subject_sel} – {t.name} ({t.block})"
            )
            for t in topics_raw
        }

    # ---------- Editierbare Tabelle -----------------------------------
    disabled_cols = ["Nachname", "Vorname"]  # read-only
    edited = st.data_editor(
        df,
        column_config=col_cfg,
        num_rows="dynamic",
        use_container_width=True,
    )


    # ---------- Speichern-Button --------------------------------------
    if st.button("💾 Änderungen speichern"):
        with Session(ENGINE) as ses:
            persist_grade_matrix(class_sel, subject_sel, edited, ses)
        st.success("Noten & Niveau wurden gespeichert!")
        safe_rerun()          # UI aktualisieren

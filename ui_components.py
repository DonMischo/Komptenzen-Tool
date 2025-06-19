# ui_components.py
# ----------------------------------------------------------------
from __future__ import annotations         # (falls schon vorhanden ok)

from typing import Dict, List               #  ← HINZUFÜGEN
import time, streamlit as st
from db_helpers import load_topic_rows, save_selections, get_subjects, get_blocks
from helpers import unique_key as _unique_key    # deine Key-Funktion
from competence_data import SUBJECTS

# ---------- Auto-Refresh alle 10 s ------------------------------
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 10:
    st.session_state.last_refresh = time.time()
    st.experimental_rerun()

def run_ui() -> Dict:
    # ----- Sidebar ------------------------------------------------
    subjects = get_subjects()
    # Reihenfolge aus competence_data übernehmen
    ordered_subjects = (
        [s for s in SUBJECTS if s in subjects] +      # zuerst genau die, die in SUBJECTS stehen
        [s for s in subjects if s not in SUBJECTS]    # Rest (evtl. neue Fächer) anhängen
    )
    subject = st.sidebar.selectbox(
        "Fach",
        ordered_subjects,
        index=0,
        key=_unique_key("subject_select"),
    )
    
    classroom = st.sidebar.selectbox(
        "Klasse", ["5a","5b","5c","6a","6b","6c","7a","7b","7c"], index=0
    )
    year = int(classroom[0])

    blocks = get_blocks(subject) or ["5/6"]
    if year <= 6 and "5/6" in blocks:
        blocks = ["5/6"]
    block = st.sidebar.selectbox("Block", blocks, index=0)

    st.sidebar.markdown("---")

    # ---------- Daten aus DB lesen -------------------------------
    rows = load_topic_rows(classroom, subject, block)
    if not rows:
        st.info("Für diese Kombination sind noch keine Kompetenzen hinterlegt.")
        return {}

    # rows → gruppieren nach Topic
    current_topic, buffer, changed = None, [], []
    for cid, topic, text, sel in rows:
        if topic != current_topic:
            if current_topic is not None:
                st.markdown("---")
            st.subheader(topic)
            current_topic = topic

        ck = st.checkbox(text, value=sel,
                         key=_unique_key(classroom, subject, topic, cid))
        if ck != sel:                     # Status geändert
            changed.append((cid, ck))

    # ----- Save-Button ------------------------------------------
    if st.button("💾 Speichern"):
        save_selections(classroom, changed)
        st.success("Gespeichert.")

    # für Aufrufer:
    return {"class": classroom, "subject": subject, "block": block}

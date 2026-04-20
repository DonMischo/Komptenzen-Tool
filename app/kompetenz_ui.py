# ------------------------------------------------------------------
# kompetenz_ui.py
# ------------------------------------------------------------------
from __future__ import annotations

import time, streamlit as st
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session
from db_schema   import ENGINE, Topic                     # für Topic-ID
from db_helpers  import (                                 # DB-Hilfen
    _get_or_create_class,
    _get_or_create_class_id,
    load_topic_rows,
    save_selections,
    get_subjects,
    get_blocks,
    get_classes,
    get_custom_competences,
    add_custom_competence,
    delete_custom_competence,
)
from helpers import unique_key as _unique_key
from helpers import safe_rerun
from competence_data  import SUBJECTS                     # Wunschreihenfolge

# -------------  Auto-Refresh (10 s) -------------------------------
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 10:
    st.session_state.last_refresh = time.time()
    safe_rerun()

# ------------------------------------------------------------------
def run_competence_ui () -> Dict:
    # ---------------- Sidebar  ------------------------------------
    db_subjects = get_subjects()                          # aus DB
    ordered_subjects = [s for s in SUBJECTS if s in db_subjects] + [
        s for s in db_subjects if s not in SUBJECTS
    ]
    classes  = get_classes()

    classroom = st.sidebar.selectbox("Klasse wählen",  classes,  key="stu_class")
    
    subject = st.sidebar.selectbox(
        "Fach", ordered_subjects, key=_unique_key("subject_select")
    )
    
    year = int(classroom[0])

    blocks = get_blocks(subject) or ["5/6"]
    if year <= 6 and "5/6" in blocks:
        blocks = ["5/6"]
    block = st.sidebar.selectbox("Block", blocks, key=_unique_key("block_sel"))

    # --------------- Daten laden ----------------------------------
    rows = load_topic_rows(classroom, subject, block)
    if not rows:
        st.info("Für diese Kombination sind noch keine Kompetenzen hinterlegt.")
        return {}

    # rows zu  {topic: [(cid,text,sel), …]}
    topics_dict: Dict[str, List[Tuple[int,str,bool]]] = {}
    for cid, topic, text, sel in rows:
        topics_dict.setdefault(topic, []).append((cid, text, sel))

    changed: List[Tuple[int,bool]] = []                  # Checkbox-Änderungen

    with Session(ENGINE) as ses:                         # eine Session
        for topic_name, items in topics_dict.items():
            # Topic-Objekt holen (für Custom-CRUD)
            topic_obj = (
                ses.query(Topic)
                   .join(Topic.subject)                     # relation → Subject
                   .filter(Topic.name == topic_name,
                           Topic.subject.has(name=subject)) # Subject.name vergleichen
                   .first()
            )
            topic_id = topic_obj.id if topic_obj else None

            # ---------- EXPANDER pro Topic -----------------------
            with st.expander(topic_name, expanded=False):
                # ----- Standard-Kompetenzen ----------------------
                for cid, text, sel in items:
                    ck = st.checkbox(
                        text,
                        value=sel,
                        key=_unique_key(classroom, subject, topic_name, cid),
                    )
                    if ck != sel:                       # geändert
                        changed.append((cid, ck))

                # ----- Custom-Kompetenzen ------------------------
                st.markdown("**Eigene Ergänzungen**")
                class_id = _get_or_create_class_id(classroom, ses)   # helper in db_helpers
                customs = get_custom_competences(topic_id, class_id, ses)
                for cc in customs:
                    col_ck, col_del = st.columns([10,1])
                    col_ck.checkbox(
                        cc.text,
                        key=_unique_key("cust", classroom, subject, topic_name, cc.id),
                    )
                    if col_del.button("🗑", key=_unique_key("del", cc.id)):
                        delete_custom_competence(cc.id, ses)
                        safe_rerun()

                # ----- Neue Kompetenz hinzufügen ----------------
                add_key = _unique_key("add_btn", topic_id)
                if st.button("➕ Ergänzen", key=add_key):
                    st.session_state[f"add_{topic_id}"] = True

                if st.session_state.get(f"add_{topic_id}"):
                    new_txt = st.text_input(
                        "Neue Kompetenz eingeben …",
                        key=_unique_key("newtxt", topic_id),
                    )
                    col_save, col_cancel = st.columns(2)
                    if col_save.button("💾 Speichern", key=_unique_key("save", topic_id)):
                        add_custom_competence(topic_id, class_id, new_txt, ses)
                        st.session_state.pop(f"add_{topic_id}")
                        safe_rerun()
                    if col_cancel.button("✖ Abbrechen", key=_unique_key("canc", topic_id)):
                        st.session_state.pop(f"add_{topic_id}")

    # --------------- Speichern-Button -----------------------------
    if changed and st.button("💾 Auswahl speichern"):
        save_selections(classroom, changed)
        st.success("Änderungen gespeichert.")

    return {"class": classroom, "subject": subject, "block": block}

# ui_components.py
# ------------------------------------------------------------
# Alle Streamlit-Widgets & UI-Logik an einem Ort
# ------------------------------------------------------------
from __future__ import annotations
from typing import Dict, List, Tuple
import re
import streamlit as st



# ------------------------------------------------------------
#  Hilfsfunktionen  →  für eindeutige Widget-Keys
# ------------------------------------------------------------
def _safe(s: str) -> str:
    """Nicht-alphanumerische Zeichen ersetzen (für Streamlit-Keys)."""
    return re.sub(r"\W+", "_", s)

def _unique_key(*parts: str, idx: int | None = None) -> str:
    """Erzeugt einen garantiert einmaligen Schlüssel."""
    key = "_".join(_safe(p) for p in parts)
    return f"{key}_{idx}" if idx is not None else key
    
    
def run_ui(competences: Dict) -> Dict:
    # ---------- SIDEBAR ----------
    st.sidebar.header("Einstellungen")
    subjects = list(competences.keys())
    subject  = st.sidebar.selectbox("Fach wählen", subjects, index=0)

    classroom = st.sidebar.selectbox(
        "Klasse wählen",
        ["5a", "5b", "5c", "6a", "6b", "6c", "7a", "7b", "7c"],
        index=0,
    )
    year  = int(classroom[0])
    block = st.sidebar.selectbox(
        "Kompetenz-Block wählen",
        ["5/6"] if year <= 6 else ["7/8", "5/6"],
        index=0,
    )
    st.sidebar.markdown("---")

    # ---------- DATEN holen ----------
    subj_dict  = competences.get(subject, {})
    block_dict = subj_dict.get(block, {})
    if not block_dict:
        st.info("Für diese Kombination sind noch keine Kompetenzen hinterlegt.")
        return {}

    st.title("📋 Kompetenzen auswählen")
    selected: Dict[str, List[str]] = {}

    # ---------- SPEZIAL-FALL „Werkstätten“ ----------
    if subject == "Werkstätten":
        st.markdown("### Werkstätten wählen")
        for topic in block_dict.keys():        # z.B. Technisches Werken, Musik …
            key = _unique_key(subject, block, topic)
            checked = st.checkbox(topic, value=True, key=key)
            if checked:
                # wir tragen eine Dummy-Liste ein, damit das Format gleich bleibt
                selected[topic] = ["Werkstatt gewählt"]
    # ---------- NORMALFALL ----------
    else:
        for topic, comp_list in block_dict.items():
            with st.expander(topic, expanded=False):
                # Select-All nur, wenn nicht Werkstätten
                sel_all_key = _unique_key("selall", subject, block, topic)
                sel_all     = st.checkbox("Alle auswählen / abwählen",
                                          key=sel_all_key)

                # Kinder-Checkboxen EINMALIG setzen, wenn sel_all wechselt
                trig_key = sel_all_key + "_trig"
                if st.session_state.get(trig_key) != sel_all:
                    for idx, _ in enumerate(comp_list):
                        child_key = _unique_key(subject, block, topic, idx=idx)
                        st.session_state[child_key] = sel_all
                    st.session_state[trig_key] = sel_all

                # eigentliche Kompetenzen
                tmp: List[str] = []
                for idx, c in enumerate(comp_list):
                    ck = _unique_key(subject, block, topic, idx=idx)
                    if st.checkbox(c, key=ck):
                        tmp.append(c)
                if tmp:
                    selected[topic] = tmp

    # ---------- SPEICHERN-Button ----------
    if st.sidebar.button("💾 Auswahl speichern"):
        if not selected:
            st.sidebar.warning("Bitte erst etwas anhaken …")
            return {}
        st.sidebar.success("Auswahl übernommen!")
        return {"class":   classroom, "subject": subject, "block": block, "data": selected}

    return {}

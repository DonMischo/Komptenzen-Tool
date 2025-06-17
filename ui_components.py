# ui_components.py
# ------------------------------------------------------------
# Alle Streamlit-Widgets & UI-Logik an einem Ort
# ------------------------------------------------------------
from __future__ import annotations
from typing import Dict, List, Tuple
import re
import streamlit as st

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------
def _safe(s: str) -> str:
    """Ersetzt alles Nicht-Alphanumerische durch '_' für Widget-Keys."""
    return re.sub(r"\W+", "_", s)


def _unique_key(*parts: str, idx: int | None = None) -> str:
    """Erzeugt einen garantiert einzigartigen Streamlit-Key."""
    key = "_".join(_safe(p) for p in parts)
    return f"{key}_{idx}" if idx is not None else key


# ------------------------------------------------------------
# Haupt-Fassade
# ------------------------------------------------------------
def run_ui(competences: Dict) -> Dict:
    """
    Zeigt die komplette Oberfläche und
    liefert bei Klick auf 'Speichern' ein Dict:
        {"subject": str, "block": str, "data": {topic: [comps]}}
    Fehlt die Auswahl, wird ein leeres Dict zurückgegeben.
    """
    # -------- Sidebar -----------------------------------------------------
    st.sidebar.header("Einstellungen")

    subjects: List[str] = list(competences.keys())
    subject: str = st.sidebar.selectbox("Fach wählen", subjects, index=0)

    classroom: str = st.sidebar.selectbox(
        "Klasse wählen",
        ["5a", "5b", "5c", "6a", "6b", "6c", "7a", "7b", "7c"],
        index=0,
    )

    # Jahrgangslogik 5/6 → nur Block 5/6, ab 7 → 7/8 + 5/6
    year = int(classroom[0])
    possible_blocks: List[str] = ["5/6"] if year <= 6 else ["7/8", "5/6"]

    block: str = st.sidebar.selectbox(
        "Kompetenz-Block wählen", possible_blocks, index=0
    )

    st.sidebar.markdown("---")

    # -------- Hauptbereich ----------------------------------------------
    st.title("📋 Kompetenzen auswählen")

    subj_dict: Dict = competences.get(subject, {})
    block_dict: Dict = subj_dict.get(block, {})

    if not block_dict:
        st.info("Für diese Kombination wurden noch keine Kompetenzen hinterlegt.")
        return {}

    selected: Dict[str, List[str]] = {}

    for topic, comp_list in block_dict.items():
        exp_key = _unique_key(subject, block, topic, idx=None)
        with st.expander(topic, expanded=False):
            # --- Select-All Checkbox ------------------------------------
            sel_all_key = _unique_key("selall", subject, block, topic)
            sel_all = st.checkbox("Alle auswählen / abwählen", key=sel_all_key)

            # ---- Kinder-Checkboxen -------------------------------------
            for idx, c in enumerate(comp_list):
                child_key = _unique_key(subject, block, topic, idx=idx)

                # Session-State vor-belegen, wenn „Alle“ getoggled wurde
                if sel_all:
                    st.session_state[child_key] = True
                elif sel_all_key in st.session_state and not sel_all:
                    st.session_state[child_key] = False

                checked = st.checkbox(c, key=child_key)
                if checked:
                    selected.setdefault(topic, []).append(c)

    # -------- Sidebar: Speichern-Button -----------------------------------
    save_btn = st.sidebar.button("💾 Auswahl speichern")
    if save_btn:
        if not selected:
            st.sidebar.warning("Bitte erst Kompetenzen auswählen …")
            return {}
        st.sidebar.success("Auswahl übernommen!")
        return {"subject": subject, "block": block, "data": selected}

    return {}

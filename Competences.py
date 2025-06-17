# competence_selector.py
"""
Streamlit‑App: Kompetenzen wählen & als YAML sichern
====================================================

Sidebar‑UI
----------
* **Fach**‑Auswahl wandert in die **Sidebar** (Selectbox).
* **Klasse** wird ebenfalls in der Sidebar gewählt.
* Hauptbereich zeigt direkt Tabs (*Block 5/6*, *Block 7* …) → Expanders für
  einzelne Themen → Checkboxen für Kompetenzen.
* Kein geschachtelter Expander mehr → Streamlit‑fehlerfrei.
* Speichern (💾) legt/ergänzt ``kompetenzen_<klasse>.yaml``.

Abhängigkeiten
--------------
```powershell
pip install streamlit pyyaml pandas
```
"""
from __future__ import annotations

import re
import yaml
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List
from competence_data import COMPETENCES, SUBJECTS

import streamlit as st
import pandas as pd


# ---------------------------------------------------------------------------
DATA_DIR = Path.cwd()


def yaml_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def yaml_save(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, width=120)


def merge_unique(old: List[str], new: List[str]) -> List[str]:
    return list(OrderedDict.fromkeys(old + new))

# ---------------------------------------------------------------------------
#  STREAMLIT UI
# ---------------------------------------------------------------------------
st.set_page_config("Kompetenz-Selector", page_icon="📋", layout="wide")

st.sidebar.header("Einstellungen")
subject = st.sidebar.selectbox("Fach wählen", SUBJECTS, index=1)
classroom = st.sidebar.selectbox(
    "Klasse wählen",
    ["5a", "5b", "5c", "6a", "6b", "6c", "7a", "7b", "7c"],
    index=0,
)

year = int(re.match(r"([567])", classroom).group(1))
blocks_to_show = ["5/6"] if year in (5, 6) else ["7/8", "5/6"]

st.sidebar.markdown("---")
file_name = f"kompetenzen_{classroom.lower()}.yaml"
st.sidebar.write(f"Zieldatei: **{file_name}**")

# ---------------------------------------------------------------------------
st.title("📋 Kompetenzen auswählen & sichern")

selected: Dict[str, Dict[str, List[str]]] = {subject: {}}
subj_dict = COMPETENCES.get(subject, {})

tabs = st.tabs([f"Block {b}" for b in blocks_to_show])
for tab, block in zip(tabs, blocks_to_show):
    with tab:
        block_dict = subj_dict.get(block, {})
        st.subheader(f"Block {block}")
        for topic, comp_list in block_dict.items():
            with st.expander(topic, expanded=False):
                # --- Select‑All Checkbox -----------------------------------
                sel_key = f"selall_{block}_{topic}"
                sel_all = st.checkbox("Alle auswählen / abwählen", key=sel_key)

                # Wenn sel_all umgeschaltet wurde ⇒ Session‑State der
                # Kinder‑Checkboxen synchronisieren, bevor sie gerendert werden.
                for i, c in enumerate(comp_list):
                    child_key = f"{block}_{topic}_{i}"
                    if sel_all:
                        st.session_state[child_key] = True
                    elif sel_key in st.session_state and not sel_all:
                        # Wenn Abwahl → nur abschalten, falls zuvor True
                        st.session_state[child_key] = False

                # --- Einzel‑Checkboxen ------------------------------------
                for i, c in enumerate(comp_list):
                    checked = st.checkbox(c, key=f"{block}_{topic}_{i}")
                    if checked:
                        selected[subject].setdefault(topic, []).append(c)

# ---------------------------------------------------------------------------
file_path = DATA_DIR / file_name
save_btn = st.sidebar.button("💾 Auswahl speichern")
action_msg = st.empty()

if save_btn:
    if not selected[subject]:
        action_msg.warning("Bitte erst Kompetenzen auswählen …")
    else:
        data = yaml_load(file_path)
        if not isinstance(data.get(subject), dict):
            data[subject] = {}
        for topic, comps in selected[subject].items():
            data[subject][topic] = merge_unique(data[subject].get(topic, []), comps)
        try:
            yaml_save(file_path, data)
            action_msg.success(f"Gespeichert → {file_name}")
        except Exception as exc:
            action_msg.error(f"Fehler beim Schreiben von {file_name}: {exc}")

# ---------------------------------------------------------------------------
if file_path.exists():
    with st.expander("Aktueller YAML-Inhalt", expanded=False):
        raw = yaml_load(file_path)
        st.code(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False))

        subj_section = raw.get(subject)
        if isinstance(subj_section, dict):
            df = pd.DataFrame(
                [
                    (top, comp)
                    for top, comps in subj_section.items()
                    for comp in comps
                ],
                columns=["Thema", "Kompetenz"],
            )
        else:
            df = pd.DataFrame(columns=["Thema", "Kompetenz"])
        st.dataframe(df, hide_index=True)
# KompetenzenTool.py  –  Streamlit-Startskript
# ------------------------------------------------------------
from __future__ import annotations
from pathlib import Path
from collections import OrderedDict
from typing import Dict, List
import datetime, yaml, streamlit as st, pandas as pd
from filelock import FileLock, Timeout                     #  ← NEU

from competence_data import COMPETENCES, SUBJECTS
import ui_components as ui

# -------- Ablageort -------------------------------------------------------
SAVE_DIR = Path("saved")
SAVE_DIR.mkdir(exist_ok=True)

# -------- Hilfsfunktionen -------------------------------------------------
def yaml_load(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def yaml_save(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            width=120,
        )

def merge_unique(old: List[str], new: List[str]) -> List[str]:
    """Alte + neue Liste → Duplikate entfernen, Reihenfolge erhalten."""
    return list(OrderedDict.fromkeys(old + new))

# -------------------------------------------------------------------------
result: Dict = ui.run_ui(COMPETENCES)

if result:
    subject = result["subject"]
    block   = result["block"]
    clss    = result["class"]          # z. B. "5a"
    new_sel = result["data"]           # {topic: [komps]}

    file_name = f"kompetenzen_{clss.lower()}.yaml"
    file_path = SAVE_DIR / file_name
    lock_path = file_path.with_suffix(file_path.suffix + ".lock")
    lock      = FileLock(lock_path, timeout=5)   # 5 s warten, dann Fehler

    try:
        with lock:
            data = yaml_load(file_path)

            # Struktur anlegen
            data.setdefault(subject, {})
            for topic, comps in new_sel.items():
                data[subject][topic] = merge_unique(
                    data[subject].get(topic, []), comps
                )

            # ----- Reihenfolge nach SUBJECT_ORDER -----------------
            ordered = OrderedDict()
            for subj in SUBJECTS:           # gewünschte Reihenfolge
                if subj in data:
                    ordered[subj] = data[subj]

            yaml_save(file_path, dict(ordered))
            

        st.sidebar.success(f"✅ Gespeichert in **{file_name}**")

        # ------- Vorschau -------------------------------------------------
        with st.expander("Aktueller YAML-Inhalt", expanded=False):
            st.code(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                language="yaml",
            )
            df = pd.DataFrame(
                [
                    (top, comp)
                    for top, comps in data[subject].items()
                    for comp in comps
                ],
                columns=["Thema", "Kompetenz"],
            )
            st.dataframe(df, hide_index=True)

    except Timeout:
        st.sidebar.error(
            "💥 Datei ist gerade von einem anderen Benutzer gesperrt.\n"
            "Bitte ein paar Sekunden warten und erneut speichern."
        )
    except Exception as exc:
        st.sidebar.error(f"❌ Fehler beim Schreiben: {exc}")

# app.py
import streamlit as st
from typing import Dict
import yaml, datetime, pathlib

# ---  eigene Module  ---
from competence_data import COMPETENCES          # nur Daten
import ui_components as ui                       # nur Oberfläche

# ---  UI anzeigen ---
result: Dict = ui.run_ui(COMPETENCES)

# ---  Falls der Benutzer auf „Speichern“ geklickt hat ---
if result:
    fn = pathlib.Path("saved") / f"{result['subject']}_{result['block']}.yaml"
    fn.parent.mkdir(exist_ok=True)
    # Eintrag anhängen (Zeitstempel → Auswahl)
    with fn.open("a", encoding="utf-8") as f:
        yaml.safe_dump(
            {str(datetime.datetime.now()) : result["data"]},
            f, allow_unicode=True, sort_keys=False
        )
    st.sidebar.info(f"Daten in **{fn.name}** gesichert.")

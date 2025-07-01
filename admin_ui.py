from __future__ import annotations
"""
admin_ui.py – Admin‑Seite für die Bericht‑Erstellung
===================================================
Sidebar:
  • (optionales) Passwort‑Feld  – Logik folgt später
  • Klassen‑Dropdown

Hauptfenster:
  • Scroll‑freie Tabelle (``st.data_editor``) aller Schüler der Klasse
    mit einer Checkbox‑Spalte **Drucken**
  • Button **„📄 Berichte erstellen“**  – derzeit Platzhalter

Die Höhe der Tabelle wird dynamisch so berechnet, dass immer alle
Zeilen auf einmal sichtbar sind; es gibt keinen vertikalen Scroll‑Bar.
"""
import streamlit as st
import pandas as pd
from sqlalchemy.orm import sessionmaker, Session

from db_schema import ENGINE, Student
from db_helpers import get_students_by_class, get_classes
from helpers import unique_key as _uk
from db_adapter import choose_database_ui

ROW_HEIGHT = 35  # Pixel pro Zeile inkl. Header; ggf. anpassen


def _load_students(classroom: str) -> list[Student]:
    with Session(ENGINE) as ses:
        return get_students_by_class(classroom, ses)


def run_admin_ui() -> None:
    """Entry‑Point für ui_components.run_ui()."""

    st.title("🛠️ Admin – Berichte erstellen")

    # -------- Sidebar -------------------------------------------------
    with st.sidebar:
        st.subheader("Admin‑Einstellungen")

        st.text_input("Passwort", type="password", key="_admin_pw")

        classes = get_classes()
        if not classes:
            st.error("Es sind noch keine Klassen angelegt.")
            st.stop()

        classroom = st.selectbox("Klasse wählen", classes, key="_admin_cls")

        # ENGINE, db_path = choose_database_ui()
        # Session = sessionmaker(bind=ENGINE, future=True)

    # -------- Daten laden --------------------------------------------
    students = _load_students(classroom)
    if not students:
        st.info(f"Keine Schüler in Klasse {classroom}.")
        return

    # -------- Tabelle vorbereiten ------------------------------------
    df = pd.DataFrame(
        {
            "ID":       [s.id for s in students],
            "Nachname": [s.last_name  for s in students],
            "Vorname":  [s.first_name for s in students],
            "Drucken":  [False] * len(students),
        }
    )

    table_height = (len(df) + 1) * ROW_HEIGHT  # +1 für Header

    df_edit = st.data_editor(
        df,
        hide_index=True,
        height=table_height,
        use_container_width=True,
        column_config={
            "Drucken": st.column_config.CheckboxColumn(required=False),
        },
        key=_uk("admin_editor", classroom),
    )

    to_print = df_edit.query("Drucken == True")["ID"].tolist()

    st.markdown("---")
    if st.button("📄 Berichte erstellen", key=_uk("create_reports", classroom)):
        st.success(f"{len(to_print)} Bericht(e) würden jetzt erstellt – Logik folgt.")
        st.json(to_print)  # Debug‑Ausgabe

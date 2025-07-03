from __future__ import annotations
"""
admin_ui.py – Admin-Seite
=========================
Es gibt genau **einen** Datensatz in der Tabelle *school_years*.
Die Sidebar zeigt diesen Eintrag (Schuljahr-Name, Halbjahr/Endjahr)
und einen editierbaren Berichtstag (Text-Eingabe DD.MM.YYYY).  

* Button **💾 Berichtstag speichern** speichert das Datum und
  führt ein `st.experimental_rerun()` aus.
* Hauptbereich bleibt unverändert (Schüler-Tabelle, Druck-Checkboxen).
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from sqlalchemy.orm import Session

from db_schema import ENGINE, Student, SchoolYear
from db_helpers import get_students_by_class, get_classes
from helpers import unique_key as _uk
from export import export_students


ROW_HEIGHT = 35  # Pixel pro Zeile inkl. Header

# ------------------------------------------------------------------
# Helper ------------------------------------------------------------
# ------------------------------------------------------------------

def _load_students(classroom: str) -> list[Student]:
    """Return ORM objects of all students in *classroom*."""
    with Session(ENGINE) as ses:
        return get_students_by_class(classroom, ses)


def _get_schoolyear() -> SchoolYear | None:
    """Return the single SchoolYear entry (newest if multiple exist)."""
    with Session(ENGINE) as ses:
        return (
            ses.query(SchoolYear)
               .order_by(SchoolYear.id.desc())
               .first()
        )


def _save_report_day(sy_id: int, new_date: date) -> None:
    """Persist *new_date* into the SchoolYear row identified by *sy_id*."""
    with Session(ENGINE) as ses:
        row = ses.query(SchoolYear).get(sy_id)
        if row:
            row.report_day = new_date
            ses.commit()


# ------------------------------------------------------------------
# Main entry --------------------------------------------------------
# ------------------------------------------------------------------

def run_admin_ui() -> None:
    """Entry-Point für *ui_components.run_ui()* – Admin-Modul."""

    st.title("🛠️ Admin – Berichte erstellen")

    # -------- Sidebar -------------------------------------------------
    with st.sidebar:
        st.subheader("Admin-Einstellungen")

        # Passwort-Feld (Platzhalter)
        st.text_input("Passwort", type="password", key="_admin_pw")

        # Klassen-Auswahl
        classes = get_classes()
        if not classes:
            st.error("Es sind noch keine Klassen angelegt.")
            st.stop()
        classroom = st.selectbox("Klasse wählen", classes, key="_admin_cls")

        # Schuljahr-Info + Berichtstag-Editor --------------------------
        sy = _get_schoolyear()
        if sy:
            label = "Endjahr" if sy.endjahr else "Halbjahr"
            st.markdown(f"**Schuljahr:** {sy.name}  \n**Modus:** {label}")

            # Textfeld (DD.MM.YYYY)
            default_str = sy.report_day.strftime("%d.%m.%Y") if sy.report_day else ""
            rpt_str = st.text_input(
                "Berichtstag (DD.MM.YYYY)",
                value=default_str,
                key="_admin_report_day",
            )

            if st.button("💾 Berichtstag speichern", key="_save_report_day"):
                try:
                    new_date = datetime.strptime(rpt_str, "%d.%m.%Y").date()
                except ValueError:
                    st.error("Ungültiges Datumsformat – bitte DD.MM.YYYY eingeben.")
                else:
                    _save_report_day(sy.id, new_date)
                    st.success(f"Berichtstag aktualisiert: {new_date.strftime('%d.%m.%Y')}")
                    safe_rerun()
        else:
            st.info("Kein Schuljahr-Eintrag in der Datenbank gefunden.")

    # -------- Hauptbereich ------------------------------------------
    students = _load_students(classroom)
    if not students:
        st.info(f"Keine Schüler in Klasse {classroom}.")
        return

    df = pd.DataFrame(
        {
            "ID":       [s.id for s in students],
            "Nachname": [s.last_name for s in students],
            "Vorname":  [s.first_name for s in students],
            "Drucken":  [False] * len(students),
        }
    )
    table_height = (len(df) + 1) * ROW_HEIGHT

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
    if st.button("📄 Berichte erstellen", key=_uk("create_reports", classroom)):
        lua_map, pdfs = export_students(to_print, classroom)
        st.success(
            f"{len(lua_map)} Lua/TeX-Dateien erzeugt, "
            f"{len(pdfs)} PDF(s) neu kompiliert."
        )
        st.json({"lua": lua_map, "pdf": [str(p) for p in pdfs]})

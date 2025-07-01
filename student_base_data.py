from __future__ import annotations
"""
studenten_ui.py – Stammdaten‑ & Zeugnistext‑Editor
"""

import math
import pandas as pd
import streamlit as st
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session

from db_schema  import ENGINE, Student
from db_helpers import get_students_by_class
from helpers    import unique_key as _uk
from helpers import safe_rerun


# ------------------------------------------------------------
# Konstanten
# ------------------------------------------------------------
ABSENCE_INT_COLS = [
    "Tage entsch.", "Tage unentsch.",
    "Std entsch.",  "Std unentsch.",
]

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def _students_to_df(students: List[Student]) -> pd.DataFrame:
    """Student‑Objekte → DataFrame für den Editor"""
    rows: List[Dict] = []
    for s in students:
        rows.append(
            {
                "Nachname"           : s.last_name,
                "Vorname"            : s.first_name,
                "Geburtstag"         : s.birthday,
                "Tage entsch."       : (s.days_absent_excused      or 0),
                "Tage unentsch."     : (s.days_absent_unexcused    or 0),
                "Std entsch."        : (s.lessons_absent_excused   or 0),
                "Std unentsch."      : (s.lessons_absent_unexcused or 0),
                "Bemerkungen"        : s.remarks or "",
                "LB"                 : bool(getattr(s, "lb", False)),
                "GB"                 : bool(getattr(s, "gb", False)),
            }
        )

    df = pd.DataFrame(rows)

    # Datentypen setzen
    df["Geburtstag"] = pd.to_datetime(df["Geburtstag"]).dt.date
    for col in ABSENCE_INT_COLS:
        df[col] = df[col].astype("Int64").fillna(0)
    return df


def _to_int_safe(value) -> int:
    """Hilfs‑Caster: NaN/None/"" ⇒ 0  sonst int(value)"""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return 0
    try:
        if isinstance(value, float) and math.isnan(value):
            return 0
    except TypeError:
        pass
    return int(value)


def _persist_df(classroom: str, df: pd.DataFrame, ses: Session) -> None:
    """Schreibt geänderte Stammdaten in die DB."""
    stu_map: Dict[Tuple[str, str], Student] = {
        (s.last_name, s.first_name): s for s in get_students_by_class(classroom, ses)
    }
    for _, row in df.iterrows():
        key = (row["Nachname"], row["Vorname"])
        stu = stu_map.get(key)
        if not stu:
            continue

        stu.birthday                 = pd.to_datetime(row["Geburtstag"]).date()
        stu.days_absent_excused      = _to_int_safe(row["Tage entsch."])
        stu.days_absent_unexcused    = _to_int_safe(row["Tage unentsch."])
        stu.lessons_absent_excused   = _to_int_safe(row["Std entsch."])
        stu.lessons_absent_unexcused = _to_int_safe(row["Std unentsch."])
        stu.remarks                  = row["Bemerkungen"] or ""
        stu.lb                       = bool(row["LB"])
        stu.gb                       = bool(row["GB"])
    ses.commit()

# ------------------------------------------------------------
# Haupt‑UI‑Funktion
# ------------------------------------------------------------

def run_base_data_editor(classroom: str) -> Dict:
    """Stammdaten‑ & Zeugnistext‑Editor für eine Klasse"""

    st.header(f"📋 Stammdaten – Klasse {classroom}")

    with Session(ENGINE) as ses:
        students = get_students_by_class(classroom, ses)
        if not students:
            st.info("Für diese Klasse sind noch keine Schüler hinterlegt.")
            return {}

        # ---------------- Tabelle ---------------------------
        df_orig = _students_to_df(students)
        df_edit = st.data_editor(
            df_orig,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "Geburtstag"   : st.column_config.DateColumn(format="DD.MM.YYYY"),
                **{c: st.column_config.NumberColumn(min_value=0, step=1) for c in ABSENCE_INT_COLS},
                "Bemerkungen"  : st.column_config.TextColumn(width="medium"),
                "LB"           : st.column_config.CheckboxColumn(),
                "GB"           : st.column_config.CheckboxColumn(),
            },
            key=_uk("stammdaten", classroom),
        )

        if st.button("💾 Änderungen speichern", key=_uk("save_base", classroom)):
            _persist_df(classroom, df_edit, ses)
            st.success("Stammdaten aktualisiert.")

        # ---------------- Zeugnistext ------------------------
        st.markdown("---")
        st.subheader("📝 Zeugnistext")

        # Auswahl‑Dropdown
        name_list = [f"{s.last_name}, {s.first_name}" for s in students]
        sel_name  = st.selectbox("Schüler auswählen", name_list, key=_uk("sel_stu", classroom))
        last, first = [p.strip() for p in sel_name.split(",", 1)]
        stu = next(s for s in students if s.last_name == last and s.first_name == first)

        txt_key = _uk("txt_report", f"{classroom}_{stu.id}")
        db_val  = stu.report_text or ""

        # Key erstmals anlegen → initialer Wert aus DB
        if txt_key not in st.session_state:
            st.session_state[txt_key] = db_val

        text = st.text_area(
            "Zeugnistext hier einfügen / bearbeiten",
            height=250,
            key=txt_key,
        )

        if st.button("💾 Text speichern", key=_uk("save_report", stu.id)):
            stu.report_text = text
            ses.commit()
            st.success("Text gespeichert.")
        safe_rerun()
    return {}

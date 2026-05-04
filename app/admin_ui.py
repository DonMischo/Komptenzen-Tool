from __future__ import annotations
"""
admin_ui.py – Admin-Seite
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from sqlalchemy.orm import Session

from db_schema import ENGINE, Student, SchoolYear
from db_helpers import get_students_by_class, get_classes
from helpers import unique_key as _uk
from export import prepare_export, compile_one


ROW_HEIGHT = 35


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_students(classroom: str) -> list[Student]:
    with Session(ENGINE) as ses:
        return get_students_by_class(classroom, ses)


def _get_schoolyear() -> SchoolYear | None:
    with Session(ENGINE) as ses:
        return ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()


def _save_report_day(sy_id: int, new_date: date) -> None:
    with Session(ENGINE) as ses:
        row = ses.query(SchoolYear).get(sy_id)
        if row:
            row.report_day = new_date
            ses.commit()


def _start_export(student_ids: list[int], classroom: str) -> None:
    """Kick off a new export run — stores state, triggers first rerun."""
    try:
        with st.spinner("Generiere Lua/TeX-Dateien …"):
            cl_dir, bases = prepare_export(student_ids, classroom)
    except Exception as e:
        st.error(f"Export fehlgeschlagen: {e}")
        return
    if not bases:
        st.warning("Keine Schüler ausgewählt.")
        return
    st.session_state["_exp_cl_dir"]  = str(cl_dir)
    st.session_state["_exp_bases"]   = bases
    st.session_state["_exp_idx"]     = 0
    st.session_state["_exp_pdfs"]    = []
    st.session_state["_exp_errors"]  = {}
    st.session_state["_exp_stop"]    = False
    st.rerun()


def _render_export_progress() -> None:
    """
    Called every rerun while an export is in progress.
    Compiles one student, then reruns — or shows results when done.
    Returns without doing anything if no export is active.
    """
    if "_exp_bases" not in st.session_state:
        return

    bases   = st.session_state["_exp_bases"]
    cl_dir  = Path(st.session_state["_exp_cl_dir"])
    idx     = st.session_state["_exp_idx"]
    total   = len(bases)
    stopped = st.session_state.get("_exp_stop", False)

    st.markdown("---")
    st.subheader("Zeugniserstellung läuft …" if not stopped else "Zeugniserstellung gestoppt")

    bar    = st.progress(idx / total if total else 1.0)
    status = st.empty()

    if idx < total and not stopped:
        base = bases[idx]
        status.text(f"{idx + 1}/{total}: {base.replace('_', ' ')}")

        if st.button("⏹ Stop", key="_exp_stop_btn"):
            st.session_state["_exp_stop"] = True
            st.rerun()

        pdf, err = compile_one(cl_dir, base)
        if pdf:
            st.session_state["_exp_pdfs"].append(str(pdf))
        if err:
            st.session_state["_exp_errors"][base] = err

        st.session_state["_exp_idx"] += 1
        st.rerun()

    else:
        # Finished or stopped — show results
        bar.progress(1.0)
        status.empty()
        pdfs   = st.session_state["_exp_pdfs"]
        errors = st.session_state["_exp_errors"]

        if pdfs:
            st.success(f"✅ {len(pdfs)}/{total} PDF(s) erstellt – gespeichert in `{cl_dir}`")
        if stopped and idx < total:
            st.info(f"Gestoppt nach {idx}/{total} Schüler(n).")
        if errors:
            st.warning(f"⚠️ {len(errors)} Fehler beim Kompilieren.")
            for base, err in errors.items():
                with st.expander(f"❌ lualatex-Fehler: {base}", expanded=True):
                    st.code(err[-3000:], language="text")

        if st.button("✖ Schließen", key="_exp_close"):
            for k in ["_exp_cl_dir", "_exp_bases", "_exp_idx",
                      "_exp_pdfs", "_exp_errors", "_exp_stop"]:
                st.session_state.pop(k, None)
            st.rerun()


# ------------------------------------------------------------------
# Main entry
# ------------------------------------------------------------------

def run_admin_ui() -> None:
    st.title("🛠️ Admin – Berichte erstellen")

    # -------- Sidebar -------------------------------------------------
    with st.sidebar:
        st.subheader("Admin-Einstellungen")

        classes = get_classes()
        if not classes:
            st.error("Es sind noch keine Klassen angelegt.")
            st.stop()
        classroom = st.selectbox("Klasse wählen", classes, key="_admin_cls")

        sy = _get_schoolyear()
        if sy:
            label = "Endjahr" if sy.endjahr else "Halbjahr"
            st.markdown(f"**Schuljahr:** {sy.name}  \n**Modus:** {label}")

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
                    st.rerun()
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

    df_edit = st.data_editor(
        df,
        hide_index=True,
        height=(len(df) + 1) * ROW_HEIGHT,
        width="stretch",
        column_config={
            "Drucken": st.column_config.CheckboxColumn(required=False),
        },
        key=_uk("admin_editor", classroom),
    )

    to_print     = df_edit.query("Drucken == True")["ID"].tolist()
    all_ids      = df_edit["ID"].tolist()

    # Show progress UI if an export is running (blocks buttons below)
    _render_export_progress()

    if "_exp_bases" in st.session_state:
        return  # don't show buttons while export is active

    st.markdown("---")
    col_sel, col_all = st.columns(2)

    with col_sel:
        if st.button(
            f"📄 Ausgewählte erstellen ({len(to_print)})",
            key=_uk("create_selected", classroom),
            disabled=not to_print,
        ):
            _start_export(to_print, classroom)

    with col_all:
        if st.button(
            f"📄 Alle erstellen ({len(all_ids)})",
            key=_uk("create_all", classroom),
        ):
            _start_export(all_ids, classroom)

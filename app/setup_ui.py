# setup_ui.py
# ------------------------------------------------------------------
"""
Startup / setup page – shown before the main app.
Handles: DB selection, schema init, Zeugnistag, backup, suggestions.
"""

from __future__ import annotations
import os
import re
import subprocess
from datetime import date, datetime

import streamlit as st
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import Session

from db_schema import (
    ENGINE,
    SchoolYear,
    _pg_base_url,
    switch_engine,
    init_db,
    list_report_dbs,
    create_report_db,
    suggest_db_name,
)
from time_functions import (
    fetch_halfyear_report_day,
    fetch_last_school_day,
    get_school_year,
)
from student_loader import (
    sync_students_from_upload,
    count_students,
)
from generate_test_data import generate_class_7a

DB_RX = re.compile(r"^reports_(\d{4})_(\d{2})_(hj|ej)$", re.I)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _schema_ready_for(db_name: str) -> bool:
    """Check whether the given DB has the schema (subjects table exists)."""
    try:
        eng = create_engine(f"{_pg_base_url()}/{db_name}", future=True)
        result = sa_inspect(eng).has_table("subjects")
        eng.dispose()
        return result
    except Exception:
        return False


def _drop_db(db_name: str) -> None:
    admin_url = f"{_pg_base_url()}/postgres"
    eng = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with eng.connect() as conn:
            # Terminate existing connections first
            conn.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = :db AND pid <> pg_backend_pid()"
            ), {"db": db_name})
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
    finally:
        eng.dispose()


def _pg_dump(db_name: str) -> bytes | None:
    """Run pg_dump and return SQL bytes, or None on failure."""
    url = f"{_pg_base_url()}/{db_name}"
    try:
        result = subprocess.run(
            ["pg_dump", url],
            capture_output=True,
            timeout=120,
        )
        return result.stdout if result.returncode == 0 else None
    except FileNotFoundError:
        return None  # pg_dump not installed
    except Exception:
        return None


def _get_school_year_row() -> SchoolYear | None:
    try:
        with Session(ENGINE) as ses:
            return ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_setup_ui() -> None:
    st.title("Kompetenzen-Tool")
    st.caption("Einrichtung & Verwaltung")

    # -----------------------------------------------------------------------
    # 1. Datenbank
    # -----------------------------------------------------------------------
    st.header("1. Datenbank")

    try:
        available = list_report_dbs()
    except Exception as e:
        st.error(f"Kann keine Verbindung zu PostgreSQL aufbauen: {e}")
        st.code("POSTGRES_URL = " + (_pg_base_url() or "nicht gesetzt"))
        st.stop()

    current_db = st.session_state.get("current_db", ENGINE.url.database or "")

    # --- select existing ---
    if available:
        col_sel, col_badge = st.columns([4, 1])
        with col_sel:
            sel_idx = available.index(current_db) if current_db in available else 0
            selected = st.selectbox("Vorhandene Datenbank wählen", available,
                                    index=sel_idx, key="_s_sel")
        with col_badge:
            st.markdown("<br>", unsafe_allow_html=True)
            if _schema_ready_for(selected):
                st.success("✅ Bereit")
            else:
                st.warning("⚠️ Kein Schema")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🔌 Verbinden", key="_s_connect"):
                switch_engine(selected)
                st.session_state["current_db"] = selected
                if not _schema_ready_for(selected):
                    st.session_state.pop("setup_done", None)
                st.rerun()

        with c2:
            schema_ok = _schema_ready_for(selected)
            label = "✅ Schema OK" if schema_ok else "🔧 Schema initialisieren"
            if st.button(label, key="_s_init", disabled=schema_ok):
                if selected != ENGINE.url.database:
                    switch_engine(selected)
                    st.session_state["current_db"] = selected
                with st.spinner("Initialisiere Schema & Kompetenzen …"):
                    init_db(drop=False, populate=True)
                st.success("Fertig!")
                st.rerun()

        with c3:
            if st.button("🗑️ Löschen", key="_s_del", type="secondary"):
                st.session_state["_confirm_delete"] = selected

        # delete confirmation
        if st.session_state.get("_confirm_delete") == selected:
            st.error(f"**{selected}** unwiderruflich löschen?")
            y, n = st.columns(2)
            with y:
                if st.button("Ja, löschen", key="_s_del_yes"):
                    _drop_db(selected)
                    if st.session_state.get("current_db") == selected:
                        st.session_state.pop("current_db", None)
                        st.session_state.pop("setup_done", None)
                        switch_engine("postgres")
                    st.session_state.pop("_confirm_delete", None)
                    st.rerun()
            with n:
                if st.button("Abbrechen", key="_s_del_no"):
                    st.session_state.pop("_confirm_delete", None)
                    st.rerun()
    else:
        selected = None
        st.info("Noch keine Datenbank vorhanden. Lege unten eine neue an.")

    # --- create new ---
    with st.expander("➕ Neue Datenbank anlegen"):
        c1, c2, c3 = st.columns([1, 3, 1])
        with c1:
            new_term = st.selectbox("Termin", ["hj", "ej"], key="_s_term")
        with c2:
            # Push updated suggestion into session state when term changes
            if st.session_state.get("_s_term_prev") != new_term:
                st.session_state["_s_new_name"] = suggest_db_name(new_term)
                st.session_state["_s_term_prev"] = new_term
            new_name = st.text_input("DB-Name", key="_s_new_name")
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Anlegen", key="_s_create"):
                if new_name in (available or []):
                    st.warning("Name bereits vorhanden.")
                elif not DB_RX.fullmatch(new_name):
                    st.error("Ungültiger Name. Erwartet: reports_YYYY_YY_hj/ej")
                else:
                    with st.spinner(f"Erstelle {new_name} …"):
                        create_report_db(new_name)
                        switch_engine(new_name)
                        st.session_state["current_db"] = new_name
                        init_db(drop=False, populate=True)
                    st.success(f"Datenbank {new_name} angelegt und initialisiert.")
                    st.rerun()

    # everything below only makes sense with a ready schema.
    # Priority: explicit connect > selectbox selection > ENGINE url > nothing
    active_db = (
        st.session_state.get("current_db")
        or st.session_state.get("_s_sel")
        or (ENGINE.url.database if ENGINE.url.database != "postgres" else "")
        or ""
    )

    if not active_db or not _schema_ready_for(active_db):
        st.info("Wähle eine Datenbank aus und klicke **🔌 Verbinden**, um fortzufahren.")
        return

    # Ensure ENGINE points to active_db (covers app restarts + implicit selection)
    if ENGINE.url.database != active_db:
        switch_engine(active_db)
        st.session_state["current_db"] = active_db

    st.divider()

    # -----------------------------------------------------------------------
    # 🧪 Testdaten (development helper)
    # -----------------------------------------------------------------------
    with st.expander("🧪 Testdaten generieren (Klasse 7a)", expanded=False):
        st.markdown(
            "Befüllt die Datenbank mit realistischen Testdaten für **Klasse 7a**:  \n"
            "Niveaus 1–3, Noten 1–4, ein Wahlpflichtfach pro Schüler, "
            "Zeugnistexte (~1 A4-Seite) und Sonderschüler **Alexander Herrmann** "
            "(Förderschwerpunkt Lernen, Worturteile in Mathe & Englisch).  \n"
            "⚠️ Bestehende Daten für Klasse 7a werden überschrieben."
        )
        if st.button("▶ Testdaten jetzt generieren", key="_s_gen_test"):
            with st.spinner("Generiere Testdaten …"):
                result = generate_class_7a()
            if result.startswith("✅"):
                st.success(result)
            else:
                st.error(result)

    st.divider()

    # -----------------------------------------------------------------------
    # 2. Zeugnistag
    # -----------------------------------------------------------------------
    st.header("2. Zeugnistag")

    sy = _get_school_year_row()
    is_ej    = sy.endjahr   if sy else False
    sy_name  = sy.name      if sy else get_school_year()
    existing = sy.report_day if sy else None
    label    = "Endjahr" if is_ej else "Halbjahr"

    st.markdown(f"**Schuljahr:** {sy_name} — {label}")

    # date input – value driven by session state so the fetch button can update it
    default_val = st.session_state.get("_ztag_value", existing or date.today())
    col_d, col_f = st.columns([2, 1])
    with col_d:
        zeugnistag = st.date_input("Datum", value=default_val,
                                   format="DD.MM.YYYY", key="_s_ztag")
    with col_f:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🌐 Aus Internet laden", key="_s_fetch"):
            with st.spinner("Lade Ferientermine …"):
                try:
                    raw = fetch_last_school_day() if is_ej else fetch_halfyear_report_day()
                    fetched = datetime.strptime(raw, "%d.%m.%Y").date()
                    st.session_state["_ztag_value"] = fetched
                    st.success(f"Vorschlag: **{fetched.strftime('%d.%m.%Y')}**  \nKlicke Speichern zum Übernehmen.")
                    st.rerun()
                except Exception as e:
                    st.warning(f"Konnte Ferien nicht laden: {e}")

    if st.button("💾 Zeugnistag speichern", key="_s_save_ztag"):
        try:
            with Session(ENGINE) as ses:
                row = ses.query(SchoolYear).order_by(SchoolYear.id.desc()).first()
                if row:
                    row.report_day = zeugnistag
                    ses.commit()
                    st.session_state.pop("_ztag_value", None)
                    st.success(f"Gespeichert: **{zeugnistag.strftime('%d.%m.%Y')}**")
                else:
                    st.error("Kein Schuljahreintrag in der Datenbank.")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

    st.divider()

    # -----------------------------------------------------------------------
    # 3. Schüler importieren
    # -----------------------------------------------------------------------
    st.header("3. Schüler importieren")

    n_students = count_students()
    if n_students:
        st.success(f"✅ {n_students} Schüler in der Datenbank")
    else:
        st.warning("⚠️ Noch keine Schüler in der Datenbank")

    with st.expander("📂 CSV hochladen & synchronisieren",
                     expanded=(n_students == 0)):
        st.markdown(
            "**Format:** CSV mit Header-Zeile. Pflichtfelder: "
            "`Nachname`, `Vorname`, `Klasse`, `Geburtsdatum`  \n"
            "Optional: `Fehltage`, `Fehltage Unentschuldigt`, "
            "`Fehlstunden`, `Fehlstunden Unentschuldigt`, "
            "`Zeugnistext`, `Bemerkungen`"
        )
        uploaded = st.file_uploader(
            "students.csv hochladen", type="csv", key="_s_csv_upload"
        )
        remove_flag = st.checkbox(
            "Schüler entfernen, die nicht in der CSV stehen",
            value=True, key="_s_remove_missing"
        )
        if uploaded is not None:
            if st.button("🔄 Synchronisieren", key="_s_do_sync", type="primary"):
                try:
                    added, updated, removed, row_errors = sync_students_from_upload(
                        uploaded.getvalue(), remove_missing=remove_flag
                    )
                    st.success(
                        f"Fertig — **{added}** neu hinzugefügt, "
                        f"**{updated}** aktualisiert, "
                        f"**{removed}** entfernt."
                    )
                    if row_errors:
                        with st.expander(f"⚠️ {len(row_errors)} Zeile(n) übersprungen"):
                            for err in row_errors:
                                st.warning(err)
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler beim Import: {e}")

    st.divider()

    # -----------------------------------------------------------------------
    # 4. Backup
    # -----------------------------------------------------------------------
    st.header("4. Backup")

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("📦 pg_dump erstellen", key="_s_dump"):
            with st.spinner("Erstelle Dump …"):
                dump = _pg_dump(active_db)
            if dump:
                st.download_button(
                    label="⬇️ SQL-Dump herunterladen",
                    data=dump,
                    file_name=f"{active_db}_{date.today()}.sql",
                    mime="text/plain",
                    key="_s_dl_dump",
                )
            else:
                st.error("pg_dump fehlgeschlagen. "
                         "Stelle sicher, dass `postgresql-client` im Container installiert ist "
                         "und der DB-User die CONNECT-Berechtigung hat.")
    with col_b2:
        st.caption("Erstellt einen vollständigen SQL-Dump der gewählten Datenbank "
                   "inkl. Schema und Daten. Kann mit `psql` wiederhergestellt werden.")

    st.divider()

    # -----------------------------------------------------------------------
    # 5. Vorschläge
    # -----------------------------------------------------------------------
    with st.expander("💡 Vorschläge & nächste Schritte", expanded=False):
        st.markdown("""
**Mögliche Erweiterungen:**

| Feature | Nutzen |
|---|---|
| 📋 Klassen-Vorlage kopieren | Kompetenzen einer Klasse auf eine andere übertragen |
| 🖨️ Sammel-Export | Alle Klassen auf einmal als PDF exportieren |
| 📊 Notenübersicht | Klassenweiser Durchschnitt pro Fach/Thema |
| 🔄 Automatisches Backup | pg_dump per Cron täglich sichern |
| 👤 Benutzer-Login | Lehreranmeldung per Passwort absichern |
| 🏫 Mehrere Schulen | Mandantenfähigkeit über separate DB-Instanzen |
| 📧 Export-Paket | Alle Zeugnisse als ZIP herunterladen |
| 📅 Kalenderansicht | Übersicht über bevorstehende Zeugnistermine |
        """)

    st.divider()

    # -----------------------------------------------------------------------
    # Weiter
    # -----------------------------------------------------------------------
    if st.button("▶️ Zur App", type="primary", width="stretch", key="_s_done"):
        st.session_state["setup_done"] = True
        st.rerun()

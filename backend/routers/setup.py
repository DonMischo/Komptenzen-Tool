# routers/setup.py
from __future__ import annotations

import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.orm import Session

import db_schema
from student_loader import count_students, sync_students_from_upload
from db_schema import (
    SchoolYear, create_report_db, init_db, list_report_dbs,
    suggest_db_name, switch_engine, _pg_base_url,
)
from deps import get_current_user, get_db
from schemas import (
    DatabaseCreateRequest, DatabaseListResponse, DatabaseSelectRequest,
    DatabaseSuggestResponse, ReportDayResponse, ReportDayUpdateRequest,
    SchemaStatusResponse, StudentImportResponse,
)
from time_functions import fetch_halfyear_report_day, fetch_last_school_day

router = APIRouter()


# ---------------------------------------------------------------------------
# Public endpoint — no auth required
# ---------------------------------------------------------------------------

@router.get("/public/latest-db")
def public_latest_db():
    """Returns the latest report DB name for auto-connection on the public site."""
    dbs = sorted(list_report_dbs())
    if not dbs:
        return {"db": None}
    switch_engine(dbs[-1])
    return {"db": dbs[-1]}


# ---------------------------------------------------------------------------
# Databases
# ---------------------------------------------------------------------------

def _current_db(request: Request) -> str | None:
    return request.headers.get("x-active-db")


@router.get("/databases", response_model=DatabaseListResponse)
def list_databases(request: Request, _: str = Depends(get_current_user)):
    dbs = list_report_dbs()
    return DatabaseListResponse(databases=dbs, current=_current_db(request))


@router.post("/databases", response_model=DatabaseListResponse)
def create_database(req: DatabaseCreateRequest, request: Request, _: str = Depends(get_current_user)):
    import re
    if not re.match(r"^reports_\d{4}_\d{2}_(hj|ej)$", req.name):
        raise HTTPException(400, "Ungültiger Datenbankname (erwartet: reports_YYYY_YY_hj|ej)")
    existing = list_report_dbs()
    if req.name not in existing:
        create_report_db(req.name)
    switch_engine(req.name)
    init_db(drop=False, populate=True)
    return DatabaseListResponse(databases=list_report_dbs(), current=req.name)


@router.post("/databases/select")
def select_database(req: DatabaseSelectRequest, _: str = Depends(get_current_user)):
    if req.name not in list_report_dbs():
        raise HTTPException(404, "Datenbank nicht gefunden")
    switch_engine(req.name)
    return {"ok": True, "db": req.name}


@router.delete("/databases/{name}")
def delete_database(name: str, _: str = Depends(get_current_user)):
    if name not in list_report_dbs():
        raise HTTPException(404, "Datenbank nicht gefunden")
    admin_url = f"{_pg_base_url()}/postgres"
    from sqlalchemy import create_engine
    eng = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
    finally:
        eng.dispose()
    return {"ok": True}


@router.get("/databases/suggest", response_model=DatabaseSuggestResponse)
def suggest_database(term: str = "hj", _: str = Depends(get_current_user)):
    return DatabaseSuggestResponse(suggested=suggest_db_name(term))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def _schema_ready(db: Session) -> bool:
    try:
        inspector = sa_inspect(db_schema.ENGINE)
        return "subjects" in inspector.get_table_names()
    except Exception:
        return False


@router.get("/setup/schema-status", response_model=SchemaStatusResponse)
def schema_status(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    ready = _schema_ready(db)
    count = 0
    if ready:
        try:
            count = count_students()
        except Exception:
            pass
    db_name = db_schema.ENGINE.url.database or ""
    return SchemaStatusResponse(db_name=db_name, schema_ready=ready, student_count=count)


@router.post("/setup/init-schema", response_model=SchemaStatusResponse)
def init_schema(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    init_db(drop=False, populate=True)
    db_name = db_schema.ENGINE.url.database or ""
    return SchemaStatusResponse(db_name=db_name, schema_ready=True, student_count=count_students())


# ---------------------------------------------------------------------------
# Report day
# ---------------------------------------------------------------------------

def _get_school_year(db: Session) -> SchoolYear | None:
    return db.query(SchoolYear).order_by(SchoolYear.id.desc()).first()


@router.get("/setup/report-day", response_model=ReportDayResponse)
def get_report_day(db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    sy = _get_school_year(db)
    if sy is None:
        raise HTTPException(404, "Kein Schuljahreintrag vorhanden")
    rd = sy.report_day.strftime("%d.%m.%Y") if sy.report_day else None
    return ReportDayResponse(report_day=rd, school_year=sy.name, is_endjahr=sy.endjahr)


@router.put("/setup/report-day", response_model=ReportDayResponse)
def set_report_day(req: ReportDayUpdateRequest, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    sy = _get_school_year(db)
    if sy is None:
        raise HTTPException(404, "Kein Schuljahreintrag vorhanden")
    try:
        sy.report_day = datetime.strptime(req.report_day, "%d.%m.%Y").date()
    except ValueError:
        raise HTTPException(400, "Ungültiges Datum (erwartet: DD.MM.YYYY)")
    db.commit()
    return ReportDayResponse(
        report_day=sy.report_day.strftime("%d.%m.%Y"),
        school_year=sy.name,
        is_endjahr=sy.endjahr,
    )


@router.get("/setup/report-day/fetch")
def fetch_report_day(type: str = "hj", _: str = Depends(get_current_user)):
    try:
        if type == "ej":
            suggested = fetch_last_school_day()
        else:
            suggested = fetch_halfyear_report_day()
        return {"suggested": suggested}
    except Exception as e:
        raise HTTPException(502, f"Ferien-Daten konnten nicht geladen werden: {e}")


# ---------------------------------------------------------------------------
# Test data (development / demo)
# ---------------------------------------------------------------------------

@router.post("/setup/testdata")
def generate_testdata(_: str = Depends(get_current_user)):
    from generate_test_data import generate_class_7a
    msg = generate_class_7a()
    return {"message": msg}


# ---------------------------------------------------------------------------
# Student import
# ---------------------------------------------------------------------------

@router.post("/setup/students/upload", response_model=StudentImportResponse)
async def upload_students(
    file: UploadFile = File(...),
    remove_missing: bool = Form(False),
    _: str = Depends(get_current_user),
):
    csv_bytes = await file.read()
    try:
        added, updated, removed, errors = sync_students_from_upload(csv_bytes, remove_missing)
    except Exception as e:
        raise HTTPException(400, str(e))
    return StudentImportResponse(added=added, updated=updated, removed=removed, errors=errors)


# ---------------------------------------------------------------------------
# Backup (pg_dump)
# ---------------------------------------------------------------------------

@router.get("/setup/backup")
def backup_database(request: Request, _: str = Depends(get_current_user)):
    db_name = _current_db(request)
    if not db_name:
        raise HTTPException(400, "Keine aktive Datenbank ausgewählt")

    import re, os
    pg_url = _pg_base_url()
    match = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?", pg_url)
    env = os.environ.copy()
    cmd = ["pg_dump", "-Fp"]
    if match:
        env["PGPASSWORD"] = match.group(2)
        cmd += ["-U", match.group(1), "-h", match.group(3)]
        if match.group(4):
            cmd += ["-p", match.group(4)]
    cmd.append(db_name)

    try:
        result = subprocess.run(cmd, capture_output=True, env=env, timeout=120)
        if result.returncode != 0:
            raise HTTPException(500, f"pg_dump Fehler: {result.stderr.decode()}")
        sql_bytes = result.stdout
    except FileNotFoundError:
        raise HTTPException(500, "pg_dump nicht gefunden")

    today = datetime.now().strftime("%Y%m%d")
    filename = f"{db_name}_{today}.sql"

    def iter_bytes():
        yield sql_bytes

    return StreamingResponse(
        iter_bytes(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

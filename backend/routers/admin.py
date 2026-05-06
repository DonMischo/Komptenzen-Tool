# routers/admin.py — student list and PDF export via background task + polling
from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from db_helpers import get_students_by_class
from export import compile_one, prepare_export
from deps import get_current_user, get_db
from schemas import AdminStudentItem, ExportPrepareRequest, ExportPrepareResponse
import db_schema

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory job store
# {job_id: {cl_dir, basenames, active_db, done: bool, results: list}}
_jobs: dict[str, dict] = {}


@router.get("/students", response_model=list[AdminStudentItem])
def list_students(
    class_name: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    students = get_students_by_class(class_name, db)
    return [
        AdminStudentItem(
            id=s.id,
            last_name=s.last_name,
            first_name=s.first_name,
            class_name=s.school_class.name if s.school_class else class_name,
        )
        for s in students
    ]


def _run_export(job_id: str) -> None:
    """Background task: compile all students and update _jobs in place."""
    job = _jobs.get(job_id)
    if not job:
        return

    cl_dir = Path(job["cl_dir"])
    basenames: list[str] = job["basenames"]
    active_db = job.get("active_db")

    if active_db:
        db_schema.switch_engine(active_db)

    for base in basenames:
        if job.get("cancelled"):
            break
        pdf, err = compile_one(cl_dir, base)
        job["results"].append({
            "type": "progress",
            "basename": base,
            "success": err is None,
            "error": err,
            "index": len(job["results"]) + 1,
            "total": len(basenames),
        })

    job["done"] = True


@router.post("/export/prepare", response_model=ExportPrepareResponse)
def export_prepare(
    req: ExportPrepareRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.student_ids:
        raise HTTPException(400, "Keine Schüler ausgewählt")

    active_db = request.headers.get("x-active-db")
    try:
        cl_dir, basenames = prepare_export(req.student_ids, req.classroom)
    except Exception as e:
        logger.exception("export_prepare failed")
        raise HTTPException(500, f"Export-Vorbereitung fehlgeschlagen: {e}")

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "cl_dir": str(cl_dir),
        "basenames": basenames,
        "active_db": active_db,
        "done": False,
        "cancelled": False,
        "results": [],
    }
    background_tasks.add_task(_run_export, job_id)
    return ExportPrepareResponse(job_id=job_id, cl_dir=str(cl_dir), total=len(basenames))


@router.get("/export/progress/{job_id}")
def export_progress(job_id: str, _: str = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Export-Job nicht gefunden")
    return {
        "done": job["done"],
        "total": len(job["basenames"]),
        "results": job["results"],
    }


@router.post("/export/cancel/{job_id}")
def export_cancel(job_id: str, _: str = Depends(get_current_user)):
    job = _jobs.get(job_id)
    if job:
        job["cancelled"] = True
    return {"ok": True}

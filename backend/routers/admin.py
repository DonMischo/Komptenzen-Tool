# routers/admin.py — student list and PDF export via SSE
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

import logging
from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from db_helpers import get_students_by_class
from export import compile_one, prepare_export
from deps import get_current_user, get_db
from schemas import AdminStudentItem, ExportPrepareRequest, ExportPrepareResponse
import db_schema

router = APIRouter()

# In-memory job store: {job_id: {cl_dir, basenames, active_db}}
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


@router.post("/export/prepare", response_model=ExportPrepareResponse)
def export_prepare(
    req: ExportPrepareRequest,
    request: Request,
    _: str = Depends(get_current_user),
    db: Session = Depends(get_db),  # ensures switch_engine() is called first
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
    }
    return ExportPrepareResponse(job_id=job_id, cl_dir=str(cl_dir), total=len(basenames))


@router.get("/export/stream/{job_id}")
async def export_stream(job_id: str, request: Request):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Export-Job nicht gefunden")

    async def generate():
        cl_dir = Path(job["cl_dir"])
        basenames: list[str] = job["basenames"]
        active_db = job.get("active_db")

        if active_db:
            db_schema.switch_engine(active_db)

        loop = asyncio.get_event_loop()

        for i, base in enumerate(basenames):
            if await request.is_disconnected():
                break

            pdf, err = await loop.run_in_executor(None, compile_one, cl_dir, base)

            event_data = json.dumps({
                "type": "progress",
                "index": i + 1,
                "total": len(basenames),
                "basename": base,
                "success": err is None,
                "error": err,
            })
            yield {"data": event_data}

        yield {"data": json.dumps({
            "type": "done",
            "index": len(basenames),
            "total": len(basenames),
        })}

        _jobs.pop(job_id, None)

    return EventSourceResponse(generate())

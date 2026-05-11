# routers/stammdaten.py — student base data and report text
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_helpers import get_students_by_class
from db_schema import Student
from deps import get_db, get_current_user
from schemas import StudentBaseData, StudentBaseDataUpdate, ReportTextUpdate

router = APIRouter(dependencies=[Depends(get_current_user)])


def _student_to_schema(stu: Student) -> StudentBaseData:
    return StudentBaseData(
        id=stu.id,
        last_name=stu.last_name,
        first_name=stu.first_name,
        birthday=stu.birthday.strftime("%d.%m.%Y") if stu.birthday else None,
        days_absent_excused=stu.days_absent_excused or 0,
        days_absent_unexcused=stu.days_absent_unexcused or 0,
        lessons_absent_excused=stu.lessons_absent_excused or 0,
        lessons_absent_unexcused=stu.lessons_absent_unexcused or 0,
        remarks=stu.remarks or "",
        lb=bool(stu.lb),
        gb=bool(stu.gb),
        report_text=stu.report_text or "",
    )


@router.get("", response_model=list[StudentBaseData])
def list_stammdaten(
    class_name: str,
    db: Session = Depends(get_db),
):
    students = get_students_by_class(class_name, db)
    return [_student_to_schema(s) for s in students]


@router.post("/batch")
def save_stammdaten_batch(
    data: list[StudentBaseData],
    db: Session = Depends(get_db),
):
    updated = 0
    for item in data:
        stu = db.get(Student, item.id)
        if stu is None:
            continue
        if item.birthday:
            try:
                stu.birthday = datetime.strptime(item.birthday, "%d.%m.%Y").date()
            except ValueError:
                pass
        stu.days_absent_excused    = item.days_absent_excused
        stu.days_absent_unexcused  = item.days_absent_unexcused
        stu.lessons_absent_excused  = item.lessons_absent_excused
        stu.lessons_absent_unexcused = item.lessons_absent_unexcused
        stu.remarks = item.remarks
        stu.lb = item.lb
        stu.gb = item.gb
        updated += 1
    db.commit()
    return {"ok": True, "updated": updated}


@router.patch("/{student_id}", response_model=StudentBaseData)
def update_student(
    student_id: int,
    req: StudentBaseDataUpdate,
    db: Session = Depends(get_db),
):
    stu = db.get(Student, student_id)
    if stu is None:
        raise HTTPException(404, "Schüler nicht gefunden")

    if req.birthday is not None:
        try:
            stu.birthday = datetime.strptime(req.birthday, "%d.%m.%Y").date()
        except ValueError:
            raise HTTPException(400, "Ungültiges Datum (erwartet: DD.MM.YYYY)")
    if req.days_absent_excused is not None:
        stu.days_absent_excused = req.days_absent_excused
    if req.days_absent_unexcused is not None:
        stu.days_absent_unexcused = req.days_absent_unexcused
    if req.lessons_absent_excused is not None:
        stu.lessons_absent_excused = req.lessons_absent_excused
    if req.lessons_absent_unexcused is not None:
        stu.lessons_absent_unexcused = req.lessons_absent_unexcused
    if req.remarks is not None:
        stu.remarks = req.remarks
    if req.lb is not None:
        stu.lb = req.lb
    if req.gb is not None:
        stu.gb = req.gb

    db.commit()
    return _student_to_schema(stu)


@router.get("/{student_id}/report-text")
def get_report_text(
    student_id: int,
    db: Session = Depends(get_db),
):
    stu = db.get(Student, student_id)
    if stu is None:
        raise HTTPException(404, "Schüler nicht gefunden")
    return {"report_text": stu.report_text or ""}


@router.put("/{student_id}/report-text")
def save_report_text(
    student_id: int,
    req: ReportTextUpdate,
    db: Session = Depends(get_db),
):
    stu = db.get(Student, student_id)
    if stu is None:
        raise HTTPException(404, "Schüler nicht gefunden")
    stu.report_text = req.report_text
    db.commit()
    return {"ok": True}

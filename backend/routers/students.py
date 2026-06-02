# routers/students.py — grade matrix
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_helpers import (
    get_students_by_class, get_topics_by_subject,
    fetch_grade_matrix, persist_grade_matrix, get_niveau,
)
from db_schema import Subject
from deps import get_db, get_current_user
from schemas import (
    GradeMatrixColumn, GradeMatrixResponse, GradeMatrixRow, GradeMatrixSaveRequest,
)

router = APIRouter(dependencies=[Depends(get_current_user)])

LEBENSPRAXIS = "Lebenspraxis"


@router.get("/matrix", response_model=GradeMatrixResponse)
def get_matrix(
    class_name: str,
    subject: str,
    db: Session = Depends(get_db),
):
    students = get_students_by_class(class_name, db)
    if not students:
        return GradeMatrixResponse(columns=[], rows=[])

    # Lebenspraxis: only LB/GB students, no topic columns, Niveau = free text
    if subject == LEBENSPRAXIS:
        lb_gb = [s for s in students if s.lb or s.gb]
        if not lb_gb:
            return GradeMatrixResponse(columns=[], rows=[])
        subj = db.query(Subject).filter_by(name=LEBENSPRAXIS).first()
        subj_id = subj.id if subj else None
        rows = []
        for stu in lb_gb:
            niveau = (get_niveau(stu.id, subj_id, db) if subj_id else "") or ""
            stype = "gb" if stu.gb else "lb"
            rows.append(GradeMatrixRow(
                student_id=stu.id,
                last_name=stu.last_name,
                first_name=stu.first_name,
                niveau=niveau,
                grades={},
                student_type=stype,
            ))
        return GradeMatrixResponse(columns=[], rows=rows)

    topics = get_topics_by_subject(subject, db, class_name=class_name)
    if not topics:
        return GradeMatrixResponse(columns=[], rows=[])

    df = fetch_grade_matrix(students, topics, subject, db)

    columns = [
        GradeMatrixColumn(
            topic_id=t.id,
            label=f"{subject} – {t.name} ({t.block})",
        )
        for t in topics
    ]

    rows: list[GradeMatrixRow] = []
    for i, stu in enumerate(students):
        row_data = df.iloc[i]
        grades = {str(t.id): str(row_data.get(str(t.id), "") or "") for t in topics}
        stype = "gb" if stu.gb else ("lb" if stu.lb else "normal")
        rows.append(GradeMatrixRow(
            student_id=stu.id,
            last_name=stu.last_name,
            first_name=stu.first_name,
            niveau=str(row_data.get("Niveau", "") or ""),
            grades=grades,
            student_type=stype,
        ))

    return GradeMatrixResponse(columns=columns, rows=rows)


@router.post("/matrix")
def save_matrix(req: GradeMatrixSaveRequest, db: Session = Depends(get_db)):
    # Lebenspraxis: save only Niveau per student (no topic grades)
    if req.subject == LEBENSPRAXIS:
        from db_schema import Student, StudentSubject
        subj = db.query(Subject).filter_by(name=LEBENSPRAXIS).first()
        if not subj:
            return {"ok": True}
        for row in req.rows:
            stu = db.query(Student).filter_by(id=row.student_id).first()
            if not stu:
                continue
            link = db.query(StudentSubject).filter_by(
                student_id=stu.id, subject_id=subj.id
            ).first()
            if link:
                link.niveau = row.niveau or None
            else:
                db.add(StudentSubject(student_id=stu.id, subject_id=subj.id, niveau=row.niveau or None))
        db.commit()
        return {"ok": True}

    topics = get_topics_by_subject(req.subject, db, class_name=req.class_name)
    if not topics:
        raise HTTPException(404, f"Keine Themen für Fach '{req.subject}' gefunden")

    # Reconstruct pandas DataFrame expected by persist_grade_matrix
    records = []
    for row in req.rows:
        record = {
            "Nachname": row.last_name,
            "Vorname": row.first_name,
            "Niveau": row.niveau,
        }
        for t in topics:
            record[str(t.id)] = row.grades.get(str(t.id), "")
        records.append(record)

    df = pd.DataFrame(records)
    persist_grade_matrix(req.class_name, req.subject, df, db)
    return {"ok": True}

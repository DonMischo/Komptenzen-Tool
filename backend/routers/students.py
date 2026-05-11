# routers/students.py — grade matrix
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_helpers import (
    get_students_by_class, get_topics_by_subject,
    fetch_grade_matrix, persist_grade_matrix,
)
from deps import get_db, get_current_user
from schemas import (
    GradeMatrixColumn, GradeMatrixResponse, GradeMatrixRow, GradeMatrixSaveRequest,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/matrix", response_model=GradeMatrixResponse)
def get_matrix(
    class_name: str,
    subject: str,
    db: Session = Depends(get_db),
):
    students = get_students_by_class(class_name, db)
    if not students:
        return GradeMatrixResponse(columns=[], rows=[])

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
        rows.append(GradeMatrixRow(
            student_id=stu.id,
            last_name=stu.last_name,
            first_name=stu.first_name,
            niveau=str(row_data.get("Niveau", "") or ""),
            grades=grades,
        ))

    return GradeMatrixResponse(columns=columns, rows=rows)


@router.post("/matrix")
def save_matrix(req: GradeMatrixSaveRequest, db: Session = Depends(get_db)):
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

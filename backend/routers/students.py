# routers/students.py — grade matrix
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_helpers import (
    get_students_by_class, get_topics_by_subject,
    fetch_grade_matrix, persist_grade_matrix, get_niveau,
)
from db_schema import (
    Subject, Student, SchoolClass, Topic, Competence, ClassCompetence,
    StudentSubject, Grade,
)
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
            label=f"{t.name} ({t.block})",
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


# Subjects shown for LB/GB students per grade level
_LB_RELEVANT: dict[str, list[str]] = {
    "5": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Geschichte", "Geografie",
        "Werkstätten", "Technisches Werken", "Sport", "Medienbildung und Informatik",
        "Lebenspraxis",
    ],
    "6": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Geschichte", "Geografie",
        "Werkstätten", "Technisches Werken", "Sport", "Medienbildung und Informatik",
        "Lebenspraxis",
    ],
    "7": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Physik", "Chemie",
        "Geschichte", "Geografie", "Werkstätten", "Technisches Werken", "Sport",
        "Lebenspraxis",
    ],
}


@router.get("/{student_id}/lb-profile")
def get_lb_profile(student_id: int, db: Session = Depends(get_db)):
    """Full competence/grade profile for one LB or GB student across all subjects."""
    stu = db.get(Student, student_id)
    if not stu or (not stu.lb and not stu.gb):
        raise HTTPException(404, "Student not found or not LB/GB")

    class_row = db.scalar(select(SchoolClass).where(SchoolClass.id == stu.class_id))
    class_name = class_row.name if class_row else ""
    year = next((ch for ch in class_name if ch.isdigit()), "5")
    subject_names = _LB_RELEVANT.get(year, _LB_RELEVANT["5"])

    subjects_out = []
    for subj_name in subject_names:
        subj = db.scalar(select(Subject).where(Subject.name == subj_name))
        if not subj:
            continue

        # Niveau for this student + subject
        ss = db.scalar(
            select(StudentSubject).where(
                StudentSubject.student_id == student_id,
                StudentSubject.subject_id == subj.id,
            )
        )
        niveau = (ss.niveau if ss else None) or ""

        # Topics with selected competences for this class (skip for Lebenspraxis)
        topics_out = []
        if subj_name != LEBENSPRAXIS and class_row:
            topics = db.scalars(
                select(Topic)
                .join(Competence, Topic.id == Competence.topic_id)
                .join(ClassCompetence, Competence.id == ClassCompetence.competence_id)
                .where(
                    Topic.subject_id == subj.id,
                    ClassCompetence.class_id == class_row.id,
                    ClassCompetence.selected.is_(True),
                )
                .distinct()
                .order_by(Topic.id)
            ).all()

            for t in topics:
                grade_row = db.scalar(
                    select(Grade).where(
                        Grade.student_id == student_id,
                        Grade.topic_id == t.id,
                    )
                )
                topics_out.append({
                    "topic_id": t.id,
                    "label": f"{t.name} ({t.block})",
                    "grade": (grade_row.value if grade_row else "") or "",
                })

        subjects_out.append({
            "name": subj_name,
            "niveau": niveau,
            "topics": topics_out,
        })

    return {
        "student_id": stu.id,
        "first_name": stu.first_name,
        "last_name": stu.last_name,
        "class_name": class_name,
        "student_type": "gb" if stu.gb else "lb",
        "subjects": subjects_out,
    }

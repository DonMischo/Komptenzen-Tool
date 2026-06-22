# routers/students.py — grade matrix
from __future__ import annotations

import pandas as pd
from collections import defaultdict
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

    # Merge topics that share the same name (e.g. "Arithmetik" in 5/6 and 7/8).
    # The canonical topic (highest id = most recent block) wins; grades from
    # other blocks in the group are coalesced into the canonical column.
    name_to_ids: dict[str, list[int]] = defaultdict(list)
    for t in topics:
        name_to_ids[t.name].append(t.id)

    topic_by_id = {t.id: t for t in topics}
    canonical_id_for: dict[str, int] = {
        name: max(ids) for name, ids in name_to_ids.items()
    }

    # Coalesce duplicate-name columns in the DataFrame
    for name, ids in name_to_ids.items():
        if len(ids) < 2:
            continue
        canon_col = str(canonical_id_for[name])
        other_cols = [str(tid) for tid in ids if tid != canonical_id_for[name]]
        for row_idx in df.index:
            if not df.at[row_idx, canon_col]:
                for col in other_cols:
                    if col in df.columns and df.at[row_idx, col]:
                        df.at[row_idx, canon_col] = df.at[row_idx, col]
                        break

    # Build deduplicated topic list preserving first-occurrence order
    seen: set[str] = set()
    deduped: list = []
    for t in topics:
        if t.name not in seen:
            seen.add(t.name)
            deduped.append(topic_by_id[canonical_id_for[t.name]])

    merged_names = {name for name, ids in name_to_ids.items() if len(ids) > 1}

    columns = [
        GradeMatrixColumn(
            topic_id=t.id,
            label=t.name if t.name in merged_names else f"{t.name} ({t.block})",
        )
        for t in deduped
    ]

    rows: list[GradeMatrixRow] = []
    for i, stu in enumerate(students):
        row_data = df.iloc[i]
        grades = {str(t.id): str(row_data.get(str(t.id), "") or "") for t in deduped}
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
            raw_topics = db.scalars(
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

            # Merge same-name topics: canonical = highest topic_id
            lp_name_to_ids: dict[str, list[int]] = defaultdict(list)
            for t in raw_topics:
                lp_name_to_ids[t.name].append(t.id)
            lp_by_id = {t.id: t for t in raw_topics}
            lp_canonical = {name: max(ids) for name, ids in lp_name_to_ids.items()}
            lp_merged = {name for name, ids in lp_name_to_ids.items() if len(ids) > 1}

            seen_t: set[str] = set()
            for t in raw_topics:
                if t.name in seen_t:
                    continue
                seen_t.add(t.name)
                canon_t = lp_by_id[lp_canonical[t.name]]
                all_ids = lp_name_to_ids[t.name]

                # Find grade: prefer canonical, fall back to other alias ids
                grade_val = ""
                for tid in sorted(all_ids, reverse=True):
                    gr = db.scalar(select(Grade).where(
                        Grade.student_id == student_id,
                        Grade.topic_id == tid,
                    ))
                    if gr and gr.value:
                        grade_val = gr.value
                        break

                label = t.name if t.name in lp_merged else f"{t.name} ({t.block})"
                topics_out.append({
                    "topic_id": canon_t.id,
                    "label": label,
                    "grade": grade_val,
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

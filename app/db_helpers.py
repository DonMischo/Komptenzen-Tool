# db_helpers.py
# -------------------------------------------------------------------
"""
Datenbank-Helper für das Kompetenzen-Tool (SQLAlchemy ≥ 2.0).
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from sqlalchemy import select, update, delete, distinct, func
from sqlalchemy.orm import Session

from helpers import unique_key as _uk

import pandas as pd
import numpy as np

from db_schema import (
    ENGINE, Subject, Topic, Competence, SchoolClass, ClassCompetence,
    CustomCompetence, Student, StudentSubject, Grade,
)

# -------------------------------------------------------------------
class _AutoSes:
    def __init__(self, ses: Session | None = None):
        self._ext = ses
        self.ses: Session | None = None

    def __enter__(self) -> Session:
        if self._ext is not None:
            self.ses = self._ext
            return self.ses
        self.ses = Session(ENGINE)
        return self.ses

    def __exit__(self, exc_type, exc, tb):
        if self._ext is None and self.ses is not None:
            self.ses.close()

# -------------------------------------------------------------------
def _clean_grade(val) -> str:
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()

def _get_or_create_class(ses: Session, name: str) -> SchoolClass:
    stmt = select(SchoolClass).where(SchoolClass.name == name.strip())
    obj = ses.scalars(stmt).first()
    if obj is None:
        obj = SchoolClass(name=name.strip())
        ses.add(obj)
        ses.flush()
    return obj

def _get_or_create_class_id(name: str, ses: Session) -> int:
    return _get_or_create_class(ses, name).id

def _get_subject_id(name: str, ses: Session) -> Optional[int]:
    return ses.scalar(select(Subject.id).where(Subject.name == name.strip()))

def _get_topic_id(subject_id: int, topic_name: str, ses: Session) -> Optional[int]:
    return ses.scalar(
        select(Topic.id).where(
            (Topic.subject_id == subject_id) & (Topic.name == topic_name.strip())
        )
    )

# -------------------------------------------------------------------
def get_classes(ses: Session | None = None) -> list[str]:
    close = False
    if ses is None:
        ses, close = Session(ENGINE), True
    names = list(ses.scalars(select(SchoolClass.name).order_by(SchoolClass.name)))
    if close:
        ses.close()
    return names

def get_students_by_class(class_name: str, ses: Session) -> list[Student]:
    cls = _get_or_create_class(ses, class_name)
    return list(ses.scalars(
        select(Student)
        .where(Student.class_id == cls.id)
        .order_by(Student.last_name, Student.first_name)
    ))

def get_topics_by_subject(subject: str, ses: Session, class_name: str | None = None) -> list[Topic]:
    if class_name:
        # Subquery: IDs of topics with at least one selected competence for this class.
        # Avoids DISTINCT ON which PostgreSQL requires to match ORDER BY.
        cl = _get_or_create_class(ses, class_name)
        active_topic_ids = (
            select(Topic.id)
            .join(Competence, Topic.id == Competence.topic_id)
            .join(ClassCompetence,
                  (ClassCompetence.class_id == cl.id)
                  & (ClassCompetence.competence_id == Competence.id)
                  & (ClassCompetence.selected.is_(True)))
            .scalar_subquery()
        )
        stmt = (
            select(Topic).join(Subject)
            .where(Subject.name == subject)
            .where(Topic.id.in_(active_topic_ids))
            .order_by(Topic.block, Topic.name)
        )
    else:
        stmt = (
            select(Topic).join(Subject)
            .where(Subject.name == subject)
            .order_by(Topic.block, Topic.name)
        )
    return list(ses.scalars(stmt))

def get_subjects() -> List[str]:
    with Session(ENGINE) as ses:
        return list(ses.scalars(select(Subject.name).order_by(Subject.name)))

def get_blocks(subject: str) -> List[str]:
    with Session(ENGINE) as ses:
        return list(ses.scalars(
            select(Topic.block).join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.name == subject).distinct().order_by(Topic.block)
        ))

def load_topic_rows(class_name: str, subject: str, block: str) -> List[Tuple[int, str, str, bool]]:
    with Session(ENGINE) as ses:
        school_class = _get_or_create_class(ses, class_name)
        stmt = (
            select(Competence.id, Topic.name, Competence.text, ClassCompetence.selected)
            .join(Topic, Competence.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .outerjoin(ClassCompetence,
                       (ClassCompetence.class_id == school_class.id)
                       & (ClassCompetence.competence_id == Competence.id))
            .where(Subject.name == subject, Topic.block == block)
            .order_by(Topic.name, Competence.text)
        )
        rows = ses.execute(stmt).all()
    return [(cid, topic, text, bool(sel)) for cid, topic, text, sel in rows]

def save_selections(class_name: str, changes: List[Tuple[int, bool]]) -> None:
    if not changes:
        return
    with Session(ENGINE) as ses:
        cl = _get_or_create_class(ses, class_name)
        for comp_id, is_sel in changes:
            link = ses.scalars(
                select(ClassCompetence).where(
                    (ClassCompetence.class_id == cl.id)
                    & (ClassCompetence.competence_id == comp_id)
                )
            ).first()
            if link:
                link.selected = is_sel
            else:
                ses.add(ClassCompetence(class_id=cl.id, competence_id=comp_id, selected=is_sel))
        ses.commit()

def toggle_topic(class_name: str, topic_id: int, value: bool) -> None:
    with Session(ENGINE) as ses:
        cl = _get_or_create_class(ses, class_name)
        comp_ids = [cid for (cid,) in ses.execute(
            select(Competence.id).where(Competence.topic_id == topic_id)
        )]
        ses.execute(
            update(ClassCompetence)
            .where((ClassCompetence.class_id == cl.id)
                   & (ClassCompetence.competence_id.in_(comp_ids)))
            .values(selected=value)
        )
        existing = {cid for (cid,) in ses.execute(
            select(ClassCompetence.competence_id)
            .where((ClassCompetence.class_id == cl.id)
                   & (ClassCompetence.competence_id.in_(comp_ids)))
        )}
        ses.add_all(
            ClassCompetence(class_id=cl.id, competence_id=cid, selected=value)
            for cid in comp_ids if cid not in existing
        )
        ses.commit()

# -----------------------------------------------------------
def get_niveau(student_id: int, subject_id: int, ses: Session) -> str:
    return ses.scalar(
        select(StudentSubject.niveau).where(
            (StudentSubject.student_id == student_id)
            & (StudentSubject.subject_id == subject_id)
        )
    ) or ""

def set_niveau(student_id: int, subject_id: int, niveau: str, ses: Session):
    link = ses.scalars(
        select(StudentSubject).where(
            (StudentSubject.student_id == student_id)
            & (StudentSubject.subject_id == subject_id)
        )
    ).first()
    if link is None:
        ses.add(StudentSubject(student_id=student_id, subject_id=subject_id, niveau=niveau.strip()))
    else:
        link.niveau = niveau.strip()
    ses.commit()

# -------------------------------------------------------------------
def get_custom_competences(class_id: int, topic_id: int, ses: Session) -> List[CustomCompetence]:
    return list(ses.scalars(
        select(CustomCompetence)
        .where((CustomCompetence.class_id == class_id) & (CustomCompetence.topic_id == topic_id))
        .order_by(CustomCompetence.id)
    ))

def add_custom_competence(class_id: int, topic_id: int, text: str, ses: Session) -> CustomCompetence:
    comp = CustomCompetence(class_id=class_id, topic_id=topic_id, text=text.strip())
    ses.add(comp)
    ses.commit()
    return comp

def delete_custom_competence(comp_id: int, ses: Session):
    comp = ses.get(CustomCompetence, comp_id)
    if comp:
        ses.delete(comp)
        ses.commit()

# -------------------------------------------------------------------
def fetch_grade_matrix(students: List[Student], topics: List[Topic], subject_name: str, ses: Session) -> pd.DataFrame:
    subj_id = ses.scalar(select(Subject.id).where(Subject.name == subject_name))
    if subj_id is None:
        raise ValueError(f"Subject '{subject_name}' not found")

    grade_rows = (
        ses.query(Grade.student_id, Grade.topic_id, Grade.value)
           .filter(Grade.student_id.in_([s.id for s in students]),
                   Grade.topic_id.in_([t.id for t in topics]))
           .all()
    )
    gmap = {(sid, tid): val for sid, tid, val in grade_rows}

    rows = []
    for stu in students:
        row = {"Nachname": stu.last_name, "Vorname": stu.first_name,
               "Niveau": get_niveau(stu.id, subj_id, ses)}
        for tp in topics:
            row[str(tp.id)] = gmap.get((stu.id, tp.id), "")
        rows.append(row)
    return pd.DataFrame(rows)


def persist_grade_matrix(class_name: str, subject_name: str, df: "pd.DataFrame", ses: Session) -> None:
    cl = _get_or_create_class(ses, class_name)
    stu_map = {(s.last_name, s.first_name): s for s in cl.students}

    for _, row in df.iterrows():
        stu = stu_map.get((row["Nachname"], row["Vorname"]))
        if stu is None:
            continue

        niveau = row["Niveau"] or None
        link = (
            ses.query(StudentSubject).filter_by(student_id=stu.id)
               .join(Subject).filter(Subject.name == subject_name).first()
        )
        if link is None:
            subj = ses.query(Subject).filter_by(name=subject_name).one()
            ses.add(StudentSubject(student=stu, subject=subj, niveau=niveau))
        else:
            link.niveau = niveau

        for col_id, raw_val in row.items():
            if col_id in ("Nachname", "Vorname", "Niveau") or raw_val == "":
                continue
            topic_id = int(col_id)
            grade_row = ses.query(Grade).filter_by(student_id=stu.id, topic_id=topic_id).first()
            if grade_row:
                grade_row.value = _clean_grade(raw_val).strip()
            else:
                ses.add(Grade(student_id=stu.id, topic_id=topic_id, value=_clean_grade(raw_val).strip()))
        ses.commit()

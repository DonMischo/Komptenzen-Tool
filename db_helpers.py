# db_helpers.py
# -------------------------------------------------------------------
"""
Datenbank-Helper für das Kompetenzen-Tool (SQLAlchemy ≥ 2.0).

Funktionen
----------
get_subjects()                       -> List[str]
get_blocks(subject)                  -> List[str]
load_topic_rows(klasse, fach, block) -> [(comp_id, topic, text, selected)]
save_selections(klasse, changes)     -> Checkbox-Änderungen persistieren
toggle_topic(klasse, topic_id, val)  -> Alle an/aus für ein Topic
get_customs(topic_id, class_id)      -> eigene Kompetenzen (Liste)
add_custom(...) / delete_custom(...) -> eigene Kompetenzen ändern
"""

from __future__ import annotations
from typing import List, Tuple

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

import pandas as pd

from db_schema import (
    ENGINE,
    Subject,
    Topic,
    Competence,
    SchoolClass,
    ClassCompetence,
    CustomCompetence,
    Student,
    StudentSubject,
    Grade,
)

# -------------------------------------------------------------------
# intern: Session-Context-Manager
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
# kleine Helfer
# -------------------------------------------------------------------
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
    return ses.scalar(
        select(Subject.id).where(Subject.name == name.strip())
    )

def _get_topic_id(subject_id: int, topic_name: str, ses: Session) -> Optional[int]:
    stmt = (
        select(Topic.id)
        .where(
            (Topic.subject_id == subject_id)
            & (Topic.name == topic_name.strip())
        )
    )
    return ses.scalar(stmt)

# -------------------------------------------------------------------
# öffentliche API-Funktionen
# -------------------------------------------------------------------
def get_classes(ses: Session | None = None) -> list[str]:
    close = False
    if ses is None:
        ses, close = Session(ENGINE), True

    stmt = select(SchoolClass.name).order_by(SchoolClass.name)
    names = list(ses.scalars(stmt))  # scalars() -> list[str]

    if close:
        ses.close()
    return names

def get_students_by_class(class_name: str, ses: Session) -> list[Student]:
    cls = _get_or_create_class(ses, class_name)
    stmt = (
        select(Student)
        .where(Student.class_id == cls.id)
        .order_by(Student.last_name, Student.first_name)
    )
    return list(ses.scalars(stmt))

def get_topics_by_subject(subject_name: str, ses: Session) -> list[str]:
    """
    Liefert die Topics (z. B. „Geometrie“, „Leseverstehen“) eines Faches.
    Vollständig SQLAlchemy-2-Style: select … .scalars().all()
    """
    subj_id = _get_subject_id(subject_name, ses)
    if subj_id is None:
        return []

    stmt = (
        select(Topic.name)
        .where(Topic.subject_id == subj_id)
        # .order_by(Topic.name)
    )
    return list(ses.scalars(stmt))  # → List[str]

def get_subjects() -> List[str]:
    """Alphabetisch sortierte Fachliste."""
    with Session(ENGINE) as ses:
        stmt = select(Subject.name).order_by(Subject.name)
        return list(ses.scalars(stmt))


def get_blocks(subject: str) -> List[str]:
    """Verfügbare Doppeljahrgänge („5/6“ …) für ein Fach."""
    with Session(ENGINE) as ses:
        stmt = (
            select(Topic.block)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.name == subject)
            .distinct()
            .order_by(Topic.block)
        )
        return list(ses.scalars(stmt))


def load_topic_rows(
    class_name: str, subject: str, block: str
) -> List[Tuple[int, str, str, bool]]:
    """
    Liefert je Kompetenz:
        (competence_id, topic_name, competence_text, selected_bool)
    """
    with Session(ENGINE) as ses:
        school_class = _get_or_create_class(ses, class_name)

        stmt = (
            select(
                Competence.id,
                Topic.name,
                Competence.text,
                ClassCompetence.selected,
            )
            .join(Topic, Competence.topic_id == Topic.id)
            .join(Subject, Topic.subject_id == Subject.id)
            .outerjoin(
                ClassCompetence,
                (ClassCompetence.class_id == school_class.id)
                & (ClassCompetence.competence_id == Competence.id),
            )
            .where(Subject.name == subject, Topic.block == block)
            .order_by(Topic.name, Competence.text)
        )
        rows = ses.execute(stmt).all()

    # selected kann None sein → False
    return [
        (cid, topic, text, bool(sel)) for cid, topic, text, sel in rows
    ]


def save_selections(class_name: str, changes: List[Tuple[int, bool]]) -> None:
    """
    Persistiert Checkbox-Änderungen einer Klasse.
    changes = [(competence_id, new_selected_bool), …]
    """
    if not changes:
        return

    with Session(ENGINE) as ses:
        cl = _get_or_create_class(ses, class_name)

        for comp_id, is_sel in changes:
            stmt_sel = (
                select(ClassCompetence)
                .where(
                    (ClassCompetence.class_id == cl.id)
                    & (ClassCompetence.competence_id == comp_id)
                )
            )
            link = ses.scalars(stmt_sel).first()
            if link:
                link.selected = is_sel
            else:
                ses.add(
                    ClassCompetence(
                        class_id=cl.id,
                        competence_id=comp_id,
                        selected=is_sel,
                    )
                )
        ses.commit()


def toggle_topic(class_name: str, topic_id: int, value: bool) -> None:
    """Setzt alle Kompetenzen eines Topics für eine Klasse an/ab."""
    with Session(ENGINE) as ses:
        cl = _get_or_create_class(ses, class_name)

        # alle Competence-IDs zum Topic
        stmt_cids = select(Competence.id).where(
            Competence.topic_id == topic_id
        )
        comp_ids = [cid for (cid,) in ses.execute(stmt_cids)]

        # vorhandene Links updaten
        stmt_upd = (
            update(ClassCompetence)
            .where(
                (ClassCompetence.class_id == cl.id)
                & (ClassCompetence.competence_id.in_(comp_ids))
            )
            .values(selected=value)
        )
        ses.execute(stmt_upd)

        # fehlende Links anlegen
        stmt_exist = (
            select(ClassCompetence.competence_id)
            .where(
                (ClassCompetence.class_id == cl.id)
                & (ClassCompetence.competence_id.in_(comp_ids))
            )
        )
        existing = {cid for (cid,) in ses.execute(stmt_exist)}
        to_add = [cid for cid in comp_ids if cid not in existing]

        ses.add_all(
            ClassCompetence(
                class_id=cl.id,
                competence_id=cid,
                selected=value,
            )
            for cid in to_add
        )
        ses.commit()

# -----------------------------------------------------------
#  Niveau (Schüler × Fach)
# -----------------------------------------------------------
def get_niveau(student_id: int, subject_id: int, ses: Session) -> str:
    stmt = (
        select(StudentSubject.niveau)
        .where(
            (StudentSubject.student_id == student_id)
            & (StudentSubject.subject_id == subject_id)
        )
    )
    return ses.scalar(stmt) or ""


def set_niveau(student_id: int, subject_id: int, niveau: str, ses: Session):
    stmt = (
        select(StudentSubject)
        .where(
            (StudentSubject.student_id == student_id)
            & (StudentSubject.subject_id == subject_id)
        )
    )
    link = ses.scalars(stmt).first()
    if link is None:
        ses.add(
            StudentSubject(
                student_id=student_id,
                subject_id=subject_id,
                niveau=niveau.strip(),
            )
        )
    else:
        link.niveau = niveau.strip()
    ses.commit()

# -------------------------------------------------------------------
# Custom-Competences  (Klasse × Topic)
# -------------------------------------------------------------------
def get_custom_competences(
    class_id: int,
    topic_id: int,
    ses: Session,
) -> List[CustomCompetence]:
    stmt = (
        select(CustomCompetence)
        .where(
            (CustomCompetence.class_id == class_id)
            & (CustomCompetence.topic_id == topic_id)
        )
        .order_by(CustomCompetence.id)
    )
    return list(ses.scalars(stmt))


def add_custom_competence(
    class_id: int,
    topic_id: int,
    text: str,
    ses: Session,
) -> CustomCompetence:
    comp = CustomCompetence(
        class_id=class_id,
        topic_id=topic_id,
        text=text.strip(),
    )
    ses.add(comp)
    ses.commit()
    return comp


def delete_custom_competence(comp_id: int, ses: Session):
    comp = ses.get(CustomCompetence, comp_id)
    if comp:
        ses.delete(comp)
        ses.commit()

# -------------------------------------------------------------------
# Grade Matrix
# -------------------------------------------------------------------

def fetch_grade_matrix(
    students: List[Student],
    topics: List[str],
    subject_name: str,
    ses: Session,
) -> pd.DataFrame:
    subj_id = _get_subject_id(subject_name, ses)
    if subj_id is None:
        return pd.DataFrame()

    stmt = (
        select(Topic.id, Topic.name)
        .where((Topic.subject_id == subj_id) & (Topic.name.in_(topics)))
    )
    topic_map = {name: tid for tid, name in ses.execute(stmt)}

    rows = []
    for stu in students:
        row = {
            "Nachname": stu.last_name,
            "Vorname": stu.first_name,
            "Niveau": get_niveau(stu.id, subj_id, ses),
        }
        for tp in topics:
            tid = topic_map[tp]
            stmt_g = (
                select(Grade.value)
                .where((Grade.student_id == stu.id) & (Grade.topic_id == tid))
            )
            row[tp] = ses.scalar(stmt_g) or ""
        rows.append(row)

    return pd.DataFrame(rows)

def persist_grade_matrix(
    class_name: str,
    subject_name: str,
    df: pd.DataFrame,
    ses: Session,
):
    subj_id = _get_subject_id(subject_name, ses)
    if subj_id is None:
        return

    topics = [
        c for c in df.columns if c not in ("Nachname", "Vorname", "Niveau")
    ]

    # Name-Zuordnung
    students = {
        (s.last_name, s.first_name): s
        for s in get_students_by_class(class_name, ses)
    }

    # Topic-Name → ID
    stmt = (
        select(Topic.id, Topic.name)
        .where(
            (Topic.subject_id == subj_id)
            & (Topic.name.in_(topics))
        )
    )
    topic_ids = {name: tid for tid, name in ses.execute(stmt)}

    for _, row in df.iterrows():
        key = (row["Nachname"], row["Vorname"])
        stu = students.get(key)
        if stu is None:
            continue

        # Niveau
        set_niveau(stu.id, subj_id, str(row["Niveau"]).strip(), ses)

        # Noten
        for tp in topics:
            tid = topic_ids.get(tp)
            if tid is None:
                continue
            note = str(row[tp]).strip()
            stmt_g = (
                select(Grade)
                .where(
                    (Grade.student_id == stu.id)
                    & (Grade.topic_id == tid)
                )
            )
            grade = ses.scalars(stmt_g).first()
            if grade is None:
                if note:
                    ses.add(
                        Grade(
                            student_id=stu.id,
                            topic_id=tid,
                            value=note,
                        )
                    )
            else:
                grade.value = note

    ses.commit()

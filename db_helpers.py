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

from sqlalchemy import select, update, delete, distinct, func
from sqlalchemy.orm import Session

from helpers import unique_key as _uk     # damit wir die IDs wiederfinden


import pandas as pd
import numpy as np

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
def _clean_grade(val) -> str:
    if isinstance(val, float) and val.is_integer():
        return str(int(val))       # 1.0 → "1"
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

def get_topics_by_subject(
    subject: str,
    ses: Session,
    class_name: str | None = None,
) -> list[Topic]:                        # <-- return OBJECTS
    """
    Liefert Topic-Objekte eines Fachs.

    Wenn *class_name* angegeben ist, kommen nur Topics zurück, zu
    denen in dieser Klasse mindestens EINE Kompetenz ausgewählt wurde.
    """

    # base query: all topics of the subject
    stmt = (
        select(Topic)
        .join(Subject)
        .where(Subject.name == subject)
        .order_by(Topic.block, Topic.name)
    )

    # optional filter: at least one selected competence for the class
    if class_name:
        cl = _get_or_create_class(ses, class_name)
        stmt = (
            stmt.join(Competence)
                .join(
                    ClassCompetence,
                    (ClassCompetence.class_id == cl.id)
                    & (ClassCompetence.competence_id == Competence.id)
                    & (ClassCompetence.selected.is_(True))
                )
        ).distinct(Topic.id)

    return list(ses.scalars(stmt))

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
    topics:   List[Topic],     # real Topic objects ✔
    subject_name: str,
    ses: Session,
) -> pd.DataFrame:

    # --- NEW -------------------------------------------------------
    subj_id = ses.scalar(select(Subject.id)
                         .where(Subject.name == subject_name))
    if subj_id is None:
        raise ValueError(f"Subject '{subject_name}' not found")
    # ---------------------------------------------------------------

    rows = []
    grade_rows = (
        ses.query(Grade.student_id, Grade.topic_id, Grade.value)
           .filter(Grade.student_id.in_([s.id for s in students]),
                   Grade.topic_id.in_([t.id for t in topics]))
           .all()
    )
    gmap = {(sid, tid): val for sid, tid, val in grade_rows}

    for stu in students:
        row = {
            "Nachname": stu.last_name,
            "Vorname":  stu.first_name,
            "Niveau":   get_niveau(stu.id, subj_id, ses),   # ← uses id
        }
        for tp in topics:
            row[str(tp.id)] = gmap.get((stu.id, tp.id), "")
        rows.append(row)

    return pd.DataFrame(rows)


def persist_grade_matrix(
        class_name   : str,
        subject_name : str,
        df           : "pd.DataFrame",
        ses          : Session
) -> None:
    """
    Speichert Niveau + alle Topic-Noten aus dem data_editor-DataFrame.

    DataFrame-Aufbau:
        Nachname | Vorname | Niveau | <topic_id_1> | <topic_id_2> | …
    """
    import pandas as pd

    cl = _get_or_create_class(ses, class_name)

    # ------------------------ Hilfstabellen ------------------------
    # Topic-ID (DataFrame-Spalte)  →  echte Topic-Objekte
    topic_map: dict[str, Topic] = {
        _uk(subject_name, t.name): t          # same key formula as in UI
        for t in (
              ses.query(Topic)                # includes topics that are *not* in the table
                     .join(Subject)
                     .filter(Subject.name == subject_name)
                     .order_by(Topic.name)
           )
    }
    # Student-Name → Student-Objekt
    stu_map: dict[tuple[str, str], Student] = {
        (s.last_name, s.first_name): s for s in cl.students
    }

    # ------------------------- Iteration ---------------------------
    for _, row in df.iterrows():
        stu = stu_map.get((row["Nachname"], row["Vorname"]))
        if stu is None:
            continue

        # — Niveau (pro Schüler × Fach) —
        niveau = row["Niveau"] or None
        link = (
            ses.query(StudentSubject)
               .filter_by(student_id=stu.id)
               .join(Subject)
               .filter(Subject.name == subject_name)
               .first()
        )
        if link is None:
            subj = ses.query(Subject).filter_by(name=subject_name).one()
            link = StudentSubject(student=stu, subject=subj, niveau=niveau)
            ses.add(link)
        else:
            link.niveau = niveau

        # — Einzelnoten (pro Topic) —
        for col_id, raw_val in row.items():
            if col_id in ("Nachname", "Vorname", "Niveau") or raw_val == "":
                continue

            topic_id = int(col_id)                # ← single conversion

            grade_row = (
                ses.query(Grade)
                   .filter_by(student_id=stu.id, topic_id=topic_id)
                   .first()
            )
            if grade_row:
                grade_row.value = _clean_grade(raw_val).strip()
            else:
                ses.add(Grade(student_id=stu.id,
                              topic_id=topic_id,
                              value=_clean_grade(raw_val).strip()))
        ses.commit()

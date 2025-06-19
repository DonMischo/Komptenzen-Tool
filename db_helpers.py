# db_helpers.py
# ------------------------------------------------------------------
"""
Sämtliche DB-Zugriffe für die Streamlit-UI.
Nutzen die Modelle aus db_schema.py (SQLAlchemy ORM).

Funktionen
----------
get_subjects()                     →  Liste aller Fachnamen
get_blocks(subject)                →  Liste vorhandener Blöcke ("5/6", …)
load_topic_rows(class_name,        →  [(competence_id, topic, text, selected), …]
                 subject, block)
save_selections(class_name,        →  Änderungen persistieren (Upsert)
                 changes)
toggle_topic(class_name, topic_id, →  Alle an / aus für ein Thema
             value)
"""

from typing import List, Tuple
from sqlalchemy.orm import Session

from db_schema import (
    ENGINE,
    Subject,
    Topic,
    Competence,
    SchoolClass,
    ClassCompetence,
    CustomCompetence,
    SchoolClass
)

# ------------------------------------------------------------------
# Kleine Hilfsroutine
# ------------------------------------------------------------------
def _get_or_create_class(session: Session, name: str) -> SchoolClass:
    """Liefert Klassen-Objekt; legt es bei Bedarf an."""
    cl = session.query(SchoolClass).filter_by(name=name).first()
    if cl is None:
        cl = SchoolClass(name=name)
        session.add(cl)
        session.flush()  # erzeugt ID
    return cl

def _get_or_create_class_id(name: str, ses: Session) -> int:
    """
    Liefert die ID der Klasse 'name'.
    Existiert sie nicht, wird sie angelegt.
    """
    obj = (
        ses.query(SchoolClass)
           .filter_by(name=name.strip())
           .first()
    )
    if obj is None:
        obj = SchoolClass(name=name.strip())
        ses.add(obj)
        ses.commit()          # damit ID erzeugt wird
    return obj.id

# ------------------------------------------------------------------
# Öffentliche API-Funktionen
# ------------------------------------------------------------------
def get_subjects() -> List[str]:
    """Alphabetische Liste aller Fächer."""
    with Session(ENGINE) as ses:
        rows = ses.query(Subject.name).order_by(Subject.name).all()
        return [r[0] for r in rows]


def get_blocks(subject: str) -> List[str]:
    """Liefert die vorhandenen Kompetenz-Blöcke (z. B. '5/6') für ein Fach."""
    with Session(ENGINE) as ses:
        rows = (
            ses.query(Topic.block)
            .join(Subject)
            .filter(Subject.name == subject)
            .distinct()
            .order_by(Topic.block)
            .all()
        )
        return [r[0] for r in rows]


def load_topic_rows(
    class_name: str, subject: str, block: str
) -> List[Tuple[int, str, str, bool]]:
    """
    Gibt pro Kompetenz eine Zeile zurück:
        (competence_id, topic_name, competence_text, selected_bool)
    """
    with Session(ENGINE) as ses:
        school_class = _get_or_create_class(ses, class_name)

        rows = (
            ses.query(
                Competence.id,
                Topic.name,
                Competence.text,
                ClassCompetence.selected,
            )
            .join(Topic)
            .join(Subject)
            .outerjoin(
                ClassCompetence,
                (ClassCompetence.class_id == school_class.id)
                & (ClassCompetence.competence_id == Competence.id),
            )
            .filter(Subject.name == subject, Topic.block == block)
            .order_by(Topic.name, Competence.text)
            .all()
        )

    # selected kann None sein → False
    return [(cid, topic, text, bool(sel)) for cid, topic, text, sel in rows]


def save_selections(class_name: str, changes: List[Tuple[int, bool]]) -> None:
    """
    Persistiert Checkbox-Änderungen einer Klasse.
    changes = [(competence_id, new_selected_bool), …]
    """
    if not changes:
        return

    with Session(ENGINE) as ses:
        school_class = _get_or_create_class(ses, class_name)

        for comp_id, is_sel in changes:
            obj = (
                ses.query(ClassCompetence)
                .filter_by(class_id=school_class.id, competence_id=comp_id)
                .first()
            )
            if obj:
                obj.selected = is_sel
            else:
                ses.add(
                    ClassCompetence(
                        class_id=school_class.id,
                        competence_id=comp_id,
                        selected=is_sel,
                    )
                )
        ses.commit()


def toggle_topic(class_name: str, topic_id: int, value: bool) -> None:
    """
    Wählt ALLE Kompetenzen eines Topics für eine Klasse an/ab.
    """
    with Session(ENGINE) as ses:
        cl = _get_or_create_class(ses, class_name)

        # alle Competence-IDs zu diesem Topic
        comp_ids = (
            ses.query(Competence.id)
            .filter(Competence.topic_id == topic_id)
            .all()
        )
        comp_ids = [cid for (cid,) in comp_ids]

        # bestehende Zuordnungen aktualisieren oder neu anlegen
        for cid in comp_ids:
            obj = (
                ses.query(ClassCompetence)
                .filter_by(class_id=cl.id, competence_id=cid)
                .first()
            )
            if obj:
                obj.selected = value
            else:
                ses.add(
                    ClassCompetence(
                        class_id=cl.id, competence_id=cid, selected=value
                    )
                )
        ses.commit()

# For custom competences
def get_customs(topic_id: int, class_id: int, ses: Session):
    """Lade alle eigenen Kompetenzen für Topic *und* Klasse."""
    return (
        ses.query(CustomCompetence)
           .filter_by(topic_id=topic_id, class_id=class_id)
           .order_by(CustomCompetence.id)
           .all()
    )

def add_custom(topic_id: int, class_id: int, text: str, ses: Session) -> None:
    """Neue eigene Kompetenz anlegen (Topic + Klasse)."""
    txt = text.strip()
    if txt:
        ses.add(
            CustomCompetence(
                topic_id = topic_id,
                class_id = class_id,
                text     = txt,
            )
        )
        ses.commit()

def delete_custom(custom_id: int, ses: Session) -> None:
    ses.query(CustomCompetence).filter_by(id=custom_id).delete()
    ses.commit()
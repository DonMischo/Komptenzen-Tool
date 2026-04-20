# db_schema.py
# -----------------------------------------------
from __future__ import annotations
import os
import sys
from typing import Dict, List

from sqlalchemy import (create_engine, Column, Integer, String, Date, Boolean,
                        ForeignKey, UniqueConstraint, text)
from sqlalchemy.orm import declarative_base, relationship, Session
from competence_data import COMPETENCES

from datetime import datetime
from time_functions import (
    get_school_year,
    fetch_halfyear_report_day,
    fetch_last_school_day,
)

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _pg_base_url() -> str:
    """
    Base PostgreSQL URL without a database name.
    Set env var POSTGRES_URL, e.g.:
        postgresql://user:password@localhost:5432
    Defaults to postgresql://localhost for local trusted connections.
    """
    url = os.environ.get("POSTGRES_URL", "postgresql://localhost")
    return url.rstrip("/")


def _make_engine(db_name: str):
    url = f"{_pg_base_url()}/{db_name}"
    return create_engine(url, echo=False, future=True)


ENGINE = _make_engine("postgres")  # maintenance DB; overridden immediately by switch_engine / db_cli

Base = declarative_base()


def switch_engine(db_name: str) -> None:
    """Point ENGINE (and dependent modules) at a different PostgreSQL database."""
    global ENGINE

    if ENGINE.url.database == db_name:
        return

    ENGINE = _make_engine(db_name)

    # propagate to all modules that imported ENGINE at load time
    for m in ("student_loader", "db_helpers", "setup_ui",
              "ui_components", "admin_ui", "export", "kompetenz_ui",
              "studenten_ui", "student_base_data"):
        if m in sys.modules:
            sys.modules[m].ENGINE = ENGINE

    try:
        with ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅  ENGINE switched to {db_name}")
    except Exception as exc:
        print(f"❌  Could not connect to {db_name}: {exc}")
        raise


# ---------------------------------------------------------------------------
# PostgreSQL database management (list / create report databases)
# ---------------------------------------------------------------------------

def suggest_db_name(term: str) -> str:
    """Return a canonical DB name like 'reports_2025_26_hj'."""
    sy = get_school_year()           # "2025/2026"
    y1, y2 = sy.split("/")
    return f"reports_{y1}_{y2[2:]}_{term}"


def list_report_dbs() -> list[str]:
    """Return all PostgreSQL databases whose name starts with 'reports_'."""
    admin_url = f"{_pg_base_url()}/postgres"
    eng = create_engine(admin_url, future=True)
    try:
        with eng.connect() as conn:
            rows = conn.execute(text(
                "SELECT datname FROM pg_database "
                "WHERE datname LIKE 'reports_%' "
                "ORDER BY datname"
            ))
            return [r[0] for r in rows]
    finally:
        eng.dispose()


def create_report_db(db_name: str) -> None:
    """Create a new PostgreSQL database for a report period."""
    admin_url = f"{_pg_base_url()}/postgres"
    eng = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with eng.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        eng.dispose()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class SchoolYear(Base):
    __tablename__ = "school_years"

    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)   # e.g. "2024/2025"
    endjahr    = Column(Boolean, default=False, nullable=False)
    report_day = Column(Date, nullable=True)

    __table_args__ = (UniqueConstraint("name", "endjahr", name="uq_school_year"),)


class Subject(Base):
    __tablename__ = "subjects"
    id   = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    topics        = relationship("Topic", back_populates="subject",
                                 cascade="all, delete-orphan")
    student_links = relationship("StudentSubject", back_populates="subject",
                                 cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"
    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)
    block      = Column(String, nullable=False)   # "5/6", "7/8"
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    subject     = relationship("Subject", back_populates="topics")
    competences = relationship("Competence", back_populates="topic",
                               cascade="all, delete-orphan")
    grades      = relationship("Grade", back_populates="topic",
                               cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("subject_id", "name", "block"),)


class Competence(Base):
    __tablename__ = "competences"
    id       = Column(Integer, primary_key=True)
    text     = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    topic = relationship("Topic", back_populates="competences")

    __table_args__ = (UniqueConstraint("topic_id", "text"),)


class SchoolClass(Base):
    __tablename__ = "classes"
    id   = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)


class ClassCompetence(Base):
    __tablename__ = "class_competence"
    class_id      = Column(Integer, ForeignKey("classes.id"), primary_key=True)
    competence_id = Column(Integer, ForeignKey("competences.id"), primary_key=True)
    selected      = Column(Boolean, default=False, nullable=False)

    school_class = relationship("SchoolClass")
    competence   = relationship("Competence")


class CustomCompetence(Base):
    __tablename__ = "custom_competences"

    id       = Column(Integer, primary_key=True)
    text     = Column(String, nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)

    topic = relationship("Topic", backref="customs")

    __table_args__ = (UniqueConstraint("class_id", "topic_id", "text"),)


class Student(Base):
    __tablename__ = "students"

    id         = Column(Integer, primary_key=True)
    last_name  = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    birthday   = Column(Date,   nullable=False)
    class_id   = Column(Integer, ForeignKey("classes.id"), nullable=False)

    school_class = relationship("SchoolClass", backref="students")

    days_absent_excused      = Column(Integer, default=0)
    days_absent_unexcused    = Column(Integer, default=0)
    lessons_absent_excused   = Column(Integer, default=0)
    lessons_absent_unexcused = Column(Integer, default=0)

    report_text = Column(String, default="")
    remarks     = Column(String, default="")
    lb = Column(Boolean, default=False)
    gb = Column(Boolean, default=False)

    grades   = relationship("Grade", back_populates="student",
                            cascade="all, delete-orphan")
    subjects = relationship("StudentSubject", back_populates="student",
                            cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("last_name", "first_name", "birthday"),)

    def __repr__(self) -> str:
        return f"<Student {self.last_name}, {self.first_name} ({self.school_class.name})>"


class StudentSubject(Base):
    __tablename__ = "student_subject"

    id         = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    niveau     = Column(String, nullable=True)

    student = relationship("Student", back_populates="subjects")
    subject = relationship("Subject", back_populates="student_links")

    __table_args__ = (UniqueConstraint("student_id", "subject_id"),)


class Grade(Base):
    __tablename__ = "grades"
    id         = Column(Integer, primary_key=True)
    value      = Column(String(8), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_id   = Column(Integer, ForeignKey("topics.id"),   nullable=False)

    student = relationship("Student", back_populates="grades")
    topic   = relationship("Topic",   back_populates="grades")

    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_grade_student_topic"),
    )


# ---------------------------------------------------------------------------
# Default data helpers
# ---------------------------------------------------------------------------

DEFAULT_CLASSES = [
    "5a", "5b", "5c",
    "6a", "6b", "6c",
    "7a", "7b", "7c",
]


def ensure_default_classes() -> None:
    with Session(ENGINE) as ses:
        existing = {c.name for c in ses.query(SchoolClass)}
        for cname in DEFAULT_CLASSES:
            if cname not in existing:
                ses.add(SchoolClass(name=cname))
        ses.commit()


def ensure_school_year_entry() -> None:
    """
    Adds/updates a SchoolYear row matching the current database name.
    Reads hj/ej suffix from the PostgreSQL database name, e.g. 'reports_2025_26_hj'.
    """
    db_name = (ENGINE.url.database or "").lower()
    suffix  = db_name[-2:]   # "hj" | "ej"
    is_ej   = suffix == "ej"

    rep_str  = (
        fetch_last_school_day()
        if is_ej
        else fetch_halfyear_report_day()
    )
    rep_date = datetime.strptime(rep_str, "%d.%m.%Y").date()

    with Session(ENGINE) as ses:
        sy = (
            ses.query(SchoolYear)
               .filter_by(name=get_school_year(), endjahr=is_ej)
               .first()
        )
        if sy is None:
            ses.add(SchoolYear(
                name=get_school_year(),
                endjahr=is_ej,
                report_day=rep_date,
            ))
        else:
            sy.report_day = rep_date
        ses.commit()


def populate_from_dict(comp_dict: Dict, session: Session) -> None:
    """Insert subjects / topics / competences from COMPETENCES dict (idempotent)."""
    for subj, blocks in comp_dict.items():
        subj_obj = session.query(Subject).filter_by(name=subj).first()
        if not subj_obj:
            subj_obj = Subject(name=subj)
            session.add(subj_obj)

        for block, topics in blocks.items():
            for topic, comp_list in topics.items():
                topic_obj = (
                    session.query(Topic)
                    .filter_by(subject=subj_obj, name=topic, block=block)
                    .first()
                )
                if not topic_obj:
                    topic_obj = Topic(name=topic, block=block, subject=subj_obj)
                    session.add(topic_obj)

                existing = {c.text for c in topic_obj.competences}
                for comp in comp_list:
                    if comp not in existing:
                        topic_obj.competences.append(Competence(text=comp))

    session.commit()


def init_db(drop: bool = False, *, populate: bool = True) -> None:
    """
    Create (and optionally drop) the schema in the current ENGINE database.
    Safe to call repeatedly – create_all / drop_all are idempotent.
    """
    if drop:
        Base.metadata.drop_all(ENGINE)

    Base.metadata.create_all(ENGINE)
    ensure_default_classes()

    try:
        ensure_school_year_entry()
    except Exception as e:
        # Holiday fetching can fail (no internet, timeout) — not fatal.
        # The report day can be set manually in the Admin UI.
        print(f"⚠️  Schuljahr-Eintrag übersprungen: {e}")

    if populate:
        with Session(ENGINE) as ses:
            populate_from_dict(COMPETENCES, ses)

    print(f"✅  Schema{' + Daten' if populate else ''} OK für {ENGINE.url.database}")

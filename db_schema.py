# db_schema.py
# -----------------------------------------------
from pathlib import Path
from typing import Dict, List
from sqlalchemy import (create_engine, Column, Integer, String, Date, Boolean,
                        ForeignKey, UniqueConstraint, text)
from sqlalchemy.orm import declarative_base, relationship, Session
from competence_data import COMPETENCES      # dein großes Dict

DB_PATH = Path("kompetenzen.db")
ENGINE   = create_engine(f"sqlite:///{DB_PATH}", echo=False,
                         future=True)
Base = declarative_base()

def switch_engine(db_path: Path | str) -> None:
    global ENGINE
    
    # ---- new: bail out if unchanged -------------------------------
    if ENGINE.url.database == str(db_path):
        return 
    
    ENGINE = create_engine(f"sqlite:///{db_path}", echo=False, future=True)

    # propagate to modules that imported ENGINE early
    import sys
    for m in ("student_loader", "db_helpers"):
        if m in sys.modules:
            sys.modules[m].ENGINE = ENGINE

    # --- optional: quick sanity check & feedback --------------------
    try:
        with ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✅  ENGINE switched to {db_path}")
    except Exception as exc:
        print(f"❌  Could not connect to {db_path}: {exc}")
        raise

# ---------- Tabellen ---------------------------
class Subject(Base):
    __tablename__ = "subjects"
    id   = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    topics = relationship("Topic", back_populates="subject",
                          cascade="all, delete-orphan")
    student_links = relationship("StudentSubject", back_populates="subject", cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)
    block      = Column(String, nullable=False)          # "5/6", "7/8"
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    subject      = relationship("Subject", back_populates="topics")
    competences  = relationship("Competence", back_populates="topic",
                                cascade="all, delete-orphan")
    grades       = relationship("Grade", back_populates="topic", cascade="all, delete-orphan")
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
    class_id       = Column(Integer, ForeignKey("classes.id"), primary_key=True)
    competence_id  = Column(Integer, ForeignKey("competences.id"), primary_key=True)
    selected       = Column(Boolean, default=False, nullable=False)

    school_class  = relationship("SchoolClass")
    competence    = relationship("Competence")

# ---------- einmalige Befüllung ----------------
def populate_from_dict(comp_dict: Dict, session: Session) -> None:
    """
    Liest COMPETENCES = {Fach:{Block:{Thema:[...], ...}, ...}, ...}
    und trägt nur neue Datensätze ein.
    """
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
                    topic_obj = Topic(name=topic, block=block,
                                      subject=subj_obj)
                    session.add(topic_obj)

                # Kompetenzen
                existing = {
                    c.text for c in topic_obj.competences
                }
                for comp in comp_list:
                    if comp not in existing:
                        topic_obj.competences.append(Competence(text=comp))

    session.commit()
    
class CustomCompetence(Base):
    __tablename__ = "custom_competences"

    id        = Column(Integer, primary_key=True)
    text      = Column(String, nullable=False)

    topic_id  = Column(Integer, ForeignKey("topics.id"), nullable=False)
    topic     = relationship("Topic", backref="customs")
    class_id = Column(Integer, ForeignKey("classes.id")) # optional: nur für eine Klasse speichern

# Student data

class Grade(Base):
    __tablename__ = "grades"
    id         = Column(Integer, primary_key=True)
    value      = Column(String(8), nullable=True)          # z. B. „1“, „2-“, „✔︎“
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_id   = Column(Integer, ForeignKey("topics.id"),   nullable=False)

    # Beziehungen (optional, nur für bequemes ORM-Navigieren)
    student = relationship("Student", back_populates="grades")
    topic   = relationship("Topic",   back_populates="grades")

    __table_args__ = (
        # pro Schüler & Topic nur eine Note (ansonsten Update in persist_grade_matrix)
        UniqueConstraint("student_id", "topic_id", name="uq_grade_student_topic"),
    )

class Student(Base):
    __tablename__ = "students"

    id        = Column(Integer, primary_key=True)           # auto
    last_name = Column(String, nullable=False)
    first_name= Column(String, nullable=False)
    birthday  = Column(Date,   nullable=False)

    class_id  = Column(Integer, ForeignKey("classes.id"), nullable=False)
    school_class = relationship("SchoolClass", backref="students")

    # zusätzliche Zeugnisfelder
    days_absent_excused      = Column(Integer, default=0)
    days_absent_unexcused    = Column(Integer, default=0)
    lessons_absent_excused   = Column(Integer, default=0)
    lessons_absent_unexcused = Column(Integer, default=0)

    report_text = Column(String, default="")
    remarks     = Column(String, default="")
    lb = Column(Boolean, default=False)
    gb = Column(Boolean, default=False)


    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    subjects = relationship(
        "StudentSubject",
        back_populates="student",
        cascade="all, delete-orphan",
    )
    def __repr__(self) -> str:      # nur für Debug-Ausgaben
        return f"<Student {self.last_name}, {self.first_name} ({self.school_class.name})>"

class StudentSubject(Base):
    __tablename__ = "student_subject"

    id         = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    niveau     = Column(String, nullable=True)

    # --- Beziehungen korrigiert --------------------------
    student = relationship("Student", back_populates="subjects")
    subject = relationship("Subject", back_populates="student_links")
    # ------------------------------------------------------

    __table_args__ = (UniqueConstraint("student_id", "subject_id"),)

# set default classes
DEFAULT_CLASSES = [
    "5a", "5b", "5c",
    "6a", "6b", "6c",
    "7a", "7b", "7c",
]

def ensure_default_classes() -> None:
    """legt 5a … 7c an, falls noch nicht vorhanden"""
    with Session(ENGINE) as ses:
        existing = {c.name for c in ses.query(SchoolClass.name)}
        for cname in DEFAULT_CLASSES:
            if cname not in existing:
                ses.add(SchoolClass(name=cname))
        ses.commit()

# ---------- Hilfsfunktionen --------------------
def init_db(drop: bool = False, *, populate: bool = True) -> None:
    """
    Erzeugt (und optional löscht) das DB-Schema.
    Wenn *populate* True ist, werden die Fach-, Topic- und Kompetenz-
    Datensätze aus COMPETENCES sofort eingespielt.
    """
    if drop and DB_PATH.exists():
        DB_PATH.unlink()

    Base.metadata.create_all(ENGINE)
    ensure_default_classes()

    if populate:                              # NEW -------------------
        with Session(ENGINE) as ses:
            populate_from_dict(COMPETENCES, ses)

    print(f"✅  Schema{' + Daten' if populate else ''} OK für {ENGINE.url.database}")

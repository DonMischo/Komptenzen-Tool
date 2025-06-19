# db_schema.py
# -----------------------------------------------
from pathlib import Path
from typing import Dict, List
from sqlalchemy import (create_engine, Column, Integer, String, Date, Boolean,
                        ForeignKey, UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship, Session
from competence_data import COMPETENCES      # dein großes Dict

DB_PATH = Path("kompetenzen.db")
ENGINE   = create_engine(f"sqlite:///{DB_PATH}", echo=False,
                         future=True)
Base = declarative_base()

# ---------- Tabellen ---------------------------
class Subject(Base):
    __tablename__ = "subjects"
    id   = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

    topics = relationship("Topic", back_populates="subject",
                          cascade="all, delete-orphan")

class Topic(Base):
    __tablename__ = "topics"
    id         = Column(Integer, primary_key=True)
    name       = Column(String, nullable=False)
    block      = Column(String, nullable=False)          # "5/6", "7/8"
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    subject      = relationship("Subject", back_populates="topics")
    competences  = relationship("Competence", back_populates="topic",
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
    class_id       = Column(Integer, ForeignKey("classes.id"), primary_key=True)
    competence_id  = Column(Integer, ForeignKey("competences.id"), primary_key=True)
    selected       = Column(Boolean, default=False, nullable=False)

    # Beziehungen (optional)
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

    def __repr__(self) -> str:      # nur für Debug-Ausgaben
        return f"<Student {self.last_name}, {self.first_name} ({self.school_class.name})>"

# ---------- Hilfsfunktionen --------------------
def init_db(drop: bool = False):
    if drop and DB_PATH.exists():
        DB_PATH.unlink()
    Base.metadata.create_all(ENGINE)

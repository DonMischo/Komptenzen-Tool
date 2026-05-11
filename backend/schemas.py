# schemas.py — Pydantic request/response models for the FastAPI backend.
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class AuthSetupRequest(BaseModel):
    username: str
    password: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    username: Optional[str]
    needs_setup: bool
    role: Optional[str] = None


# ---------------------------------------------------------------------------
# Databases / Setup
# ---------------------------------------------------------------------------

class DatabaseListResponse(BaseModel):
    databases: list[str]
    current: Optional[str]


class DatabaseCreateRequest(BaseModel):
    name: str


class DatabaseSelectRequest(BaseModel):
    name: str


class DatabaseSuggestResponse(BaseModel):
    suggested: str


class SchemaStatusResponse(BaseModel):
    db_name: str
    schema_ready: bool
    student_count: int


class ReportDayResponse(BaseModel):
    report_day: Optional[str]   # "DD.MM.YYYY" or null
    school_year: str
    is_endjahr: bool


class ReportDayUpdateRequest(BaseModel):
    report_day: str             # "DD.MM.YYYY"


class StudentImportResponse(BaseModel):
    added: int
    updated: int
    removed: int
    errors: list[str]


# ---------------------------------------------------------------------------
# Classes / Subjects
# ---------------------------------------------------------------------------

class ClassListResponse(BaseModel):
    classes: list[str]


class SubjectListResponse(BaseModel):
    subjects: list[str]


class BlockListResponse(BaseModel):
    blocks: list[str]


# ---------------------------------------------------------------------------
# Competences
# ---------------------------------------------------------------------------

class CustomCompetenceItem(BaseModel):
    id: int
    text: str


class CompetenceRow(BaseModel):
    competence_id: int
    topic_name: str
    text: str
    selected: bool


class TopicGroup(BaseModel):
    topic_name: str
    topic_id: int
    competences: list[CompetenceRow]
    custom_competences: list[CustomCompetenceItem]


class CompetenceListResponse(BaseModel):
    class_name: str
    subject: str
    block: str
    topics: list[TopicGroup]


class CompetenceSaveRequest(BaseModel):
    class_name: str
    changes: list[tuple[int, bool]]


class ToggleTopicRequest(BaseModel):
    class_name: str
    topic_id: int
    value: bool


class CustomCompetenceCreate(BaseModel):
    class_name: str
    topic_id: int
    text: str


# ---------------------------------------------------------------------------
# Grade Matrix (Schülerdaten)
# ---------------------------------------------------------------------------

class GradeMatrixColumn(BaseModel):
    topic_id: int
    label: str


class GradeMatrixRow(BaseModel):
    student_id: int
    last_name: str
    first_name: str
    niveau: str
    grades: dict[str, str]      # str(topic_id) → grade value


class GradeMatrixResponse(BaseModel):
    columns: list[GradeMatrixColumn]
    rows: list[GradeMatrixRow]


class GradeMatrixSaveRequest(BaseModel):
    class_name: str
    subject: str
    rows: list[GradeMatrixRow]


# ---------------------------------------------------------------------------
# Stammdaten (Student Base Data)
# ---------------------------------------------------------------------------

class StudentBaseData(BaseModel):
    id: int
    last_name: str
    first_name: str
    birthday: Optional[str]     # "DD.MM.YYYY"
    days_absent_excused: int
    days_absent_unexcused: int
    lessons_absent_excused: int
    lessons_absent_unexcused: int
    remarks: str
    lb: bool
    gb: bool
    report_text: str


class StudentBaseDataUpdate(BaseModel):
    birthday: Optional[str] = None
    days_absent_excused: Optional[int] = None
    days_absent_unexcused: Optional[int] = None
    lessons_absent_excused: Optional[int] = None
    lessons_absent_unexcused: Optional[int] = None
    remarks: Optional[str] = None
    lb: Optional[bool] = None
    gb: Optional[bool] = None


class ReportTextUpdate(BaseModel):
    report_text: str


# ---------------------------------------------------------------------------
# Admin / Export
# ---------------------------------------------------------------------------

class AdminStudentItem(BaseModel):
    id: int
    last_name: str
    first_name: str
    class_name: str


class ExportPrepareRequest(BaseModel):
    student_ids: list[int]
    classroom: str


class ExportPrepareResponse(BaseModel):
    job_id: str
    cl_dir: str
    total: int

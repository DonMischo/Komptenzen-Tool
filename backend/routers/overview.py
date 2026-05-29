# routers/overview.py — admin overview: competence status, grade status, custom competences
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from db_schema import (
    SchoolClass, Subject, Topic, Competence, ClassCompetence,
    CustomCompetence, Student, StudentSubject, Grade,
)
from deps import get_db, get_current_admin
from schemas import (
    CompetenceStatusItem, CompetenceStatusResponse,
    SubjectGradeStatus, StudentGradeStatus, GradeStatusResponse,
    CustomCompetenceGroup, CustomCompetenceItem, CustomCompetenceUpdateRequest,
)

router = APIRouter(dependencies=[Depends(get_current_admin)])

# ---------------------------------------------------------------------------
# Subject constants
# ---------------------------------------------------------------------------

_RELEVANT: dict[str, list[str]] = {
    "5": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Geschichte", "Geografie",
        "Werkstätten", "Technisches Werken", "Sport",
    ],
    "6": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Geschichte", "Geografie",
        "Werkstätten", "Technisches Werken", "Sport",
    ],
    "7": [
        "Deutsch", "Mathematik", "Englisch", "Evangelische Religionslehre",
        "MNT - Projekt Lutherpark", "Physik", "Chemie",
        "Geschichte", "Geografie", "Werkstätten", "Technisches Werken", "Sport",
    ],
}

_WAHLPFLICHT = [
    "Wahlpflichtbereich - Französisch",
    "Wahlpflichtbereich - Spanisch",
    "Wahlpflichtbereich - Darstellen und Gestalten",
    "Wahlpflichtbereich - Natur und Technik",
]

_WP_NO_NIVEAU = ["Wahlpflichtbereich - Darstellen und Gestalten"]

# Regular subjects that only need a grade, not a niveau
_NO_NIVEAU_REGULAR = {"Sport", "Werkstätten"}


def _grade_level(class_name: str) -> str:
    for ch in class_name:
        if ch.isdigit():
            return ch
    return ""


def _relevant_subjects(class_name: str) -> tuple[list[str], list[str]]:
    level = _grade_level(class_name)
    relevant = _RELEVANT.get(level, _RELEVANT.get("5", []))
    wahlpflicht = _WAHLPFLICHT if level == "7" else []
    return relevant, wahlpflicht


# ---------------------------------------------------------------------------
# Tab 1: Competence status
# ---------------------------------------------------------------------------

@router.get("/competences", response_model=CompetenceStatusResponse)
def get_competence_status(class_name: str, db: Session = Depends(get_db)):
    class_row = db.scalar(select(SchoolClass).where(SchoolClass.name == class_name))
    relevant, _ = _relevant_subjects(class_name)

    items: list[CompetenceStatusItem] = []
    for subj_name in relevant:
        sid = db.scalar(select(Subject.id).where(Subject.name == subj_name))
        count = 0
        if sid and class_row:
            count = db.execute(
                select(func.count(ClassCompetence.competence_id))
                .join(Competence, ClassCompetence.competence_id == Competence.id)
                .join(Topic, Competence.topic_id == Topic.id)
                .where(
                    ClassCompetence.class_id == class_row.id,
                    ClassCompetence.selected.is_(True),
                    Topic.subject_id == sid,
                )
            ).scalar() or 0
        items.append(CompetenceStatusItem(name=subj_name, selected_count=count))

    return CompetenceStatusResponse(subjects=items)


# ---------------------------------------------------------------------------
# Tab 2: Grade / niveau status
# ---------------------------------------------------------------------------

@router.get("/grades", response_model=GradeStatusResponse)
def get_grade_status(class_name: str, db: Session = Depends(get_db)):
    class_row = db.scalar(select(SchoolClass).where(SchoolClass.name == class_name))
    if not class_row:
        return GradeStatusResponse(
            students=[], relevant_subjects=[], wahlpflicht_subjects=[],
            wp_no_niveau=_WP_NO_NIVEAU, no_niveau_subjects=list(_NO_NIVEAU_REGULAR),
        )

    relevant, wahlpflicht = _relevant_subjects(class_name)
    all_subject_names = relevant + wahlpflicht

    # Build subject name → id map (skip subjects not in DB)
    subj_id_map: dict[str, int] = {}
    for name in all_subject_names:
        sid = db.scalar(select(Subject.id).where(Subject.name == name))
        if sid is not None:
            subj_id_map[name] = sid

    students = list(db.scalars(
        select(Student)
        .where(Student.class_id == class_row.id)
        .order_by(Student.last_name, Student.first_name)
    ))
    if not students:
        return GradeStatusResponse(
            students=[], relevant_subjects=relevant,
            wahlpflicht_subjects=wahlpflicht, wp_no_niveau=_WP_NO_NIVEAU,
            no_niveau_subjects=list(_NO_NIVEAU_REGULAR),
        )

    all_student_ids = [s.id for s in students]
    all_subject_ids = list(subj_id_map.values())

    # Batch: niveau per (student_id, subject_id)
    niveau_map: dict[tuple[int, int], str] = {}
    for ss in db.scalars(
        select(StudentSubject).where(
            StudentSubject.student_id.in_(all_student_ids),
            StudentSubject.subject_id.in_(all_subject_ids),
        )
    ):
        niveau_map[(ss.student_id, ss.subject_id)] = ss.niveau or ""

    # Batch: which (student_id, subject_id) have non-empty grades
    grade_has: set[tuple[int, int]] = set()
    for row in db.execute(
        select(Grade.student_id, Topic.subject_id)
        .join(Topic, Grade.topic_id == Topic.id)
        .where(
            Grade.student_id.in_(all_student_ids),
            Topic.subject_id.in_(all_subject_ids),
            Grade.value.isnot(None),
            Grade.value != "",
            Grade.value != " ",
        )
        .distinct()
    ):
        grade_has.add((row.student_id, row.subject_id))

    result: list[StudentGradeStatus] = []
    for stu in students:
        subj_status: dict[str, SubjectGradeStatus] = {}
        for name in relevant:
            sid = subj_id_map.get(name)
            if sid is None:
                subj_status[name] = SubjectGradeStatus(has_niveau=False, has_grade=False)
                continue
            niveau = niveau_map.get((stu.id, sid), "")
            subj_status[name] = SubjectGradeStatus(
                has_niveau=bool(niveau.strip()),
                has_grade=(stu.id, sid) in grade_has,
            )

        wp_status: dict[str, SubjectGradeStatus] = {}
        for name in wahlpflicht:
            sid = subj_id_map.get(name)
            if sid is None:
                wp_status[name] = SubjectGradeStatus(has_niveau=False, has_grade=False)
                continue
            niveau = niveau_map.get((stu.id, sid), "")
            wp_status[name] = SubjectGradeStatus(
                has_niveau=bool(niveau.strip()),
                has_grade=(stu.id, sid) in grade_has,
            )

        result.append(StudentGradeStatus(
            student_id=stu.id,
            last_name=stu.last_name,
            first_name=stu.first_name,
            lb=bool(stu.lb),
            gb=bool(stu.gb),
            subjects=subj_status,
            wahlpflicht=wp_status,
        ))

    return GradeStatusResponse(
        students=result,
        relevant_subjects=relevant,
        wahlpflicht_subjects=wahlpflicht,
        wp_no_niveau=_WP_NO_NIVEAU,
        no_niveau_subjects=list(_NO_NIVEAU_REGULAR),
    )


# ---------------------------------------------------------------------------
# Tab 3: Custom competences (list + edit + delete)
# ---------------------------------------------------------------------------

@router.get("/custom-competences", response_model=list[CustomCompetenceGroup])
def get_custom_competences(class_name: str, db: Session = Depends(get_db)):
    class_row = db.scalar(select(SchoolClass).where(SchoolClass.name == class_name))
    if not class_row:
        return []

    relevant, _ = _relevant_subjects(class_name)

    groups: list[CustomCompetenceGroup] = []
    for subj_name in relevant:
        subj = db.scalar(select(Subject).where(Subject.name == subj_name))
        if not subj:
            continue
        for topic in db.scalars(
            select(Topic).where(Topic.subject_id == subj.id).order_by(Topic.block, Topic.name)
        ):
            customs = list(db.scalars(
                select(CustomCompetence)
                .where(
                    CustomCompetence.class_id == class_row.id,
                    CustomCompetence.topic_id == topic.id,
                )
                .order_by(CustomCompetence.id)
            ))
            if customs:
                groups.append(CustomCompetenceGroup(
                    subject=subj_name,
                    topic_id=topic.id,
                    topic_name=topic.name,
                    customs=[CustomCompetenceItem(id=cc.id, text=cc.text) for cc in customs],
                ))

    return groups


@router.put("/custom-competences/{comp_id}", response_model=CustomCompetenceItem)
def update_custom_competence(
    comp_id: int,
    body: CustomCompetenceUpdateRequest,
    db: Session = Depends(get_db),
):
    cc = db.get(CustomCompetence, comp_id)
    if not cc:
        raise HTTPException(404, "Eigene Kompetenz nicht gefunden")
    cc.text = body.text.strip()
    db.commit()
    return CustomCompetenceItem(id=cc.id, text=cc.text)

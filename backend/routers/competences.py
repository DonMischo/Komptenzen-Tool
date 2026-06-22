# routers/competences.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from db_helpers import (
    get_classes, get_subjects, get_blocks, load_topic_rows,
    save_selections, toggle_topic,
    add_custom_competence, delete_custom_competence, get_custom_competences,
    _get_or_create_class_id, sync_competences_to_parallel,
)
from db_schema import Topic, Subject
from deps import get_db, get_current_user
from schemas import (
    ClassListResponse, SubjectListResponse, BlockListResponse,
    CompetenceListResponse, CompetenceSaveRequest, CompetenceRow,
    CustomCompetenceCreate, CustomCompetenceItem, ToggleTopicRequest, TopicGroup,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/classes", response_model=ClassListResponse)
def list_classes(db: Session = Depends(get_db)):
    return ClassListResponse(classes=get_classes(db))


@router.get("/subjects", response_model=SubjectListResponse)
def list_subjects():
    return SubjectListResponse(subjects=get_subjects())


@router.get("/subjects/{name}/blocks", response_model=BlockListResponse)
def list_blocks(name: str):
    return BlockListResponse(blocks=get_blocks(name))


@router.get("/competences", response_model=CompetenceListResponse)
def list_competences(
    class_name: str,
    subject: str,
    block: str,
    db: Session = Depends(get_db),
):
    rows = load_topic_rows(class_name, subject, block)

    # Group by topic, preserving order
    topic_map: dict[str, dict] = {}
    for comp_id, topic_name, text, selected in rows:
        if topic_name not in topic_map:
            # Fetch topic_id from DB
            topic_id = db.scalar(
                select(Topic.id)
                .join(Subject, Topic.subject_id == Subject.id)
                .where(Subject.name == subject, Topic.name == topic_name, Topic.block == block)
            )
            topic_map[topic_name] = {"topic_id": topic_id, "competences": [], "custom_competences": []}
        topic_map[topic_name]["competences"].append(
            CompetenceRow(competence_id=comp_id, topic_name=topic_name, text=text, selected=selected)
        )

    class_id = _get_or_create_class_id(class_name, db)

    topics: list[TopicGroup] = []
    for topic_name, data in topic_map.items():
        topic_id = data["topic_id"]
        customs = []
        if topic_id:
            customs = [
                CustomCompetenceItem(id=cc.id, text=cc.text)
                for cc in get_custom_competences(class_id, topic_id, db)
            ]
        topics.append(TopicGroup(
            topic_name=topic_name,
            topic_id=topic_id or 0,
            competences=data["competences"],
            custom_competences=customs,
        ))

    return CompetenceListResponse(class_name=class_name, subject=subject, block=block, topics=topics)


@router.post("/competences/save")
def save_competences(req: CompetenceSaveRequest):
    save_selections(req.class_name, req.changes)
    return {"ok": True}


@router.post("/competences/toggle-topic")
def toggle_topic_endpoint(req: ToggleTopicRequest):
    toggle_topic(req.class_name, req.topic_id, req.value)
    return {"ok": True}


@router.post("/competences/custom", response_model=CustomCompetenceItem)
def add_custom(req: CustomCompetenceCreate, db: Session = Depends(get_db)):
    class_id = _get_or_create_class_id(req.class_name, db)
    cc = add_custom_competence(class_id, req.topic_id, req.text, db)
    return CustomCompetenceItem(id=cc.id, text=cc.text)


@router.delete("/competences/custom/{comp_id}")
def delete_custom(comp_id: int, db: Session = Depends(get_db)):
    delete_custom_competence(comp_id, db)
    return {"ok": True}


@router.get("/competences/preview")
def preview_table(
    class_name: str,
    subject: str,
    db: Session = Depends(get_db),
):
    """Return all selected competences for class+subject across all blocks, merged by topic name."""
    blocks = get_blocks(subject)
    class_id = _get_or_create_class_id(class_name, db)

    # Collect (topic_name, block, comp_id, text) for selected competences only
    topic_rows: dict[str, dict] = {}  # topic_name → {block, topic_id, competences}

    for block in blocks:
        rows = load_topic_rows(class_name, subject, block)
        for comp_id, topic_name, text, selected in rows:
            if not selected:
                continue
            if topic_name not in topic_rows:
                topic_id = db.scalar(
                    select(Topic.id)
                    .join(Subject, Topic.subject_id == Subject.id)
                    .where(Subject.name == subject, Topic.name == topic_name, Topic.block == block)
                )
                topic_rows[topic_name] = {
                    "topic_id": topic_id,
                    "block": block,
                    "competences": [],
                }
            if text not in topic_rows[topic_name]["competences"]:
                topic_rows[topic_name]["competences"].append(text)

    # Attach custom competences
    result = []
    for topic_name, data in topic_rows.items():
        topic_id = data["topic_id"]
        customs: list[str] = []
        if topic_id:
            customs = [cc.text for cc in get_custom_competences(class_id, topic_id, db)]
        result.append({
            "title": topic_name,
            "block": data["block"],
            "topic_id": topic_id,
            "competences": data["competences"],
            "custom_competences": customs,
        })

    return {"subject": subject, "topics": result}


@router.post("/competences/sync-to-parallel")
def sync_parallel(class_name: str, body: dict | None = None, _user=Depends(get_current_user)):
    """Copy competence selections from class_name to parallel classes.
    Optional JSON body: {"target_classes": ["7b", "7c"]} — if omitted, syncs to all parallel."""
    targets = (body or {}).get("target_classes") or None
    synced = sync_competences_to_parallel(class_name, targets)
    return {"synced_to": synced}

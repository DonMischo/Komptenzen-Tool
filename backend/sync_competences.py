"""sync_competences.py
======================
Compare the canonical competence_data.py against the current DB and apply
additions / deletions.

Two modes
---------
apply_additions_only(db)
    Safe: creates any Subject / Topic / Competence that exists in
    competence_data.py but is missing from the DB.  Never deletes anything.
    Called at startup for every report DB.

compute_diff(db) → CompetenceSyncResult
    Dry-run: returns what would be added and removed, including counts of
    ClassCompetence (teacher selections) and Grade rows that will be lost.

apply_full_sync(db) → CompetenceSyncResult
    Executes the diff: adds missing rows and deletes rows that no longer
    exist in competence_data.py.  Call this only after showing the diff
    to the user and receiving explicit confirmation.

Deletion cascade notes
----------------------
• Deleting a Competence: must manually delete ClassCompetence rows first
  (no SQLAlchemy cascade from Competence → ClassCompetence).
• Deleting a Topic: must manually delete ClassCompetence (for its
  Competence children) and CustomCompetence rows first; SQLAlchemy then
  cascades Topic → Competence and Topic → Grade.
• Deleting a Subject: same pre-cleanup, then Subject → Topic → ... cascades.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from db_schema import (
    ENGINE, Subject, Topic, Competence,
    ClassCompetence, CustomCompetence, Grade,
)
from competence_data import COMPETENCES, SUBJECTS


# ---------------------------------------------------------------------------
# Result dataclass (returned by both compute_diff and apply_full_sync)
# ---------------------------------------------------------------------------

@dataclass
class CompetenceSyncResult:
    subjects_added:      list[str] = field(default_factory=list)
    subjects_removed:    list[str] = field(default_factory=list)
    topics_added:        list[str] = field(default_factory=list)   # "Subject / Topic"
    topics_removed:      list[str] = field(default_factory=list)
    competences_added:   int = 0
    competences_removed: int = 0
    class_selections_lost: int = 0   # ClassCompetence rows deleted / to be deleted
    grades_lost:           int = 0   # Grade rows deleted / to be deleted

    @property
    def has_removals(self) -> bool:
        return bool(
            self.subjects_removed or self.topics_removed
            or self.competences_removed
        )

    @property
    def has_changes(self) -> bool:
        return bool(
            self.subjects_added or self.subjects_removed
            or self.topics_added or self.topics_removed
            or self.competences_added or self.competences_removed
        )


# ---------------------------------------------------------------------------
# Helpers: build "expected" sets from competence_data.py
# ---------------------------------------------------------------------------

def _expected_subjects() -> set[str]:
    return set(SUBJECTS)


def _expected_topics() -> dict[str, set[tuple[str, str]]]:
    """Returns {subject_name: {(block, topic_name), …}}"""
    result: dict[str, set[tuple[str, str]]] = {}
    for subj, blocks in COMPETENCES.items():
        result.setdefault(subj, set())
        for block, topics in blocks.items():
            for topic_name in topics:
                result[subj].add((block, topic_name))
    return result


def _expected_competences() -> dict[tuple[str, str, str], list[str]]:
    """Returns {(subject, block, topic): [comp_text, …]}"""
    result: dict[tuple[str, str, str], list[str]] = {}
    for subj, blocks in COMPETENCES.items():
        for block, topics in blocks.items():
            for topic_name, comp_list in topics.items():
                result[(subj, block, topic_name)] = list(comp_list)
    return result


# ---------------------------------------------------------------------------
# Additions-only (safe, called at startup)
# ---------------------------------------------------------------------------

def apply_additions_only(db: Session) -> None:
    """Idempotent: add any missing subjects / topics / competences.
    Never deletes or updates anything."""
    # 1. Ensure every subject in SUBJECTS has a row
    for name in SUBJECTS:
        if not db.query(Subject).filter_by(name=name).first():
            db.add(Subject(name=name))
    db.flush()

    # 2. Walk COMPETENCES and fill gaps
    for subj_name, blocks in COMPETENCES.items():
        subj = db.query(Subject).filter_by(name=subj_name).first()
        if not subj:
            subj = Subject(name=subj_name)
            db.add(subj)
            db.flush()

        for block, topics in blocks.items():
            for topic_name, comp_list in topics.items():
                topic = (db.query(Topic)
                           .filter_by(subject_id=subj.id, name=topic_name, block=block)
                           .first())
                if not topic:
                    topic = Topic(name=topic_name, block=block, subject=subj)
                    db.add(topic)
                    db.flush()

                existing_texts = {
                    c.text for c in db.query(Competence).filter_by(topic_id=topic.id).all()
                }
                for comp_text in comp_list:
                    if comp_text not in existing_texts:
                        db.add(Competence(text=comp_text, topic=topic))

    db.commit()


# ---------------------------------------------------------------------------
# Diff computation (dry run)
# ---------------------------------------------------------------------------

def compute_diff(db: Session) -> CompetenceSyncResult:
    result = CompetenceSyncResult()
    exp_subjects  = _expected_subjects()
    exp_topics    = _expected_topics()
    exp_comps     = _expected_competences()

    # --- Subjects ---
    db_subjects = {s.name: s for s in db.query(Subject).all()}
    for name in exp_subjects:
        if name not in db_subjects:
            result.subjects_added.append(name)
    for name, subj in db_subjects.items():
        if name not in exp_subjects:
            result.subjects_removed.append(name)

    # --- Topics & Competences ---
    for subj_name, subj in db_subjects.items():
        if subj_name in [s for s in result.subjects_removed]:
            # Whole subject being removed: count its data
            for topic in subj.topics:
                comp_ids = [c.id for c in topic.competences]
                if comp_ids:
                    result.class_selections_lost += db.scalar(
                        select(func.count(ClassCompetence.competence_id))
                        .where(ClassCompetence.competence_id.in_(comp_ids))
                    ) or 0
                result.grades_lost += db.scalar(
                    select(func.count(Grade.id)).where(Grade.topic_id == topic.id)
                ) or 0
            continue

        exp_topic_keys = exp_topics.get(subj_name, set())
        for topic in subj.topics:
            key = (topic.block, topic.name)
            if key not in exp_topic_keys:
                result.topics_removed.append(f"{subj_name} / {topic.name} [{topic.block}]")
                comp_ids = [c.id for c in topic.competences]
                if comp_ids:
                    result.class_selections_lost += db.scalar(
                        select(func.count(ClassCompetence.competence_id))
                        .where(ClassCompetence.competence_id.in_(comp_ids))
                    ) or 0
                result.grades_lost += db.scalar(
                    select(func.count(Grade.id)).where(Grade.topic_id == topic.id)
                ) or 0
            else:
                # Topic stays — check competences
                exp_comp_list = exp_comps.get((subj_name, topic.block, topic.name), [])
                exp_comp_texts = set(exp_comp_list)
                db_comp_texts = {c.text: c.id for c in topic.competences}
                for txt, cid in db_comp_texts.items():
                    if txt not in exp_comp_texts:
                        result.competences_removed += 1
                        result.class_selections_lost += db.scalar(
                            select(func.count(ClassCompetence.competence_id))
                            .where(ClassCompetence.competence_id == cid)
                        ) or 0

        # Topics to be added
        db_topic_keys = {(t.block, t.name) for t in subj.topics}
        for block, topic_name in exp_topic_keys:
            if (block, topic_name) not in db_topic_keys:
                result.topics_added.append(f"{subj_name} / {topic_name} [{block}]")
                comp_count = len(exp_comps.get((subj_name, block, topic_name), []))
                result.competences_added += comp_count

    # Count competences added for entirely new subjects/topics
    for subj_name in result.subjects_added:
        for block_topics in (COMPETENCES.get(subj_name) or {}).values():
            for comp_list in block_topics.values():
                result.competences_added += len(comp_list)

    return result


# ---------------------------------------------------------------------------
# Full sync (destructive — confirm before calling)
# ---------------------------------------------------------------------------

def apply_full_sync(db: Session) -> CompetenceSyncResult:
    """Apply the full diff: additions + deletions. Returns what was done."""
    result = CompetenceSyncResult()
    exp_subjects  = _expected_subjects()
    exp_topics    = _expected_topics()
    exp_comps     = _expected_competences()

    db_subjects = {s.name: s for s in db.query(Subject).all()}

    # --- Remove deleted subjects ---
    for name, subj in db_subjects.items():
        if name not in exp_subjects:
            result.subjects_removed.append(name)
            for topic in list(subj.topics):
                comp_ids = [c.id for c in topic.competences]
                if comp_ids:
                    n = db.execute(
                        delete(ClassCompetence).where(ClassCompetence.competence_id.in_(comp_ids))
                    ).rowcount
                    result.class_selections_lost += n
                db.execute(delete(CustomCompetence).where(CustomCompetence.topic_id == topic.id))
                result.grades_lost += len(topic.grades)
            db.delete(subj)
    db.flush()

    # Reload after deletions
    db_subjects = {s.name: s for s in db.query(Subject).all()}

    # --- Remove deleted topics / competences ---
    for subj_name, subj in db_subjects.items():
        exp_topic_keys = exp_topics.get(subj_name, set())

        for topic in list(subj.topics):
            key = (topic.block, topic.name)
            if key not in exp_topic_keys:
                result.topics_removed.append(f"{subj_name} / {topic.name} [{topic.block}]")
                comp_ids = [c.id for c in topic.competences]
                if comp_ids:
                    n = db.execute(
                        delete(ClassCompetence).where(ClassCompetence.competence_id.in_(comp_ids))
                    ).rowcount
                    result.class_selections_lost += n
                db.execute(delete(CustomCompetence).where(CustomCompetence.topic_id == topic.id))
                result.grades_lost += len(topic.grades)
                db.delete(topic)  # cascades Competence + Grade
            else:
                # Topic stays — remove individual deleted competences
                exp_comp_texts = set(exp_comps.get((subj_name, topic.block, topic.name), []))
                for comp in list(topic.competences):
                    if comp.text not in exp_comp_texts:
                        result.competences_removed += 1
                        n = db.execute(
                            delete(ClassCompetence).where(ClassCompetence.competence_id == comp.id)
                        ).rowcount
                        result.class_selections_lost += n
                        db.delete(comp)

    db.flush()

    # --- Add new subjects / topics / competences ---
    apply_additions_only(db)

    # Count additions (rough — additions_only handles idempotency)
    result.subjects_added = [n for n in exp_subjects if n not in db_subjects]
    for subj_name in exp_subjects:
        subj = db.query(Subject).filter_by(name=subj_name).first()
        if not subj:
            continue
        exp_topic_keys = exp_topics.get(subj_name, set())
        db_topic_keys  = {(t.block, t.name) for t in subj.topics}
        for block, tname in exp_topic_keys:
            if (block, tname) not in db_topic_keys:
                result.topics_added.append(f"{subj_name} / {tname} [{block}]")

    return result

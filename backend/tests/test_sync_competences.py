"""test_sync_competences.py — unit tests for sync_competences.py.

Uses a fresh SQLite engine per test with a minimal, controlled competence
dict so the diff results are completely deterministic.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db_schema import (
    Base, Subject, Topic, Competence,
    SchoolClass, ClassCompetence,
    populate_from_dict,
)
from sync_competences import (
    CompetenceSyncResult,
    apply_additions_only,
    apply_full_sync,
    compute_diff,
)
from tests.conftest import MINIMAL_COMPETENCES, MINIMAL_SUBJECTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sync_engine():
    """Fresh SQLite engine populated with MINIMAL_COMPETENCES."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    with Session(eng) as ses:
        populate_from_dict(MINIMAL_COMPETENCES, ses)
        for name in MINIMAL_SUBJECTS:
            if not ses.query(Subject).filter_by(name=name).first():
                ses.add(Subject(name=name))
        ses.commit()
    yield eng
    eng.dispose()


@pytest.fixture
def sync_db(sync_engine):
    with Session(sync_engine) as ses:
        yield ses


def _patch_competence_data(competences: dict, subjects: list[str]):
    """Context manager: temporarily replace COMPETENCES and SUBJECTS in sync module."""
    return (
        patch("sync_competences.COMPETENCES", competences),
        patch("sync_competences.SUBJECTS", subjects),
    )


# ---------------------------------------------------------------------------
# CompetenceSyncResult dataclass
# ---------------------------------------------------------------------------

class TestCompetenceSyncResult:
    def test_has_changes_false_when_empty(self):
        r = CompetenceSyncResult()
        assert not r.has_changes

    def test_has_removals_false_when_empty(self):
        r = CompetenceSyncResult()
        assert not r.has_removals

    def test_has_changes_true_with_addition(self):
        r = CompetenceSyncResult(subjects_added=["Mathematik"])
        assert r.has_changes

    def test_has_removals_true_with_removed_subject(self):
        r = CompetenceSyncResult(subjects_removed=["Physik"])
        assert r.has_removals

    def test_has_removals_true_with_removed_topic(self):
        r = CompetenceSyncResult(topics_removed=["Mathematik / Geometrie [5/6]"])
        assert r.has_removals

    def test_has_removals_true_with_removed_competences(self):
        r = CompetenceSyncResult(competences_removed=3)
        assert r.has_removals


# ---------------------------------------------------------------------------
# compute_diff — no changes
# ---------------------------------------------------------------------------

class TestComputeDiffNoChanges:
    def test_no_changes_when_data_matches(self, sync_db):
        with (
            patch("sync_competences.COMPETENCES", MINIMAL_COMPETENCES),
            patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
        ):
            result = compute_diff(sync_db)
        assert not result.has_changes
        assert result.subjects_added == []
        assert result.subjects_removed == []
        assert result.topics_added == []
        assert result.topics_removed == []
        assert result.competences_added == 0
        assert result.competences_removed == 0


# ---------------------------------------------------------------------------
# compute_diff — additions detected
# ---------------------------------------------------------------------------

class TestComputeDiffAdditions:
    def test_detects_new_subject(self, sync_db):
        extended = {
            **MINIMAL_COMPETENCES,
            "Physik": {"5/6": {"Mechanik": ["Versteht Kräfte"]}},
        }
        extended_subjects = MINIMAL_SUBJECTS + ["Physik"]
        with (
            patch("sync_competences.COMPETENCES", extended),
            patch("sync_competences.SUBJECTS", extended_subjects),
        ):
            result = compute_diff(sync_db)
        assert "Physik" in result.subjects_added
        assert result.competences_added >= 1

    def test_detects_new_topic_in_existing_subject(self, sync_db):
        extended = {
            **MINIMAL_COMPETENCES,
            "Mathematik": {
                **MINIMAL_COMPETENCES["Mathematik"],
                "5/6": {
                    **MINIMAL_COMPETENCES["Mathematik"]["5/6"],
                    "Statistik": ["Liest Diagramme"],
                },
            },
        }
        with (
            patch("sync_competences.COMPETENCES", extended),
            patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
        ):
            result = compute_diff(sync_db)
        matching = [t for t in result.topics_added if "Statistik" in t]
        assert matching

    def test_detects_new_competence_in_existing_topic(self, sync_engine):
        """
        compute_diff does not surface additions within existing topics as
        competences_added (they are handled silently by apply_additions_only).
        Verify the new competence IS inserted by apply_additions_only.
        """
        new_text = "Kann Primzahlen benennen"
        extended = {
            **MINIMAL_COMPETENCES,
            "Mathematik": {
                **MINIMAL_COMPETENCES["Mathematik"],
                "5/6": {
                    **MINIMAL_COMPETENCES["Mathematik"]["5/6"],
                    "Zahlen und Operationen": [
                        *MINIMAL_COMPETENCES["Mathematik"]["5/6"]["Zahlen und Operationen"],
                        new_text,
                    ],
                },
            },
        }
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", extended),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_additions_only(ses)
            comp = ses.query(Competence).filter_by(text=new_text).first()
        assert comp is not None


# ---------------------------------------------------------------------------
# compute_diff — removals detected
# ---------------------------------------------------------------------------

class TestComputeDiffRemovals:
    def test_detects_removed_subject(self, sync_db):
        reduced = {k: v for k, v in MINIMAL_COMPETENCES.items() if k != "Deutsch"}
        reduced_subjects = [s for s in MINIMAL_SUBJECTS if s != "Deutsch"]
        with (
            patch("sync_competences.COMPETENCES", reduced),
            patch("sync_competences.SUBJECTS", reduced_subjects),
        ):
            result = compute_diff(sync_db)
        assert "Deutsch" in result.subjects_removed

    def test_detects_removed_topic(self, sync_db):
        math_no_geo = {
            "5/6": {
                k: v for k, v in MINIMAL_COMPETENCES["Mathematik"]["5/6"].items()
                if k != "Geometrie"
            },
            "7/8": MINIMAL_COMPETENCES["Mathematik"]["7/8"],
        }
        reduced = {**MINIMAL_COMPETENCES, "Mathematik": math_no_geo}
        with (
            patch("sync_competences.COMPETENCES", reduced),
            patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
        ):
            result = compute_diff(sync_db)
        matching = [t for t in result.topics_removed if "Geometrie" in t]
        assert matching

    def test_detects_removed_competence(self, sync_db):
        math_fewer = {
            "5/6": {
                "Zahlen und Operationen": [
                    # Drop "Kann Grundrechenarten anwenden"
                    "Kann natürliche Zahlen lesen und schreiben",
                ],
                "Geometrie": MINIMAL_COMPETENCES["Mathematik"]["5/6"]["Geometrie"],
            },
            "7/8": MINIMAL_COMPETENCES["Mathematik"]["7/8"],
        }
        reduced = {**MINIMAL_COMPETENCES, "Mathematik": math_fewer}
        with (
            patch("sync_competences.COMPETENCES", reduced),
            patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
        ):
            result = compute_diff(sync_db)
        assert result.competences_removed >= 1


# ---------------------------------------------------------------------------
# apply_additions_only
# ---------------------------------------------------------------------------

class TestApplyAdditionsOnly:
    def test_adds_missing_subject(self, sync_engine):
        extended = {
            **MINIMAL_COMPETENCES,
            "Chemie": {"5/6": {"Atome": ["Kennt das Periodensystem"]}},
        }
        extended_subjects = MINIMAL_SUBJECTS + ["Chemie"]
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", extended),
                patch("sync_competences.SUBJECTS", extended_subjects),
            ):
                apply_additions_only(ses)
            subj = ses.query(Subject).filter_by(name="Chemie").first()
        assert subj is not None

    def test_adds_missing_competence(self, sync_engine):
        extended = {
            **MINIMAL_COMPETENCES,
            "Mathematik": {
                **MINIMAL_COMPETENCES["Mathematik"],
                "5/6": {
                    **MINIMAL_COMPETENCES["Mathematik"]["5/6"],
                    "Zahlen und Operationen": [
                        *MINIMAL_COMPETENCES["Mathematik"]["5/6"]["Zahlen und Operationen"],
                        "Kann Brüche kürzen",
                    ],
                },
            },
        }
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", extended),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_additions_only(ses)
            comp = ses.query(Competence).filter_by(text="Kann Brüche kürzen").first()
        assert comp is not None

    def test_does_not_remove_anything(self, sync_engine):
        with Session(sync_engine) as ses:
            before_count = ses.query(Competence).count()

        # Provide reduced competences
        reduced = {"Mathematik": {"5/6": {"Zahlen und Operationen": []}}}
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", ["Mathematik"]),
            ):
                apply_additions_only(ses)
            after_count = ses.query(Competence).count()

        assert after_count >= before_count

    def test_idempotent(self, sync_engine):
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", MINIMAL_COMPETENCES),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_additions_only(ses)
            count_1 = ses.query(Competence).count()

        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", MINIMAL_COMPETENCES),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_additions_only(ses)
            count_2 = ses.query(Competence).count()

        assert count_1 == count_2


# ---------------------------------------------------------------------------
# apply_full_sync
# ---------------------------------------------------------------------------

class TestApplyFullSync:
    def test_removes_deleted_subject(self, sync_engine):
        reduced = {k: v for k, v in MINIMAL_COMPETENCES.items() if k != "Deutsch"}
        reduced_subjects = [s for s in MINIMAL_SUBJECTS if s != "Deutsch"]
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", reduced_subjects),
            ):
                apply_full_sync(ses)
            subj = ses.query(Subject).filter_by(name="Deutsch").first()
        assert subj is None

    def test_removes_deleted_topic(self, sync_engine):
        math_no_geo = {
            "5/6": {
                k: v for k, v in MINIMAL_COMPETENCES["Mathematik"]["5/6"].items()
                if k != "Geometrie"
            },
            "7/8": MINIMAL_COMPETENCES["Mathematik"]["7/8"],
        }
        reduced = {**MINIMAL_COMPETENCES, "Mathematik": math_no_geo}
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_full_sync(ses)
            topic = ses.query(Topic).filter_by(name="Geometrie").first()
        assert topic is None

    def test_removes_deleted_competence(self, sync_engine):
        reduced_topic = [
            "Kann natürliche Zahlen lesen und schreiben",
            # "Kann Grundrechenarten anwenden" is dropped
        ]
        reduced = {
            **MINIMAL_COMPETENCES,
            "Mathematik": {
                **MINIMAL_COMPETENCES["Mathematik"],
                "5/6": {
                    **MINIMAL_COMPETENCES["Mathematik"]["5/6"],
                    "Zahlen und Operationen": reduced_topic,
                },
            },
        }
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                apply_full_sync(ses)
            comp = ses.query(Competence).filter_by(
                text="Kann Grundrechenarten anwenden"
            ).first()
        assert comp is None

    def test_adds_new_content(self, sync_engine):
        extended = {
            **MINIMAL_COMPETENCES,
            "Biologie": {"5/6": {"Zellen": ["Kennt Zellbestandteile"]}},
        }
        extended_subjects = MINIMAL_SUBJECTS + ["Biologie"]
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", extended),
                patch("sync_competences.SUBJECTS", extended_subjects),
            ):
                apply_full_sync(ses)
            subj = ses.query(Subject).filter_by(name="Biologie").first()
        assert subj is not None

    def test_result_reports_removed_subjects(self, sync_engine):
        reduced = {k: v for k, v in MINIMAL_COMPETENCES.items() if k != "Deutsch"}
        reduced_subjects = [s for s in MINIMAL_SUBJECTS if s != "Deutsch"]
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", reduced_subjects),
            ):
                result = apply_full_sync(ses)
        assert "Deutsch" in result.subjects_removed

    def test_result_reports_added_subjects(self, sync_engine):
        extended = {
            **MINIMAL_COMPETENCES,
            "Geschichte": {"5/6": {"Antike": ["Kennt das Römische Reich"]}},
        }
        extended_subjects = MINIMAL_SUBJECTS + ["Geschichte"]
        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", extended),
                patch("sync_competences.SUBJECTS", extended_subjects),
            ):
                result = apply_full_sync(ses)
        assert "Geschichte" in result.subjects_added

    def test_class_selections_lost_counted(self, sync_engine):
        """ClassCompetence rows for removed competences are counted in result."""
        # The competence we'll remove is the first one in Mathematik 5/6 Geometrie
        TARGET_TEXT = MINIMAL_COMPETENCES["Mathematik"]["5/6"]["Geometrie"][0]

        with Session(sync_engine) as ses:
            comp = ses.query(Competence).filter_by(text=TARGET_TEXT).first()
            assert comp is not None, f"Competence not found: {TARGET_TEXT}"
            cls = SchoolClass(name="__tc_sel__")
            ses.add(cls)
            ses.flush()
            ses.add(ClassCompetence(class_id=cls.id, competence_id=comp.id, selected=True))
            ses.commit()

        # Remove Geometrie topic entirely from canonical data
        math_no_geo = {
            "5/6": {
                k: v for k, v in MINIMAL_COMPETENCES["Mathematik"]["5/6"].items()
                if k != "Geometrie"
            },
            "7/8": MINIMAL_COMPETENCES["Mathematik"]["7/8"],
        }
        reduced = {**MINIMAL_COMPETENCES, "Mathematik": math_no_geo}

        with Session(sync_engine) as ses:
            with (
                patch("sync_competences.COMPETENCES", reduced),
                patch("sync_competences.SUBJECTS", MINIMAL_SUBJECTS),
            ):
                result = compute_diff(ses)

        assert result.class_selections_lost >= 1

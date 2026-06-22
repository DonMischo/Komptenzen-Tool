"""test_db_helpers.py — unit tests for db_helpers.py.

All tests use a fresh SQLite engine per test class (via the helpers_engine
fixture) and monkeypatch db_helpers.ENGINE for functions that use the global.

Covers:
- _clean_grade: float/int/string edge cases
- _get_or_create_class: creation, idempotency
- get_classes: ordering
- get_students_by_class: ordering, empty class
- get_topics_by_subject: with/without class filter
- save_selections / load_topic_rows: upsert, toggle off
- toggle_topic: creates missing links, updates existing
- get_niveau / set_niveau: create and update
- sync_competences_to_parallel: copies selections, stays in year group
- get_custom_competences / add / delete
- fetch_grade_matrix: shape, niveau, grades
- persist_grade_matrix: upsert grades and niveau
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db_schema import (
    Base, Subject, Topic, Competence, SchoolClass,
    ClassCompetence, CustomCompetence, Student, StudentSubject, Grade,
)
from db_helpers import (
    _clean_grade,
    _get_or_create_class,
    get_classes,
    get_students_by_class,
    get_topics_by_subject,
    save_selections,
    load_topic_rows,
    toggle_topic,
    get_niveau,
    set_niveau,
    sync_competences_to_parallel,
    get_custom_competences,
    add_custom_competence,
    delete_custom_competence,
    fetch_grade_matrix,
    persist_grade_matrix,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def helpers_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def populated(helpers_engine):
    """
    Returns engine populated with:
      classes: 7a, 7b, 7c
      subject: Mathematik
        topic: Zahlen [5/6] with 2 competences
        topic: Algebra [7/8] with 1 competence
      students in 7a: Müller Anna, Schmidt Bob
    """
    with Session(helpers_engine) as ses:
        cls_7a = SchoolClass(name="7a")
        cls_7b = SchoolClass(name="7b")
        cls_7c = SchoolClass(name="7c")
        ses.add_all([cls_7a, cls_7b, cls_7c])
        ses.flush()

        subj = Subject(name="Mathematik")
        ses.add(subj)
        ses.flush()

        t1 = Topic(name="Zahlen", block="5/6", subject=subj)
        t2 = Topic(name="Algebra", block="7/8", subject=subj)
        ses.add_all([t1, t2])
        ses.flush()

        c1 = Competence(text="Kann zählen", topic=t1)
        c2 = Competence(text="Kann addieren", topic=t1)
        c3 = Competence(text="Löst Gleichungen", topic=t2)
        ses.add_all([c1, c2, c3])
        ses.flush()

        anna = Student(last_name="Müller", first_name="Anna",
                       birthday=date(2012, 1, 1), school_class=cls_7a)
        bob  = Student(last_name="Schmidt", first_name="Bob",
                       birthday=date(2012, 2, 2), school_class=cls_7a)
        ses.add_all([anna, bob])
        ses.commit()

    return helpers_engine


# ---------------------------------------------------------------------------
# _clean_grade
# ---------------------------------------------------------------------------

class TestCleanGrade:
    def test_whole_float_becomes_int_string(self):
        assert _clean_grade(3.0) == "3"

    def test_non_whole_float_stays(self):
        assert _clean_grade(3.5) == "3.5"

    def test_string_stripped(self):
        assert _clean_grade("  4  ") == "4"

    def test_integer_unchanged(self):
        assert _clean_grade(2) == "2"

    def test_none_becomes_string(self):
        assert _clean_grade(None) == "None"


# ---------------------------------------------------------------------------
# _get_or_create_class
# ---------------------------------------------------------------------------

class TestGetOrCreateClass:
    def test_creates_new_class(self, helpers_engine):
        with Session(helpers_engine) as ses:
            cls = _get_or_create_class(ses, "8a")
            ses.commit()
        with Session(helpers_engine) as ses:
            assert ses.query(SchoolClass).filter_by(name="8a").first() is not None

    def test_returns_existing_class(self, helpers_engine):
        with Session(helpers_engine) as ses:
            first  = _get_or_create_class(ses, "8a")
            second = _get_or_create_class(ses, "8a")
            ses.commit()
        with Session(helpers_engine) as ses:
            assert ses.query(SchoolClass).filter_by(name="8a").count() == 1

    def test_strips_whitespace(self, helpers_engine):
        with Session(helpers_engine) as ses:
            cls = _get_or_create_class(ses, "  8b  ")
            ses.commit()
            assert cls.name == "8b"


# ---------------------------------------------------------------------------
# get_classes
# ---------------------------------------------------------------------------

class TestGetClasses:
    def test_returns_alphabetical_order(self, populated):
        with patch("db_helpers.ENGINE", populated):
            names = get_classes()
        assert names == sorted(names)

    def test_returns_all_classes(self, populated):
        with patch("db_helpers.ENGINE", populated):
            names = get_classes()
        assert set(names) == {"7a", "7b", "7c"}


# ---------------------------------------------------------------------------
# get_students_by_class
# ---------------------------------------------------------------------------

class TestGetStudentsByClass:
    def test_returns_students_in_class(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
        assert len(students) == 2

    def test_ordered_by_last_name(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
        names = [s.last_name for s in students]
        assert names == sorted(names)

    def test_empty_class_returns_empty(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7b", ses)
        assert students == []

    def test_unknown_class_created_and_returns_empty(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("9z", ses)
            ses.commit()
        assert students == []


# ---------------------------------------------------------------------------
# get_topics_by_subject
# ---------------------------------------------------------------------------

class TestGetTopicsBySubject:
    def test_all_topics_without_class_filter(self, populated):
        with Session(populated) as ses:
            topics = get_topics_by_subject("Mathematik", ses)
        assert len(topics) == 2

    def test_returns_empty_for_unknown_subject(self, populated):
        with Session(populated) as ses:
            topics = get_topics_by_subject("Physik", ses)
        assert topics == []

    def test_class_filter_returns_only_selected(self, populated):
        # Select c1 for 7a
        with Session(populated) as ses:
            cls = ses.query(SchoolClass).filter_by(name="7a").first()
            c1  = ses.query(Competence).filter_by(text="Kann zählen").first()
            ses.add(ClassCompetence(class_id=cls.id, competence_id=c1.id, selected=True))
            ses.commit()

        with Session(populated) as ses:
            topics = get_topics_by_subject("Mathematik", ses, class_name="7a")
        # Only "Zahlen" topic has a selected competence
        assert len(topics) == 1
        assert topics[0].name == "Zahlen"

    def test_class_filter_empty_when_nothing_selected(self, populated):
        with Session(populated) as ses:
            topics = get_topics_by_subject("Mathematik", ses, class_name="7a")
        assert topics == []


# ---------------------------------------------------------------------------
# save_selections / load_topic_rows
# ---------------------------------------------------------------------------

class TestSaveSelections:
    def test_creates_new_selection(self, populated):
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id

        with patch("db_helpers.ENGINE", populated):
            save_selections("7a", [(c1_id, True)])
            rows = load_topic_rows("7a", "Mathematik", "5/6")

        selected = {r[1]: r[3] for r in rows}   # topic_name: selected
        assert any(r[3] for r in rows if r[2] == "Kann zählen")

    def test_updates_existing_selection(self, populated):
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id

        with patch("db_helpers.ENGINE", populated):
            save_selections("7a", [(c1_id, True)])
            save_selections("7a", [(c1_id, False)])
            rows = load_topic_rows("7a", "Mathematik", "5/6")

        assert not any(r[3] for r in rows if r[2] == "Kann zählen")

    def test_no_changes_is_noop(self, populated):
        with patch("db_helpers.ENGINE", populated):
            save_selections("7a", [])   # must not raise


class TestLoadTopicRows:
    def test_returns_all_competences_in_block(self, populated):
        with patch("db_helpers.ENGINE", populated):
            rows = load_topic_rows("7a", "Mathematik", "5/6")
        assert len(rows) == 2  # c1, c2

    def test_unselected_by_default(self, populated):
        with patch("db_helpers.ENGINE", populated):
            rows = load_topic_rows("7a", "Mathematik", "5/6")
        assert all(not r[3] for r in rows)

    def test_row_structure(self, populated):
        with patch("db_helpers.ENGINE", populated):
            rows = load_topic_rows("7a", "Mathematik", "5/6")
        comp_id, topic_name, text, selected = rows[0]
        assert isinstance(comp_id, int)
        assert isinstance(topic_name, str)
        assert isinstance(text, str)
        assert isinstance(selected, bool)


# ---------------------------------------------------------------------------
# toggle_topic
# ---------------------------------------------------------------------------

class TestToggleTopic:
    def test_toggle_on_creates_links(self, populated):
        with Session(populated) as ses:
            t1 = ses.query(Topic).filter_by(name="Zahlen").first()
            t1_id = t1.id

        with patch("db_helpers.ENGINE", populated):
            toggle_topic("7a", t1_id, True)
            rows = load_topic_rows("7a", "Mathematik", "5/6")

        assert all(r[3] for r in rows)

    def test_toggle_off_deselects(self, populated):
        with Session(populated) as ses:
            t1 = ses.query(Topic).filter_by(name="Zahlen").first()
            t1_id = t1.id

        with patch("db_helpers.ENGINE", populated):
            toggle_topic("7a", t1_id, True)
            toggle_topic("7a", t1_id, False)
            rows = load_topic_rows("7a", "Mathematik", "5/6")

        assert all(not r[3] for r in rows)

    def test_toggle_idempotent(self, populated):
        with Session(populated) as ses:
            t1 = ses.query(Topic).filter_by(name="Zahlen").first()
            t1_id = t1.id

        with patch("db_helpers.ENGINE", populated):
            toggle_topic("7a", t1_id, True)
            toggle_topic("7a", t1_id, True)
            rows = load_topic_rows("7a", "Mathematik", "5/6")

        assert all(r[3] for r in rows)


# ---------------------------------------------------------------------------
# get_niveau / set_niveau
# ---------------------------------------------------------------------------

class TestNiveau:
    def test_get_niveau_empty_when_not_set(self, populated):
        with Session(populated) as ses:
            anna = ses.query(Student).filter_by(first_name="Anna").first()
            subj = ses.query(Subject).filter_by(name="Mathematik").first()
            niveau = get_niveau(anna.id, subj.id, ses)
        assert niveau == ""

    def test_set_and_get_niveau(self, populated):
        with Session(populated) as ses:
            anna = ses.query(Student).filter_by(first_name="Anna").first()
            subj = ses.query(Subject).filter_by(name="Mathematik").first()
            set_niveau(anna.id, subj.id, "A2", ses)
            niveau = get_niveau(anna.id, subj.id, ses)
        assert niveau == "A2"

    def test_set_niveau_updates_existing(self, populated):
        with Session(populated) as ses:
            anna = ses.query(Student).filter_by(first_name="Anna").first()
            subj = ses.query(Subject).filter_by(name="Mathematik").first()
            set_niveau(anna.id, subj.id, "A2", ses)
            set_niveau(anna.id, subj.id, "B1", ses)
            niveau = get_niveau(anna.id, subj.id, ses)
        assert niveau == "B1"

    def test_set_niveau_strips_whitespace(self, populated):
        with Session(populated) as ses:
            anna = ses.query(Student).filter_by(first_name="Anna").first()
            subj = ses.query(Subject).filter_by(name="Mathematik").first()
            set_niveau(anna.id, subj.id, "  B2  ", ses)
            niveau = get_niveau(anna.id, subj.id, ses)
        assert niveau == "B2"


# ---------------------------------------------------------------------------
# sync_competences_to_parallel
# ---------------------------------------------------------------------------

class TestSyncCompetencesToParallel:
    def _select_for_class(self, engine, class_name: str, comp_id: int):
        with Session(engine) as ses:
            cls = ses.query(SchoolClass).filter_by(name=class_name).first()
            ses.add(ClassCompetence(class_id=cls.id, competence_id=comp_id, selected=True))
            ses.commit()

    def test_copies_to_parallel_classes(self, populated):
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id
        self._select_for_class(populated, "7a", c1_id)

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a")

        assert set(affected) == {"7b", "7c"}

        with Session(populated) as ses:
            for cname in ("7b", "7c"):
                cls = ses.query(SchoolClass).filter_by(name=cname).first()
                link = ses.query(ClassCompetence).filter_by(
                    class_id=cls.id, competence_id=c1_id
                ).first()
                assert link is not None
                assert link.selected is True

    def test_does_not_touch_other_year_classes(self, populated):
        with Session(populated) as ses:
            cls_5a = SchoolClass(name="5a")
            ses.add(cls_5a)
            ses.commit()
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id
        self._select_for_class(populated, "7a", c1_id)

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a")

        assert "5a" not in affected

    def test_returns_empty_when_no_parallel(self, populated):
        # Remove 7b and 7c, only 7a remains
        with Session(populated) as ses:
            for name in ("7b", "7c"):
                cls = ses.query(SchoolClass).filter_by(name=name).first()
                if cls:
                    ses.delete(cls)
            ses.commit()

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a")

        assert affected == []

    def test_no_digit_class_returns_empty(self, populated):
        with patch("db_helpers.ENGINE", populated):
            result = sync_competences_to_parallel("abc")
        assert result == []

    def test_target_classes_limits_sync(self, populated):
        """target_classes=["7b"] only syncs to 7b, not 7c."""
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id
        self._select_for_class(populated, "7a", c1_id)

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a", target_classes=["7b"])

        assert affected == ["7b"]

        # 7b got it, 7c did not
        with Session(populated) as ses:
            cls7b = ses.query(SchoolClass).filter_by(name="7b").first()
            cls7c = ses.query(SchoolClass).filter_by(name="7c").first()
            link7b = ses.query(ClassCompetence).filter_by(
                class_id=cls7b.id, competence_id=c1_id
            ).first()
            link7c = ses.query(ClassCompetence).filter_by(
                class_id=cls7c.id, competence_id=c1_id
            ).first()
            assert link7b is not None and link7b.selected is True
            assert link7c is None

    def test_target_classes_empty_list_syncs_none(self, populated):
        """Empty target_classes → no classes synced (treated as empty filter)."""
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id
        self._select_for_class(populated, "7a", c1_id)

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a", target_classes=[])

        assert affected == []

    def test_none_target_classes_syncs_all(self, populated):
        """target_classes=None → all parallel classes (default behaviour)."""
        with Session(populated) as ses:
            c1 = ses.query(Competence).filter_by(text="Kann zählen").first()
            c1_id = c1.id
        self._select_for_class(populated, "7a", c1_id)

        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a", target_classes=None)

        assert set(affected) == {"7b", "7c"}

    def test_target_class_not_in_year_returns_empty(self, populated):
        """Requesting a target from another year group returns empty."""
        with patch("db_helpers.ENGINE", populated):
            affected = sync_competences_to_parallel("7a", target_classes=["5a"])

        assert affected == []


# ---------------------------------------------------------------------------
# Custom competences
# ---------------------------------------------------------------------------

class TestCustomCompetences:
    def test_add_custom_competence(self, populated):
        with Session(populated) as ses:
            cls = ses.query(SchoolClass).filter_by(name="7a").first()
            t1  = ses.query(Topic).filter_by(name="Zahlen").first()
            cc  = add_custom_competence(cls.id, t1.id, "Eigene Kompetenz", ses)
            assert cc.id is not None
            assert cc.text == "Eigene Kompetenz"

    def test_get_custom_competences(self, populated):
        with Session(populated) as ses:
            cls = ses.query(SchoolClass).filter_by(name="7a").first()
            t1  = ses.query(Topic).filter_by(name="Zahlen").first()
            add_custom_competence(cls.id, t1.id, "CC1", ses)
            add_custom_competence(cls.id, t1.id, "CC2", ses)
            items = get_custom_competences(cls.id, t1.id, ses)
        assert len(items) == 2

    def test_delete_custom_competence(self, populated):
        with Session(populated) as ses:
            cls = ses.query(SchoolClass).filter_by(name="7a").first()
            t1  = ses.query(Topic).filter_by(name="Zahlen").first()
            cc  = add_custom_competence(cls.id, t1.id, "To delete", ses)
            cc_id = cc.id
            delete_custom_competence(cc_id, ses)
            items = get_custom_competences(cls.id, t1.id, ses)
        assert len(items) == 0

    def test_delete_nonexistent_is_noop(self, populated):
        with Session(populated) as ses:
            delete_custom_competence(99999, ses)   # must not raise

    def test_text_stripped_on_add(self, populated):
        with Session(populated) as ses:
            cls = ses.query(SchoolClass).filter_by(name="7a").first()
            t1  = ses.query(Topic).filter_by(name="Zahlen").first()
            cc  = add_custom_competence(cls.id, t1.id, "  Leerzeichen  ", ses)
            text = cc.text  # read before session closes
        assert text == "Leerzeichen"

    def test_custom_not_visible_to_other_class(self, populated):
        with Session(populated) as ses:
            cls_a = ses.query(SchoolClass).filter_by(name="7a").first()
            cls_b = ses.query(SchoolClass).filter_by(name="7b").first()
            t1    = ses.query(Topic).filter_by(name="Zahlen").first()
            add_custom_competence(cls_a.id, t1.id, "Only 7a", ses)
            items = get_custom_competences(cls_b.id, t1.id, ses)
        assert items == []


# ---------------------------------------------------------------------------
# fetch_grade_matrix
# ---------------------------------------------------------------------------

class TestFetchGradeMatrix:
    def test_returns_dataframe(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df = fetch_grade_matrix(students, topics, "Mathematik", ses)
        assert isinstance(df, pd.DataFrame)

    def test_row_count_matches_students(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df = fetch_grade_matrix(students, topics, "Mathematik", ses)
        assert len(df) == 2

    def test_columns_include_student_fields(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df = fetch_grade_matrix(students, topics, "Mathematik", ses)
        assert "Nachname" in df.columns
        assert "Vorname"  in df.columns
        assert "Niveau"   in df.columns

    def test_topic_columns_present(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df = fetch_grade_matrix(students, topics, "Mathematik", ses)
            topic_ids = {str(t.id) for t in topics}
        assert topic_ids.issubset(set(df.columns))

    def test_grades_empty_by_default(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df = fetch_grade_matrix(students, topics, "Mathematik", ses)
            topic_cols = [str(t.id) for t in topics]
        assert all(df[col].eq("").all() for col in topic_cols)

    def test_raises_for_unknown_subject(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            with pytest.raises(ValueError, match="not found"):
                fetch_grade_matrix(students, [], "Nichtexistent", ses)

    def test_niveau_reflected_in_df(self, populated):
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            subj     = ses.query(Subject).filter_by(name="Mathematik").first()
            anna     = next(s for s in students if s.first_name == "Anna")
            set_niveau(anna.id, subj.id, "B2", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            df       = fetch_grade_matrix(students, topics, "Mathematik", ses)
        anna_row = df[df["Vorname"] == "Anna"]
        assert anna_row.iloc[0]["Niveau"] == "B2"


# ---------------------------------------------------------------------------
# persist_grade_matrix
# ---------------------------------------------------------------------------

class TestPersistGradeMatrix:
    def _make_df(self, populated, grades: dict | None = None) -> tuple:
        """Build a minimal DataFrame for 7a/Mathematik and return (df, topic_ids)."""
        with Session(populated) as ses:
            students = get_students_by_class("7a", ses)
            topics   = get_topics_by_subject("Mathematik", ses)
            topic_ids = [str(t.id) for t in topics]
            rows = []
            for stu in students:
                row = {"Nachname": stu.last_name, "Vorname": stu.first_name, "Niveau": ""}
                for tid in topic_ids:
                    row[tid] = (grades or {}).get((stu.first_name, tid), "")
                rows.append(row)
        return pd.DataFrame(rows), topic_ids

    def test_persists_grade(self, populated):
        with Session(populated) as ses:
            topics   = get_topics_by_subject("Mathematik", ses)
            topic_id = str(topics[0].id)

        df, _ = self._make_df(populated, {("Anna", topic_id): "3"})
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df, ses)

        with Session(populated) as ses:
            anna  = ses.query(Student).filter_by(first_name="Anna").first()
            grade = ses.query(Grade).filter_by(student_id=anna.id, topic_id=int(topic_id)).first()
        assert grade is not None
        assert grade.value == "3"

    def test_updates_existing_grade(self, populated):
        with Session(populated) as ses:
            topics   = get_topics_by_subject("Mathematik", ses)
            topic_id = str(topics[0].id)

        df, _ = self._make_df(populated, {("Anna", topic_id): "3"})
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df, ses)

        df2, _ = self._make_df(populated, {("Anna", topic_id): "5"})
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df2, ses)

        with Session(populated) as ses:
            anna  = ses.query(Student).filter_by(first_name="Anna").first()
            grade = ses.query(Grade).filter_by(student_id=anna.id, topic_id=int(topic_id)).first()
        assert grade.value == "5"

    def test_empty_grade_not_stored(self, populated):
        df, _ = self._make_df(populated)  # all grades ""
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df, ses)
        with Session(populated) as ses:
            assert ses.query(Grade).count() == 0

    def test_persists_niveau(self, populated):
        with Session(populated) as ses:
            topics   = get_topics_by_subject("Mathematik", ses)
            topic_id = str(topics[0].id)

        df, _ = self._make_df(populated)
        df.loc[df["Vorname"] == "Anna", "Niveau"] = "B1"
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df, ses)

        with Session(populated) as ses:
            anna = ses.query(Student).filter_by(first_name="Anna").first()
            subj = ses.query(Subject).filter_by(name="Mathematik").first()
            assert get_niveau(anna.id, subj.id, ses) == "B1"

    def test_unknown_student_skipped(self, populated):
        df, _ = self._make_df(populated)
        extra = pd.DataFrame([{"Nachname": "Ghost", "Vorname": "Student", "Niveau": ""}])
        df = pd.concat([df, extra], ignore_index=True)
        with Session(populated) as ses:
            persist_grade_matrix("7a", "Mathematik", df, ses)  # must not raise

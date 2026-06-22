"""test_api_lb_profile.py — Tests for GET /api/students/{id}/lb-profile.

The endpoint returns a full competence/grade profile for one LB or GB student
across all relevant subjects for their class grade level.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from db_schema import (
    Base, SchoolClass, Student, Subject, Topic, Competence,
    ClassCompetence, StudentSubject, Grade,
)


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def lb_seed(client, sqlite_engine):
    """Class 5a_lbp: one LB student, one GB student, one normal student.

    Subject "Mathematik" (in _LB_RELEVANT["5"]) with one selected topic.
    Also adds "Lebenspraxis" subject so that path is covered.
    """
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = SchoolClass(name="5a_lbp")
        ses.add(cls)
        ses.flush()

        subj = Subject(name="Mathematik_lbp")
        lp_subj = Subject(name="Lebenspraxis_lbp")
        ses.add_all([subj, lp_subj])
        ses.flush()

        t1 = Topic(name="Zahlen_lbp", block="5/6", subject=subj)
        ses.add(t1)
        ses.flush()

        c1 = Competence(text="Rechnen_lbp", topic=t1)
        ses.add(c1)
        ses.flush()

        ses.add(ClassCompetence(class_id=cls.id, competence_id=c1.id, selected=True))

        lb_stu = Student(last_name="Lehmann_lbp", first_name="Lara",
                         birthday=date(2014, 3, 1), school_class=cls, lb=True)
        gb_stu = Student(last_name="Geber_lbp", first_name="Georg",
                         birthday=date(2014, 4, 2), school_class=cls, gb=True)
        normal = Student(last_name="Normal_lbp", first_name="Nina",
                         birthday=date(2014, 5, 3), school_class=cls)
        ses.add_all([lb_stu, gb_stu, normal])
        ses.commit()
        ids = {
            "cls_id": cls.id, "subj_id": subj.id, "lp_subj_id": lp_subj.id,
            "t1_id": t1.id, "c1_id": c1.id,
            "lb_id": lb_stu.id, "gb_id": gb_stu.id, "normal_id": normal.id,
        }

    yield ids

    with Session(sqlite_engine) as ses:
        ses.query(StudentSubject).filter(
            StudentSubject.student_id.in_([ids["lb_id"], ids["gb_id"], ids["normal_id"]])
        ).delete(synchronize_session=False)
        ses.query(Grade).filter(
            Grade.student_id.in_([ids["lb_id"], ids["gb_id"], ids["normal_id"]])
        ).delete(synchronize_session=False)
        ses.query(Student).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(ClassCompetence).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(Competence).filter_by(topic_id=ids["t1_id"]).delete()
        ses.query(Topic).filter_by(id=ids["t1_id"]).delete()
        ses.query(Subject).filter_by(id=ids["subj_id"]).delete()
        ses.query(Subject).filter_by(id=ids["lp_subj_id"]).delete()
        ses.query(SchoolClass).filter_by(id=ids["cls_id"]).delete()
        ses.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLbProfileGet:
    def test_lb_student_returns_200(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        assert r.status_code == 200

    def test_gb_student_returns_200(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['gb_id']}/lb-profile")
        assert r.status_code == 200

    def test_normal_student_returns_404(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['normal_id']}/lb-profile")
        assert r.status_code == 404

    def test_unknown_student_returns_404(self, client):
        r = client.get("/api/students/999999/lb-profile")
        assert r.status_code == 404

    def test_response_has_required_fields(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        data = r.json()
        for field in ("student_id", "first_name", "last_name", "class_name",
                      "student_type", "subjects"):
            assert field in data

    def test_student_id_matches(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        assert r.json()["student_id"] == lb_seed["lb_id"]

    def test_student_type_lb(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        assert r.json()["student_type"] == "lb"

    def test_student_type_gb(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['gb_id']}/lb-profile")
        assert r.json()["student_type"] == "gb"

    def test_class_name_returned(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        assert r.json()["class_name"] == "5a_lbp"

    def test_subjects_is_list(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        assert isinstance(r.json()["subjects"], list)

    def test_subject_has_required_fields(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        # The endpoint only returns subjects that exist in the DB and in _LB_RELEVANT.
        # Our seed uses "Mathematik_lbp" which is NOT in _LB_RELEVANT, so subjects will be
        # empty (or contain only DB subjects whose names match _LB_RELEVANT exactly).
        # This just verifies field shape for any returned subjects.
        for s in r.json()["subjects"]:
            assert "name" in s
            assert "niveau" in s
            assert "topics" in s

    def test_niveau_empty_by_default(self, client, lb_seed):
        r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
        for s in r.json()["subjects"]:
            assert s["niveau"] == ""

    def test_niveau_persisted_when_set(self, client, lb_seed, sqlite_engine):
        """If a StudentSubject row exists, its niveau is returned."""
        # We need a subject name that IS in _LB_RELEVANT["5"].
        # Inject one directly into the DB using the existing seed subject id
        # by temporarily renaming via a real _LB_RELEVANT subject.
        # Instead: patch the relevant list to include our seed subject name.
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {
            "5": ["Mathematik_lbp"],
            "6": ["Mathematik_lbp"],
            "7": ["Mathematik_lbp"],
        }
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            # Set niveau via StudentSubject
            with Session(sqlite_engine) as ses:
                subj = ses.get(Subject, lb_seed["subj_id"])
                ses.add(StudentSubject(
                    student_id=lb_seed["lb_id"],
                    subject_id=subj.id,
                    niveau="2",
                ))
                ses.commit()

            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            data = r.json()
            math = next((s for s in data["subjects"] if s["name"] == "Mathematik_lbp"), None)
            assert math is not None
            assert math["niveau"] == "2"

            # Cleanup
            with Session(sqlite_engine) as ses:
                ses.query(StudentSubject).filter_by(student_id=lb_seed["lb_id"]).delete()
                ses.commit()

    def test_topics_included_for_lb_subject(self, client, lb_seed, sqlite_engine):
        """Topics with selected competences appear in the profile."""
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Mathematik_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            math = next((s for s in r.json()["subjects"] if s["name"] == "Mathematik_lbp"), None)
            assert math is not None
            assert len(math["topics"]) == 1

    def test_topic_label_excludes_subject_name(self, client, lb_seed):
        """Topic labels use 'Name (Block)' format, not 'Subject – Name (Block)'."""
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Mathematik_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            math = next(s for s in r.json()["subjects"] if s["name"] == "Mathematik_lbp")
            label = math["topics"][0]["label"]
            assert "Zahlen_lbp" in label
            assert "Mathematik_lbp" not in label

    def test_topic_grade_empty_by_default(self, client, lb_seed):
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Mathematik_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            math = next(s for s in r.json()["subjects"] if s["name"] == "Mathematik_lbp")
            assert math["topics"][0]["grade"] == ""

    def test_topic_grade_persisted_when_set(self, client, lb_seed, sqlite_engine):
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Mathematik_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            with Session(sqlite_engine) as ses:
                ses.add(Grade(student_id=lb_seed["lb_id"],
                              topic_id=lb_seed["t1_id"], value="3"))
                ses.commit()

            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            math = next(s for s in r.json()["subjects"] if s["name"] == "Mathematik_lbp")
            assert math["topics"][0]["grade"] == "3"

            with Session(sqlite_engine) as ses:
                ses.query(Grade).filter_by(student_id=lb_seed["lb_id"]).delete()
                ses.commit()

    def test_lebenspraxis_has_no_topics(self, client, lb_seed):
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Lebenspraxis_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            lp = next((s for s in r.json()["subjects"] if s["name"] == "Lebenspraxis_lbp"), None)
            # Lebenspraxis gets no topics (no topic grid for it)
            assert lp is not None
            assert lp["topics"] == []

    def test_unselected_competence_not_in_topics(self, client, lb_seed, sqlite_engine):
        """If a ClassCompetence is deselected, the topic is excluded."""
        from unittest.mock import patch
        import routers.students as stu_mod
        patched = {"5": ["Mathematik_lbp"], "6": [], "7": []}
        with patch.object(stu_mod, "_LB_RELEVANT", patched):
            with Session(sqlite_engine) as ses:
                cc = ses.query(ClassCompetence).filter_by(
                    class_id=lb_seed["cls_id"], competence_id=lb_seed["c1_id"]
                ).first()
                cc.selected = False
                ses.commit()

            r = client.get(f"/api/students/{lb_seed['lb_id']}/lb-profile")
            math = next(s for s in r.json()["subjects"] if s["name"] == "Mathematik_lbp")
            assert math["topics"] == []

            with Session(sqlite_engine) as ses:
                cc = ses.query(ClassCompetence).filter_by(
                    class_id=lb_seed["cls_id"], competence_id=lb_seed["c1_id"]
                ).first()
                cc.selected = True
                ses.commit()

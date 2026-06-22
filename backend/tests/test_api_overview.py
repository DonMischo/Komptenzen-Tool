"""test_api_overview.py — HTTP-layer tests for routers/overview.py.

Covers:
- GET /api/overview/competences   — per-subject selection counts
- GET /api/overview/grades        — per-student grade/niveau status
- GET /api/overview/custom-competences — list + update
- PUT /api/overview/custom-competences/{id}
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from db_schema import (
    Base, SchoolClass, Student, Subject, Topic, Competence,
    ClassCompetence, CustomCompetence,
)


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def ov_seed(client, sqlite_engine):
    """Seed class 7a_ov with one student, subject Deutsch_ov with one topic and one competence."""
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = SchoolClass(name="7a_ov")
        ses.add(cls)
        ses.flush()

        subj = Subject(name="Deutsch_ov")
        ses.add(subj)
        ses.flush()

        t1 = Topic(name="Lesen_ov", block="7", subject=subj)
        ses.add(t1)
        ses.flush()

        c1 = Competence(text="Kann lesen", topic=t1)
        ses.add(c1)
        ses.flush()

        ses.add(ClassCompetence(class_id=cls.id, competence_id=c1.id, selected=True))

        anna = Student(
            last_name="Braun", first_name="Anna",
            birthday=date(2012, 4, 1), school_class=cls,
        )
        ses.add(anna)
        ses.commit()
        ids = {
            "cls_id": cls.id, "subj_id": subj.id, "t1_id": t1.id,
            "c1_id": c1.id, "anna_id": anna.id,
        }

    yield ids

    with Session(sqlite_engine) as ses:
        ses.query(Student).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(ClassCompetence).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(CustomCompetence).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(Competence).filter_by(topic_id=ids["t1_id"]).delete()
        ses.query(Topic).filter_by(id=ids["t1_id"]).delete()
        ses.query(Subject).filter_by(id=ids["subj_id"]).delete()
        ses.query(SchoolClass).filter_by(id=ids["cls_id"]).delete()
        ses.commit()


# ---------------------------------------------------------------------------
# GET /api/overview/competences
# ---------------------------------------------------------------------------

class TestOverviewCompetences:
    def test_returns_200(self, client):
        r = client.get("/api/overview/competences", params={"class_name": "7a_ov"})
        assert r.status_code == 200

    def test_response_has_subjects_key(self, client):
        r = client.get("/api/overview/competences", params={"class_name": "7a_ov"})
        assert "subjects" in r.json()

    def test_returns_list_of_subjects(self, client):
        r = client.get("/api/overview/competences", params={"class_name": "7a_ov"})
        assert isinstance(r.json()["subjects"], list)

    def test_each_item_has_required_fields(self, client):
        r = client.get("/api/overview/competences", params={"class_name": "7a_ov"})
        for item in r.json()["subjects"]:
            assert "name" in item
            assert "selected_count" in item
            assert "total_count" in item
            assert "custom_count" in item

    def test_unknown_class_returns_empty_counts(self, client):
        r = client.get("/api/overview/competences", params={"class_name": "99z_ov_unused"})
        assert r.status_code == 200
        for item in r.json()["subjects"]:
            assert item["selected_count"] == 0


# ---------------------------------------------------------------------------
# GET /api/overview/grades
# ---------------------------------------------------------------------------

class TestOverviewGrades:
    def test_returns_200(self, client):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        assert r.status_code == 200

    def test_unknown_class_returns_empty_students(self, client):
        r = client.get("/api/overview/grades", params={"class_name": "99z_ov_unused"})
        assert r.json()["students"] == []

    def test_response_has_required_keys(self, client, ov_seed):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        data = r.json()
        for key in ("students", "relevant_subjects", "wahlpflicht_subjects",
                    "wp_no_niveau", "no_niveau_subjects"):
            assert key in data

    def test_contains_seeded_student(self, client, ov_seed):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        students = r.json()["students"]
        names = [s["last_name"] for s in students]
        assert "Braun" in names

    def test_student_has_required_fields(self, client, ov_seed):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        stu = r.json()["students"][0]
        for field in ("student_id", "last_name", "first_name", "lb", "gb",
                      "has_report_text", "subjects", "wahlpflicht"):
            assert field in stu

    def test_report_text_false_by_default(self, client, ov_seed):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        assert r.json()["students"][0]["has_report_text"] is False

    def test_report_text_true_when_set(self, client, ov_seed, sqlite_engine):
        with Session(sqlite_engine) as ses:
            anna = ses.get(Student, ov_seed["anna_id"])
            anna.report_text = "Sehr gute Leistungen."
            ses.commit()
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        assert r.json()["students"][0]["has_report_text"] is True

    def test_relevant_subjects_list(self, client, ov_seed):
        r = client.get("/api/overview/grades", params={"class_name": "7a_ov"})
        relevant = r.json()["relevant_subjects"]
        assert isinstance(relevant, list)
        assert len(relevant) > 0


# ---------------------------------------------------------------------------
# GET /api/overview/custom-competences
# ---------------------------------------------------------------------------

class TestOverviewCustomCompetences:
    def test_returns_200(self, client):
        r = client.get("/api/overview/custom-competences", params={"class_name": "7a_ov"})
        assert r.status_code == 200

    def test_returns_list(self, client):
        r = client.get("/api/overview/custom-competences", params={"class_name": "7a_ov"})
        assert isinstance(r.json(), list)

    def test_empty_when_no_customs(self, client, ov_seed):
        r = client.get("/api/overview/custom-competences", params={"class_name": "7a_ov"})
        assert r.json() == []

    def test_unknown_class_returns_empty(self, client):
        r = client.get("/api/overview/custom-competences", params={"class_name": "99z_ov_unused"})
        assert r.json() == []


# ---------------------------------------------------------------------------
# PUT /api/overview/custom-competences/{comp_id}
# ---------------------------------------------------------------------------

class TestUpdateCustomCompetence:
    @pytest.fixture
    def custom_comp(self, ov_seed, sqlite_engine):
        with Session(sqlite_engine) as ses:
            cc = CustomCompetence(
                class_id=ov_seed["cls_id"],
                topic_id=ov_seed["t1_id"],
                text="Original",
            )
            ses.add(cc)
            ses.commit()
            cc_id = cc.id
        yield cc_id
        with Session(sqlite_engine) as ses:
            ses.query(CustomCompetence).filter_by(id=cc_id).delete()
            ses.commit()

    def test_update_returns_200(self, client, custom_comp):
        r = client.put(f"/api/overview/custom-competences/{custom_comp}",
                       json={"text": "Aktualisiert"})
        assert r.status_code == 200

    def test_update_text(self, client, custom_comp):
        client.put(f"/api/overview/custom-competences/{custom_comp}",
                   json={"text": "Neue Kompetenz"})
        r = client.put(f"/api/overview/custom-competences/{custom_comp}",
                       json={"text": "Nochmal"})
        assert r.json()["text"] == "Nochmal"

    def test_update_strips_whitespace(self, client, custom_comp):
        r = client.put(f"/api/overview/custom-competences/{custom_comp}",
                       json={"text": "  Leerzeichen  "})
        assert r.json()["text"] == "Leerzeichen"

    def test_update_unknown_returns_404(self, client):
        r = client.put("/api/overview/custom-competences/999999",
                       json={"text": "Ghost"})
        assert r.status_code == 404

    def test_response_has_id_and_text(self, client, custom_comp):
        r = client.put(f"/api/overview/custom-competences/{custom_comp}",
                       json={"text": "Test"})
        assert "id" in r.json()
        assert "text" in r.json()

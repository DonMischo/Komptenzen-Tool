"""test_api_grades.py — HTTP-layer tests for routers/students.py (grade matrix).

Covers GET /api/students/matrix and POST /api/students/matrix,
including the Lebenspraxis special path.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from db_schema import (
    Base, SchoolClass, Student, Subject, Topic, Competence,
    ClassCompetence, StudentSubject,
)


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def grade_seed(client, sqlite_engine):
    """Seed class 6a with two students; subject Physik_g with one topic and one competence."""
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = SchoolClass(name="6a_g")
        ses.add(cls)
        ses.flush()

        subj = Subject(name="Physik_g")
        ses.add(subj)
        ses.flush()

        t1 = Topic(name="Mechanik_g", block="5/6", subject=subj)
        ses.add(t1)
        ses.flush()

        c1 = Competence(text="Kraft verstehen", topic=t1)
        ses.add(c1)
        ses.flush()

        # Select c1 for class 6a_g
        ses.add(ClassCompetence(class_id=cls.id, competence_id=c1.id, selected=True))

        anna = Student(last_name="Meyer", first_name="Anna",
                       birthday=date(2013, 1, 1), school_class=cls)
        bob  = Student(last_name="Wolf", first_name="Bob",
                       birthday=date(2013, 2, 2), school_class=cls)
        ses.add_all([anna, bob])
        ses.commit()
        ids = {
            "cls_id": cls.id, "subj_id": subj.id,
            "t1_id": t1.id, "c1_id": c1.id,
            "anna_id": anna.id, "bob_id": bob.id,
        }

    yield ids

    with Session(sqlite_engine) as ses:
        ses.query(Student).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(ClassCompetence).filter_by(class_id=ids["cls_id"]).delete()
        ses.query(Competence).filter_by(topic_id=ids["t1_id"]).delete()
        ses.query(Topic).filter_by(id=ids["t1_id"]).delete()
        ses.query(Subject).filter_by(id=ids["subj_id"]).delete()
        ses.query(SchoolClass).filter_by(id=ids["cls_id"]).delete()
        ses.commit()


# ---------------------------------------------------------------------------
# GET /api/students/matrix
# ---------------------------------------------------------------------------

class TestGetMatrix:
    def test_empty_class_returns_empty(self, client):
        r = client.get("/api/students/matrix", params={
            "class_name": "99z_empty", "subject": "Mathematik",
        })
        assert r.status_code == 200
        assert r.json()["columns"] == []
        assert r.json()["rows"] == []

    def test_returns_200(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        assert r.status_code == 200

    def test_response_shape(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        data = r.json()
        assert "columns" in data
        assert "rows" in data

    def test_row_count_matches_students(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        assert len(r.json()["rows"]) == 2

    def test_columns_count_matches_topics(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        assert len(r.json()["columns"]) == 1

    def test_row_fields(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        row = r.json()["rows"][0]
        for field in ("student_id", "last_name", "first_name", "niveau", "grades", "student_type"):
            assert field in row

    def test_no_topics_selected_returns_empty(self, client, grade_seed, sqlite_engine):
        # Remove the ClassCompetence selection temporarily
        with Session(sqlite_engine) as ses:
            ses.query(ClassCompetence).filter_by(class_id=grade_seed["cls_id"]).delete()
            ses.commit()
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        assert r.json()["columns"] == []
        assert r.json()["rows"] == []
        # Re-add for cleanup
        with Session(sqlite_engine) as ses:
            ses.add(ClassCompetence(
                class_id=grade_seed["cls_id"],
                competence_id=grade_seed["c1_id"],
                selected=True,
            ))
            ses.commit()

    def test_student_type_normal_by_default(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        for row in r.json()["rows"]:
            assert row["student_type"] == "normal"

    def test_lb_student_type(self, client, grade_seed, sqlite_engine):
        with Session(sqlite_engine) as ses:
            anna = ses.get(Student, grade_seed["anna_id"])
            anna.lb = True
            ses.commit()
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        anna_row = next(row for row in r.json()["rows"] if row["first_name"] == "Anna")
        assert anna_row["student_type"] == "lb"

    def test_column_label_excludes_subject_name(self, client, grade_seed):
        """Column headers must be 'Topic (Block)', not 'Subject – Topic (Block)'."""
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        label = r.json()["columns"][0]["label"]
        assert "Physik_g" not in label
        assert "Mechanik_g" in label
        assert "(" in label  # block suffix present

    def test_column_label_contains_block(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        label = r.json()["columns"][0]["label"]
        assert "5/6" in label


# ---------------------------------------------------------------------------
# GET /api/students/matrix — Lebenspraxis path
# ---------------------------------------------------------------------------

class TestGetMatrixLebenspraxis:
    def test_no_lb_students_returns_empty(self, client, grade_seed):
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Lebenspraxis",
        })
        assert r.status_code == 200
        assert r.json()["rows"] == []
        assert r.json()["columns"] == []

    def test_lb_student_appears(self, client, grade_seed, sqlite_engine):
        with Session(sqlite_engine) as ses:
            anna = ses.get(Student, grade_seed["anna_id"])
            anna.lb = True
            ses.commit()
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Lebenspraxis",
        })
        assert len(r.json()["rows"]) == 1
        assert r.json()["rows"][0]["first_name"] == "Anna"
        assert r.json()["rows"][0]["student_type"] == "lb"


# ---------------------------------------------------------------------------
# POST /api/students/matrix
# ---------------------------------------------------------------------------

class TestSaveMatrix:
    def _matrix_payload(self, grade_seed, grades: dict | None = None) -> dict:
        topic_id = str(grade_seed["t1_id"])
        return {
            "class_name": "6a_g",
            "subject": "Physik_g",
            "rows": [
                {
                    "student_id": grade_seed["anna_id"],
                    "last_name": "Meyer",
                    "first_name": "Anna",
                    "niveau": "B1",
                    "grades": {topic_id: (grades or {}).get("anna", "")},
                    "student_type": "normal",
                },
                {
                    "student_id": grade_seed["bob_id"],
                    "last_name": "Wolf",
                    "first_name": "Bob",
                    "niveau": "",
                    "grades": {topic_id: (grades or {}).get("bob", "")},
                    "student_type": "normal",
                },
            ],
        }

    def test_returns_200(self, client, grade_seed):
        r = client.post("/api/students/matrix", json=self._matrix_payload(grade_seed))
        assert r.status_code == 200

    def test_returns_ok(self, client, grade_seed):
        r = client.post("/api/students/matrix", json=self._matrix_payload(grade_seed))
        assert r.json()["ok"] is True

    def test_saves_grades(self, client, grade_seed):
        payload = self._matrix_payload(grade_seed, grades={"anna": "3"})
        client.post("/api/students/matrix", json=payload)
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        anna_row = next(row for row in r.json()["rows"] if row["first_name"] == "Anna")
        topic_id = str(grade_seed["t1_id"])
        assert anna_row["grades"][topic_id] == "3"

    def test_saves_niveau(self, client, grade_seed):
        client.post("/api/students/matrix", json=self._matrix_payload(grade_seed))
        r = client.get("/api/students/matrix", params={
            "class_name": "6a_g", "subject": "Physik_g",
        })
        anna_row = next(row for row in r.json()["rows"] if row["first_name"] == "Anna")
        assert anna_row["niveau"] == "B1"

    def test_no_topics_returns_404(self, client, grade_seed):
        payload = {
            "class_name": "6a_g",
            "subject": "Nichtexistent_g",
            "rows": [],
        }
        r = client.post("/api/students/matrix", json=payload)
        assert r.status_code == 404

    def test_lebenspraxis_save_returns_ok(self, client, grade_seed, sqlite_engine):
        with Session(sqlite_engine) as ses:
            ses.add(Subject(name="Lebenspraxis"))
            ses.commit()
        payload = {
            "class_name": "6a_g",
            "subject": "Lebenspraxis",
            "rows": [{
                "student_id": grade_seed["anna_id"],
                "last_name": "Meyer",
                "first_name": "Anna",
                "niveau": "LB-Text",
                "grades": {},
                "student_type": "lb",
            }],
        }
        r = client.post("/api/students/matrix", json=payload)
        assert r.status_code == 200
        assert r.json()["ok"] is True

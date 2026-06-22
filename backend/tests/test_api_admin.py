"""test_api_admin.py — HTTP-layer tests for routers/admin.py.

Covers: student listing, user management (list/create/delete),
competence-sync diff/apply, export prepare/progress/cancel.
Export compile is mocked — we only verify the HTTP layer.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from db_schema import Base, SchoolClass, Student


# ---------------------------------------------------------------------------
# Seed fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_student(client, sqlite_engine):
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = ses.query(SchoolClass).filter_by(name="10a").first()
        if not cls:
            cls = SchoolClass(name="10a")
            ses.add(cls)
            ses.flush()
        stu = Student(
            last_name="Bauer",
            first_name="Lisa",
            birthday=date(2011, 3, 15),
            school_class=cls,
        )
        ses.add(stu)
        ses.commit()
        yield stu.id
    with Session(sqlite_engine) as ses:
        ses.query(Student).filter_by(last_name="Bauer", first_name="Lisa").delete()
        ses.commit()


# ---------------------------------------------------------------------------
# GET /api/admin/students
# ---------------------------------------------------------------------------

class TestAdminListStudents:
    def test_returns_200(self, client, admin_student):
        r = client.get("/api/admin/students", params={"class_name": "10a"})
        assert r.status_code == 200

    def test_returns_list(self, client, admin_student):
        r = client.get("/api/admin/students", params={"class_name": "10a"})
        assert isinstance(r.json(), list)

    def test_contains_seeded_student(self, client, admin_student):
        r = client.get("/api/admin/students", params={"class_name": "10a"})
        names = [s["last_name"] for s in r.json()]
        assert "Bauer" in names

    def test_response_has_required_fields(self, client, admin_student):
        r = client.get("/api/admin/students", params={"class_name": "10a"})
        item = r.json()[0]
        assert "id" in item
        assert "last_name" in item
        assert "first_name" in item
        assert "class_name" in item

    def test_empty_class_returns_empty_list(self, client):
        r = client.get("/api/admin/students", params={"class_name": "99z_unused"})
        assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/admin/users
# ---------------------------------------------------------------------------

class TestAdminListUsers:
    def test_returns_200(self, client):
        with patch("auth_pure.list_users", return_value=[
            {"id": 1, "username": "alice", "role": "admin"},
        ]):
            r = client.get("/api/admin/users")
        assert r.status_code == 200

    def test_returns_list(self, client):
        with patch("auth_pure.list_users", return_value=[]):
            r = client.get("/api/admin/users")
        assert isinstance(r.json(), list)

    def test_contains_user_data(self, client):
        with patch("auth_pure.list_users", return_value=[
            {"id": 1, "username": "bob", "role": "lehrer"},
        ]):
            r = client.get("/api/admin/users")
        assert r.json()[0]["username"] == "bob"
        assert r.json()[0]["role"] == "lehrer"


# ---------------------------------------------------------------------------
# POST /api/admin/users
# ---------------------------------------------------------------------------

class TestAdminCreateUser:
    def test_returns_201(self, client):
        with patch("auth_pure.create_user"):
            r = client.post("/api/admin/users", json={
                "username": "newteacher", "password": "pass123", "role": "lehrer",
            })
        assert r.status_code == 201

    def test_returns_ok(self, client):
        with patch("auth_pure.create_user"):
            r = client.post("/api/admin/users", json={
                "username": "newteacher", "password": "pass123", "role": "lehrer",
            })
        assert r.json()["ok"] is True

    def test_duplicate_returns_400(self, client):
        from sqlalchemy.exc import IntegrityError
        with patch("auth_pure.create_user", side_effect=IntegrityError("", "", None)):
            r = client.post("/api/admin/users", json={
                "username": "dup", "password": "pass123", "role": "admin",
            })
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{username}
# ---------------------------------------------------------------------------

class TestAdminDeleteUser:
    def test_delete_existing_returns_200(self, client):
        with patch("auth_pure.delete_user", return_value=True):
            r = client.delete("/api/admin/users/oldteacher")
        assert r.status_code == 200

    def test_delete_nonexistent_returns_404(self, client):
        with patch("auth_pure.delete_user", return_value=False):
            r = client.delete("/api/admin/users/ghost")
        assert r.status_code == 404

    def test_cannot_delete_self(self, client):
        # conftest overrides get_current_admin to return "testadmin"
        r = client.delete("/api/admin/users/testadmin")
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/admin/competence-sync/diff
# ---------------------------------------------------------------------------

class TestCompetenceSyncDiff:
    def _mock_result(self):
        m = MagicMock()
        m.subjects_added = []
        m.subjects_removed = []
        m.topics_added = []
        m.topics_removed = []
        m.competences_added = 0
        m.competences_removed = 0
        m.class_selections_lost = 0
        m.grades_lost = 0
        m.has_changes = False
        m.has_removals = False
        return m

    def test_returns_200(self, client):
        with patch("routers.admin.compute_diff", return_value=self._mock_result()):
            r = client.get("/api/admin/competence-sync/diff")
        assert r.status_code == 200

    def test_response_has_required_keys(self, client):
        with patch("routers.admin.compute_diff", return_value=self._mock_result()):
            r = client.get("/api/admin/competence-sync/diff")
        data = r.json()
        for key in ("subjects_added", "subjects_removed", "topics_added",
                    "topics_removed", "competences_added", "has_changes"):
            assert key in data

    def test_has_changes_false_when_no_diff(self, client):
        with patch("routers.admin.compute_diff", return_value=self._mock_result()):
            r = client.get("/api/admin/competence-sync/diff")
        assert r.json()["has_changes"] is False


# ---------------------------------------------------------------------------
# POST /api/admin/competence-sync/apply
# ---------------------------------------------------------------------------

class TestCompetenceSyncApply:
    def _mock_result(self):
        m = MagicMock()
        m.subjects_added = ["Physik"]
        m.subjects_removed = []
        m.topics_added = ["Mechanik"]
        m.topics_removed = []
        m.competences_added = 5
        m.competences_removed = 0
        m.class_selections_lost = 0
        m.grades_lost = 0
        m.has_changes = True
        m.has_removals = False
        return m

    def test_returns_200(self, client):
        with patch("routers.admin.apply_full_sync", return_value=self._mock_result()):
            r = client.post("/api/admin/competence-sync/apply")
        assert r.status_code == 200

    def test_returns_added_subjects(self, client):
        with patch("routers.admin.apply_full_sync", return_value=self._mock_result()):
            r = client.post("/api/admin/competence-sync/apply")
        assert "Physik" in r.json()["subjects_added"]


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

class TestExportEndpoints:
    def test_prepare_no_students_returns_400(self, client):
        r = client.post("/api/admin/export/prepare", json={
            "student_ids": [], "classroom": "10a",
        })
        assert r.status_code == 400

    def test_progress_unknown_job_returns_404(self, client):
        r = client.get("/api/admin/export/progress/nonexistent-job-id")
        assert r.status_code == 404

    def test_cancel_unknown_job_returns_200(self, client):
        r = client.post("/api/admin/export/cancel/nonexistent-job-id")
        assert r.status_code == 200

    def test_prepare_returns_job_id(self, client, admin_student):
        with patch("routers.admin.prepare_export", return_value=("/tmp/cl", ["student1"])):
            r = client.post("/api/admin/export/prepare", json={
                "student_ids": [admin_student], "classroom": "10a",
            })
        assert r.status_code == 200
        assert "job_id" in r.json()
        assert "total" in r.json()

    def test_progress_known_job(self, client, admin_student):
        with patch("routers.admin.prepare_export", return_value=("/tmp/cl", ["student1"])):
            prep = client.post("/api/admin/export/prepare", json={
                "student_ids": [admin_student], "classroom": "10a",
            })
        job_id = prep.json()["job_id"]
        r = client.get(f"/api/admin/export/progress/{job_id}")
        assert r.status_code == 200
        assert "done" in r.json()
        assert "results" in r.json()

    def test_cancel_known_job(self, client, admin_student):
        with patch("routers.admin.prepare_export", return_value=("/tmp/cl", ["student1"])):
            prep = client.post("/api/admin/export/prepare", json={
                "student_ids": [admin_student], "classroom": "10a",
            })
        job_id = prep.json()["job_id"]
        r = client.post(f"/api/admin/export/cancel/{job_id}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

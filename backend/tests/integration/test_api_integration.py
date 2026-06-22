"""Integration tests for the FastAPI application against real PostgreSQL.

Uses TestClient with a real SQLAlchemy session on reports_2025_26_ej.
Auth dependencies are still overridden — we test the data layer, not auth.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch

from integration_helpers import requires_pg, REAL_DB_URL


@pytest.fixture(scope="module")
def live_client(real_db_engine):
    from deps import get_db, get_current_user, get_current_admin

    def _real_db():
        with Session(real_db_engine) as ses:
            yield ses

    def _user():
        return "testadmin"

    with (
        patch("auth_pure._ensure_table", return_value=None),
        patch("migrations.run_migrations_all_report_dbs", return_value=None),
    ):
        from main import app
        app.dependency_overrides[get_db]           = _real_db
        app.dependency_overrides[get_current_user]  = _user
        app.dependency_overrides[get_current_admin] = _user
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
        app.dependency_overrides.clear()


@requires_pg
class TestHealthAndSetup:
    def test_health(self, live_client):
        r = live_client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_schema_status(self, live_client):
        r = live_client.get("/api/setup/schema-status")
        assert r.status_code == 200
        data = r.json()
        assert "schema_ready" in data
        assert data["schema_ready"] is True
        assert "student_count" in data

    def test_list_databases(self, live_client):
        r = live_client.get("/api/databases")
        assert r.status_code == 200
        assert "databases" in r.json()
        assert "reports_2025_26_ej" in r.json()["databases"]


@requires_pg
class TestClassesAndStudents:
    def test_list_classes(self, live_client):
        r = live_client.get("/api/classes")
        assert r.status_code == 200
        classes = r.json()["classes"]
        assert isinstance(classes, list)

    def test_list_stammdaten_for_each_class(self, live_client):
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        for cls_name in classes[:3]:   # limit to first 3 to keep test fast
            r = live_client.get("/api/stammdaten", params={"class_name": cls_name})
            assert r.status_code == 200
            assert isinstance(r.json(), list)

    def test_admin_student_list(self, live_client):
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        r = live_client.get("/api/admin/students", params={"class_name": classes[0]})
        assert r.status_code == 200

    def test_report_text_roundtrip(self, live_client, real_db_engine):
        """Read a student, update their report_text, verify it's persisted."""
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        students = live_client.get(
            "/api/stammdaten", params={"class_name": classes[0]}
        ).json()
        if not students:
            pytest.skip("No students in first class")

        stu_id = students[0]["id"]
        original = students[0]["report_text"]

        # Write a sentinel
        live_client.put(f"/api/stammdaten/{stu_id}/report-text",
                        json={"report_text": "__integration_test_sentinel__"})
        r = live_client.get(f"/api/stammdaten/{stu_id}/report-text")
        assert r.json()["report_text"] == "__integration_test_sentinel__"

        # Restore original
        live_client.put(f"/api/stammdaten/{stu_id}/report-text",
                        json={"report_text": original})


@requires_pg
class TestSubjectsAndCompetences:
    def test_list_subjects(self, live_client):
        r = live_client.get("/api/subjects")
        assert r.status_code == 200
        subjects = r.json()["subjects"]
        assert isinstance(subjects, list)
        assert len(subjects) > 0

    def test_list_blocks_for_mathematik(self, live_client):
        r = live_client.get("/api/subjects/Mathematik/blocks")
        assert r.status_code == 200
        blocks = r.json()["blocks"]
        assert isinstance(blocks, list)

    def test_competence_sync_diff(self, live_client):
        r = live_client.get("/api/admin/competence-sync/diff")
        assert r.status_code == 200
        data = r.json()
        assert "has_changes" in data
        assert "subjects_added" in data


@requires_pg
class TestOverview:
    def test_overview_competences(self, live_client):
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        r = live_client.get("/api/overview/competences",
                            params={"class_name": classes[0]})
        assert r.status_code == 200
        assert "subjects" in r.json()

    def test_overview_grades(self, live_client):
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        r = live_client.get("/api/overview/grades",
                            params={"class_name": classes[0]})
        assert r.status_code == 200
        data = r.json()
        assert "students" in data
        assert "relevant_subjects" in data

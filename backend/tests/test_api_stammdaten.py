"""test_api_stammdaten.py — HTTP-layer tests for routers/stammdaten.py.

Uses the shared sqlite_engine from conftest. Each test class seeds its own
student and cleans up afterwards to stay isolated.
"""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from db_schema import Base, SchoolClass, Student


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def student(client, sqlite_engine):
    """Create a single student in class 8a, yield the student id, then clean up."""
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        cls = ses.query(SchoolClass).filter_by(name="8a").first()
        if not cls:
            cls = SchoolClass(name="8a")
            ses.add(cls)
            ses.flush()
        stu = Student(
            last_name="Testmann",
            first_name="Karl",
            birthday=date(2012, 5, 10),
            school_class=cls,
        )
        ses.add(stu)
        ses.commit()
        stu_id = stu.id

    yield stu_id

    with Session(sqlite_engine) as ses:
        ses.query(Student).filter_by(id=stu_id).delete()
        ses.commit()


# ---------------------------------------------------------------------------
# GET /api/stammdaten
# ---------------------------------------------------------------------------

class TestListStammdaten:
    def test_returns_200(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        assert r.status_code == 200

    def test_returns_list(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        assert isinstance(r.json(), list)

    def test_contains_seeded_student(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        names = [s["last_name"] for s in r.json()]
        assert "Testmann" in names

    def test_empty_class_returns_empty_list(self, client, sqlite_engine):
        r = client.get("/api/stammdaten", params={"class_name": "9z_unused"})
        assert r.json() == []

    def test_response_has_required_fields(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        item = r.json()[0]
        for field in ("id", "last_name", "first_name", "birthday",
                      "days_absent_excused", "days_absent_unexcused",
                      "remarks", "lb", "gb", "report_text"):
            assert field in item


# ---------------------------------------------------------------------------
# PATCH /api/stammdaten/{id}
# ---------------------------------------------------------------------------

class TestPatchStudent:
    def test_update_returns_200(self, client, student):
        r = client.patch(f"/api/stammdaten/{student}", json={"remarks": "Neuer Kommentar"})
        assert r.status_code == 200

    def test_update_remarks(self, client, student):
        client.patch(f"/api/stammdaten/{student}", json={"remarks": "Sehr fleißig"})
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        updated = next(s for s in r.json() if s["id"] == student)
        assert updated["remarks"] == "Sehr fleißig"

    def test_update_absent_days(self, client, student):
        client.patch(f"/api/stammdaten/{student}", json={"days_absent_excused": 3})
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        updated = next(s for s in r.json() if s["id"] == student)
        assert updated["days_absent_excused"] == 3

    def test_update_lb_flag(self, client, student):
        client.patch(f"/api/stammdaten/{student}", json={"lb": True})
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        updated = next(s for s in r.json() if s["id"] == student)
        assert updated["lb"] is True

    def test_invalid_birthday_returns_400(self, client, student):
        r = client.patch(f"/api/stammdaten/{student}", json={"birthday": "not-a-date"})
        assert r.status_code == 400

    def test_valid_birthday_format(self, client, student):
        r = client.patch(f"/api/stammdaten/{student}", json={"birthday": "15.03.2012"})
        assert r.status_code == 200
        assert r.json()["birthday"] == "15.03.2012"

    def test_unknown_student_returns_404(self, client):
        r = client.patch("/api/stammdaten/999999", json={"remarks": "x"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/stammdaten/batch
# ---------------------------------------------------------------------------

class TestBatchSave:
    def test_batch_returns_200(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        items = r.json()
        r2 = client.post("/api/stammdaten/batch", json=items)
        assert r2.status_code == 200

    def test_batch_returns_updated_count(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        items = r.json()
        r2 = client.post("/api/stammdaten/batch", json=items)
        assert r2.json()["updated"] == len(items)

    def test_batch_updates_absence(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        items = r.json()
        items[0]["days_absent_unexcused"] = 7
        client.post("/api/stammdaten/batch", json=items)
        r2 = client.get("/api/stammdaten", params={"class_name": "8a"})
        assert r2.json()[0]["days_absent_unexcused"] == 7

    def test_batch_empty_list_is_noop(self, client):
        r = client.post("/api/stammdaten/batch", json=[])
        assert r.status_code == 200
        assert r.json()["updated"] == 0

    def test_batch_skips_unknown_ids(self, client, student):
        r = client.get("/api/stammdaten", params={"class_name": "8a"})
        items = r.json()
        items.append({**items[0], "id": 999999})
        r2 = client.post("/api/stammdaten/batch", json=items)
        assert r2.json()["updated"] == len(items) - 1


# ---------------------------------------------------------------------------
# GET/PUT /api/stammdaten/{id}/report-text
# ---------------------------------------------------------------------------

class TestReportText:
    def test_get_report_text_returns_200(self, client, student):
        r = client.get(f"/api/stammdaten/{student}/report-text")
        assert r.status_code == 200

    def test_get_empty_by_default(self, client, student):
        r = client.get(f"/api/stammdaten/{student}/report-text")
        assert r.json()["report_text"] == ""

    def test_put_report_text(self, client, student):
        client.put(f"/api/stammdaten/{student}/report-text",
                   json={"report_text": "Sehr gut gemacht."})
        r = client.get(f"/api/stammdaten/{student}/report-text")
        assert r.json()["report_text"] == "Sehr gut gemacht."

    def test_get_unknown_student_returns_404(self, client):
        r = client.get("/api/stammdaten/999999/report-text")
        assert r.status_code == 404

    def test_put_unknown_student_returns_404(self, client):
        r = client.put("/api/stammdaten/999999/report-text", json={"report_text": "x"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET/PUT /api/stammdaten/{id}/remarks
# ---------------------------------------------------------------------------

class TestRemarks:
    def test_get_remarks_returns_200(self, client, student):
        r = client.get(f"/api/stammdaten/{student}/remarks")
        assert r.status_code == 200

    def test_get_empty_by_default(self, client, student):
        r = client.get(f"/api/stammdaten/{student}/remarks")
        assert r.json()["remarks"] == ""

    def test_put_remarks(self, client, student):
        client.put(f"/api/stammdaten/{student}/remarks", json={"remarks": "Fleißige Schülerin."})
        r = client.get(f"/api/stammdaten/{student}/remarks")
        assert r.json()["remarks"] == "Fleißige Schülerin."

    def test_get_unknown_returns_404(self, client):
        r = client.get("/api/stammdaten/999999/remarks")
        assert r.status_code == 404

    def test_put_unknown_returns_404(self, client):
        r = client.put("/api/stammdaten/999999/remarks", json={"remarks": "x"})
        assert r.status_code == 404

"""test_api_setup.py — API-level tests for the setup router.

All PostgreSQL-specific functions (list_report_dbs, create_report_db,
switch_engine) are mocked so these tests run without a live database.
The DB dependency is served by the SQLite engine from conftest.
"""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from db_schema import Base, SchoolYear, SchoolClass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_DB_NAME = "reports_2025_26_hj"
EJ_DB_NAME    = "reports_2025_26_ej"


def _seed_school_year(sqlite_engine, is_ej: bool = False):
    """Upsert a SchoolYear row so report-day endpoints don't 404."""
    from sqlalchemy.orm import Session
    Base.metadata.create_all(sqlite_engine)
    with Session(sqlite_engine) as ses:
        ses.query(SchoolYear).delete()
        ses.add(SchoolYear(
            name="2025/2026",
            endjahr=is_ej,
            report_day=date(2026, 2, 7),
        ))
        ses.commit()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealth:
    def test_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/databases
# ---------------------------------------------------------------------------

class TestListDatabases:
    def test_returns_list(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]):
            r = client.get("/api/databases")
        assert r.status_code == 200
        data = r.json()
        assert data["databases"] == [VALID_DB_NAME]

    def test_empty_when_no_dbs(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.get("/api/databases")
        assert r.status_code == 200
        assert r.json()["databases"] == []

    def test_current_db_from_header(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]):
            r = client.get(
                "/api/databases",
                headers={"x-active-db": VALID_DB_NAME},
            )
        assert r.json()["current"] == VALID_DB_NAME


# ---------------------------------------------------------------------------
# POST /api/databases (create)
# ---------------------------------------------------------------------------

class TestCreateDatabase:
    def test_invalid_name_rejected(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.post("/api/databases", json={"name": "bad_name"})
        assert r.status_code == 400

    def test_invalid_name_missing_prefix(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.post("/api/databases", json={"name": "2025_26_hj"})
        assert r.status_code == 400

    def test_valid_hj_name_accepted(self, client, sqlite_engine):
        with (
            patch("routers.setup.list_report_dbs", return_value=[]),
            patch("routers.setup.create_report_db", return_value=None),
            patch("routers.setup.switch_engine", return_value=None),
            patch("routers.setup.init_db", return_value=None),
            patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]),
        ):
            r = client.post("/api/databases", json={"name": VALID_DB_NAME})
        assert r.status_code == 200

    def test_valid_ej_name_accepted(self, client):
        with (
            patch("routers.setup.list_report_dbs", return_value=[]),
            patch("routers.setup.create_report_db", return_value=None),
            patch("routers.setup.switch_engine", return_value=None),
            patch("routers.setup.init_db", return_value=None),
            patch("routers.setup.list_report_dbs", return_value=[EJ_DB_NAME]),
        ):
            r = client.post("/api/databases", json={"name": EJ_DB_NAME})
        assert r.status_code == 200

    def test_existing_db_not_recreated(self, client):
        """If DB already exists in list, create_report_db must not be called."""
        mock_create = MagicMock()
        with (
            patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]),
            patch("routers.setup.create_report_db", mock_create),
            patch("routers.setup.switch_engine", return_value=None),
            patch("routers.setup.init_db", return_value=None),
        ):
            r = client.post("/api/databases", json={"name": VALID_DB_NAME})
        assert r.status_code == 200
        mock_create.assert_not_called()


# ---------------------------------------------------------------------------
# POST /api/databases/select
# ---------------------------------------------------------------------------

class TestSelectDatabase:
    def test_select_existing_db(self, client):
        with (
            patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]),
            patch("routers.setup.switch_engine", return_value=None),
        ):
            r = client.post("/api/databases/select", json={"name": VALID_DB_NAME})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["db"] == VALID_DB_NAME

    def test_select_nonexistent_db_returns_404(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.post("/api/databases/select", json={"name": VALID_DB_NAME})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/databases/{name}
# ---------------------------------------------------------------------------

class TestDeleteDatabase:
    def test_delete_existing(self, client):
        mock_eng = MagicMock()
        mock_conn = MagicMock()
        mock_eng.connect.return_value.__enter__ = lambda s: mock_conn
        mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
        with (
            patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME]),
            patch("routers.setup._pg_base_url", return_value="postgresql://localhost"),
            patch("sqlalchemy.create_engine", return_value=mock_eng),
        ):
            r = client.delete(f"/api/databases/{VALID_DB_NAME}")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_delete_nonexistent_returns_404(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.delete(f"/api/databases/{VALID_DB_NAME}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/databases/suggest
# ---------------------------------------------------------------------------

class TestSuggestDatabase:
    def test_suggest_hj(self, client):
        with patch("routers.setup.suggest_db_name", return_value=VALID_DB_NAME):
            r = client.get("/api/databases/suggest?term=hj")
        assert r.status_code == 200
        assert r.json()["suggested"] == VALID_DB_NAME

    def test_suggest_ej(self, client):
        with patch("routers.setup.suggest_db_name", return_value=EJ_DB_NAME):
            r = client.get("/api/databases/suggest?term=ej")
        assert r.status_code == 200
        assert r.json()["suggested"] == EJ_DB_NAME


# ---------------------------------------------------------------------------
# GET /api/setup/schema-status
# ---------------------------------------------------------------------------

class TestSchemaStatus:
    def test_schema_not_ready_returns_false(self, client):
        with (
            patch("routers.setup._schema_ready", return_value=False),
            patch("routers.setup.count_students", return_value=0),
        ):
            r = client.get("/api/setup/schema-status")
        assert r.status_code == 200
        assert r.json()["schema_ready"] is False

    def test_schema_ready_returns_true(self, client):
        with (
            patch("routers.setup._schema_ready", return_value=True),
            patch("routers.setup.count_students", return_value=5),
        ):
            r = client.get("/api/setup/schema-status")
        assert r.status_code == 200
        assert r.json()["schema_ready"] is True
        assert r.json()["student_count"] == 5


# ---------------------------------------------------------------------------
# GET /api/setup/report-day
# ---------------------------------------------------------------------------

class TestReportDay:
    def test_get_report_day(self, client, sqlite_engine):
        _seed_school_year(sqlite_engine)
        r = client.get("/api/setup/report-day")
        assert r.status_code == 200
        data = r.json()
        assert "report_day" in data
        assert "school_year" in data
        assert "is_endjahr" in data

    def test_get_report_day_no_entry_returns_404(self, client, sqlite_engine):
        from sqlalchemy.orm import Session
        # Ensure no SchoolYear rows exist for this test
        with Session(sqlite_engine) as ses:
            ses.query(SchoolYear).delete()
            ses.commit()
        r = client.get("/api/setup/report-day")
        assert r.status_code == 404

    def test_set_report_day_valid(self, client, sqlite_engine):
        _seed_school_year(sqlite_engine)
        r = client.put(
            "/api/setup/report-day",
            json={"report_day": "15.06.2026"},
        )
        assert r.status_code == 200
        assert r.json()["report_day"] == "15.06.2026"

    def test_set_report_day_invalid_format(self, client, sqlite_engine):
        _seed_school_year(sqlite_engine)
        r = client.put(
            "/api/setup/report-day",
            json={"report_day": "2026-06-15"},
        )
        assert r.status_code == 400

    def test_report_day_is_endjahr_flag(self, client, sqlite_engine):
        _seed_school_year(sqlite_engine, is_ej=True)
        r = client.get("/api/setup/report-day")
        assert r.status_code == 200
        assert r.json()["is_endjahr"] is True


# ---------------------------------------------------------------------------
# GET /api/public/latest-db
# ---------------------------------------------------------------------------

class TestPublicLatestDb:
    def test_returns_latest_db(self, client):
        # sorted() puts hj before ej (alphabetical), so the last item is hj here.
        # The endpoint does sorted(list_report_dbs())[-1].
        dbs = sorted([VALID_DB_NAME, EJ_DB_NAME])
        expected = dbs[-1]
        with (
            patch("routers.setup.list_report_dbs", return_value=[VALID_DB_NAME, EJ_DB_NAME]),
            patch("routers.setup.switch_engine", return_value=None),
        ):
            r = client.get("/api/public/latest-db")
        assert r.status_code == 200
        assert r.json()["db"] == expected

    def test_returns_null_when_no_dbs(self, client):
        with patch("routers.setup.list_report_dbs", return_value=[]):
            r = client.get("/api/public/latest-db")
        assert r.status_code == 200
        assert r.json()["db"] is None

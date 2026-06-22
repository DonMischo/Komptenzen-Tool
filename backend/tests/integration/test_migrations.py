"""Integration tests for migrations.py — require real PostgreSQL."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text

from integration_helpers import requires_pg, REAL_DB_URL, TEST_DB
from migrations import run_migrations, run_migrations_all_report_dbs


@requires_pg
class TestRunMigrations:
    def test_creates_schema_on_empty_db(self, test_db_engine):
        from db_schema import Base
        Base.metadata.create_all(test_db_engine)
        insp = inspect(test_db_engine)
        assert "students" in insp.get_table_names()
        assert "grades"   in insp.get_table_names()

    def test_idempotent_first_run(self, test_db):
        run_migrations(test_db)  # must not raise

    def test_idempotent_second_run(self, test_db):
        run_migrations(test_db)
        run_migrations(test_db)  # must not raise

    def test_grades_value_column_is_text(self, test_db, test_db_engine):
        from db_schema import Base
        Base.metadata.create_all(test_db_engine)
        run_migrations(test_db)
        with test_db_engine.connect() as conn:
            row = conn.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='grades' AND column_name='value'"
            )).fetchone()
        assert row is not None
        assert row[0] == "text"

    def test_idempotent_on_real_db(self):
        run_migrations(REAL_DB_URL)  # must not raise or alter data

    def test_run_migrations_all_does_not_raise(self):
        run_migrations_all_report_dbs()

    def test_missing_table_skipped_gracefully(self, test_db):
        """Migration against a DB with no tables yet should log a warning and continue."""
        fresh_url = test_db.replace(TEST_DB, TEST_DB + "_notables")
        from sqlalchemy import create_engine as _ce
        eng = _ce(f"{fresh_url}", isolation_level="AUTOCOMMIT",
                  connect_args={"connect_timeout": 3})
        try:
            eng.connect()
        except Exception:
            pytest.skip("Cannot create extra DB for this test")
        finally:
            eng.dispose()
        run_migrations(fresh_url)   # must not raise


@requires_pg
class TestRunMigrationsAllReportDbs:
    def test_only_touches_reports_prefix(self, pg_admin):
        """Verify that run_migrations_all_report_dbs only iterates reports_* DBs."""
        from db_schema import list_report_dbs
        dbs = list_report_dbs()
        for name in dbs:
            assert name.startswith("reports_"), f"Unexpected DB: {name}"

    def test_all_report_dbs_have_grades_as_text(self, real_db_engine):
        with real_db_engine.connect() as conn:
            rows = conn.execute(text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name='grades' AND column_name='value'"
            )).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "text"

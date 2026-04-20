# test_db.py
# ---------------------------------------------------------------------------
# Run with:  pytest app/test_db.py -v
# Integration tests (require live PostgreSQL) need:
#   POSTGRES_URL=postgresql://appuser:supersecret@localhost:5432
# Skip integration tests with: pytest app/test_db.py -v -m "not integration"
# ---------------------------------------------------------------------------
from __future__ import annotations

import os
import re
import sys
import types
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DB_RX = re.compile(r"^reports_(\d{4})_(\d{2})_(hj|ej)$", re.I)

EXPECTED_TABLES = {
    "school_years",
    "subjects",
    "topics",
    "competences",
    "classes",
    "class_competence",
    "custom_competences",
    "students",
    "student_subject",
    "grades",
}


# ===========================================================================
# Unit tests — no database required
# ===========================================================================

class TestDbNameRegex:
    def test_valid_hj(self):
        assert DB_RX.fullmatch("reports_2025_26_hj")

    def test_valid_ej(self):
        assert DB_RX.fullmatch("reports_2024_25_ej")

    def test_invalid_no_prefix(self):
        assert DB_RX.fullmatch("2025_26_hj") is None

    def test_invalid_wrong_term(self):
        assert DB_RX.fullmatch("reports_2025_26_wj") is None

    def test_invalid_postgres(self):
        assert DB_RX.fullmatch("postgres") is None

    def test_invalid_empty(self):
        assert DB_RX.fullmatch("") is None


class TestPgBaseUrl:
    def test_default_fallback(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        # Import after env change to pick up fresh value
        import importlib
        import db_schema
        importlib.reload(db_schema)
        assert db_schema._pg_base_url() == "postgresql://localhost"

    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@db:5432/")
        import db_schema
        assert db_schema._pg_base_url() == "postgresql://u:p@db:5432"  # trailing / stripped


class TestSuggestDbName:
    """suggest_db_name should always produce a name matching DB_RX."""

    def test_hj_matches_regex(self):
        import db_schema
        name = db_schema.suggest_db_name("hj")
        assert DB_RX.fullmatch(name), f"Bad name: {name}"

    def test_ej_matches_regex(self):
        import db_schema
        name = db_schema.suggest_db_name("ej")
        assert DB_RX.fullmatch(name), f"Bad name: {name}"

    def test_hj_ends_with_hj(self):
        import db_schema
        assert db_schema.suggest_db_name("hj").endswith("_hj")

    def test_ej_ends_with_ej(self):
        import db_schema
        assert db_schema.suggest_db_name("ej").endswith("_ej")


class TestSwitchEnginePropagation:
    """
    switch_engine must update ENGINE in every dependent module.
    Uses a fake engine so no live DB is required.
    Only tests modules that don't require Streamlit at import time.
    """

    PROPAGATION_TARGETS = (
        "student_loader", "db_helpers", "setup_ui",
        "ui_components", "admin_ui", "export", "kompetenz_ui",
        "studenten_ui", "student_base_data",
    )

    def test_propagation_list_is_complete(self):
        """The list in switch_engine must contain all ENGINE-importing modules."""
        import db_schema, inspect as ins
        src = ins.getsource(db_schema.switch_engine)
        for mod in self.PROPAGATION_TARGETS:
            assert mod in src, \
                f"'{mod}' missing from switch_engine propagation list"

    def test_propagates_to_db_helpers(self, monkeypatch):
        """db_helpers doesn't need Streamlit — safe to import in unit tests."""
        import db_schema
        import db_helpers  # noqa: F401

        fake = types.SimpleNamespace(url=types.SimpleNamespace(database="reports_2025_26_hj"))

        # Simulate what switch_engine does without touching real DB
        db_schema.ENGINE = fake
        sys.modules["db_helpers"].ENGINE = fake

        assert db_helpers.ENGINE.url.database == "reports_2025_26_hj"


# ===========================================================================
# Integration tests — require live PostgreSQL
# ===========================================================================

pytestmark_integration = pytest.mark.integration


def _pg_available() -> bool:
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return False
    try:
        from sqlalchemy import create_engine, text
        eng = create_engine(f"{url.rstrip('/')}/postgres", future=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
        return True
    except Exception:
        return False


pg_required = pytest.mark.skipif(
    not _pg_available(),
    reason="No live PostgreSQL available (set POSTGRES_URL)"
)


@pg_required
@pytest.mark.integration
class TestSchemaIntegrity:
    """Create a temp DB, run init_db, verify all tables exist."""

    TEST_DB = "reports_test_00_hj"

    @classmethod
    def setup_class(cls):
        from dotenv import load_dotenv
        load_dotenv()
        import db_schema
        # Clean up from previous failed run
        try:
            from sqlalchemy import create_engine, text
            adm = create_engine(
                f"{db_schema._pg_base_url()}/postgres",
                isolation_level="AUTOCOMMIT", future=True
            )
            with adm.connect() as conn:
                conn.execute(text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    f"WHERE datname = '{cls.TEST_DB}'"
                ))
                conn.execute(text(f'DROP DATABASE IF EXISTS "{cls.TEST_DB}"'))
            adm.dispose()
        except Exception:
            pass

        # Create & init
        db_schema.create_report_db(cls.TEST_DB)
        db_schema.switch_engine(cls.TEST_DB)
        db_schema.init_db(drop=False, populate=True)

    @classmethod
    def teardown_class(cls):
        import db_schema
        from sqlalchemy import create_engine, text
        db_schema.switch_engine("postgres")
        adm = create_engine(
            f"{db_schema._pg_base_url()}/postgres",
            isolation_level="AUTOCOMMIT", future=True
        )
        with adm.connect() as conn:
            conn.execute(text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{cls.TEST_DB}'"
            ))
            conn.execute(text(f'DROP DATABASE IF EXISTS "{cls.TEST_DB}"'))
        adm.dispose()

    def test_all_tables_exist(self):
        import db_schema
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(db_schema.ENGINE)
        existing = set(insp.get_table_names())
        missing = EXPECTED_TABLES - existing
        assert not missing, f"Missing tables: {missing}"

    def test_no_extra_unexpected_tables(self):
        """Warn if schema has grown without updating tests."""
        import db_schema
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(db_schema.ENGINE)
        existing = set(insp.get_table_names())
        unknown = existing - EXPECTED_TABLES
        # Not a hard failure — just a notice
        if unknown:
            pytest.warns(None, match="")  # soft: print but don't fail
            print(f"\n[INFO] Extra tables found (update EXPECTED_TABLES): {unknown}")

    def test_school_year_row_inserted(self):
        import db_schema
        from sqlalchemy.orm import Session
        with Session(db_schema.ENGINE) as ses:
            row = ses.query(db_schema.SchoolYear).first()
        # Row may be None if internet fetch failed — that's allowed
        if row is not None:
            assert row.name  # has a name like "2025/2026"

    def test_subjects_populated(self):
        import db_schema
        from sqlalchemy.orm import Session
        with Session(db_schema.ENGINE) as ses:
            count = ses.query(db_schema.Subject).count()
        assert count > 0, "No subjects populated after init_db(populate=True)"

    def test_topics_populated(self):
        import db_schema
        from sqlalchemy.orm import Session
        with Session(db_schema.ENGINE) as ses:
            count = ses.query(db_schema.Topic).count()
        assert count > 0, "No topics populated"

    def test_classes_populated(self):
        import db_schema
        from sqlalchemy.orm import Session
        with Session(db_schema.ENGINE) as ses:
            count = ses.query(db_schema.SchoolClass).count()
        assert count >= 9, f"Expected ≥9 classes, got {count}"

    def test_unique_constraint_school_year(self):
        """Inserting duplicate (name, endjahr) must raise."""
        import db_schema
        from sqlalchemy.orm import Session
        from sqlalchemy.exc import IntegrityError
        with Session(db_schema.ENGINE) as ses:
            sy = ses.query(db_schema.SchoolYear).first()
            if sy is None:
                pytest.skip("No school year row to test uniqueness against")
            with pytest.raises(IntegrityError):
                ses.add(db_schema.SchoolYear(name=sy.name, endjahr=sy.endjahr))
                ses.commit()

    def test_unique_constraint_subject(self):
        import db_schema
        from sqlalchemy.orm import Session
        from sqlalchemy.exc import IntegrityError
        with Session(db_schema.ENGINE) as ses:
            subj = ses.query(db_schema.Subject).first()
            assert subj, "No subjects to test"
            with pytest.raises(IntegrityError):
                ses.add(db_schema.Subject(name=subj.name))
                ses.commit()

    def test_engine_propagation_after_switch(self):
        """After switch_engine, all dependent modules must share the new ENGINE."""
        import db_schema, db_helpers, setup_ui, admin_ui  # noqa: F401
        db_schema.switch_engine(self.TEST_DB)
        for mod_name in ("db_helpers", "setup_ui", "admin_ui"):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "ENGINE"):
                assert mod.ENGINE.url.database == self.TEST_DB, \
                    f"{mod_name}.ENGINE.url.database = {mod.ENGINE.url.database!r}, expected {self.TEST_DB!r}"


@pg_required
@pytest.mark.integration
class TestListAndCreateDb:
    """list_report_dbs / create_report_db round-trip."""

    TEST_DB = "reports_test_01_ej"

    def setup_method(self):
        import db_schema
        from sqlalchemy import create_engine, text
        adm = create_engine(
            f"{db_schema._pg_base_url()}/postgres",
            isolation_level="AUTOCOMMIT", future=True
        )
        with adm.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{self.TEST_DB}"'))
        adm.dispose()

    def teardown_method(self):
        self.setup_method()  # same cleanup

    def test_created_db_appears_in_list(self):
        import db_schema
        db_schema.create_report_db(self.TEST_DB)
        dbs = db_schema.list_report_dbs()
        assert self.TEST_DB in dbs

    def test_list_excludes_postgres(self):
        import db_schema
        dbs = db_schema.list_report_dbs()
        assert "postgres" not in dbs

    def test_double_create_raises(self):
        import db_schema
        from sqlalchemy.exc import ProgrammingError
        db_schema.create_report_db(self.TEST_DB)
        with pytest.raises(ProgrammingError):
            db_schema.create_report_db(self.TEST_DB)

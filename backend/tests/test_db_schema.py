"""test_db_schema.py — unit tests for db_schema.py.

Covers:
- DB name suggestion
- Schema creation (init_db) with SQLite
- populate_from_dict: initial population, idempotency
- ensure_default_classes: creation, idempotency
- switch_engine: no-op when same DB, module propagation
- list_report_dbs / create_report_db: tested via mocking
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock, patch, call

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import db_schema
from db_schema import (
    Base,
    Subject, Topic, Competence, SchoolClass, SchoolYear,
    DEFAULT_CLASSES,
    ensure_default_classes,
    init_db,
    populate_from_dict,
    suggest_db_name,
    switch_engine,
    list_report_dbs,
    create_report_db,
    _pg_base_url,
    _make_engine,
)
from tests.conftest import MINIMAL_COMPETENCES, MINIMAL_SUBJECTS


# ---------------------------------------------------------------------------
# suggest_db_name
# ---------------------------------------------------------------------------

class TestSuggestDbName:
    def test_hj_format(self):
        name = suggest_db_name("hj")
        assert re.match(r"^reports_\d{4}_\d{2}_hj$", name), name

    def test_ej_format(self):
        name = suggest_db_name("ej")
        assert re.match(r"^reports_\d{4}_\d{2}_ej$", name), name

    def test_year_parts_consistent(self):
        name = suggest_db_name("hj")
        # e.g. reports_2025_26_hj — the short year is last 2 digits of full year + 1
        _, y1, y2, _ = name.split("_")
        assert int(y2) == (int(y1) + 1) % 100


# ---------------------------------------------------------------------------
# _pg_base_url
# ---------------------------------------------------------------------------

class TestPgBaseUrl:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("POSTGRES_URL", raising=False)
        url = _pg_base_url()
        assert url == "postgresql://localhost"

    def test_trailing_slash_stripped(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pw@db:5432/")
        url = _pg_base_url()
        assert not url.endswith("/")

    def test_custom_url(self, monkeypatch):
        monkeypatch.setenv("POSTGRES_URL", "postgresql://u:p@host:5433")
        url = _pg_base_url()
        assert url == "postgresql://u:p@host:5433"


# ---------------------------------------------------------------------------
# populate_from_dict
# ---------------------------------------------------------------------------

class TestPopulateFromDict:
    def test_creates_subjects(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            subjects = ses.query(Subject).all()
            names = {s.name for s in subjects}
        assert "Mathematik" in names
        assert "Deutsch" in names

    def test_creates_topics(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            topics = ses.query(Topic).all()
            topic_names = {t.name for t in topics}
        assert "Zahlen und Operationen" in topic_names
        assert "Geometrie" in topic_names
        assert "Algebra" in topic_names
        assert "Lesen" in topic_names

    def test_creates_competences(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            comps = ses.query(Competence).all()
            texts = {c.text for c in comps}
        assert "Kann natürliche Zahlen lesen und schreiben" in texts
        assert "Löst lineare Gleichungen" in texts

    def test_topic_linked_to_correct_subject(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            algebra = ses.query(Topic).filter_by(name="Algebra").first()
            assert algebra is not None
            assert algebra.subject.name == "Mathematik"
            assert algebra.block == "7/8"

    def test_idempotent(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            count_after_first = ses.query(Competence).count()
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            count_after_second = ses.query(Competence).count()
        assert count_after_first == count_after_second

    def test_competence_count_matches_dict(self, fresh_engine):
        Base.metadata.create_all(fresh_engine)
        expected = sum(
            len(comps)
            for blocks in MINIMAL_COMPETENCES.values()
            for topics in blocks.values()
            for comps in topics.values()
        )
        with Session(fresh_engine) as ses:
            populate_from_dict(MINIMAL_COMPETENCES, ses)
            actual = ses.query(Competence).count()
        assert actual == expected


# ---------------------------------------------------------------------------
# ensure_default_classes
# ---------------------------------------------------------------------------

class TestEnsureDefaultClasses:
    def test_creates_all_default_classes(self, fresh_engine, monkeypatch):
        Base.metadata.create_all(fresh_engine)
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        ensure_default_classes()
        with Session(fresh_engine) as ses:
            names = {c.name for c in ses.query(SchoolClass).all()}
        for expected in DEFAULT_CLASSES:
            assert expected in names

    def test_count_matches(self, fresh_engine, monkeypatch):
        Base.metadata.create_all(fresh_engine)
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        ensure_default_classes()
        with Session(fresh_engine) as ses:
            count = ses.query(SchoolClass).count()
        assert count == len(DEFAULT_CLASSES)

    def test_idempotent(self, fresh_engine, monkeypatch):
        Base.metadata.create_all(fresh_engine)
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        ensure_default_classes()
        ensure_default_classes()
        with Session(fresh_engine) as ses:
            count = ses.query(SchoolClass).count()
        assert count == len(DEFAULT_CLASSES)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

class TestInitDb:
    def test_creates_tables(self, fresh_engine, monkeypatch):
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        monkeypatch.setattr(db_schema, "ensure_school_year_entry", lambda: None)
        init_db(populate=False)
        inspector = sa_inspect(fresh_engine)
        tables = inspector.get_table_names()
        for expected in ("subjects", "topics", "competences", "students",
                         "grades", "classes", "school_years"):
            assert expected in tables, f"Missing table: {expected}"

    def test_populate_true_fills_subjects(self, fresh_engine, monkeypatch):
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        monkeypatch.setattr(db_schema, "ensure_school_year_entry", lambda: None)
        # Use real COMPETENCES (large but tests real data path)
        init_db(populate=True)
        with Session(fresh_engine) as ses:
            count = ses.query(Subject).count()
        assert count > 0

    def test_drop_true_recreates_schema(self, fresh_engine, monkeypatch):
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        monkeypatch.setattr(db_schema, "ensure_school_year_entry", lambda: None)
        # First init
        init_db(populate=False)
        # Add a class manually
        with Session(fresh_engine) as ses:
            ses.add(SchoolClass(name="__test__"))
            ses.commit()
        # Drop + reinit — custom class should be gone
        init_db(drop=True, populate=False)
        with Session(fresh_engine) as ses:
            cls = ses.query(SchoolClass).filter_by(name="__test__").first()
        assert cls is None

    def test_init_is_safe_to_call_twice(self, fresh_engine, monkeypatch):
        monkeypatch.setattr(db_schema, "ENGINE", fresh_engine)
        monkeypatch.setattr(db_schema, "ensure_school_year_entry", lambda: None)
        init_db(populate=False)
        init_db(populate=False)  # must not raise


# ---------------------------------------------------------------------------
# switch_engine
# ---------------------------------------------------------------------------

class TestSwitchEngine:
    def test_noop_when_same_db(self, monkeypatch):
        original = db_schema.ENGINE
        db_name = str(original.url.database)
        switch_engine(db_name)
        assert db_schema.ENGINE is original

    def test_switches_engine_global(self, monkeypatch):
        new_engine = MagicMock()
        new_engine.url.database = "reports_2025_26_hj"
        new_engine.connect.return_value.__enter__ = lambda s: MagicMock()
        new_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

        with (
            patch.object(db_schema, "_make_engine", return_value=new_engine),
            patch("migrations.run_migrations", return_value=None),
        ):
            old_db = str(db_schema.ENGINE.url.database)
            if old_db != "reports_2025_26_hj":
                switch_engine("reports_2025_26_hj")
                assert db_schema.ENGINE is new_engine

    def test_propagates_to_loaded_modules(self, monkeypatch):
        import types, sys
        fake_mod = types.ModuleType("db_helpers")
        fake_mod.ENGINE = None
        sys.modules["db_helpers"] = fake_mod

        new_engine = MagicMock()
        new_engine.url.database = "reports_2099_00_hj"
        conn_ctx = MagicMock()
        conn_ctx.__enter__ = lambda s: MagicMock()
        conn_ctx.__exit__ = MagicMock(return_value=False)
        new_engine.connect.return_value = conn_ctx

        try:
            with (
                patch.object(db_schema, "_make_engine", return_value=new_engine),
                patch("migrations.run_migrations", return_value=None),
            ):
                switch_engine("reports_2099_00_hj")
            assert fake_mod.ENGINE is new_engine
        finally:
            del sys.modules["db_helpers"]
            # restore ENGINE to something sensible
            db_schema.ENGINE = _make_engine("postgres")

    def test_raises_on_failed_connection(self, monkeypatch):
        bad_engine = MagicMock()
        bad_engine.url.database = "reports_9999_99_hj"
        bad_engine.connect.side_effect = Exception("connection refused")

        with patch.object(db_schema, "_make_engine", return_value=bad_engine):
            with pytest.raises(Exception, match="connection refused"):
                switch_engine("reports_9999_99_hj")


# ---------------------------------------------------------------------------
# list_report_dbs / create_report_db (mock PG admin connection)
# ---------------------------------------------------------------------------

class TestListReportDbs:
    def test_returns_only_reports_dbs(self, monkeypatch):
        mock_rows = [("reports_2024_25_hj",), ("reports_2025_26_ej",)]
        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_rows
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_conn
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_eng = MagicMock()
        mock_eng.connect.return_value = mock_ctx

        with patch("db_schema.create_engine", return_value=mock_eng):
            result = list_report_dbs()

        assert result == ["reports_2024_25_hj", "reports_2025_26_ej"]

    def test_returns_empty_list_when_none(self, monkeypatch):
        mock_conn = MagicMock()
        mock_conn.execute.return_value = []
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_conn
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_eng = MagicMock()
        mock_eng.connect.return_value = mock_ctx

        with patch("db_schema.create_engine", return_value=mock_eng):
            result = list_report_dbs()

        assert result == []


class TestCreateReportDb:
    def test_executes_create_database(self):
        mock_conn = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = lambda s: mock_conn
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_eng = MagicMock()
        mock_eng.connect.return_value = mock_ctx

        with patch("db_schema.create_engine", return_value=mock_eng):
            create_report_db("reports_2025_26_hj")

        executed_sql = mock_conn.execute.call_args[0][0]
        assert "CREATE DATABASE" in str(executed_sql)
        assert "reports_2025_26_hj" in str(executed_sql)

    def test_uses_autocommit_isolation(self):
        mock_eng = MagicMock()
        mock_eng.connect.return_value.__enter__ = lambda s: MagicMock()
        mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)

        with patch("db_schema.create_engine", return_value=mock_eng) as mock_ce:
            create_report_db("reports_2025_26_hj")

        _, kwargs = mock_ce.call_args
        assert kwargs.get("isolation_level") == "AUTOCOMMIT"

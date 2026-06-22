"""conftest.py — shared fixtures for all backend tests.

Strategy
--------
- SQLite in-memory is used as a drop-in for PostgreSQL models/schema tests.
  SQLite lacks pg_database, AUTOCOMMIT CREATE DATABASE, information_schema
  column type checks — those are mocked wherever they appear.
- FastAPI TestClient with dependency overrides replaces get_db and auth deps.
- The app lifespan (auth_pure._ensure_table, run_migrations_all_report_dbs)
  is mocked so tests don't need a live PostgreSQL.

psycopg2 note
-------------
psycopg2 is only available inside Docker (no Windows binary). We stub it out
at sys.modules level before importing any backend module so SQLAlchemy's
PostgreSQL dialect import doesn't crash. The global ENGINE is immediately
replaced with a SQLite engine in all fixtures that need DB access.
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub psycopg2 only when the real driver is not installed (e.g. on Windows).
# Inside Docker psycopg2 is available — stubbing it would break integration tests.
# ---------------------------------------------------------------------------
try:
    import psycopg2  # noqa: F401 — just checking availability
except ImportError:
    for _mod in ("psycopg2", "psycopg2.extensions", "psycopg2.extras",
                 "psycopg2._psycopg"):
        if _mod not in sys.modules:
            sys.modules[_mod] = MagicMock()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Make sure the backend directory is on sys.path so imports work when pytest
# is run from the project root or from backend/.
_BACKEND = os.path.dirname(os.path.dirname(__file__))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import db_schema
from db_schema import Base
from deps import create_token, get_current_user, get_current_admin, get_db

# ---------------------------------------------------------------------------
# Minimal competence data used by sync/populate tests (avoids loading all
# ~1000 real competences, keeps fixtures fast and deterministic).
# ---------------------------------------------------------------------------

MINIMAL_COMPETENCES: dict = {
    "Mathematik": {
        "5/6": {
            "Zahlen und Operationen": [
                "Kann natürliche Zahlen lesen und schreiben",
                "Kann Grundrechenarten anwenden",
            ],
            "Geometrie": [
                "Erkennt geometrische Grundformen",
            ],
        },
        "7/8": {
            "Algebra": [
                "Löst lineare Gleichungen",
            ],
        },
    },
    "Deutsch": {
        "5/6": {
            "Lesen": [
                "Liest flüssig und sinnverstehend",
            ],
        },
    },
}

MINIMAL_SUBJECTS: list[str] = ["Mathematik", "Deutsch", "Lebenspraxis"]


# ---------------------------------------------------------------------------
# SQLite engine — shared across the whole test session for speed
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sqlite_engine():
    """Session-scoped SQLite in-memory engine with schema created once.

    StaticPool forces all sessions/connections to share a single underlying
    connection, which is required for SQLite :memory: databases — without it
    each new connection gets its own empty database.
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Function-scoped session that rolls back after each test."""
    with Session(sqlite_engine) as session:
        yield session
        session.rollback()


# ---------------------------------------------------------------------------
# Fresh SQLite engine (for tests that need a clean schema)
# ---------------------------------------------------------------------------

@pytest.fixture
def fresh_engine():
    """New empty SQLite engine per test — tables not yet created.

    Also uses StaticPool so that Base.metadata.create_all() and subsequent
    Session() calls all see the same in-memory database.
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Auth tokens
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def admin_token():
    return create_token("testadmin", role="admin")


@pytest.fixture(scope="session")
def lehrer_token():
    return create_token("testlehrer", role="lehrer")


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def client(sqlite_engine):
    """
    TestClient with:
    - get_db → SQLite session
    - get_current_user / get_current_admin → bypassed (returns "testadmin")
    - lifespan calls to PostgreSQL → mocked
    """
    def _override_get_db():
        with Session(sqlite_engine) as session:
            yield session

    def _override_user():
        return "testadmin"

    with (
        patch("auth_pure._ensure_table", return_value=None),
        patch("migrations.run_migrations_all_report_dbs", return_value=None),
    ):
        from main import app
        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = _override_user
        app.dependency_overrides[get_current_admin] = _override_user

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

        app.dependency_overrides.clear()
